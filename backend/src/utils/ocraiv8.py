from google import genai
from google.genai import types
import json
import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from src.utils.settings import settings
from src.models.model import ResponseModel
from src.models.dmaengine import LLMExtractorOutput, DMASignal, ImpactFactor, FinancialFactor
from src.utils.subissuemaster import subissueMaster

router = APIRouter()

print("Loading SentenceTransformer model...")
embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# ------------------------------------------------------------------
# [AI 에이전트 가이드]
# 이 파일은 DMA(이중중대성평가) v8.2 아키텍처의 핵심 엔진입니다.
# 핵심 컨셉: "LLM(인공지능)에게 점수 매기는 권한을 뺏고, 오직 '증거 수집'만 시킨다!"
# 인공지능은 글을 읽고 이해하는 데는 뛰어나지만, 정교한 수학적 채점(1~5점)은 일관성이 떨어집니다(환각 현상).
# 따라서 LLM은 "문서에서 어떤 이슈가 언급되었고, 근거 문장이 무엇인지"만 찾아오고,
# 최종 점수 계산은 파이썬 코드가 엄격한 수학 공식(Rule-based)으로 처리합니다.
# ------------------------------------------------------------------

# Gemini Client 설정 (구글의 AI 모델을 사용하기 위한 연결 고리)
client = genai.Client(api_key=settings.gemini_api_key)
modelName = settings.gemini_model

# 62개 서브이슈 캐싱 변수 (DB나 엑셀에서 읽어온 62개 표준 ESG 이슈 목록을 메모리에 저장해 둡니다)
_ISSUE_DICTIONARY_STR = ""
_ISSUE_DICTIONARY_LIST = []
_ISSUE_VECTORS = None
_ISSUE_KEYS = []

def load_issue_dictionary():
    """
    [기능] 62개의 표준 ESG 이슈(Dictionary)와 설명문(Sentence)을 읽어옵니다.
    [이유] LLM이 아무 단어나 막 만들어내는 것을 방지하기 위해 프롬프트에 주입하고,
          동시에 시맨틱 검색(임베딩)을 위한 기준 벡터 62개를 미리 만들어 두기 위함입니다.
    """
    global _ISSUE_DICTIONARY_STR, _ISSUE_DICTIONARY_LIST, _ISSUE_VECTORS, _ISSUE_KEYS
    # 이미 읽어온 적이 있다면 그대로 반환 (속도 최적화)
    if _ISSUE_DICTIONARY_STR and _ISSUE_VECTORS is not None:
        return _ISSUE_DICTIONARY_STR, _ISSUE_DICTIONARY_LIST
    
    try:
        _ISSUE_KEYS = list(subissueMaster.keys())
        issue_texts = []
        _ISSUE_DICTIONARY_LIST = []
        
        for key in _ISSUE_KEYS:
            meta = subissueMaster[key]
            # 설명문이 있으면 설명문 사용, 없으면 이름 사용
            # sentence: subissuemaster.py의 핵심 anchor (media pipeline과 동일)
            text = meta.get("sentence") or meta.get("subIssueSentence") or meta.get("subIssueNameKr")
            issue_texts.append(text)
            _ISSUE_DICTIONARY_LIST.append(meta.get("subIssueNameKr"))
            
        _ISSUE_DICTIONARY_STR = ", ".join(_ISSUE_DICTIONARY_LIST)
        
        # 62개 표준 이슈의 임베딩 벡터 사전 계산 (배치 인코딩)
        print("Pre-computing SubIssue master vectors...")
        _ISSUE_VECTORS = embedding_model.encode(issue_texts)
        
    except Exception as e:
        print("Failed to load issue dict:", e)
        _ISSUE_DICTIONARY_STR = "기후변화, 산업안전, 공급망 관리, 제품안전, 자원순환 등"
        _ISSUE_DICTIONARY_LIST = []
        
    return _ISSUE_DICTIONARY_STR, _ISSUE_DICTIONARY_LIST

# JSON 응답 정제용 함수 (LLM이 준 문자열을 파이썬에서 쓰기 좋게 딕셔너리로 바꿉니다)
def clean(responseText: str) -> list:
    if not responseText:
        return []
    try:
        data = json.loads(responseText.strip())
    except json.JSONDecodeError:
        cleanedStr = responseText.replace('\\n', '').replace('\\"', '"')
        data = json.loads(cleanedStr)
    return data

# 오류 방지를 위하여 Max 파일 수 제한 및 재시도 로직 설정
MAX_TASKS = 1
MAX_RETRIES = 3
RETRY_DELAY = 5  # 실패 시 5초 쉬고 다시 시도

