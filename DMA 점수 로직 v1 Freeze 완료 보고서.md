# DMA 점수 로직 v1 Freeze 완료 보고서

## 변경 요약

12개 완료 기준을 모두 충족하는 "DMA 점수 로직 v1 freeze"를 완료했습니다.

---

## 변경된 파일

### [dmascoring.py](file:///c:/Users/hi/Desktop/dev_skm/backend/src/utils/dmascoring.py) — 순수 factor→score 계산기로 정제
- **regulation hard-rule 블록 제거**: `sourceType == "regulation"` 분기에서 `SUPPLY_CHAIN`, `CLIMATE`, `DATA_SECURITY` 문자열 포함 여부로 점수를 고정 반환하던 코드를 삭제.
- 이제 `dmascoring.py`는 sourceType에 무관하게 순수하게 factor 수치만으로 0~5 점수를 계산합니다.
- `SCORE_UI_MULTIPLIER = 2` 상수 선언. DB/API는 0~5, UI는 `score05 * 2`로 0~10 환산.

### [dmaaggregator.py](file:///c:/Users/hi/Desktop/dev_skm/backend/src/utils/dmaaggregator.py) — 가중치 확정
- **Final stage weights 변경**: `survey=0.36/benchmark=0.32/media=0.32` → `survey=0.40/benchmark=0.35/media=0.25`
- 3개 가중치 상수 블록을 파일 상단에 명시적으로 선언:
  - `FINAL_STAGE_WEIGHTS` = survey=0.40, benchmark=0.35, media_external=0.25
  - `MEDIA_SOURCE_TYPE_WEIGHTS` = news=1.0, agency=1.2, regulation=1.3
  - `SURVEY_GROUP_WEIGHTS` = employee=0.30, management=0.40, external=0.30
- Benchmark 산식에 `[v1 provisional]` 주석 추가.
- `getCoverageStatus()` 반환값 `"NONE"` → `"NO_DATA"` 변경.

### [subissuemaster.py](file:///c:/Users/hi/Desktop/dev_skm/backend/src/utils/subissuemaster.py) — IRO 검증 헬퍼 추가
- `SCORING_CAPABLE_IROS` 상수: `{negative_impact, positive_impact, financial_risk, financial_opportunity}`
- `getScoringAllowedIros(subIssueCode)` 함수: scoring_axis_allowed에서 위 4개만 필터링하여 반환.
- `governance_quality`, `risk_management_maturity`, `transition_risk` 등 보조 axis는 자동 제외.

### [medias/baseline.py](file:///c:/Users/hi/Desktop/dev_skm/backend/src/services/medias/baseline.py) — IRO 검증 게이트 적용
- `_resolveIroDirection()` 내부 함수: `getScoringAllowedIros()`를 호출하여 impact/financial 각 축에 허용된 IRO가 있는지 확인.
- **허용된 scoring IRO가 없으면 해당 factor는 `None`으로 설정** (무조건 fallback 생성하지 않음).

### [benchmarks/adapter.py](file:///c:/Users/hi/Desktop/dev_skm/backend/src/services/benchmarks/adapter.py) — AI iroHint 검증
- `_validateIroHint()`: AI 반환 iroHint를 `isAllowedIro()`로 검증.
- 불허 시 같은 축 내의 scoring 가능 IRO로 대체 시도, 없으면 해당 factor 제거.

### [apis/media.py](file:///c:/Users/hi/Desktop/dev_skm/backend/src/apis/media.py) — Coverage 노출
- `MediaAnalyzeResponse`에 `coverageStatus: str` 필드 추가.
- DB 컬럼 추가 없이 관측된 stage 수를 기반으로 재계산하여 반환.

---

## 검증 결과

테스트 기사 2건에 대해 전체 파이프라인을 실행한 결과:

| SubIssue | allowedScoringIros | impactFactor | financialFactor | impactScore | financialScore |
|----------|-------------------|-------------|----------------|-------------|----------------|
| `E_CLIMATE__GHG_SCOPE12_EMISSIONS` | negative_impact, financial_risk | negative | risk | 2.35 | 1.95 |
| `S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_CODE_DUE_DILIGENCE` | negative_impact | negative | **None** | 2.35 | **None** |

> [!TIP]
> `SUPPLIER_CODE_DUE_DILIGENCE`는 `scoring_axis_allowed`에 `negative_impact`만 있으므로, financial factor가 정확히 `None`으로 처리됩니다. 이것이 `isAllowedIro()` 검증이 작동하는 증거입니다.

### 12개 완료 기준 체크

```
 1. [x] 모든 source는 DMASignal로 들어간다
 2. [x] subIssueCode는 subissuemaster.py key만 사용한다
 3. [x] 한글명은 displaySubIssueName으로만 사용한다
 4. [x] AI는 점수를 직접 주지 않는다
 5. [x] Impact/Financial 점수는 dmascoring.py가 계산한다
 6. [x] IRO 유형은 source rule → scoring_axis_allowed → baseline → AI hint 순
 7. [x] stage aggregation은 source별 weight와 NULL 제외 평균
 8. [x] final aggregation은 benchmark/media/survey NULL 제외 재가중 평균
 9. [x] DB에는 0~5 점수만 저장한다
10. [x] UI에는 필요 시 0~10으로 환산한다
11. [x] coverage status를 API response에 포함한다
12. [x] ESG_DMA_SCORE_SUMMARY 기준으로 topIssues와 rank를 반환한다
```

---

## 후속 작업 (이번 freeze 범위 밖)

1. `ESG_DMA_SIGNAL_DETAIL` 테이블에 `scoring_payload_json JSON` 컬럼 추가 (DB migration)
2. Regulation adapter 구현 (`services/regulations/baseline.py`에 regulation 전용 factor rule 이관)
3. Agency adapter 구현
4. Survey axis 분리
5. Benchmark ratio/blind spot 정교화 (현재 v1 provisional)
