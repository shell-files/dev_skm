from src.models.model import ResponseModel

from src.utils.ai import (
    REPORT_TEMPLATES,
    ISSUE_MAP,
    getFactData,
    replaceTemplate,
    searchSrKnowledgeHybrid,
    compressSrContext,
    generateIssueReport,
    
)


def generateReportProcess(req, token):
    factData = getFactData(req.companyId, req.year)
    
    reportOutput = []

    for idx, template in enumerate(REPORT_TEMPLATES):

        issueInfo = ISSUE_MAP[idx + 1]

        filledText, usedMetrics = replaceTemplate(
            template,
            factData
        )

        rows = searchSrKnowledgeHybrid(
            issueInfo["subIssueName"],
            issueInfo["subIssueId"]
        )

        compressedContext = compressSrContext(rows)

        report = generateIssueReport(
            filledText,
            compressedContext
        )

        reportOutput.append({
            "section_no": idx + 1,
            "issue": issueInfo["subIssueName"],

            "template": template,
            "filled_template": filledText,

            "used_atomic_metrics": [
                {
                    "atomic_metric_id": metricId,
                    "value": factData.get(metricId, {}).get("value"),
                    "unit": factData.get(metricId, {}).get("unit")
                }
                for metricId in usedMetrics
                if metricId != "COMPANY_NAME"
            ],

            "report": report
        })

    return ResponseModel(
        True,
        "보고서 생성 완료",
        reportOutput
    )