def normalize_mapping_weights(raw_label, threshold=0.35, alpha=1.5, top_k=3):
    """
    [기능] LLM이 뽑아낸 원문 이슈(raw_label)를 딥러닝 임베딩(SentenceTransformer)으로 변환하여,
          62개 표준 설명문(Sentence) 벡터들과 코사인 유사도(Cosine Similarity)를 계산해 분배합니다.
    - threshold=0.35: 시맨틱 검색이므로 유사도가 35점 미만이면 의미가 다르다고 보고 버립니다.
    - top_k=3: 제일 의미상 비슷한 표준 단어를 최대 3개까지만 고릅니다.
    - normalize: 3개로 나눠줄 때, 합쳐서 100%(1.0)가 되도록 비율을 조정합니다.
    """
    if _ISSUE_VECTORS is None or not raw_label:
        return []

    # 1. 원문(raw_label)을 임베딩 벡터로 변환
    vec = embedding_model.encode([raw_label], show_progress_bar=False)[0]
    
    # 2. 62개 전체 표준 이슈와 코사인 유사도 일괄 계산
    sims = cosine_similarity([vec], _ISSUE_VECTORS)[0]

    scored = []
    # 3. 임계치(threshold)를 넘는 것만 필터링
    for idx, sim in enumerate(sims):
        if sim >= threshold:
            key = _ISSUE_KEYS[idx]
            term = subissueMaster[key]["subIssueNameKr"]
            # alpha(1.5)를 제곱하여 차이를 더 극대화 (비슷할수록 가중치를 훨씬 높게 줌)
            raw_weight = max(0, float(sim) - threshold) ** alpha
            scored.append({
                "term": term,
                "similarity": float(sim),
                "raw_weight": raw_weight,
                "key": key
            })

    # 4. 유사도가 높은 순서대로 정렬해서 상위 3개(top_k)만 남깁니다.
    scored = sorted(scored, key=lambda x: x["similarity"], reverse=True)[:top_k]
    total = sum(x["raw_weight"] for x in scored)

    if total <= 0:
        return []

    # 5. 각 항목의 가중치를 총합으로 나눠서 비율을 만듭니다 (예: 0.7, 0.2, 0.1)
    for item in scored:
        item["mapping_weight"] = float(item["raw_weight"] / total)
        item["similarity_rank"] = scored.index(item) + 1

    return scored

def get_baseline_factors(sub_issue_code: str):
    """
    [기능] 자동차부품 산업 기준 기본(Baseline) Factor를 제공합니다.
    LLM이 직접 Factor를 정확히 산출하기 어렵기 때문에, MVP 단계에서는 매핑된 sub_issue에 따라 기본 강도를 부여합니다.
    """
    scale, scope, likelihood, irremediability = 3, 3, 3, 3
    mag = 3
    
    if sub_issue_code in ["E_CLIMATE_TRANSITION_PLAN", "E_GHG_EMISSION"] or "CLIMATE" in sub_issue_code:
        scale, scope, likelihood = 4, 4, 4
        mag = 4
    elif "SUPPLY_CHAIN" in sub_issue_code:
        scale, scope = 4, 3
        mag = 4
    elif "PRODUCT_SAFETY" in sub_issue_code:
        scale, scope, irremediability = 4, 4, 4
        mag = 4
    elif "TRAINING" in sub_issue_code or "CAPABILITY" in sub_issue_code:
        scale, scope, likelihood, irremediability = 3, 3, 4, 1
        mag = 3
    elif "LOW_CARBON_PRODUCT" in sub_issue_code or "ECO_FRIENDLY_PRODUCT" in sub_issue_code:
        scale, scope, likelihood, irremediability = 4, 4, 4, 1
        mag = 4
        
    return scale, scope, likelihood, irremediability, mag



