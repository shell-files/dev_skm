from sentence_transformers import SentenceTransformer
import json
import os
import numpy as np

from subissue_master import SUBISSUE_MASTER

INPUT_FILE = "embedded_esg_chunks.jsonl"
OUTPUT_FILE = "similarity_results.jsonl"
SUBISSUE_VECTOR_FILE = "subissue_vectors.jsonl"
MODEL_NAME = "BAAI/bge-m3"

model = SentenceTransformer(MODEL_NAME)


def build_subissue_prototypes():
    prototypes = []

    for sub_issue_id, metadata in SUBISSUE_MASTER.items():
        title = metadata.get("sub_issue_name", sub_issue_id)
        description = metadata.get("description", "")
        issue_group = metadata.get("issue_group_code")
        text = f"{title}. {description}" if description else title

        prototypes.append({
            "sub_issue_id": sub_issue_id,
            "issue_group_code": issue_group,
            "sub_issue_name": title,
            "text": text,
        })

    return prototypes


def save_subissue_vectors(prototypes, embeddings):
    with open(SUBISSUE_VECTOR_FILE, "w", encoding="utf-8") as f:
        for proto, vector in zip(prototypes, embeddings):
            record = {
                "sub_issue_id": proto["sub_issue_id"],
                "issue_group_code": proto["issue_group_code"],
                "sub_issue_name": proto["sub_issue_name"],
                "text": proto["text"],
                "embedding": vector.tolist(),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_subissue_vectors():
    if not os.path.exists(SUBISSUE_VECTOR_FILE):
        return None

    records = []
    with open(SUBISSUE_VECTOR_FILE, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    return records


def get_subissue_vectors(force_rebuild=False):
    if not force_rebuild:
        records = load_subissue_vectors()
        if records:
            return records

    prototypes = build_subissue_prototypes()
    texts = [proto["text"] for proto in prototypes]
    embeddings = model.encode(texts)

    save_subissue_vectors(prototypes, embeddings)

    vectors = []
    for proto, vector in zip(prototypes, embeddings):
        vectors.append({
            **proto,
            "embedding": vector.tolist(),
        })

    return vectors


def cosine_similarity(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def find_top_matches(chunk_embedding, subissue_vectors, top_k=3):
    chunk_vector = np.asarray(chunk_embedding, dtype=np.float32)
    scores = []

    for sub in subissue_vectors:
        score = cosine_similarity(chunk_vector, sub["embedding"])
        scores.append({
            "sub_issue_id": sub["sub_issue_id"],
            "issue_group_code": sub["issue_group_code"],
            "sub_issue_name": sub["sub_issue_name"],
            "score": score,
        })

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:top_k]


def run():
    subissue_vectors = get_subissue_vectors()
    if not subissue_vectors:
        print("서브이슈 임베딩을 생성할 수 없습니다.")
        return

    records = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    if not records:
        print("입력 데이터가 없습니다: embedded_esg_chunks.jsonl")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for record in records:
            chunk_embedding = record.get("embedding")
            if not chunk_embedding:
                continue

            top_matches = find_top_matches(chunk_embedding, subissue_vectors, top_k=3)
            best_match = top_matches[0] if top_matches else None

            output_record = {
                **record,
                "issue_similarity_matches": top_matches,
                "best_sub_issue_id": best_match["sub_issue_id"] if best_match else None,
                "best_sub_issue_name": best_match["sub_issue_name"] if best_match else None,
                "best_issue_group_code": best_match["issue_group_code"] if best_match else None,
                "best_similarity_score": best_match["score"] if best_match else None,
            }
            out_f.write(json.dumps(output_record, ensure_ascii=False) + "\n")

    print(f"유사도 계산 완료: {len(records)}개 레코드 저장 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
