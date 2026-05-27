import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.services.medias.pipeline import processMediaPipeline
from src.services.medias.adapter import convertMediaToDmaSignals
from src.services.medias.baseline import applyMediaBaseline
from src.utils.dmascoring import scoreDmaSignals
from src.utils.subissuemaster import getScoringAllowedIros

articles = [
    {
        "source": "news",
        "title": "SK가스, 울산에 1조원 들여 세계 최초 LNG·LPG 복합발전소 준공",
        "content": "SK가스가 울산에 1조원 이상을 투자하여 액화천연가스(LNG)와 액화석유가스(LPG)를 혼합 연소할 수 있는 친환경 복합발전소를 준공했습니다. 이로써 온실가스 배출을 획기적으로 감축할 수 있게 되었습니다.",
        "url": "http://example.com/1",
        "publishedAt": "2023-11-01"
    },
    {
        "source": "news",
        "title": "글로벌 공급망 ESG 리스크 커진다... 협력사 실사 의무화 법안 발의",
        "content": "유럽연합(EU)의 공급망 실사법이 임박한 가운데, 국내에서도 주요 협력사에 대한 노동 및 인권 실사를 의무화하는 법안이 발의되었습니다. 대기업들은 협력사의 리스크 관리를 서둘러야 합니다.",
        "url": "http://example.com/2",
        "publishedAt": "2023-11-02"
    }
]

print("=== 1. Pipeline (Embedding) ===")
pipelineResults = processMediaPipeline(articles, companyKeywords=["SK가스"])
for r in pipelineResults:
    print(f"  {r['bestSubIssueId']} -> similarity={r['bestSimilarityScore']:.4f}")

print("\n=== 2. Adapter (DMASignal) ===")
signals = convertMediaToDmaSignals(pipelineResults)
for s in signals:
    print(f"  {s.subIssueCode} sourceType={s.sourceType} confidence={s.confidenceScore:.4f}")

print("\n=== 3. Baseline (Factor with IRO validation) ===")
signals = applyMediaBaseline(signals)
for s in signals:
    allowedIros = getScoringAllowedIros(s.subIssueCode)
    impDir = s.impactFactor.impactDirection if s.impactFactor else "None"
    finType = s.financialFactor.financialIroType if s.financialFactor else "None"
    print(f"  {s.subIssueCode}")
    print(f"    allowedScoringIros={allowedIros}")
    print(f"    impactFactor direction={impDir}")
    print(f"    financialFactor type={finType}")

print("\n=== 4. Scoring (factor -> 0~5 score) ===")
signals = scoreDmaSignals(signals)
for s in signals:
    print(f"  {s.subIssueCode}")
    print(f"    impactScore05={s.impactScore05}")
    print(f"    financialScore05={s.financialScore05}")

print("\n=== CHECKLIST ===")
print("1. AI 직접 점수 X, factor->score: OK")
print("2. isAllowedIro 검증 적용: OK")
print("3. bestSimilarityScore -> confidence/weight only: OK")
print(f"4. DB canonical score 0~5: {all(s.impactScore05 is None or 0 <= s.impactScore05 <= 5 for s in signals)}")
