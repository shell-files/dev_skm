import json
import psycopg2
from pgvector.psycopg2 import register_vector
from settings import settings

def upload_data_to_postgres(file_path):
    conn = psycopg2.connect(
        dbname=settings.pg_db_database,
        user=settings.pg_db_user,
        password=settings.pg_db_password,
        host=settings.pg_db_host,
        port=settings.pg_db_port
    )
    register_vector(conn)
    cur = conn.cursor()
    
    print(f"[{file_path}] 적재 시작...")
    
    # 테이블이 없으면 자동 생성
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_sr (
            id SERIAL PRIMARY KEY,
            year VARCHAR(4),
            page INT,
            text TEXT,
            mapped_issues JSONB,
            embedding VECTOR(768)
        );
    """)
    
    # 데이터 읽기 및 삽입
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            mapped_issues = json.dumps(data.get("mapped_issues", []), ensure_ascii=False)
            
            cur.execute("""
                INSERT INTO ai_sr (year, page, text, mapped_issues, embedding)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['year'], data['page'], data['text'], mapped_issues, data['embedding']))
            count += 1
            
    conn.commit()
    cur.close()
    conn.close()
    print(f"[{file_path}] 적재 완료 (총 {count}개 레코드).")

if __name__ == "__main__":
    upload_data_to_postgres("storage/embeddings/2023/2023Em.jsonl")
    upload_data_to_postgres("storage/embeddings/2024/2024Em.jsonl")
    upload_data_to_postgres("storage/embeddings/2025/2025Em.jsonl")