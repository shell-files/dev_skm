from src.services.medias.pipeline import processMediaPipeline
from src.services.medias.adapter import convertMediaToDmaSignals
from src.services.medias.baseline import applyMediaBaseline
from src.utils.dmascoring import scoreDmaSignals
from src.utils.dmarepository import saveDmaSignals

def runMediaAnalysis(articles: list, runId: int):
    """
    미디어/언론 분석 전체 워크플로우를 실행합니다.
    """
    # 1. Pipeline: chunk -> embedding -> similarity
    pipelineResults = processMediaPipeline(articles)
    
    # 2. Adapter: convert to DMASignal
    signals = convertMediaToDmaSignals(pipelineResults)
    
    # 3. Baseline: apply media-specific baseline
    baselinedSignals = applyMediaBaseline(signals)
    
    # 4. Scoring
    scoredSignals = scoreDmaSignals(baselinedSignals)
    
    # 5. DB Save
    # saveDmaSignals(runId=runId, signals=scoredSignals, fileId=None, sourceTitle="Media Analysis")
    return scoredSignals
