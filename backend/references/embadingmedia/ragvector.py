import psycopg
import logging
from langchain_ollama import ChatOllama
from sentence_transformers import SentenceTransformer
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. 로깅 설정 (수업 때 쓰시던 스타일)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================================================
# 💡 [핵심] settings 없이 로컬 Ollama 환경 직접 변수 선언
# ==========================================================================
OLLAMA_BASE_URL = "http://localhost:11434"  # 로컬 Ollama 기본 포트 주소
OLLAMA_MODEL_NAME = "gemma4:latest"        

# 2. ChatOllama 직접 초기화 (settings 의존성 제거)
llm = ChatOllama(
    model=OLLAMA_MODEL_NAME,
    base_url=OLLAMA_BASE_URL,
    temperature=0.1  # SR 보고서의 객관성을 위해 낮게 세팅
)

# 3. 768차원 KR-SBERT 임베딩 모델 로드 (가상환경 내 캐시 저장)
sbertModel = SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS", cache_folder="./model_cache")


# 🛠️ 4. pgvector 기반 SR 지식 창고 검색 함수
def searchSrKnowledge(query: str) -> str:
    """우리가 구축한 pgvector 데이터베이스에서 실시간으로 가장 유사도가 높은 뉴스 청크 3개를 검색합니다."""
    logger.info(f"--- 📥 [SR pgvector Search] '{query}' 관련 공시 데이터 추출 중 ---")
    
    # 사용자 질문을 768차원 벡터 배열로 변환
    queryVector = sbertModel.encode(query).tolist()
    
    # 로컬 PostgreSQL 컨테이너 연결 주소 (기본 계정 및 패스워드 1234)
    dbUrl = "postgresql://postgres:1234@localhost:5432/postgres"
    
    try:
        conn = psycopg.connect(dbUrl)
        cursor = conn.cursor()
        
        # 코사인 거리(<=>) 연산으로청크 추출
        searchQuery = """
            SELECT chunk, sub_issue_name, best_similarity_score
            FROM esg_chunks
            ORDER BY chunk_embedding <=> %s::vector
        """
        cursor.execute(searchQuery, (queryVector,))
        rows = cursor.fetchall()
        
        contextPieces = []
        for idx, row in enumerate(rows):
            chunkText, subIssueName, score = row
            # SR 보고서 매핑의 근거가 되는 온톨로지 카테고리명을 태깅
            contextPieces.append(f"※ [공시 기준 영역: {subIssueName}] {chunkText}")
            
        cursor.close()
        conn.close()
        
        return "\n\n".join(contextPieces)
        
    except Exception as e:
        logger.error(f"지속가능경영 공시 데이터 조회 실패: {e}")
        return "관련 SR 공시 지식을 DB에서 찾을 수 없습니다."


#  5. 실전 지속가능경영보고서(SR) 생성 함수
def generateSrReport(srSectionTopic: str):
    # Step A: pgvector 창고에서 3,048개 데이터 기반 실전 팩트 컨텍스트 추출
    retrievedContext = searchSrKnowledge(srSectionTopic)
    
    # Step B: 글로벌 공시 규격(GRI 등) 서술 유도를 위한 전문 프롬프트 구성
    srPrompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 글로벌 ESG 공시 표준(GRI, ESRS, ISSB)에 정통한 지속가능경영보고서(SR) 전문 심사관이자 작성 에이전트입니다.\n"
            "반드시 아래 제공된 [실제 ESG 공시 및 뉴스 컨텍스트]만을 바탕으로 사용자의 요구사항에 맞는 지속가능경영보고서 서술 형식을 작성하세요.\n"
            "주어진 컨텍스트 외에 근거 없는 수치나 가짜 정보를 절대 지어내지 마십시오(환각 금지).\n\n"
            "[실제 ESG 공시 및 뉴스 컨텍스트]\n"
            "{context}\n\n"
            "[보고서 작성 원칙]\n"
            "1. 해당 ESG 리스크가 기업 경영에 미치는 영향(Impact)과 위험 요소를 객관적으로 서술하십시오.\n"
            "2. 제공된 컨텍스트의 '공시 기준 영역' 구조를 반영하여 보고서 문단을 구성하십시오.\n"
            "3. 격식 있고 딱딱한 공시용 전문 비즈니스 톤앤매너(~함, ~임, ~구축함 등 명사형 종결 또는 격식체)를 유지하십시오."
        )),
        ("human", "다음 주제에 대한 지속가능경영보고서(SR) 공시 문단을 작성해 줘: {question}")
    ])
    
    # Step C: LangChain 파이프라인 구조 연결 (수업 때 쓰시던 체인 구조)
    chain = srPrompt | llm | StrOutputParser()
    
    logger.info("🤖 Ollama가 공시 기준에 의거하여 SR 보고서 초안을 작성 중입니다...")
    srResult = chain.invoke({
        "context": retrievedContext,
        "question": srSectionTopic
    })
    
    print("\n================📋 생성된 지속가능경영보고서(SR) 초안 ================")
    print(srResult)
    print("====================================================================")
    return srResult


if __name__ == "__main__":
    # 실행 테스트
    topic = """
        [공시 항목]: 용수 사용 및 취수 관리 현황 (E3-03)
        [실측 데이터]: {
            "metric_id": "E3-03__A0178",
            "company_scope_unit": "A 자회사",
            "site": "용인 제1사업장",
            "water_use_type": "생산공정 냉각수",
            "value_numeric": 45000,
            "unit": "m3",
            "year": "2025년"
        }
        위에 제공된 실측 데이터를 바탕으로 글로벌 ESG 공시 표준 규격에 맞는 지속가능경영보고서를 작성해줘.
        """
    generateSrReport(topic)