import json
import re
from datetime import datetime

from subissuemaster import subissueMaster

inputFile = "esgAiTrainingDataset.jsonl"
outputFile = "processedEsgChunks.jsonl"


# =========================
# 간단 chunk 분리
# =========================
def splitChunk(text, maxLen=400):

    sentences = re.split(r'(?<=[.。])\s', text)

    chunks = []
    current = ""

    for s in sentences:
        if len(current) + len(s) < maxLen:
            current += " " + s
        else:
            chunks.append(current.strip())
            current = s

    if current:
        chunks.append(current.strip())

    return chunks


# =========================
# 사전 기반 매핑 규칙
# RAG 흐름에서 이 단계가 먼저 수행되며, 매핑 실패 항목은 학습 데이터에서 제외됩니다.
# =========================
KEYWORD_SUBISSUE_MAP = [
    (["탄소", "배출"], "Climate-02"),
    (["에너지"], "Energy-01"),
    (["재생"], "Energy-02"),
    (["안전"], "Safety-02"),
]


def mapSubissues(text):
    matchedIds = []

    for keywords, subId in KEYWORD_SUBISSUE_MAP:
        if any(keyword in text for keyword in keywords):
            matchedIds.append(subId)

    return list(dict.fromkeys(matchedIds))  # 중복 제거


# =========================
# main
# =========================
def process():

    results = []

    with open(inputFile, "r", encoding="utf-8") as f:

        for line in f:
            data = json.loads(line)
            chunks = splitChunk(data["paragraph"])
            for c in chunks:
                subIds = mapSubissues(c)
                
                if not subIds:
                    subIds = ["Unknown"]
                for subId in subIds:
                    metadata = subissueMaster.get(subId, {})

                    results.append({
                        "source": data["source"],
                        "title": data["title"],
                        "chunk": c,
                        "issue_group": metadata.get("issue_group_code", "Unknown"),
                        "issue_group_domain": metadata.get("esg_domain"),
                        "sub_issue_id": sub_id,
                        "sub_issue_name": metadata.get("sub_issue_name"),
                        "sub_issue_description": metadata.get("description"),
                        "base_metric_ids": metadata.get("base_metric_ids"),
                        "atomic_metric_ids": metadata.get("atomic_metric_ids"),
                    })

    with open(outputFile, "w", encoding="utf-8") as f:

        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"완료: {len(results)} chunks 생성")


if __name__ == "__main__":
    process()