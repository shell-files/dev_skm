# Backend G0 DMA Refactor Inventory v1

Date: 2026-05-29
Branch: fixed/backend_refactoring_ljb
Base: origin/feature/onborading_renewal

## 1. Purpose

This inventory is the approval gate before a real G0/DMA naming refactor.

The goal is to make G0/DMA backend code easier to scan by applying
`BACKEND_METADATA_NAMING_RULES_v1.md` to file names, function names, and safe
Python-local variable names.

This document does not implement any code rename. It defines the candidate map,
canonical new names, wrapper policy, callsite scope, and smoke plan.

Core rule:

```text
New compact names become canonical.
Existing long public functions remain as compatibility wrappers.
Internal G0/DMA callsites move to compact canonical names after approval.
Protected auth/token/common/API-path/DB-schema areas stay untouched.
```

## 2. Target Files

Service layer:

```text
backend/src/services/materialities/context.py
backend/src/services/materialities/contextgraph.py
backend/src/services/materialities/financialexposure.py
```

Utility/repository/scoring layer:

```text
backend/src/utils/companycontextrepository.py
backend/src/utils/dmafinancialrepository.py
backend/src/utils/dmarepository.py
backend/src/utils/dmaaggregator.py
backend/src/utils/dmascoring.py
backend/src/utils/subissuemaster.py
```

Model layer:

```text
backend/src/models/dmaengine.py
backend/src/models/materiality.py
backend/src/models/materialitycontext.py
```

API layer, minimal import/callsite-only scope:

```text
backend/src/apis/materiality.py
```

## 3. Protected Areas

Do not modify:

```text
backend/src/utils/auth.py
backend/src/utils/tokenset.py
backend/src/utils/fastset.py
backend/src/models/auth.py
```

Do not alter these flows or contracts:

```text
login/logout/JWT/token validation
API route path
DB schema/column
FastAPI module-prefix routing behavior
Kafka/mail optional dependency behavior
```

## 4. File Rename Map

File naming rule for backend Python source: lowercase singular, no underscore.

| Current file | Candidate canonical file | Decision | Notes |
|---|---|---|---|
| `backend/src/utils/companycontextrepository.py` | `backend/src/utils/dmacontext.py` | Candidate | Repository responsibilities are G0 context/run/profile/modifier persistence. Needs import compatibility phase. |
| `backend/src/utils/dmafinancialrepository.py` | `backend/src/utils/dmafinancial.py` | Candidate | G0-02 financial basis utility. Needs compatibility module or import migration. |
| `backend/src/utils/dmaaggregator.py` | `backend/src/utils/dmaaggregation.py` | Candidate | More noun-like than aggregator; do not change weights. |
| `backend/src/services/materialities/financialexposure.py` | keep | Keep | Already conforms after Step 2 rename. |
| `backend/src/services/materialities/contextgraph.py` | keep or `contextprofilegraph.py` | Review | Current name conforms. `contextprofilegraph.py` is clearer but longer. Keep unless clarity issue persists. |
| `backend/src/services/materialities/context.py` | `contextmodifier.py` or `dmacontextservice.py` | Review | `contextmodifier.py` is compact and specific. `dmacontextservice.py` is explicit but less compact. |
| `backend/src/utils/dmascoring.py` | keep | Keep | Clear domain file. |
| `backend/src/utils/dmarepository.py` | keep | Keep for now | Large file, but high import risk. Prefer function canonicalization first. |
| `backend/src/utils/subissuemaster.py` | keep | Keep | Single Source of Truth. Do not rename in this phase. |

Implementation note:

```text
File renames must be done in isolated commits.
If an old import path is externally used, keep a thin compatibility module that re-exports canonical functions.
```

## 5. Function Rename Map

New names use the approved verb/object dictionary from
`BACKEND_METADATA_NAMING_RULES_v1.md`.

### 5-1. `context.py`

| Current public function | Canonical new name | Wrapper policy |
|---|---|---|
| `applyCompanyContextModifiers` | `applyModifiers` | Keep old as wrapper |
| `getCompanyContextProfile` | `getProfile` | Keep old as wrapper |
| `buildCompanyContextProfile` | `buildProfile` | Keep old as wrapper |
| `calculateContextModifier` | `calcModifier` | Keep old as wrapper |
| `applyRankMovementGuards` | `applyRankGuards` | Keep old as wrapper |
| `hasObservedStage` | `checkObservedStage` | Keep old as wrapper if public/imported |

### 5-2. `companycontextrepository.py`

