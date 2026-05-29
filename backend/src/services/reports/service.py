import json
from decimal import Decimal
from typing import Optional

from src.models.report import (
    CompanyBreakdownDto,
    DownloadOptionDto,
    RelatedParagraphDto,
    ReportDownloadResponseDto,
    ReportDraftParagraphDto,
    ReportDraftPatchResponseDto,
    ReportDraftResponseDto,
    ReportDraftSectionDto,
    ReportDraftSummaryDto,
    ReportMetricTraceDto,
    ReportTraceResponseDto,
    YearValueDto,
)
from src.utils.reportrepository import (
    getAtomicMetricRows,
    getCalculationRuleByAtomicMetric,
    getDraftById,
    getKpiFactById,
    getKpiFactsByCompanyAtomic,
    getLatestReportRunByMaterialityRun,
    getReferencesForDraftIds,
    getReferencesForParagraph,
    getReportDraftRows,
    getRollupResultById,
    getRollupResultsByParentAtomic,
)
from src.utils.subissuemaster import getSubIssueMeta


REPORT_MISSING_SCHEMA_FIELDS = [
    "edited_text",
    "last_edited_by_user_id",
    "last_edited_at",
    "section_order",
    "paragraph_order",
]


def getReportDrafts(runId: int) -> ReportDraftResponseDto:
    reportRun = getLatestReportRunByMaterialityRun(runId)
    reportRunId = _safeInt(reportRun.get("id"))
    if reportRunId is None:
        return ReportDraftResponseDto(
            runId=runId,
            reportRunId=None,
            summary=ReportDraftSummaryDto(),
            sections=[],
            downloadOptions=_downloadOptions(),
            implementationStatus="SKELETON",
            missingSchemaFields=REPORT_MISSING_SCHEMA_FIELDS,
            orderSource="ID_ASC_FALLBACK",
        )

    draftRows = getReportDraftRows(reportRunId)
    draftIds = [_safeInt(row.get("id")) for row in draftRows if row.get("id") is not None]
    references = getReferencesForDraftIds([draftId for draftId in draftIds if draftId is not None])
    refsByDraft = _groupReferencesByDraft(references)
    atomicIds = sorted({ref.get("atomic_metric_id") for ref in references if ref.get("atomic_metric_id")})
    atomicRows = getAtomicMetricRows(atomicIds)
    metricIdByAtomic = {row.get("atomic_metric_id"): row.get("metric_id") for row in atomicRows}

    sectionsByKey = {}
    for row in draftRows:
        draftId = _safeInt(row.get("id"))
        if draftId is None:
            continue
        subIssueCode = row.get("sub_issue_code")
        sectionCode = row.get("section_code")
        sectionKey = sectionCode or subIssueCode or f"draft-{draftId}"
        meta = getSubIssueMeta(subIssueCode) if subIssueCode else {}
        if sectionKey not in sectionsByKey:
            sectionsByKey[sectionKey] = ReportDraftSectionDto(
                sectionId=sectionKey,
                sectionCode=sectionCode,
                sectionTitle=meta.get("subIssueNameKr") or sectionCode or "보고서 섹션",
                subIssueCode=subIssueCode,
                displaySubIssueName=meta.get("subIssueNameKr") if subIssueCode else None,
                paragraphs=[],
            )

        draftRefs = refsByDraft.get(draftId, [])
        referencedMetricIds = sorted(
            {
                metricIdByAtomic.get(ref.get("atomic_metric_id")) or ref.get("atomic_metric_id")
                for ref in draftRefs
                if ref.get("atomic_metric_id")
            }
        )
        generatedText = row.get("generated_text") or ""
        sectionsByKey[sectionKey].paragraphs.append(
            ReportDraftParagraphDto(
                paragraphId=draftId,
                draftId=draftId,
                paragraphOrder=draftId,
                originalGeneratedText=generatedText,
                editableText=generatedText,
                editedText=None,
                approvalStatus=row.get("approval_status") or "draft",
                qaStatus=row.get("qa_status"),
                lastEditedAt=str(row.get("updated_at")) if row.get("updated_at") is not None else None,
                referencedMetricIds=referencedMetricIds,
                traceAvailableYn=len(draftRefs) > 0,
            )
        )

    totalParagraphs = len(draftRows)
    paragraphsWithRefs = len([draftId for draftId, refs in refsByDraft.items() if refs])
    revisionRequiredCount = sum(
        1
        for row in draftRows
        if (row.get("qa_status") not in [None, "pass"] or row.get("approval_status") not in [None, "approved"])
    )

    return ReportDraftResponseDto(
        runId=runId,
        reportRunId=reportRunId,
        summary=ReportDraftSummaryDto(
            generatedPageCount=len(sectionsByKey),
            referencedKpiCount=len(atomicIds),
            evidenceLinkRate=round((paragraphsWithRefs / totalParagraphs) * 100, 1) if totalParagraphs else 0.0,
            revisionRequiredCount=revisionRequiredCount,
        ),
        sections=list(sectionsByKey.values()),
        downloadOptions=_downloadOptions(),
        implementationStatus="SKELETON",
        missingSchemaFields=REPORT_MISSING_SCHEMA_FIELDS,
        orderSource="ID_ASC_FALLBACK",
    )


