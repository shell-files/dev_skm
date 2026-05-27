from typing import Optional
from src.models.dmaengine import DMASignal

def convertToDmaSignals(resultList: list, fileId: Optional[int]) -> list[DMASignal]:
    """
    분석 결과를 DMASignal 객체 리스트로 변환한다.
    입력 result는 camelCase만 허용한다.
    """
    signalsToSave = []

    for result in resultList:
        try:
            signalPayload = dict(result)
            signalPayload["teSrFileId"] = fileId

            signal = DMASignal(**signalPayload)
            signalsToSave.append(signal)
        except Exception as error:
            print(f"DMASignal parse error: {error}")

    return signalsToSave