| Current public function | Canonical new name | Wrapper policy |
|---|---|---|
| `getMaterialityRunContext` | `getRun` | Keep old as wrapper |
| `getCompanyG0Facts` | `listG0Facts` | Keep old as wrapper |
| `getDmaScoreSummaryRowsForContext` | `listScoreRows` | Keep old as wrapper |
| `replaceCompanyContextProfile` | `replaceProfile` | Keep old as wrapper |
| `updateContextModifiers` | `updateModifiers` | Keep old as wrapper |
| `getLatestCompanyContextProfile` | `getLatestProfile` | Keep old as wrapper |
| `clampSystemModifier` | `clampModifier` | Keep old as wrapper |

### 5-3. `dmafinancialrepository.py`

| Current public function | Canonical new name | Wrapper policy |
|---|---|---|
| `getG0FinancialBasis` | `getBasis` | Keep old as wrapper |
| `buildFinancialBasisPriority` | `buildPriority` | Keep old as wrapper |
| `fetchFinancialBasisRows` | `fetchRows` | Keep old as wrapper |
| `buildBasisFromRows` | `buildBasis` | Keep old as wrapper |
| `isUsableBasis` | `checkUsable` | Keep old as wrapper |
| `emptyFinancialBasis` | `buildEmptyBasis` | Keep old as wrapper |
| `normalizeFinancialValue` | `normalizeValue` | Keep old as wrapper |

### 5-4. `financialexposure.py`

These short wrappers already exist after Step 3 and should become canonical in
new G0/DMA callsites.

| Existing long function | Canonical new name | Status |
|---|---|---|
| `applyG0FinancialExposure` | `applyExposure` | Alias exists |
| `applyG0FinancialExposureForRun` | `applyRunExposure` | Alias exists |
| `buildFinancialExposureForSignal` | `buildExposure` | Alias exists |
| `buildFinancialExposureForSignalWithBasis` | `buildExposureWithBasis` | Alias exists |
| `calculateChannelScore` | `calcChannelScore` | Alias exists |
| `sourceTypeMagnitudeBonus` | `calcSourceBonus` | Alias exists |
| `confidenceMagnitudeCap` | `calcConfidenceCap` | Alias exists |
| `dominantMagnitude` | `resolveDominant` | Alias exists |
| `canApplyFinancialExposure` | `checkIro` | Alias exists |
| `resolvePreferConsolidated` | `resolveScope` | Alias exists |

### 5-5. `dmascoring.py`

| Current public function | Canonical new name | Wrapper policy |
|---|---|---|
| `calculateImpactScore` | `calcImpact` | Keep old as wrapper |
| `calculateFinancialScore` | `calcFinancial` | Keep old as wrapper |
| `scoreDmaSignals` | `scoreSignals` | Keep old as wrapper |
| `timeHorizonToUrgency` | `mapUrgency` | Keep old as wrapper |

### 5-6. `dmaaggregator.py`

| Current public function | Canonical new name | Wrapper policy |
|---|---|---|
| `aggregateBenchmarkSignals` | `aggregateBenchmark` | Keep old as wrapper |
| `aggregateSurveyScores` | `aggregateSurvey` | Keep old as wrapper |
| `aggregateMediaSignals` | `aggregateMedia` | Keep old as wrapper |
| `weightedAvgAvailable` | `calcWeightedAvg` | Keep old as wrapper |
| `calculateFinalMateriality` | `calcFinal` | Keep old as wrapper |

### 5-7. `dmarepository.py`

| Current public function | Canonical new name | Wrapper policy |
|---|---|---|
| `saveDmaSignals` | `saveSignals` | Keep old as wrapper |
| `normalizeEvidencePublishedAt` | `normalizePublishedAt` | Keep old as wrapper |
| `insertDmaEvidence` | `insertEvidence` | Keep old as wrapper |
| `getSignalsByGroup` | `listSignals` | Keep old as wrapper |
| `recalculateStageScore` | `recalcStage` | Keep old as wrapper |
| `recalculateSurveyScore` | `recalcSurvey` | Keep old as wrapper |
| `upsertStageScoreSummary` | `upsertStage` | Keep old as wrapper |
| `recalculateFinalScore` | `recalcFinal` | Keep old as wrapper |
| `updateDmaRankings` | `updateRanks` | Keep old as wrapper |
| `upsertFinalScoreSummary` | `upsertFinal` | Keep old as wrapper |
| `getDmaResults` | `listResults` | Keep old as wrapper |
| `getTopIssuesByMediaScore` | `listTopMediaIssues` | Keep old as wrapper |
| `getMediaCoverageFromSummary` | `getCoverage` | Keep old as wrapper |
| `getMediaObservedSubIssueCount` | `countMediaSubIssues` | Keep old as wrapper |
| `getMaterialityRunInfo` | `getRunInfo` | Keep old as wrapper |
| `getSelectedSubIssues` | `listSelectedSubIssues` | Keep old as wrapper |
| `getTopIssuesByStageScore` | `listTopStageIssues` | Keep old as wrapper |
| `getSignalObservationCounts` | `listSignalCounts` | Keep old as wrapper |
| `getDistinctObservedSubIssueCount` | `countObservedSubIssues` | Keep old as wrapper |
| `getEvidenceCountsBySource` | `listEvidenceCounts` | Keep old as wrapper |
| `getEvidenceSamples` | `listEvidenceSamples` | Keep old as wrapper |
| `getSurveyGroupCounts` | `listSurveyCounts` | Keep old as wrapper |
| `getSurveyGroupScores` | `listSurveyScores` | Keep old as wrapper |
| `getRequiredMetricCountForSubIssues` | `countRequiredMetrics` | Keep old as wrapper |
| `getMissingRequiredMetricCount` | `countMissingMetrics` | Keep old as wrapper |
| `getLatestReportRunByMaterialityRun` | `getLatestReportRun` | Keep old as wrapper |