def patchReportDraft(draftId: int, editedText: str) -> ReportDraftPatchResponseDto:
    # Phase 2A does not mutate report drafts because edited_text columns are not in the clean schema yet.
    existingDraft = getDraftById(draftId)
    if not existingDraft:
        return ReportDraftPatchResponseDto(
            draftId=draftId,
            editStatus="not_found",
            lastEditedAt=None,
            implementationStatus="SKELETON",
            missingSchemaFields=REPORT_MISSING_SCHEMA_FIELDS,
        )
    return ReportDraftPatchResponseDto(
        draftId=draftId,
        editStatus="not_saved_missing_schema",
        lastEditedAt=str(existingDraft.get("updated_at")) if existingDraft.get("updated_at") is not None else None,
        implementationStatus="SKELETON",
        missingSchemaFields=REPORT_MISSING_SCHEMA_FIELDS,
    )


def getParagraphTrace(runId: int, paragraphId: int) -> ReportTraceResponseDto:
    references = getReferencesForParagraph(paragraphId)
    traceType = _resolveTraceType(references)
    atomicIds = sorted({ref.get("atomic_metric_id") for ref in references if ref.get("atomic_metric_id")})
    atomicRows = getAtomicMetricRows(atomicIds)
    metrics = [_metricTraceFromAtomic(row) for row in atomicRows]

    latestValue = None
    valuesByYear = []
    companyBreakdown = []
    calculationFormula = None
    aiEvidenceSummary = "Phase 2A skeleton trace입니다. 조회 가능한 reference와 KPI/rollup 값만 반환합니다."

    if traceType == "DIRECT":
        directRef = next((ref for ref in references if ref.get("reference_type") in ["kpi_fact", "onboarding_input"]), None)
        if directRef and directRef.get("reference_type") == "kpi_fact":
            fact = getKpiFactById(_safeInt(directRef.get("reference_id")) or 0)
            latestValue = _valueFromRow(fact)
            if fact.get("company_id") is not None and fact.get("atomic_metric_id"):
                valuesByYear = [
                    YearValueDto(
                        year=int(row.get("reporting_year")),
                        value=_valueFromRow(row),
                        unit=row.get("unit"),
                        approvalStatus=row.get("approval_status"),
                    )
                    for row in getKpiFactsByCompanyAtomic(int(fact["company_id"]), fact["atomic_metric_id"])
                    if row.get("reporting_year") is not None
                ]
        calculationFormula = _resolveCalculationFormula(atomicRows)

    elif traceType == "GROUP_ROLLUP":
        rollupRef = next((ref for ref in references if ref.get("reference_type") == "rollup_result"), None)
        if rollupRef:
            rollup = getRollupResultById(_safeInt(rollupRef.get("reference_id")) or 0)
            latestValue = _valueFromRow(rollup)
            calculationFormula = rollup.get("calculation_trace") or _resolveCalculationFormula(atomicRows)
            if rollup.get("parent_company_id") is not None and rollup.get("group_atomic_metric_id"):
                valuesByYear = [
                    YearValueDto(
                        year=int(row.get("reporting_year")),
                        value=_valueFromRow(row),
                        unit=row.get("unit"),
                        approvalStatus=row.get("rollup_status"),
                    )
                    for row in getRollupResultsByParentAtomic(int(rollup["parent_company_id"]), rollup["group_atomic_metric_id"])
                    if row.get("reporting_year") is not None
                ]
            companyBreakdown = _parseCompanyBreakdown(
                rollup.get("source_company_values_json"),
                _safeInt(rollup.get("reporting_year")),
                rollup.get("unit"),
            )

    else:
        calculationFormula = _resolveCalculationFormula(atomicRows)

    return ReportTraceResponseDto(
        runId=runId,
        paragraphId=paragraphId,
        traceType=traceType,
        sourceModeLabel=_sourceModeLabel(traceType),
        metrics=metrics,
        latestValue=latestValue,
        valuesByYear=valuesByYear,
        companyBreakdown=companyBreakdown,
        calculationFormula=calculationFormula,
        aiEvidenceSummary=aiEvidenceSummary,
        relatedParagraphs=[],
        implementationStatus="SKELETON",
        missingSchemaFields=REPORT_MISSING_SCHEMA_FIELDS,
    )


