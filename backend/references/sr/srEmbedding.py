import json
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
# subissueMaster를 불러옵니다.
from subissuemaster import subissueMaster 
from settings import settings

# 1. 설정
HF_TOKEN = settings.hf_token
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
INPUT_FILE = "./storage/ocr/chunks/2024/SR_2024_FINAL_RECONSTRUCTED.json" 
OUTPUT_FILE = "2024Em.jsonl"
CACHE_DIR = Path(__file__).resolve().parent / "model_cache"

# 모델 로드
print(f"[{MODEL_NAME}] 모델을 로드 중입니다...")
model = SentenceTransformer(MODEL_NAME, cache_folder=str(CACHE_DIR))

# 2. 분류를 위한 이슈 앵커(SubIssueSentence) 벡터화
print("의미 기반 도메인 분류를 위한 앵커 벡터를 생성합니다...")
issue_anchors = []
for sub_id, info in subissueMaster.items():
    # 서브이슈 설명 문장을 벡터화하여 비교 기준으로 삼습니다.
    sentence = info.get("subIssueSentence", "")
    embedding = model.encode(sentence)
    issue_anchors.append({
        "id": sub_id,
        "domain": info.get("domain"),
        "groupName": info.get("issueGroupNameKr"),
        "name": info.get("subIssueNameKr"),
        "embedding": embedding
    })

# 앵커 벡터들만 따로 추출
anchor_vectors = [a["embedding"] for a in issue_anchors]

def run():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    chunks = [record["text"] for record in records]
    vectors = model.encode(chunks) # 임베딩 수행

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for record, vector in zip(records, vectors):
            text = record.get("text", "")
            # [핵심] 의미 유사도 기반 자동 매핑
            # 페이지 청크 벡터와 각 이슈 앵커 벡터 간의 코사인 유사도 계산
            similarities = util.cos_sim(vector, anchor_vectors)[0]
            if len(text) < 50: 
                mapped_issues = []
            else:
                similarities = util.cos_sim(vector, anchor_vectors)[0]
                mapped_issues = []
                for i, score in enumerate(similarities):
                    if score > 0.45: 
                        mapped_issues.append({
                            "domain": issue_anchors[i]["domain"],
                            "issueGroupName": issue_anchors[i]["groupName"],
                            "subIssueId": issue_anchors[i]["id"],
                            "subIssueName": issue_anchors[i]["name"],
                        })
            
            # 최종 결과 기록
            outputRecord = {
                "year":"2024",
                **record,
                "embedding": vector.tolist(),
                "mapped_issues": mapped_issues,
                "has_mapping": len(mapped_issues) > 0
            }
            out_f.write(json.dumps(outputRecord, ensure_ascii=False) + "\n")

    print(f"임베딩 및 의미 기반 태깅 완료: {OUTPUT_FILE}")

if __name__ == "__main__":
    run()