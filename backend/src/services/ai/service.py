<<<<<<< HEAD
"""
service.py
레이어: Service (ai)
역할: AI ESG 보고서 생성 서비스 — LangChain + RAG 기반 섹션별 초안 생성.
"""
=======
>>>>>>> origin/skm_test
from src.models.model import ResponseModel

from src.utils.ai import (
    REPORT_TEMPLATES,
    ISSUE_MAP,
    getFactData,
    replaceTemplate,
    searchSrKnowledgeHybrid,
    compressSrContext,
    generateIssueReport,
    createReportRun
    
)


def generateReportProcess(req, token):
<<<<<<< HEAD
    """KPI Fact와 SR 지식 베이스를 결합해 섹션별 ESG 보고서 초안을 생성하고 DB에 저장한다."""
=======
>>>>>>> origin/skm_test
    factData = getFactData(req.companyId, req.year)
    
    reportOutput = []
    run_success, run_id, created_at = createReportRun(
        req.materialityRunId,
        req.companyId,
        req.year,
        "gemma4:e4b",
        "v1"
    )

    if not run_success:
        raise Exception("RUN 생성 실패")
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
            run_id=run_id,
            created_at=created_at,
            companyId=req.companyId,
            reportingYear=req.year,
            subIssueId=issueInfo["subIssueId"],
            sectionNo=idx + 1,
            template=template,
            filledText=filledText,
            compressedContext=compressedContext,
            factData=factData,
            usedMetrics=usedMetrics
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