def createReportDownload(runId: int, fileType: str) -> ReportDownloadResponseDto:
    reportRun = getLatestReportRunByMaterialityRun(runId)
    reportRunId = _safeInt(reportRun.get("id"))
    return ReportDownloadResponseDto(
        runId=runId,
        reportRunId=reportRunId,
        fileType=fileType,
        downloadUrl=None,
        expiresAt=None,
        availableYn=False,
        implementationStatus="SKELETON",
        message="Phase 2A에서는 다운로드 contract만 제공합니다. 실제 PDF/DOCX 생성은 P1 후속입니다.",
    )


def _downloadOptions() -> list[DownloadOptionDto]:
    return [
        DownloadOptionDto(fileType="pdf", label="PDF", availableYn=False),
        DownloadOptionDto(fileType="docx", label="DOCX", availableYn=False),
    ]


def _groupReferencesByDraft(rows: list[dict]) -> dict:
    result = {}
    for row in rows:
        draftId = _safeInt(row.get("report_section_draft_id"))
        if draftId is None:
            continue
        result.setdefault(draftId, []).append(row)
    return result


def _resolveTraceType(references: list[dict]) -> str:
    types = {ref.get("reference_type") for ref in references}
    if "rollup_result" in types:
        return "GROUP_ROLLUP"
    if "kpi_fact" in types or "onboarding_input" in types:
        return "DIRECT"
    return "UNKNOWN"


def _sourceModeLabel(traceType: str) -> str:
    if traceType == "GROUP_ROLLUP":
        return "그룹 통합 지표"
    if traceType == "DIRECT":
        return "직접 관리 지표"
    return "출처 유형 미확정"


def _metricTraceFromAtomic(row: dict) -> ReportMetricTraceDto:
    return ReportMetricTraceDto(
        metricId=row.get("metric_id"),
        atomicMetricId=row.get("atomic_metric_id"),
        metricName=row.get("metric_name_kr"),
        atomicMetricName=row.get("atomic_name_kr"),
        unit=row.get("unit"),
        dataType=row.get("data_value_type"),
    )


def _resolveCalculationFormula(atomicRows: list[dict]) -> Optional[str]:
    for row in atomicRows:
        if row.get("calculation_formula"):
            return row.get("calculation_formula")
        if row.get("calculation_rule_code"):
            rule = getCalculationRuleByAtomicMetric(row["atomic_metric_id"])
            if rule.get("calculation_formula_label"):
                return rule["calculation_formula_label"]
    return None


def _parseCompanyBreakdown(rawJson, year: Optional[int], unit: Optional[str]) -> list[CompanyBreakdownDto]:
    if not rawJson:
        return []
    try:
        parsed = json.loads(rawJson)
    except Exception:
        return []

    if isinstance(parsed, dict):
        values = parsed.get("companies") or parsed.get("companyBreakdown") or parsed.get("sourceCompanyValues") or []
        if isinstance(values, dict):
            values = [{"companyName": key, "value": value} for key, value in values.items()]
    elif isinstance(parsed, list):
        values = parsed
    else:
        values = []

    total = 0.0
    normalized = []
    for item in values:
        if not isinstance(item, dict):
            continue
        value = _safeFloat(item.get("value") or item.get("value_numeric") or item.get("contributionValue"))
        if value is not None:
            total += value
        normalized.append((item, value))

    result = []
    for item, value in normalized:
        result.append(
            CompanyBreakdownDto(
                companyId=_safeInt(item.get("companyId") or item.get("company_id")),
                companyName=item.get("companyName") or item.get("company_name") or item.get("companyCode"),
                year=_safeInt(item.get("year")) or year,
                value=value if value is not None else item.get("value_text"),
                unit=item.get("unit") or unit,
                contributionRate=round((value / total) * 100, 1) if value is not None and total > 0 else None,
            )
        )
    return result


def _valueFromRow(row: dict):
    if not row:
        return None
    numeric = row.get("value_numeric")
    if numeric is not None:
        return _safeFloat(numeric)
    return row.get("value_text")


def _safeFloat(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safeInt(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
