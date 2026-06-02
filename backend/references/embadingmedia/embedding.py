from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
from core.paths import (
    processedJsonl,
    embeddedJsonl
)

INPUT_FILE = processedJsonl
# OUTPUT_FILE = embeddedJsonl
# model = SentenceTransformer("BAAI/bge-m3")
from settings import settings
from sentence_transformers import SentenceTransformer
OUTPUT_FILE = Path(embeddedJsonl).parent / "embeddedEsgChunks_sbert.jsonl"

HF_TOKEN = settings.hf_token
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
CACHE_DIR = Path(__file__).resolve().parent / "model_cache"

# 2. 모델 인스턴스 생성 (경로 정의가 모두 끝난 후 실행하여 에러 차단)
print(f"[{MODEL_NAME}] 모델을 로드 중입니다... (캐시 폴더: {CACHE_DIR})")
model = SentenceTransformer(MODEL_NAME, cache_folder=str(CACHE_DIR))

def embed(text):
    return model.encode(text).tolist()


def run():
    records = []

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            records.append(data)

    if not records:
        print("입력 데이터가 없습니다: processedEsgChunks.jsonl")
        return

    chunks = [record["chunk"] for record in records]
    vectors = model.encode(chunks).tolist()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for record, vector in zip(records, vectors):
            outputRecord = {
                **record,
                "embedding": vector
            }
            out_f.write(json.dumps(outputRecord, ensure_ascii=False) + "\n")

    print(f"임베딩 완료: {len(records)}개 레코드 저장 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    run()