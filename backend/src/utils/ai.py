import re
import json
import psycopg

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import SentenceTransformer
from pgvector.psycopg import register_vector

from src.utils.db import findAll, save, addKey, saveMany
from src.utils.settings import settings


# ==================================================
# 상수
# ==================================================

REPORT_TEMPLATES = [
    "{E1-05__QL0001} 기준연도는 {E1-05__QL0002}이며 기준연도 연결 Scope 1·2 배출량은 {E1-05__G0003}이다. {E1-05__QL0004} 보고연도 연결 Scope 1·2 배출량은 {E1-06__G0003}, 전년 대비 감축량은 {E1-06__G0004}, 감축률은 {E1-06__G0005}이다. 재생에너지 전환율은 {E1-07__G0003}이며, {E1-05__QL0005}",
    "{S6-01__QL0001} {S6-02__QL0001} 연결 기준 공급업체 감사 수행률은 {S6-04__G0003}, 고위험 공급업체 수는 {S6-04__G0004}이다. 공급망 CAP 완료율은 {S6-05__G0003}이며, {S6-05__QL0001}",
    "{S3-01__QL0001} {S3-01__QL0002} 주요 프로그램은 {S3-01__QL0003}, {S3-01__QL0004}로 구성된다. 연결 임직원 수는 {S1-02__G0001}이며, 1인당 교육시간은 {S3-02__G0002}, 핵심직무 교육 달성률은 {S3-02__G0003}이다.",
    "{AP-E-06__QL0001} {AP-E-06__QL0002} 연결 친환경 제품 매출액은 {AP-E-06__G0001}이며, 연결 매출 대비 비중은 {AP-E-06__G0003}이다. 회피 배출량은 {AP-E-06__G0004}, 사회적 비용 절감 효과는 {AP-E-06__G0005}로 산정된다.",
    "{AP-S-01__QL0001} {AP-S-01__QL0002} {AP-S-01__QL0003} 연결 기준 필드액션 건수는 {AP-S-01__G0001}, 리콜 건수는 {AP-S-01__G0002}이며, 제품안전 CAP 완료율은 {AP-S-01__G0005}이다."
]

ISSUE_MAP = {
    1: {
        "subIssueId": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
        "subIssueName": "기후목표·전환계획"
    },
    2: {
        "subIssueId": "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP",
        "subIssueName": "공급망 감사·시정조치"
    },
    3: {
        "subIssueId": "S_TALENT__TRAINING_DEVELOPMENT",
        "subIssueName": "교육훈련·역량개발"
    },
    4: {
        "subIssueId": "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE",
        "subIssueName": "저탄소·친환경 제품"
    },
    5: {
        "subIssueId": "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY",
        "subIssueName": "소비자 건강·제품안전"
    }
}


# ==================================================
# 모델
# ==================================================

sbertModel = SentenceTransformer(
    "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
    cache_folder="./model_cache"
)

llm = ChatOllama(
    model="gemma4:e4b",
    base_url=f"http://{settings.ollama_url}:11434",
    temperature=0.1,
    num_predict=2048,
    repeat_penalty=1.1
)


# ==================================================
# 공통 함수
# ==================================================
def validateReport(text):
    """보고서 형태를 유지하면서 불필요한 제어 문자만 제거"""
    # 마크다운 기호(##, **)는 지우지 않습니다.
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text, flags=re.UNICODE)
    return text.strip()

# ==================================================
# DB 저장 핵심 함수
# ==================================================

def saveReportRun(
    companyId,
    reportingYear,
    subIssueId,
    sectionNo,
    llmModel,
    promptVersion,
    templateSnapshot,
    filledTemplate,
    reportText
):

    sql = """
        INSERT INTO ESG_REPORT_AI_RUN (
            materiality_run_id,
            company_id,
            reporting_year,
            llm_model,
            prompt_version
        )
        VALUES (?, ?, ?, ?, ?)
        """
    params = (
        None,
        companyId,
        reportingYear,
        llmModel,
        promptVersion
    )

    success, run_id = addKey(sql, params)

    return success, run_id

def saveSection(runId, sectionNo, subIssueId, template, filledText, reportText):

    sql = """
        INSERT INTO ESG_REPORT_AI_SECTION (
            ai_run_id,
            section_no,
            sub_issue_id,
            template_snapshot,
            filled_template,
            report_text
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """

    success, section_id = addKey(sql, (
        runId,
        sectionNo,
        subIssueId,
        template,
        filledText,
        reportText
    ))

    return success, section_id

    
