from sentence_transformers import SentenceTransformer
import json
import os
import numpy as np
from pathlib import Path

from subissuemaster import subissueMaster
from core.paths import embeddedJsonl, similarityJsonl, subissueVectorJsonl

# ==========================================================================================
# [카멜 케이스 파일 경로 정의] 각 모델별 파일들이 꼬이지 않도록 명시적 분리
# ==========================================================================================
# 1. BGE-M3 관련 경로
BGE_INPUT_FILE = embeddedJsonl
BGE_OUTPUT_FILE = similarityJsonl
BGE_SUBISSUE_VECTOR_FILE = subissueVectorJsonl

# 2. KR-SBERT 관련 경로 (카멜 케이스 규칙을 유지하되, 실제 파일명인 _sbert로 매칭)
SBERT_INPUT_FILE = os.path.join(os.path.dirname(embeddedJsonl), "embeddedEsgChunks_sbert.jsonl")

# 출력 파일명들은 깔끔하게 카멜 케이스 규칙을 유지하시면 됩니다.
SBERT_OUTPUT_FILE = os.path.join(os.path.dirname(similarityJsonl), "similaritySbert.jsonl")
SBERT_SUBISSUE_VECTOR_FILE = os.path.join(os.path.dirname(subissueVectorJsonl), "subissueVectorSbert.jsonl")


def buildSubissuePrototypes():
    """ 
    v4.3 사전 구조의 subIssueSentence(앵커)와 keywordKr을 결합하여
    풍부한 프로토타입 텍스트 벡터 기준점을 생성하는 카멜 형식 함수 
    """
    prototypes = []
    
    for subId, info in subissueMaster.items():
        # 💡 핵심: 앵커 문장과 키워드 리스트를 결합하여 문맥 인지력 극대화
        anchorSentence = info.get("subIssueSentence", "")
        keywordsKr = " ".join(info.get("keywordKr", []))
        
        # 문장과 키워드 사이에 공백을 주어 자연스러운 컨텍스트 형성
        combinedText = f"{anchorSentence} {keywordsKr}".strip()
        
        prototypes.append({
            "subIssueId": subId,
            "text": combinedText,
            "subIssueNameKr": info.get("subIssueNameKr", ""),
            "issueGroupId": info.get("issueGroupId", "")
        })
        
    return prototypes


