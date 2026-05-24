import json
import re
import os
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from subissuemaster import subissueMaster

# ==================================================
# 0. PATH CONFIG
# ==================================================
inputDir = Path("storage/ocr/chunks")
outputDir = Path("storage/embeddings")
outputDir.mkdir(parents=True, exist_ok=True)

# ==================================================
# 1. MODEL LOADING
# ==================================================
modelName = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
print(f"Loading Embedding Model: {modelName}...")
embeddingModel = SentenceTransformer(modelName)

# ==================================================
# 2. SUBISSUE MASTER VECTOR PRE-COMPUTATION
# ==================================================
sub_issue_ids = []
sub_issue_texts = []
sub_issue_meta = []

for sid, info in subissueMaster.items():
    # 시맨틱 매칭 품질을 높이기 위해 구체적인 설명문(Sentence)을 우선 활용
    text = info.get("subIssueSentence") or info.get("subIssueNameKr")
    sub_issue_ids.append(sid)
    sub_issue_texts.append(text)
    sub_issue_meta.append(info)

print("Pre-computing SubIssue master vectors...")
sub_issue_vectors = embeddingModel.encode(sub_issue_texts)

# ==================================================
# 3. OCR CLEANING PATTERNS
# ==================================================
headerPatterns = [
    r"Letter to Stakeholders",
    r"Corporate Overview",
    r"Environment",
    r"Social",
    r"Governance",
    r"Appendix",
    r"임직원\s*·\s*공급망\s*·\s*지역사회\s*·\s*고객"
]

def cleanLine(line: str) -> str:
    line = line.strip()
    if not line:
        return ""

    # 상단/하단 반복 헤더 제거
    for pattern in headerPatterns:
        if re.search(pattern, line, re.IGNORECASE):
            return ""

    # 페이지 번호 표시 라인 제거 (예: ## Page 61, ==Page 71==)
    if re.match(r"^(=|#)*\s*Page\s*\d+\s*(?:==|##)?", line, re.IGNORECASE):
        return ""

    return line

# ==================================================
# 4. PAGE SPLIT (안정형)
# ==================================================
def splitByPages(text: str):
    parts = re.split(r"(?:==|##)?\s*Page\s*(\d+)\s*(?:==|##)?", text)

    pages = []
    current_page = 0

    for part in parts:
        if not part:
            continue

        if part.isdigit():
            current_page = int(part)
            continue

        pages.append((current_page, part.strip()))

    return pages

# ==================================================
# 5. PARAGRAPH RESTORE (테이블 보존 로직 추가)
# ==================================================
def splitParagraphs(pageText: str):
    lines = pageText.split("\n")

    paras = []
    buf = []
    prev = ""

    for line in lines:
        c = cleanLine(line)
        if not c:
            continue

        # [개선] 마크다운 테이블 행(|)인 경우 문단 병합 루프에서 분리하여 격리 저장
        if c.startswith("|"):
            if buf:
                paras.append(" ".join(buf))
                buf = []
            paras.append(c) # 테이블 라인은 단독 문단으로 취급
            prev = c
            continue

        # 기존 이전 줄이 테이블(|)이었다면 현재 일반 문장과 묶이지 않도록 버퍼 비움
        if prev.startswith("|") and buf:
            paras.append(" ".join(buf))
            buf = []

        # 불렛 기호나 짧은 줄, 문장 종결 어미 기반 분할 여부 결정
        isBreak = (
            c.startswith(("•", "-", "*", "■", "①", "②", "③")) or
            (len(c) < 25 and buf) or
            re.search(r"(다|습니다|함|임|됨|음|요)\s*$", prev)
        )

        if buf and isBreak:
            paras.append(" ".join(buf))
            buf = [c]
        else:
            buf.append(c)

        prev = c

    if buf:
        paras.append(" ".join(buf))

    return [p for p in paras if len(p) > 5]

# ==================================================
# 6. CHUNK SPLIT (정규식 공백 조건 완화)
# ==================================================
def splitChunk(text: str, maxLen: int = 400):
    # [개선] 마침표 뒤에 공백이 없어도 정상적으로 split 되도록 후방탐색 패턴 수정
    sentences = re.split(r"(?<=[.!?。])", text)

    chunks = []
    buf = []
    size = 0

    for s in sentences:
        s_strip = s.strip()
        if not s_strip:
            continue

        buf.append(s_strip)
        size += len(s_strip)

        if size >= maxLen:
            chunks.append(" ".join(buf))
            buf = []
            size = 0

    if buf:
        chunks.append(" ".join(buf))

    return chunks

