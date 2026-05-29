from src.models.dmaengine import DMASignal

def convertMediaToDmaSignals(analysisResults: list) -> list[DMASignal]:
    """
    미디어/언론 분석 결과를 DMASignal 객체 리스트로 변환합니다.
    """
    signalsToSave = []
    for res in analysisResults:
        sig = DMASignal(
            subIssueCode=res["bestSubIssueId"],
            sourceStep="media_external",
            sourceType="news",
            # bestSimilarityScore를 점수로 직접 쓰지 않고 confidence/mapping weight로 사용
            confidenceScore=res["bestSimilarityScore"],
            similarityScore=res["bestSimilarityScore"],
            mappingWeight=res["bestSimilarityScore"],
            displaySubIssueName=res["bestSubIssueNameKr"],
            evidenceSpans=[res["chunk"]] if res.get("chunk") else [],
            rawIssueLabel=res.get("title", ""),
            # 확장 메타데이터 (DB 보존용)
            sourceTitle=res.get("title", ""),
            sourceUrl=res.get("url", ""),
            publishedAt=res.get("publishedAt", ""),
            scoringPayloadJson={
                "source": res.get("source", ""),
                "issueSimilarityMatches": res.get("issueSimilarityMatches", [])
            }
        )
        signalsToSave.append(sig)
    return signalsToSave
