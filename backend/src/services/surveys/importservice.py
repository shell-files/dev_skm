from __future__ import annotations

from src.repositories.dmasurveyresponserepository import (
    getReadySurveyFormForRun,
    replaceSurveyResponsesForFormTx,
)
from src.services.surveys import importmeta as _im
from src.services.surveys import importparser as _ip


def previewSurveyResponses(runId: int) -> dict:
    form = getReadySurveyFormForRun(runId)
    master_sheet_id = form["master_sheet_id"]
    survey_form_id = form["id"]

    workbook = _im._loadWorkbookValues(master_sheet_id)
    meta = _im._parseMetaSheets(workbook)

    rows, skipped = _ip.parseResponseSheets(
        run_id=runId,
        survey_form_id=survey_form_id,
        master_sheet_id=master_sheet_id,
        workbook=workbook,
        meta=meta,
    )

    return {
        "runId": runId,
        "surveyFormId": survey_form_id,
        "masterSheetId": master_sheet_id,
        "metaSheets": {
            "formRegistry": meta["formRegistry"],
            "selectorMap": meta["selectorMap"],
            "questionMap": meta["questionMap"],
            "issueMap": meta["issueMap"],
        },
        "responseSheets": meta["response_sheets"],
        "previewRows": rows[:20],
    }


def importSurveyResponsesForRun(runId: int) -> dict:
    form = getReadySurveyFormForRun(runId)
    master_sheet_id = form["master_sheet_id"]
    survey_form_id = form["id"]

    workbook = _im._loadWorkbookValues(master_sheet_id)
    meta = _im._parseMetaSheets(workbook)

    rows, skipped = _ip.parseResponseSheets(
        run_id=runId,
        survey_form_id=survey_form_id,
        master_sheet_id=master_sheet_id,
        workbook=workbook,
        meta=meta,
    )

    db_result = replaceSurveyResponsesForFormTx(
        runId=runId,
        surveyFormId=survey_form_id,
        rows=rows,
    )

    respondent_sets: dict = {}
    for row in rows:
        group = row["respondentGroup"]
        key = row["sourceResponseKey"]
        if group not in respondent_sets:
            respondent_sets[group] = set()
        respondent_sets[group].add(key)
    respondent_counts = {g: len(ks) for g, ks in respondent_sets.items()}

    return {
        "runId": runId,
        "surveyFormId": survey_form_id,
        "masterSheetId": master_sheet_id,
        "importedRowCount": len(rows),
        "insertedCount": db_result.get("insertedCount", len(rows)),
        "updatedCount": db_result.get("updatedCount", 0),
        "skippedCount": len(skipped),
        "respondentCounts": respondent_counts,
        "status": "success",
    }
