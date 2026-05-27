import numpy as np
import re
from sentence_transformers import SentenceTransformer
from src.utils.subissuemaster import subissueMaster, getSubIssueDisplayName

# 모델을 전역에서 한 번만 로드하도록 지연 초기화 패턴 사용
_model = None
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS")
    return _model

# 마스터 벡터 캐싱
_subissueVectors = None
def get_subissue_vectors():
    global _subissueVectors
    if _subissueVectors is not None:
        return _subissueVectors
        
    model = get_model()
    prototypes = []
    
    for subId, info in subissueMaster.items():
        # User Instruction 5: sentence 필드 사용 (subIssueSentence 대신)
        anchorSentence = info.get("sentence", "")
        keywordsKr = " ".join(info.get("keywordKr", []))
        keywordsEn = " ".join(info.get("keywordForeignEn", []))
        
        combinedText = f"{anchorSentence} {keywordsKr} {keywordsEn}".strip()
        if combinedText:
            prototypes.append({
                "subIssueId": subId,
                "text": combinedText,
                "subIssueNameKr": getSubIssueDisplayName(subId)
            })
            
    if not prototypes:
        return []
        
    texts = [p["text"] for p in prototypes]
    embeddings = model.encode(texts)
    
    _subissueVectors = []
    for proto, vector in zip(prototypes, embeddings):
        _subissueVectors.append({
            **proto,
            "embedding": vector.tolist()
        })
        
    return _subissueVectors

def splitChunk(text: str) -> list[str]:
    # 간단한 단락 분할. 실제로는 토큰 길이 기반 분할 등을 적용할 수 있습니다.
    chunks = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if len(paragraph) > 20:
            chunks.append(paragraph)
    return chunks

def cosineSimilarity(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    aNorm = np.linalg.norm(a)
    bNorm = np.linalg.norm(b)
    if aNorm == 0 or bNorm == 0:
        return 0.0
    return float(np.dot(a, b) / (aNorm * bNorm))

def findTopMatches(chunkEmbedding, subissueVectors, topK=3):
    scores = []
    for sub in subissueVectors:
        score = cosineSimilarity(chunkEmbedding, sub["embedding"])
        scores.append({
            "issueId": sub["subIssueId"],
            "subIssueNameKr": sub["subIssueNameKr"],
            "score": score,
        })
    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:topK]

def mapSubissues(text: str) -> list[str]:
    matchedIds = []
    lowerText = text.lower() 
    
    for subId, info in subissueMaster.items():
        keywords = info.get("keywordKr", []) + info.get("keywordForeignEn", [])
        for keyword in keywords:
            if not keyword: continue
            
            if keyword.isalnum():
                pattern = rf"\b{re.escape(keyword.lower())}\b"
                if re.search(pattern, lowerText):
                    matchedIds.append(subId)
                    break
            else:
                if keyword.lower() in lowerText:
                    matchedIds.append(subId)
                    break
                    
    return list(dict.fromkeys(matchedIds))

def processMediaPipeline(
    articles: list,
    companyKeywords: list = None,
    industryKeywords: list = None,
    similarityThreshold: float = 0.45,
    topK: int = 3,
) -> list:
    """
    실제 임베딩 기반 미디어 파이프라인.
    """
    if companyKeywords is None: companyKeywords = []
    if industryKeywords is None: industryKeywords = []

    results = []
    
    # 1. 서브이슈 프로토타입 임베딩 로드
    subissueVectors = get_subissue_vectors()
    if not subissueVectors:
        print("서브이슈 벡터를 초기화할 수 없습니다.")
        return []
        
    model = get_model()

    for article in articles:
        content = article.get("content", "")
        title = article.get("title", "")
        # 본문을 청크로 분할
        chunks = splitChunk(content)
        
        # 제목도 독립적인 청크로 추가
        if title and len(title.strip()) > 5:
            chunks.insert(0, title.strip())

        for chunk in chunks:
            # rag.py 로직: 키워드 필터링. companyKeywords 가 있다면 추가적인 필터링 로직에 사용할 수 있으나 
            # 지금은 기본적으로 subissueMaster 키워드 매칭을 1차 후보군으로 사용
            matchedSubIds = mapSubissues(chunk)
            
            # 매칭된 서브이슈가 없으면 해당 청크는 통과
            if not matchedSubIds:
                continue
                
            # 청크 임베딩 생성
            chunkVector = model.encode([chunk])[0]
            
            # 1차 필터링된 서브이슈 벡터들만 추려 유사도 계산
            filteredSubissueVectors = [sv for sv in subissueVectors if sv["subIssueId"] in matchedSubIds]
            
            # 만약 필터링된 벡터군이 없으면 전체 비교 (안전장치)
            if not filteredSubissueVectors:
                filteredSubissueVectors = subissueVectors
                
            topMatches = findTopMatches(chunkVector, filteredSubissueVectors, topK=topK)
            bestMatch = topMatches[0] if topMatches else None
            
            if bestMatch and bestMatch["score"] >= similarityThreshold:
                results.append({
                    "source": article.get("source", "news"),
                    "title": title,
                    "url": article.get("url", ""),
                    "publishedAt": article.get("publishedAt", ""),
                    "chunk": chunk,
                    "bestSubIssueId": bestMatch["issueId"],
                    "bestSubIssueNameKr": bestMatch["subIssueNameKr"],
                    "bestSimilarityScore": bestMatch["score"],
                    "issueSimilarityMatches": topMatches
                })
                
    return results
