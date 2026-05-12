from sentence_transformers import SentenceTransformer
import json

INPUT_FILE = "processed_esg_chunks.jsonl"
OUTPUT_FILE = "embedded_esg_chunks.jsonl"

model = SentenceTransformer("BAAI/bge-m3")

def embed(text):
    return model.encode(text).tolist()


def run():
    records = []

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            records.append(data)

    if not records:
        print("입력 데이터가 없습니다: processed_esg_chunks.jsonl")
        return

    chunks = [record["chunk"] for record in records]
    vectors = model.encode(chunks).tolist()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for record, vector in zip(records, vectors):
            output_record = {
                **record,
                "embedding": vector
            }
            out_f.write(json.dumps(output_record, ensure_ascii=False) + "\n")

    print(f"임베딩 완료: {len(records)}개 레코드 저장 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    run()