from src.utils.subissuemaster import subissueMaster, getSubIssueDisplayName

def processMediaPipeline(
    articles: list,
    companyKeywords: list = None,
    industryKeywords: list = None,
    similarityThreshold: float = 0.45,
    topK: int = 3,
) -> list:
    """
    미디어 기사를 입력받아 청크 분할, 키워드 매핑, 임베딩, 유사도 판별 파이프라인을 실행합니다.
    (현재는 MVP 목적으로 키워드 매핑 로직 적용. 추후 embedding 로직 이식)
    """
    if companyKeywords is None: companyKeywords = []
    if industryKeywords is None: industryKeywords = []

    results = []
    
    # MVP 5개 핵심 이슈 (subissuemaster의 Key 기준)
    mvp_keys = [
        "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
        "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP",
        "S_TALENT__TRAINING_DEVELOPMENT",
        "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE",
        "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY"
    ]
    
    # MVP 이슈 대상 키워드 매핑 생성
    keyword_map = {}
    for key in mvp_keys:
        meta = subissueMaster.get(key)
        if meta:
            # 기본 한글 키워드 활용
            for kw in meta.get("keywordKr", []):
                keyword_map[kw] = key
                
    # 추가로 기사 매핑용으로 부족할 수 있으니 수동 보완 (MVP Mocking)
    keyword_map.update({
        "기후": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
        "온실가스": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
        "탄소": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
        "공급망": "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP",
        "협력사": "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP",
        "교육": "S_TALENT__TRAINING_DEVELOPMENT",
        "역량": "S_TALENT__TRAINING_DEVELOPMENT",
        "친환경": "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE",
        "저탄소": "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE",
        "안전": "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY",
        "소비자": "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY",
    })

    for article in articles:
        content = article.get("content", "")
        title = article.get("title", "")
        text = title + " " + content
        
        best_issue_id = None
        best_score = 0.0
        
        # 단순 키워드 출현 빈도로 유사도 모방
        for keyword, issue_id in keyword_map.items():
            if keyword in text:
                score = 0.5 + (text.count(keyword) * 0.1)
                score = min(score, 0.95)
                if score > best_score:
                    best_score = score
                    best_issue_id = issue_id
                    
        if best_score >= similarityThreshold and best_issue_id:
            results.append({
                "source": article.get("source", "news"),
                "title": title,
                "url": article.get("url", ""),
                "publishedAt": article.get("publishedAt", ""),
                "chunk": text[:500],
                "bestSubIssueId": best_issue_id,
                "bestSubIssueNameKr": getSubIssueDisplayName(best_issue_id),
                "bestSimilarityScore": best_score,
                "issueSimilarityMatches": [{"issueId": best_issue_id, "score": best_score}]
            })
            
    return results