def saveMetricTrace(sectionId, usedMetrics, factData):

    sql = """
        INSERT INTO ESG_REPORT_AI_METRIC_TRACE (
            section_id,
            atomic_metric_id,
            metric_source_version,
            value_numeric,
            value_text,
            unit
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """

    rows = []

    for m in usedMetrics:
        fact = factData.get(m)
        if not fact:
            continue

        rows.append((sectionId, m, "v1", fact.get("value"), None, fact.get("unit")))

    if rows:
        saveMany(sql, rows)
# ==================================================
# KPI 조회
# ==================================================

def getFactData(companyId, reportingYear):

    sql = f"""
        SELECT f.atomic_metric_id, f.value_numeric, f.value_text, f.unit, aes_d(c.company_name, '{settings.maria_db_key}') AS company_name
        FROM ESG_KPI_FACT f 
        JOIN COMPANY c 
        ON f.company_id=c.id 
        WHERE company_id = ? 
        AND f.reporting_year = ?
        AND c.delete_yn = 0
        AND f.delete_yn = 0
    """

    rows = findAll(sql, (companyId, reportingYear,))

    dataMap = {}
    companyName = "A_GROUP"

    for row in rows:
        if row["company_name"]:
            companyName = row["company_name"]
        value = (
            row["value_numeric"]
            if row["value_numeric"] is not None
            else row["value_text"]
        )
        dataMap[row["atomic_metric_id"]] = {
            "value": str(value or ""),
            "unit": str(row["unit"] or "")
        }
        dataMap["COMPANY_NAME"] = {
            "value": companyName,
            "unit": ""
        }
    rollupSql = """
        SELECT group_atomic_metric_id, value_numeric, value_text, unit 
        FROM ESG_GROUP_ROLLUP_RESULT 
        WHERE parent_company_id = ?
        AND reporting_year = ?
        AND delete_yn = 0
    """

    rollupRows = findAll(
        rollupSql,
        (companyId,reportingYear, )
    )

    for row in rollupRows:
        atomicId = row["group_atomic_metric_id"]

        if (
            atomicId not in dataMap
            or dataMap[atomicId]["value"] == ""
        ):
            value = (
                row["value_numeric"]
                if row["value_numeric"] is not None
                else row["value_text"]
            )

            dataMap[atomicId] = {
                "value": str(value or ""),
                "unit": str(row["unit"] or "")
            }
    return dataMap


# ==================================================
# 템플릿 치환
# ==================================================
def formatUnit(value, unit):
    if value is None or value == "":
        return "[데이터 미집계]"

    # 1) 숫자 변환 가능 여부 판단
    is_number = True
    try:
        num = float(value)
    except:
        is_number = False

    # 2) unit 없는 경우 → 텍스트 유지 (중요)
    if not unit:
        return str(value).strip()

    if not is_number:
        return str(value).strip()

    # 3) 숫자 + unit 처리
    if unit == "%":
        return f"{num:.2f}%"

    if unit == "KRW":
        return f"{num:,.0f} {unit}"

    if unit in ["MWh", "tCO2eq"]:
        return f"{num:,.2f} {unit}"

    if unit in ["개", "개사", "건", "명"]:
        return f"{num:,.0f} {unit}"

    if unit == "시간":
        return f"{num:,.1f} 시간"

    if unit == "시간/명":
        return f"{num:,.2f} 시간/명"

    return f"{num} {unit}"


def replaceTemplate(template, factData):
    usedMetrics = set()

    def replaceToken(match):
        key = match.group(1)
        usedMetrics.add(key)

        data = factData.get(key)
        if not data:
            return "[데이터 미집계]"

        value = data.get("value", "")
        unit = data.get("unit", "")

        return formatUnit(value, unit)

    companyName = factData.get("COMPANY_NAME", {}).get("value", "A_GROUP")

    filledText = re.sub(
        r"\{(.*?)\}",
        replaceToken,
        template
    ).replace("A_GROUP", companyName)

    return filledText, list(usedMetrics)


# ==================================================
# SR 검색
# ==================================================

