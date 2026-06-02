# ingestToPgvector.py
import json
import psycopg
from pgvector.psycopg import register_vector

def ingestToPgvector():
    # 1. PostgreSQL DB 연결 정보 설정 (도커 또는 클라우드 환경에 맞게 수정)
    dbUrl = "postgresql://SKM:1234@192.168.0.201:5432/ESG"
    
    print("🚀 pgvector 데이터베이스에 연결하는 중...")
    conn = psycopg.connect(dbUrl)
    cursor = conn.cursor()

    print("🛠️ pgvector 확장 모듈 및 esg_chunks 테이블 상태 점검 중...")
    
    # 1. pgvector 확장 기능 활성화 (반드시 필요)
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # 2. esg_chunks 테이블이 없다면 생성 (768차원 SBERT 규격 세팅)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS esg_chunks (
            id SERIAL PRIMARY KEY,
            source VARCHAR(50),
            title TEXT,
            chunk TEXT,
            issue_group VARCHAR(100),
            issue_group_domain VARCHAR(10),
            sub_issue_id VARCHAR(100),
            sub_issue_name VARCHAR(100),
            best_sub_issue_id VARCHAR(100),
            chunk_embedding vector(768), -- SBERT 768차원 공간 할당
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    print("✅ 데이터베이스 스키마 준비 완료!")
    # ==========================================================================
    
    # 💡 필수: 현재 세션 커서에 pgvector 처리기 확장 등록
    register_vector(conn)
    
    # 2. 파이프라인 최종 출력 파일 경로 바인딩
    # (유사도 매칭 점수와 최고 매칭 subIssueId가 결합된 최종 결과 파일)
    similarityFile = "./output/embeddings/similaritySbert.jsonl"
    
    print("📥 3개년치 ESG 분석 완료 데이터를 pgvector에 적재하기 위해 읽는 중...")
    
    insertQuery = """
        INSERT INTO esg_chunks (
            source, title, chunk, issue_group, issue_group_domain, 
            sub_issue_id, sub_issue_name, best_sub_issue_id, chunk_embedding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    batchRecords = []
    batchSize = 200  # 3개년치 대용량 데이터이므로 속도 향상을 위해 배치 사이즈를 200으로 상향
    totalCount = 0

    with open(similarityFile, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            
            record = json.loads(line)
            
            # --- 💡 필터링 로직 추가 시작 ---
            # 'chunk'와 'title'에서 검색할 키워드들
            keywords = ["현대모비스", "자동차 부품", "자동차부품"]
            text_to_search = (record.get("chunk", "") + " " + record.get("title", "")).replace(" ", "")
            
            # 키워드 중 하나라도 포함되어 있는지 확인 (공백 제거 후 비교하면 정확도 향상)
            if not any(kw.replace(" ", "") in text_to_search for kw in keywords):
                continue  # 키워드가 없으면 다음 라인으로 패스
            # --- 💡 필터링 로직 추가 끝 ---
            
            # 💡 확인된 파일 구조 매핑: 'embedding' 키에서 768차원 어레이 추출
            chunkVector = record.get("embedding")
            if not chunkVector:
                continue
                
            # DB 스키마(Snake)와 매칭할 파라미터 튜플 생성 (데이터는 카멜 키에서 바인딩)
            recordData = (
                record.get("source", ""),
                record.get("title", ""),
                record.get("chunk", ""),
                record.get("issueGroup", "미분류"),
                record.get("issueGroupDomain", "Unknown"),
                record.get("subIssueId", ""),
                record.get("subIssueName", "미분류"),
                record.get("bestSubIssueId", ""),
                chunkVector  # list 구조가 pgvector에 의해 vector(768)로 변환됨
            )
            
            batchRecords.append(recordData)
            
            # 벌크 인서트를 통한 고속 커밋
            if len(batchRecords) >= batchSize:
                cursor.executemany(insertQuery, batchRecords)
                conn.commit()
                totalCount += len(batchRecords)
                print(f" [진행 상황] 현재 {totalCount}개 뉴스 청크 DB 적재 완료...")
                batchRecords = []

        # 잔여 레코드 처리
        if batchRecords:
            cursor.executemany(insertQuery, batchRecords)
            conn.commit()
            totalCount += len(batchRecords)

    cursor.close()
    conn.close()
    
    print(f"===============[ 적재 완료 ]===============")
    print(f"✅ 총 {totalCount}개의 3개년치 의미적 데이터셋이 pgvector에 안전하게 저장되었습니다.")

if __name__ == "__main__":
    ingestToPgvector()