def saveSubissueVectors(filePath, prototypes, embeddings):
    """ 마스터 벡터를 지정된 파일에 저장 """
    with open(filePath, "w", encoding="utf-8") as f:
        for proto, vector in zip(prototypes, embeddings):
            record = {
                **proto,
                "embedding": vector.tolist(),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def loadSubissueVectors(filePath):
    """ 마스터 벡터 파일을 로드 """
    if not os.path.exists(filePath):
        return None

    records = []
    with open(filePath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def getSubissueVectors(model, subissueVectorFile, forceRebuild=False):
    """ 각 모델에 맞춰 동적으로 마스터 사전 벡터를 생성하거나 로드하는 함수 """
    if not forceRebuild:
        records = loadSubissueVectors(subissueVectorFile)
        if records:
            return records

    print(f"-> [알림] {Path(subissueVectorFile).name} 사전 벡터 파일 재생성 중...")
    prototypes = buildSubissuePrototypes()
    texts = [proto["text"] for proto in prototypes]
    embeddings = model.encode(texts)

    saveSubissueVectors(subissueVectorFile, prototypes, embeddings)

    vectors = []
    for proto, vector in zip(prototypes, embeddings):
        vectors.append({
            **proto,
            "embedding": vector.tolist(),
        })
    return vectors


def cosineSimilarity(a, b):
    """ 코사인 유사도 연산 함수 """
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    aNorm = np.linalg.norm(a)
    bNorm = np.linalg.norm(b)
    if aNorm == 0 or bNorm == 0:
        return 0.0
    return float(np.dot(a, b) / (aNorm * bNorm))


def findTopMatches(chunkEmbedding, subissueVectors, topK=3):
    """ 가장 유사도가 높은 상위 K개의 서브이슈를 매칭하는 함수 """
    chunkVector = np.asarray(chunkEmbedding, dtype=np.float32)
    scores = []

    for sub in subissueVectors:
        score = cosineSimilarity(chunkVector, sub["embedding"])
        scores.append({
            "subIssueId": sub["subIssueId"],
            "issueGroupId": sub.get("issueGroupId"),
            "subIssueNameKr": sub.get("subIssueNameKr"),
            "score": score,
        })

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:topK]


def processSimilarityPipeline(modelName, inputFile, outputFile, subissueVectorFile, cacheFolder=None):
    """ 특정 모델의 임베딩 파일을 받아 유사도 매칭 프로세스를 수행하는 핵심 코어 함수 """
    print(f"\n========================================================= [{modelName}] 파이프라인 가동")
    
    # 모델 로드 (SBERT의 경우 cache_folder 적용)
    if cacheFolder:
        model = SentenceTransformer(modelName, cache_folder=cacheFolder)
    else:
        model = SentenceTransformer(modelName)

    # 1. 해당 모델 전용 서브이슈 마스터 벡터 로드 (차원 불일치를 막기 위해 forceRebuild=True 권장)
    subissueVectors = getSubissueVectors(model, subissueVectorFile, forceRebuild=True)
    if not subissueVectors:
        print(f"❌ {modelName} 서브이슈 임베딩을 생성할 수 없습니다.")
        return

    # 2. 뉴스 청크 임베딩 데이터 로드
    records = []
    try:
        with open(inputFile, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except FileNotFoundError:
        print(f"❌ 입력 파일을 찾을 수 없습니다: {inputFile}")
        return

    if not records:
        print(f"⚠️ 입력 데이터가 비어있습니다: {inputFile}")
        return

    # 3. 유사도 연산 및 카멜 케이스 결과 저장
    print(f"-> 유사도 분석 시작 (총 {len(records)}개 청크)...")
    with open(outputFile, "w", encoding="utf-8") as outF:
        for record in records:
            chunkEmbedding = record.get("embedding")
            if not chunkEmbedding:
                continue

            topMatches = findTopMatches(chunkEmbedding, subissueVectors, topK=3)
            bestMatch = topMatches[0] if topMatches else None

            # 프론트엔드 연동을 고려한 완벽한 카멜 형식 아웃풋 구성
            outputRecord = {
                **record,
                "issueSimilarityMatches": topMatches,
                "bestSubIssueId": bestMatch["subIssueId"] if bestMatch else None,
                "bestSubIssueNameKr": bestMatch["subIssueNameKr"] if bestMatch else None,
                "bestIssueGroupId": bestMatch["issueGroupId"] if bestMatch else None,
                "bestSimilarityScore": bestMatch["score"] if bestMatch else None,
            }
            outF.write(json.dumps(outputRecord, ensure_ascii=False) + "\n")

    print(f"✅ 완료: {len(records)}개 레코드 저장 -> {outputFile}")


def run():
    """ 두 모델의 유사도 매칭을 원클릭으로 순차 실행하는 메인 제어기 """
    # # 🚀 1. AS-IS: BGE-M3 파이프라인 구동 (1024차원)
    # processSimilarityPipeline(
    #     modelName="BAAI/bge-m3",
    #     inputFile=BGE_INPUT_FILE,
    #     outputFile=BGE_OUTPUT_FILE,
    #     subissueVectorFile=BGE_SUBISSUE_VECTOR_FILE
    # )

    # 🚀 2. TO-BE: KR-SBERT 파이프ライン 구동 (768차원)
    processSimilarityPipeline(
        modelName="snunlp/KR-SBERT-V40K-klueNLI-augSTS",
        inputFile=SBERT_INPUT_FILE,
        outputFile=SBERT_OUTPUT_FILE,
        subissueVectorFile=SBERT_SUBISSUE_VECTOR_FILE,
        cacheFolder="./model_cache"
    )


if __name__ == "__main__":
    run()