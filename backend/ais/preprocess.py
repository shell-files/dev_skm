import json
import re
from datetime import datetime

from subissue_master import SUBISSUE_MASTER

INPUT_FILE = "esg_ai_training_dataset.jsonl"
OUTPUT_FILE = "processed_esg_chunks.jsonl"


# =========================
# 간단 chunk 분리
# =========================
def split_chunk(text, max_len=400):

    sentences = re.split(r'(?<=[.。])\s', text)

    chunks = []
    current = ""

    for s in sentences:

        if len(current) + len(s) < max_len:
            current += " " + s
        else:
            chunks.append(current.strip())
            current = s

    if current:
        chunks.append(current.strip())

    return chunks


# =========================
# 아주 간단 taxonomy rule (테스트용)
# =========================
def map_subissue(text):

    if "탄소" in text or "배출" in text:
        return "Climate", "Climate-02", "GHG 배출량·감축성과"

    if "에너지" in text:
        return "Energy", "Energy-01", "에너지 사용량·에너지원 믹스"

    if "재생" in text:
        return "Energy", "Energy-02", "재생에너지 전환"

    if "안전" in text:
        return "Safety", "Safety-02", "재해율·중대재해"

    return "Unknown", "Unknown", "Unknown"


# =========================
# main
# =========================
def process():

    results = []

    with open(INPUT_FILE, "r", encoding="utf-8") as f:

        for line in f:

            data = json.loads(line)

            chunks = split_chunk(data["paragraph"])

            for c in chunks:

                issue_group, sub_id, sub_name = map_subissue(c)
                metadata = SUBISSUE_MASTER.get(sub_id, {})

                results.append({
                    "source": data["source"],
                    "title": data["title"],
                    "chunk": c,
                    "issue_group": issue_group,
                    "issue_group_domain": metadata.get("esg_domain"),
                    "sub_issue_id": sub_id,
                    "sub_issue_name": metadata.get("sub_issue_name", sub_name),
                    "sub_issue_description": metadata.get("description"),
                    "base_metric_ids": metadata.get("base_metric_ids"),
                    "atomic_metric_ids": metadata.get("atomic_metric_ids"),
                })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"완료: {len(results)} chunks 생성")


if __name__ == "__main__":
    process()