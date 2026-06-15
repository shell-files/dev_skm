from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
from jobs.core.paths import (
    processedJsonl,
    embeddedJsonl
)

INPUT_FILE = processedJsonl
OUTPUT_FILE = Path(embeddedJsonl).parent / "embeddedEsgChunks_sbert.jsonl"

HF_TOKEN = ''
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
CACHE_DIR = Path(__file__).resolve().parent / "model_cache"


def step05():
    print(f"[{MODEL_NAME}] 모델을 로드 중입니다... (캐시 폴더: {CACHE_DIR})")
    model = SentenceTransformer(MODEL_NAME, cache_folder=str(CACHE_DIR))
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