## 6. Variable Cleanup Candidates

Search command used for inventory:

```powershell
rg -n "\b[a-z]+_[a-zA-Z0-9_]+\b" backend/src/services/materialities backend/src/utils backend/src/models backend/src/apis/materiality.py
```

The result is intentionally noisy because SQL columns, SQL aliases, JSON keys,
subIssue metadata keys, and DB row keys are snake_case by contract.

### 6-1. Do not change

Do not rename these categories:

```text
DB columns in SQL text
SQL aliases that mirror DB columns
dictionary keys returned by repository rows
JSON payload keys already contracted with API/DB
Pydantic DTO fields
subissuemaster.py metadata keys
external payload keys
```

Examples that must stay:

```text
sub_issue_code
context_json
modifier_json
company_id
reporting_year
delete_yn
source_published_at
scoring_axis_allowed
mapped_metric_ids
```

### 6-2. Candidate cleanup categories

Only Python-local names should be considered after manual review:

```text
temporary local variables in service/utils functions
loop variables created from internal transformations
helper-only intermediate names
API handler function names if route path and operation behavior remain stable
```

Candidate examples from current scan:

```text
backend/src/apis/materiality.py
- get_dma_results -> getDmaResultsHandler or keep to avoid OpenAPI operation-id churn
- get_benchmark_result -> getBenchmarkResultHandler or keep
- get_media_result -> getMediaResultHandler or keep
- get_survey_result -> getSurveyResultHandler or keep
- get_selection_process -> getSelectionProcessHandler or keep
- apply_company_context_modifiers -> applyContextModifiersHandler or keep
- get_company_context_profile -> getContextProfileHandler or keep

backend/src/services/materialities/context.py
- Most Python variables are already camelCase.
- row.get("snake_case") expressions are DB row-key access and must remain.

backend/src/utils/*repository.py
- SQL text and DB row keys dominate the snake_case results.
- Rename only local variables that do not represent DB/API keys.
```

Recommendation:

```text
Variable cleanup should be a separate low-risk pass after function canonicalization.
Do not combine variable cleanup with file rename commits.
```

## 7. Canonical/New Name Rules

Canonical names are the compact names listed in this document.

Rules:

```text
1. Add canonical implementation or alias first.
2. Keep old long public function as compatibility wrapper.
3. Move internal G0/DMA imports and callsites to canonical names.
4. Do not change behavior, trace shape, score formula, DB writes, or API paths.
5. Update module metadata headers and __all__ exports in the same commit.
6. Do not remove old public functions until a later deprecation window is approved.
```

Preferred implementation shape:

```python
def applyModifiers(...):
    ...


def applyCompanyContextModifiers(...):
    return applyModifiers(...)
```

For high-risk repository files, it is acceptable to invert this temporarily:

```python
def applyModifiers(...):
    return applyCompanyContextModifiers(...)
```

but canonical code should eventually put real logic under the compact name.

## 8. Compatibility Wrapper Policy

Keep wrappers when any of these are true:

```text
function is imported by apis/materiality.py
function is imported by service modules
function is used by tests/smoke scripts
function is public in __all__
function has been referenced in planning/API contract docs
```

Wrapper constraints:

```text
thin delegation only
no new DB mutation
no trace/output mutation
no default argument change
no exception behavior change
no side effects beyond the canonical function
```

## 9. Callsite Replacement Scope

Allowed:

```text
G0/DMA internal service imports
G0/DMA internal util imports
materiality service callsites
materiality API import/callsite only when route path is unchanged
```

Not allowed:

```text
route path changes
DB schema/column changes
DTO field changes
auth/token/common imports
media/benchmark adapter connection changes
scoring formula changes
aggregation weight changes
```

API handler names in `backend/src/apis/materiality.py` are a special case:

