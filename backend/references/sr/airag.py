import mariadb
import sys
import psycopg
import re
import logging
import time
import json

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import SentenceTransformer
from settings import settings

from pgvector.psycopg import register_vector

# ==================================================
# 설정 및 로깅
# ==================================================
logging.basicConfig(level=logging.INFO, format='%(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

llm = ChatOllama(
    model="gemma4:e4b",
    base_url="http://localhost:11434",
    temperature=0.1,
    num_predict=2048,
    repeat_penalty=1.1
)

sbertModel = SentenceTransformer(
    "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
    cache_folder="./model_cache"
)

issueMap = {
    0: "기후목표·전환계획",
    1: "공급망 감사·시정조치",
    2: "교육훈련·역량개발",
    3: "저탄소·친환경 제품", 
    4: "소비자 건강·제품안전"
}

# ==================================================
# 데이터베이스 함수들
# ==================================================

def getFactData(companyId):
    try:
        conn = mariadb.connect(
            user=settings.mysql_user, password=settings.mysql_password,
            host=settings.mysql_host, port=settings.mysql_port,
            database=settings.mysql_database
        )
    except mariadb.Error as e:
        print(f"MariaDB 연결 실패: {e}")
        sys.exit(1)

    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT f.atomic_metric_id, f.value_numeric, f.value_text, f.unit, aes_d(c.company_name, '{settings.db_decryption_key}')
        FROM ESG_KPI_FACT f JOIN COMPANY c ON f.company_id=c.id
        WHERE f.company_id=%s AND f.delete_yn=0
    """, (companyId,))

    dataMap = {}
    companyName = "A_GROUP"
    
    for atomicId, vNum, vText, unit, compName in cur:
        if compName: companyName = compName
        dataMap[atomicId] = {
            "value": str(vNum if vNum is not None else (vText or "")),
            "unit": str(unit if unit else "")
        }
    
    cur.execute(f"""
            SELECT group_atomic_metric_id, value_numeric, value_text, unit
            FROM ESG_GROUP_ROLLUP_RESULT
            WHERE parent_company_id=%s AND delete_yn=0
        """, (companyId,))
        
    for atomicId, vNum, vText, unit in cur:
        if atomicId not in dataMap or (dataMap[atomicId]["value"] == ""):
            dataMap[atomicId] = {
                "value": str(vNum if vNum is not None else (vText or "")),
                "unit": str(unit if unit else "")
            }
            
    cur.close(); conn.close()
    
    dataMap["COMPANY_NAME"] = {"value": companyName, "unit": ""}
    return dataMap

def searchSrKnowledgeHybrid(subIssueIds, queryVector):
    conn = psycopg.connect(
        dbname=settings.pg_db_database,
        user=settings.pg_db_user,
        password=settings.pg_db_password,
        host=settings.pg_db_host,
        port=settings.pg_db_port
    )
    register_vector(conn)
    cur = conn.cursor()

    sql = """
    SELECT year, page, text, (1-(embedding <=> %s::vector)) as score
    FROM ai_sr 
    WHERE mapped_issues @> %s::jsonb
    ORDER BY score DESC
    """
    
    # 1. 인자로 받은 subIssueIds 리스트를 JSON 배열 형태로 변환
    tagJson = json.dumps([{"subIssueId": sid} for sid in subIssueIds])
    
    # 2. queryVector와 tag_json을 쿼리에 전달
    cur.execute(sql, (queryVector, tagJson))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    context = "\n\n".join([f"[참고({r[0]}년, {r[1]}페이지)]: {r[2]}" for r in rows]) if rows else "참고할 문체 데이터 없음"
    return context, rows

# ==================================================
# 보고서 생성 함수
# ==================================================

def generateFullReport(companyId, templates):
    startTime = time.time()
    factData = getFactData(companyId) 
    companyName = factData.get("COMPANY_NAME", {}).get("value", "A_GROUP")
    
    reportOutput = []
    debugInfo = []

    def replaceToken(match):
        key = match.group(1)
        data = factData.get(key)
        
        if not data or data.get("value") == "": 
            return "[데이터 미집계]"
        
        val = data.get("value", "")
        unit = data.get("unit", "")
        
        try:
            num = float(val)
            if num.is_integer():
                formattedVal = f"{int(num):,}"
            else:
                formattedVal = f"{num:,.2f}"
            return f"{formattedVal} {unit}".strip()
        except (ValueError, TypeError):
            return f"{val} {unit}".strip()

    systemInstruction = """
        당신은 전문 ESG 보고서 작성 컨설턴트입니다.
        1. [실측 데이터]에 [데이터 미집계]라고 표시된 항목은 무조건 "[데이터 미집계]"라고만 표기하십시오. 
        절대 미집계 이유를 서술하거나 미집계로 인한 한계를 설명하는 잡담을 포함하지 마십시오.
        2. [문체 참고 예시]의 수치나 기업명을 절대 복사하지 마십시오.
        3. 사고 과정 없이 최종 보고서 내용만 출력하십시오.
        4. 수치는 최소 2회 이상 언급하고, 250~400자 이내의 문단 형태로 작성하십시오.
        5. 영어로 작성할 보고서는 무조건 한국어로 작성하십시오.
        """

    for idx, template in enumerate(templates):
        filledText = re.sub(r"\{(.*?)\}", replaceToken, template).replace("A_GROUP", companyName)
        issueTag = issueMap.get(idx, "기타")
        context, rows = searchSrKnowledgeHybrid(issueTag, sbertModel.encode(issueTag).tolist())

        prompt = ChatPromptTemplate.from_messages([
            ("system", systemInstruction),
            ("human", "[실측 데이터]\n{filledText}\n\n[문체 참고 예시]\n{context}\n\n위 데이터를 기반으로 ESG 보고서 섹션을 작성하라.")
        ])
        
        result = (prompt | llm | StrOutputParser()).invoke({"filledText": filledText, "context": context})
        reportOutput.append(result)
        debugInfo.append({"이슈": issueTag, "입력": filledText, "출처": [{"title": r[1], "score": round(r[3], 3)} for r in rows]})

    print(f"보고서 생성 완료! 소요 시간: {time.time() - startTime:.2f}초")
    return reportOutput, debugInfo

# ==================================================
# 템플릿 검증 함수
# ==================================================

def verifyTemplateData(companyId, templates):
    factData = getFactData(companyId)
    
    print("\n" + "="*50)
    print("템플릿 데이터 치환 검증")
    print("="*50)
    
    for i, template in enumerate(templates):
        print(f"\n[템플릿 {i+1} 검증]")
        
        def replaceHelper(match):
            key = match.group(1)
            data = factData.get(key)
            if not data or not isinstance(data, dict) or data.get("value") == "":
                return "[데이터 미집계]"
            
            val = data.get("value", "")
            unit = data.get("unit", "")
            
            try:
                num = float(val)
                if num.is_integer():
                    formattedVal = f"{int(num):,}"
                else:
                    formattedVal = f"{num:,.2f}"
                return f"{formattedVal} {unit}".strip()
            except (ValueError, TypeError):
                return f"{val} {unit}".strip()

        filled = re.sub(r"\{(.*?)\}", replaceHelper, template)
        print(f"  - 결과 문장: {filled}")

# ==================================================
# 실행부
# ==================================================

if __name__ == "__main__":
    templates = [
        "{G0-01__QL0001} {G0-01__QL0002} 보고기간은 {G0-05__QL0001}이며, 연결 공시 범위는 {G0-05__QL0002}이다. 연결 매출액은 {G0-02__G0001}, 연결 사업장 수는 {G0-03__G0001}이다. 가치사슬은 {G0-04__QL0001}, {G0-04__QL0002}, {G0-04__QL0003}로 설명한다.",
        "{E1-05__QL0001} 기준연도는 {E1-05__QL0002}이며 기준연도 연결 Scope 1·2 배출량은 {E1-05__G0003}이다. {E1-05__QL0004} 보고연도 연결 Scope 1·2 배출량은 {E1-06__G0003}, 전년 대비 감축량은 {E1-06__G0004}, 감축률은 {E1-06__G0005}이다. 재생에너지 전환율은 {E1-07__G0003}이며, {E1-05__QL0005}",
        "{S6-01__QL0001} {S6-02__QL0001} 연결 기준 공급업체 감사 수행률은 {S6-04__G0003}, 고위험 공급업체 수는 {S6-04__G0004}이다. 공급망 CAP 완료율은 {S6-05__G0003}이며, {S6-05__QL0001}",
        "{S3-01__QL0001} {S3-01__QL0002} 주요 프로그램은 {S3-01__QL0003}, {S3-01__QL0004}로 구성된다. 연결 임직원 수는 {S1-02__G0001}이며, 1인당 교육시간은 {S3-02__G0002}, 핵심직무 교육 달성률은 {S3-02__G0003}이다.",
        "{AP-E-06__QL0001} {AP-E-06__QL0002} 연결 친환경 제품 매출액은 {AP-E-06__G0001}이며, 연결 매출 대비 비중은 {AP-E-06__G0003}이다. 회피 배출량은 {AP-E-06__G0004}, 사회적 비용 절감 효과는 {AP-E-06__G0005}로 산정된다.",
        "{AP-S-01__QL0001} {AP-S-01__QL0002} {AP-S-01__QL0003} 연결 기준 필드액션 건수는 {AP-S-01__G0001}, 리콜 건수는 {AP-S-01__G0002}이며, 제품안전 CAP 완료율은 {AP-S-01__G0005}이다."
    ]
    
    print(f"\n[시스템 가동] 회사 ID: 6 분석 시작...")
    
    # 1. 데이터 검증 (시간 측정)
    aStartTotal = time.time()
    verifyTemplateData(6, templates)
    aTotalTime = time.time() - aStartTotal
    print(f"검증 소요 시간: {aTotalTime:.2f}초")
    # 2. 보고서 생성 및 시간 측정
    bStartTotal = time.time()
    report, debug = generateFullReport(6, templates)
    bTotalTime = time.time() - bStartTotal
    print(f"생성 소요 시간: {bTotalTime:.2f}초")
    # 3. 성능 요약 및 데이터 상태 확인
    print("\n" + "="*50)
    print(f"총 소요 시간: {aTotalTime + bTotalTime:.2f}초")
    print(f"분석 결과 요약")
    print("="*50)
    print(f"생성된 섹션 수: {len(report)}개")
    print(f"데이터 매칭 상태: {'양호' if '[데이터 미집계]' not in str(report) else '일부 데이터 누락됨'}")
    print("="*50)

    print("\n--- [최종 보고서] ---\n")
    print("\n\n".join(report))