def searchSrKnowledgeHybrid(issueName, subIssueId):
    queryText = f"{issueName} {subIssueId}"
    queryVector = (
        sbertModel
        .encode(queryText)
        .tolist()
    )

    conn = psycopg.connect(
        dbname=settings.pg_db_database,
        user=settings.pg_db_user,
        password=settings.pg_db_password,
        host=settings.pg_db_host,
        port=settings.pg_db_port
    )

    register_vector(conn)
    cur = conn.cursor()

    tagJson = json.dumps([{"subIssueId": subIssueId}])

    sql = """
        SELECT year, page, text, mapped_issues,
               (1 - (embedding <=> %s::vector)) as score
        FROM ai_sr
        WHERE mapped_issues @> %s::jsonb
        ORDER BY score DESC
    """

    cur.execute(sql, (queryVector, tagJson))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# ==================================================
# SR 압축
# ==================================================

def compressSrContext(rows):

    if not rows:
        return "참고 없음"

    years = set()
    themes = []

    for row in rows[:5]:
        years.add(str(row[0]))
        text = row[2]
        if len(text) > 80:
            text = text[:80]
        themes.append(text)

    return (
        "[STYLE INSIGHT]\n"
        f"- 참고 연도: {', '.join(sorted(years))}\n"
        "- 서술 패턴: 수치 기반 설명형 문장\n"
        "- 핵심 표현: 감축, 증가, 확대, 전환, 개선 중심\n"
        f"- 예시 키워드: {', '.join(themes[:3])}"
    )


# ==================================================
# 보고서 생성
# ==================================================

def generateIssueReport(
    companyId,
    reportingYear,
    subIssueId,
    sectionNo,
    template,
    filledText,
    compressedContext,
    factData,
    usedMetrics 
):

    systemInstruction = """
        당신은 전문 ESG 보고서 작성 컨설턴트입니다.

        [필수 출력 규칙]
        1. 반드시 존댓말(합니다/입니다)로 작성하십시오.
        2. 문단은 반드시 "설명형 1문단 + 수치 설명 + 해석" 구조를 따르십시오.
        3. 동일 수치는 반드시 2회 이상 자연스럽게 반복하십시오.
        4. 문장은 짧게 끊되 리듬감 있는 서술형으로 작성하십시오.
        5. 절대 bullet, 제목, 목록 형태를 사용하지 마십시오.
        6. 참고 데이터 외의 가정 수치/사례를 추가하지 마십시오.
        7. [데이터 미집계]는 반드시 그대로 유지하십시오.
        8. SR은 문체 참고용이며 문장 구조를 모방하지 마십시오.
        9. 최종 출은 보고서 본문만 작성하십시오 (설명/메타 금지).
        """

    prompt = ChatPromptTemplate.from_messages([
            ("system", systemInstruction),

            ("human",
        """
        [DATA - FACTS]
        {filledText}

        [STYLE GUIDE]
        다음은 보고서 작성 스타일 규칙이다:
        - 수치 기반 설명 중심
        - 수치는 최소 2회 이상 자연스럽게 반복
        - 간결한 설명형 문장

        [REFERENCE - INSIGHTS]
        {compressed_context}

        [TASK]
        위 DATA를 기반으로 ESG 보고서 문단 1개를 작성하라.

        [OUTPUT STRUCTURE]
        - 1문단 완성형
        - 첫 문장: 전체 개요
        - 중간: 핵심 수치 설명
        - 마지막: 의미/성과 해석
        - 반드시 존댓말 유지
        """
            )
        ])

    result = (
        prompt
        | llm
        | StrOutputParser()
    ).invoke({
        "filledText": filledText,
        "compressed_context": compressedContext
    })

    result = validateReport(result)
    
    # ==================================================
    # 1. RUN 저장
    # ==================================================
    success, run_id = saveReportRun(
        companyId,
        reportingYear,
        subIssueId,
        sectionNo,
        "gemma4:e4b",
        "v1",
        template,
        filledText,
        result
    )

    if not success:
        raise Exception("RUN insert 실패")
    # ==================================================
    # 2. SECTION 저장
    # ==================================================
    success, section_id = saveSection(
        run_id,
        sectionNo,
        subIssueId,
        template,
        filledText,
        result
    )

    if not success:
        raise Exception("SECTION insert 실패")
    # ==================================================
    # 3. METRIC TRACE 저장
    # ==================================================
    saveMetricTrace(
        section_id,
        usedMetrics,
        factData
    )

    return {"report": result, "run_id": run_id  }