```text
Route paths are protected.
Handler function names may affect generated OpenAPI operation IDs.
Therefore handler renames should be delayed unless Antigravity/frontend is confirmed not to rely on operation IDs.
```

## 10. Smoke Checklist

Run after every implementation commit:

```powershell
cd backend
.\.venv\Scripts\python.exe -m compileall src
```

Import smoke groups:

```powershell
.\.venv\Scripts\python.exe -c "from src.services.materialities.context import applyModifiers, applyCompanyContextModifiers; print('context imports ok')"
.\.venv\Scripts\python.exe -c "from src.services.materialities.financialexposure import applyExposure, applyG0FinancialExposure; print('financial exposure imports ok')"
.\.venv\Scripts\python.exe -c "from src.utils.dmascoring import calcImpact, calculateImpactScore; print('scoring imports ok')"
.\.venv\Scripts\python.exe -c "from src.utils.dmaaggregator import calcFinal, calculateFinalMateriality; print('aggregation imports ok')"
```

Static checks:

```powershell
rg "financial_exposure|context_graph" backend/src
git diff origin/feature/onborading_renewal -- backend/src/utils/auth.py
git diff origin/feature/onborading_renewal -- backend/src/utils/tokenset.py
git diff origin/feature/onborading_renewal -- backend/src/utils/fastset.py
git diff origin/feature/onborading_renewal -- backend/src/models/auth.py
git diff -- backend/src/apis/materiality.py
```

Expected:

```text
compileall passes
old and new imports both work
protected-area diffs are empty
API route paths are unchanged
DB schema/column diffs are absent
scoring formulas are unchanged
aggregation weights are unchanged
```

## 11. Step-by-Step Commit Plan

### Commit 1. Inventory only

```text
docs: add G0 DMA refactor inventory
```

Files:

```text
BACKEND_G0_DMA_REFACTOR_INVENTORY_v1.md
```

### Commit 2. Context service canonical functions

Scope:

```text
backend/src/services/materialities/context.py
backend/src/apis/materiality.py import/callsite only if needed
```

Work:

```text
applyModifiers canonical implementation
getProfile canonical implementation
buildProfile canonical implementation
calcModifier canonical implementation
applyRankGuards canonical implementation
checkObservedStage canonical implementation
old names become wrappers
```

### Commit 3. Context repository canonical functions

Scope:

```text
backend/src/utils/companycontextrepository.py
backend/src/services/materialities/context.py callsites
```

Work:

```text
getRun/listG0Facts/listScoreRows/replaceProfile/updateModifiers/getLatestProfile/clampModifier
old names remain wrappers
```

### Commit 4. Financial basis repository canonical functions

Scope:

```text
backend/src/utils/dmafinancialrepository.py
backend/src/services/materialities/financialexposure.py callsites
```

Work:

```text
getBasis/buildPriority/fetchRows/buildBasis/checkUsable/buildEmptyBasis/normalizeValue
old names remain wrappers
```

### Commit 5. Scoring/aggregation canonical functions

Scope:

```text
backend/src/utils/dmascoring.py
backend/src/utils/dmaaggregator.py
G0/DMA internal callsites
```

Work:

```text
calcImpact/calcFinancial/scoreSignals/mapUrgency
aggregateBenchmark/aggregateSurvey/aggregateMedia/calcWeightedAvg/calcFinal
old names remain wrappers
```

### Commit 6. DMA repository canonical functions

Scope:

```text
backend/src/utils/dmarepository.py
backend/src/services/materialities/service.py callsites
other G0/DMA internal callsites
```

Work:

```text
saveSignals/recalcStage/recalcFinal/updateRanks/listResults/listTopMediaIssues/etc.
old names remain wrappers
```

### Commit 7. Optional file rename pass

Only after function-level migration is stable:

```text
companycontextrepository.py -> dmacontext.py
dmafinancialrepository.py -> dmafinancial.py
dmaaggregator.py -> dmaaggregation.py
context.py -> contextmodifier.py or keep
```

Rules:

```text
use git mv
update imports only
consider compatibility re-export modules for old paths
compile/import smoke after each rename
```

### Commit 8. Variable cleanup pass

Scope:

```text
Python-local variables only
no SQL/DB/API/DTO/key rename
```

This commit should be last because it has the lowest behavioral value and can
make diffs noisy.

## 12. Forbidden Changes

```text
delete existing public functions
change API route path
change DB schema/column
change DTO field names
change scoring formula
change aggregation weights
modify auth/token/common protected files
connect media/benchmark adapters
change selected subIssue logic
change subissuemaster.py source of truth semantics
```

## 13. Approval Gate

No code rename should start until this inventory is reviewed.

After approval, each implementation commit must be small, reversible, and
limited to one responsibility group.