# ------------------------------------------------------------------
# 8단계 텍스트 분석 엔진 메인 함수 (v8.2 Rule-based Scorer 적용)
# ------------------------------------------------------------------
async def gemini(results: List[Dict[str, Any]], filePaths: List[str]) -> ResponseModel:
    
    # 62개 이슈 사전을 로드합니다.
    issue_dict_str, issue_dict_list = load_issue_dictionary()
    semaphore = asyncio.Semaphore(MAX_TASKS)
    
    # 개별 파일(PDF 등)을 하나씩 분석하는 함수입니다.
    async def oneGemini(result: Dict[str, Any], filePath: str) -> Dict[str, Any]:
        async with semaphore:
            uploadedFile = None
            fileName = result.get("file_name", "")
            companyName = result.get("company_name", "")
            type = result.get("type", "")
            source_step = result.get("source_step", "media_external")
            source_type = result.get("source_type", type)
            
            # --- Retry 로직 --- 
            # (AI 서버가 일시적으로 멈출 수 있으므로, 실패하면 3번까지 재시도합니다)
            for attempt in range(MAX_RETRIES):
                try:
                    # ==================================================
                    # Step 1. Retriever / Chunker (데이터 확보)
                    # ==================================================
                    # 파일을 구글 Gemini 서버로 안전하게 업로드합니다.
                    fileConfig = types.UploadFileConfig(mime_type="application/pdf")
                    with open(filePath, "rb") as f:
                        uploadedFile = client.files.upload(file=f, config=fileConfig)
    
                    maxAttempts = 120  # 3초 * 120 = 최대 360초 대기
                    attempts = 0
                    
                    # 파일 업로드 및 처리가 완료될 때까지 기다립니다.
                    while True:
                        uploadedFile = client.files.get(name=uploadedFile.name)
                        if uploadedFile.state == types.FileState.ACTIVE:
                            break
                        elif uploadedFile.state == types.FileState.FAILED:
                            raise Exception("파일 업로드에 실패했습니다.")
                        elif attempts >= maxAttempts:
                            raise Exception("구글 서버의 파일 가공 대기 시간이 초과되었습니다.")
                        await asyncio.sleep(3)
                        uploadedFile = client.files.get(name=uploadedFile.name)
                        attempts += 1
                
                    # ==================================================
                    # Step 2~4. LLM Extractor (추출기)
                    # ==================================================
                    # 프롬프트(명령어)의 핵심: "Do NOT score them from 1 to 5" (점수 매기지 마!)
                    # 대신 1. 원문 표현, 2. 표준 단어 후보, 3. 기회/리스크 여부(IRO), 4. 시기(단기/장기), 5. **증거 문장** 만 뽑아내라고 명령합니다.
                    extractor_prompt = f"""
                    Perform the role of a Double Materiality Assessment Extractor.
                    Analyze the provided document and extract key sustainability issues based ONLY on the provided Issue Dictionary.
                    
                    [Issue Dictionary]
                    {issue_dict_str}
                    
                    Do NOT score them from 1 to 5. Instead, strictly extract:
                    1. The raw issue labels as they appear in the text.
                    2. The most relevant candidate terms from the Issue Dictionary (up to 3).
                    3. IRO Hint (financial_risk, financial_opportunity, negative_impact, positive_impact, context).
                    4. Time Horizon Hint (short, mid, long).
                    5. Exact evidence spans from the document proving the issue.
                    """
                    
                    # LLMExtractorOutput 스키마에 맞춰 JSON 형태로 결과를 달라고 강제합니다.
                    extractor_config = types.GenerateContentConfig(
                        temperature=0.1, # 창의성은 끄고(0.1) 정확하게 답변하게 함
                        response_mime_type="application/json",
                        response_schema=LLMExtractorOutput,
                    )
                    extractor_res = client.models.generate_content(
                        model=settings.gemini_model,
                        contents=[uploadedFile, extractor_prompt],
                        config=extractor_config
                    )
                    
                    # 볼일 끝난 파일은 구글 서버에서 즉시 삭제하여 보안을 유지합니다.
                    if uploadedFile:
                        client.files.delete(name=uploadedFile.name)
                        uploadedFile = None
                    
                    # LLM이 뽑아준 결과물을 파이썬 객체로 변환합니다.
                    extractor_data = json.loads(extractor_res.text)
                    extracted_issues = extractor_data.get("extracted_issues", [])
                    
                    # ==================================================
                    # Step 5~8. Rule-based Scorer, Judge, Aggregator (규칙 기반 채점 및 심판)
                    # ==================================================
                    final_results = []
                    dma_details = [] # DB에 꼼꼼하게 남길 감사(Audit)용 상세 원장
                    
                    # 추출된 각각의 이슈에 대해 처리를 시작합니다.
                    for issue in extracted_issues:
                        raw_label = issue.get("raw_issue_label", "")
                        candidates = issue.get("candidate_dictionary_terms", [])
                        iro_hint = issue.get("iro_hint", "negative_impact")
                        time_horizon_hint = issue.get("time_horizon_hint", "short")
                        evidence_spans = issue.get("evidence_spans", [])
                        
                        judge_status = "pass"
                        confidence_score = 0.9
                        
                        # Step 7. Judge (심판 단계): 증거 문장이 없으면? 가짜(환각)일 확률이 높으므로 즉시 짤라버립니다(Reject).
                        if not evidence_spans or len(evidence_spans) == 0:
                            judge_status = "reject"
                            confidence_score = 0.0
                            continue # 다음 이슈로 넘어감
                            
                        # Step 5. AI Embedding Scorer (임베딩 유사도 기반 가중치 부여 및 최대 3곳 분배)
                        # LLM이 뽑은 raw_label 텍스트 자체를 딥러닝 임베딩(SentenceTransformer) 처리하여
                        # subissuemaster_v8의 62개 설명문(Sentence)과 코사인 유사도(Cosine Similarity)를 비교합니다.
                        # threshold를 0.35로 낮추어 의미론적 유사성(Semantic Similarity)을 더 잘 잡도록 변경했습니다.
                        mapped_terms = normalize_mapping_weights(raw_label, threshold=0.35, alpha=1.5, top_k=3)
                        
                        # 유사도 60점을 넘는 항목이 하나도 없다면 버립니다.
                        if not mapped_terms:
                            continue
                            
                        # 배분된 비율(mapping_weight)만큼 신뢰도를 분할하여 할당합니다.
                        for mapped in mapped_terms:
                            term = mapped["term"]
                            key = mapped["key"]
                            weight = mapped["mapping_weight"]
                            sim = mapped["similarity"]
                            
                            impact_factor = None
                            financial_factor = None
                            
                            scale, scope, likelihood, irremediability, mag = get_baseline_factors(key)
                            
                            # [핵심] 재무적 중대성(Financial)과 환경/사회적 중대성(Impact) 요소를 분리해서 저장합니다! (점수 계산은 안함)
                            if iro_hint in ["negative_impact", "positive_impact"]:
                                impact_factor = ImpactFactor(
                                    impactDirection="negative" if "negative" in iro_hint else "positive",
                                    actuality="actual",
                                    scale=scale, scope=scope, irremediability=irremediability, likelihood=likelihood,
                                    timeHorizon=time_horizon_hint,
                                    evidenceSpans=evidence_spans
                                )
                                
                            if iro_hint in ["financial_risk", "financial_opportunity"]:
                                financial_factor = FinancialFactor(
                                    financialIroType="risk" if "risk" in iro_hint else "opportunity",
                                    revenueMagnitude=mag, costMagnitude=mag, capexMagnitude=0,
                                    assetLiabilityMagnitude=0, financingMagnitude=0, legalRegulatoryMagnitude=0,
                                    likelihood=likelihood,
                                    timeHorizon=time_horizon_hint,
                                    evidenceSpans=evidence_spans
                                )
                                
                            # ------------------------------------------------------------------
                            # [상세 데이터 저장 (Audit 추적용 DMASignal)]
                            # 추출된 증거와 매핑 정보를 Rule Engine으로 넘길 준비를 합니다.
                            # ------------------------------------------------------------------
                            signal = DMASignal(
                                subIssueCode=key,
                                sourceStep=source_step,
                                sourceType=source_type,
                                impactFactor=impact_factor,
                                financialFactor=financial_factor,
                                impactScore05=None,  # Rule Engine이 나중에 계산
                                financialScore05=None, # Rule Engine이 나중에 계산
                                confidenceScore=confidence_score * weight,
                                rawIssueLabel=f"{raw_label} ({term})",
                                displaySubIssueName=term,
                                similarityScore=sim,
                                similarityRank=mapped.get("similarity_rank"),
                                mappingWeight=weight,
                                judgeStatus=judge_status,
                                evidenceSpans=evidence_spans
                            )
                            dma_details.append(signal)
                            
                            # ==================================================
                            # Step 8. Gateway 응답 준비 (프론트엔드로 보내줄 1차 결과 조립)
                            # ==================================================
                            # Rule Engine이 없더라도 파이프라인 진행을 위해 signal 데이터를 딕셔너리로 반환합니다.
                            sig_dict = signal.model_dump()
                            final_results.append(sig_dict)
                    
                    data = {"fileName": fileName, "companyName": companyName, "type": type, "result": final_results}
                    return data
                    
                except Exception as e:
                    # 에러 발생 시 로그를 찍고 다음 Retry로 넘어갑니다.
                    print(f'{fileName} (attempt {attempt+1}):', str(e))
                    if uploadedFile:
                        try:
                            client.files.delete(name=uploadedFile.name)
                        except Exception:
                            pass  
                    # 3번 다 실패하면 빈 결과를 내보냅니다.
                    if attempt == MAX_RETRIES - 1:
                        data = {"fileName": fileName, "companyName": companyName, "type": type, "result": []} 
                        return data
                    await asyncio.sleep(RETRY_DELAY)
        
    tasks = [oneGemini(results[i], filePaths[i]) for i in range(len(filePaths))]
    
    # 여러 파일을 동시에 병렬 처리(비동기)하여 속도를 높입니다.
    totalOutputs = await asyncio.gather(*tasks, return_exceptions=True)

    finalResults = []
    for res in totalOutputs:
        if isinstance(res, Exception):
            finalResults.append({
                "fileName": "", 
                "companyName": "SYSTEM",
                "type": "ERROR",
                "result": [],
                "status": f"CRITICAL_SYSTEM_ERROR: {str(res)}"
            })
        else:
            finalResults.append(res)
            
    return ResponseModel(True, "분석이 완료되었습니다.", finalResults)