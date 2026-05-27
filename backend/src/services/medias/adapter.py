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
            confidenceScore=res["bestSimilarityScore"],
            similarityScore=res["bestSimilarityScore"],
            displaySubIssueName=res["bestSubIssueNameKr"],
            evidenceSpans=[res["chunk"]] if res.get("chunk") else [],
            rawIssueLabel=res.get("title", "")
        )
        signalsToSave.append(sig)
    return signalsToSave