# ==================================================
# 7. SEMANTIC MATCH (SubIssue 매핑)
# ==================================================
def find_best_subissue(text: str, threshold=0.35):
    # 단건 인코딩 유지 (매핑 프로세스 전용)
    vec = embeddingModel.encode([text], show_progress_bar=False)[0]

    sims = cosine_similarity([vec], sub_issue_vectors)[0]
    idx = int(np.argmax(sims))
    score = sims[idx]

    # 임계치 미달 시 데이터 드롭 대신 'UNMAPPED' 태그 부여 (Silent Loss 차단)
    if score < threshold:
        return "UNMAPPED", "General", "General", "General"

    meta = sub_issue_meta[idx]

    return (
        sub_issue_ids[idx],
        meta["subIssueNameKr"],
        meta["issueGroupId"],
        meta["domain"]
    )

# ==================================================
# 8. EMBEDDING TEXT INJECTION
# ==================================================
def buildEmbeddingText(subId, chunk):
    if subId == "UNMAPPED":
        return chunk
        
    meta = subissueMaster.get(subId, {})
    return " ".join([
        meta.get("issueGroupNameKr", ""),
        meta.get("subIssueNameKr", ""),
        meta.get("subIssueSentence", ""),
        chunk
    ])

# ==================================================
# 9. PIPELINE CORE (속도 및 버그 해결 버전)
# ==================================================
def run():
    files = sorted(list(inputDir.glob("*.txt")))
    if not files:
        print(f"[경고] '{inputDir}' 경로에 txt 파일이 존재하지 않습니다.")
        return

    for file in files:
        print(f"\n Processing: {file.name}")

        with open(file, "r", encoding="utf-8") as f:
            text = f.read()

        pages = splitByPages(text)
        results = []
        embedding_payloads = [] # 배치를 위한 임베딩 입력 텍스트 저장 리스트

        for pageNum, pageText in pages:
            #  [치명적 에러 수정] 파일 전체 레벨 정제 로직 제거
            # pageText = cleanLine(pageText) <- 이 유실 유발 코드를 삭제했습니다.

            paragraphs = splitParagraphs(pageText)

            for pIdx, para in enumerate(paragraphs):
                chunks = splitChunk(para)

                for cIdx, chunk in enumerate(chunks):
                    # 서브이슈 매핑 검색 (Soft Mapping)
                    sid, name, gid, domain = find_best_subissue(chunk)
                    
                    # 벡터 가중치를 보정할 컨텍스트 텍스트 결합
                    embeddingText = buildEmbeddingText(sid, chunk)
                    embedding_payloads.append(embeddingText)

                    # 기본 구조 빌드 (임베딩 데이터는 배치 처리 후 수집)
                    results.append({
                        "sourceFile": file.name,
                        "pageNumber": pageNum,
                        "paragraphIndex": pIdx,
                        "chunkIndex": cIdx,
                        "chunk": chunk,
                        "domain": domain,
                        "issueGroupId": gid,
                        "subIssueId": sid,
                        "subIssueNameKr": name,
                        "embedding": None # 임시 공백 처리
                    })

        # ⚡ [성능 최적화] 모여진 청크 텍스트들을 배치로 한 번에 임베딩 인코딩
        if results:
            print(f"└  Extracting embeddings for {len(results)} chunks in batch...")
            embeddings = embeddingModel.encode(embedding_payloads, batch_size=32, show_progress_bar=False)
            
            # 생성된 임베딩 결과를 오브젝트에 매핑
            for i, emb in enumerate(embeddings):
                results[i]["embedding"] = emb.tolist()

        # 파일별 결과 내보내기 (.jsonl)
        outFile = outputDir / f"{file.stem}_embedded.jsonl"
        with open(outFile, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        print(f" Done: {file.name} → Created {len(results)} chunks")
# ==================================================
# 10. EXECUTE
# ==================================================
if __name__ == "__main__":
    run()