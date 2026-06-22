<<<<<<< HEAD
﻿"""
formservice.py
레이어: Service (surveys)
역할: 설문 폼 생성·배포·조회 서비스.
"""
=======
>>>>>>> origin/skm_test
import copy
import json

import requests

from src.utils.settings import settings
<<<<<<< HEAD
from src.repositories.dmasurveyformrepository import (
=======
from src.utils.dmasurveyformrepository import (
>>>>>>> origin/skm_test
    SURVEY_FORM_WORKFLOW_TYPE,
    SURVEY_TEMPLATE_VERSION,
    claimRetryableSurveyFormTx,
    findSurveyRunContext,
    getOrFreezeSurveyFormSnapshotTx,
    getSurveyFormByRunId,
    markSurveyFormReadyTx,
    markSurveyFormRetryableBestEffort,
    toSurveyFormResponse,
)
<<<<<<< HEAD
from src.repositories.dmaworkflowrepository import upsertDmaWorkflowStatus
=======
from src.utils.dmaworkflowrepository import upsertDmaWorkflowStatus
>>>>>>> origin/skm_test

APPS_SCRIPT_URL = settings.APPS_SCRIPT_URL

# ── Workflow stage constants ─────────────────────────────────────────────────
_STAGE_TOP20_FREEZE  = "TOP20_FREEZE"
_STAGE_PAYLOAD_BUILD = "PAYLOAD_BUILD"
_STAGE_FORM_CREATE   = "FORM_CREATE"
_STAGE_URL_SAVE      = "URL_SAVE"
_STAGE_COMPLETED     = "COMPLETED"

_PROGRESS_TOP20_FREEZE  = 20
_PROGRESS_PAYLOAD_BUILD = 45
_PROGRESS_FORM_CREATE   = 70
_PROGRESS_URL_SAVE      = 90
_PROGRESS_COMPLETED     = 100


# ── Survey template helpers (SSOT — service.py re-imports from here) ─────────

def loadSurveyTemplate() -> dict:
    with open(settings.surveyTemplate, "r", encoding="utf-8") as f:
        return json.load(f)


def isTop5Question(question: dict) -> bool:
    return (
        question.get("type") == "top5"
        or question.get("code") == "RANKING_TOP5"
    )


def buildQuestion(question: dict, issues: list) -> dict:
    if isTop5Question(question):
        return {
            "type": "top5",
            "code": question["code"],
            "title": question["title"],
            "description": question.get("description", ""),
            "options": [{"code": issue["code"], "name": issue["name"]} for issue in issues],
        }
    return {
        "type": "grid",
        "code": question["code"],
        "title": question["title"],
        "description": question.get("description", ""),
        "group": question["group"],
        "rows": [{"code": issue["code"], "label": issue["name"]} for issue in issues],
        "columns": ["1", "2", "3", "4", "5"],
    }


def buildRespondent(template: dict, respondentType: str) -> "dict | None":
    respondent = next(
        (x for x in template["respondentTypes"] if x["value"] == respondentType),
        None,
    )
    if not respondent:
        return None

    issues = template["meta"]["issues"]
    sections: dict = {}

    for questionKey in respondent["questionSet"]:
        question = copy.deepcopy(template["questions"][questionKey])
        group = question.get("group", "common")
        if group not in sections:
            sections[group] = []
        sections[group].append(buildQuestion(question, issues))

    variants = []
    selector = respondent.get("selector")

    if selector:
        for option in selector["options"]:
            route = option["route"]
            order = ["common"]
            if route == "finance":
                order += ["finance"]
            elif route == "impact":
                order += ["impact"]
            elif route == "both":
                order += ["impact", "finance"]
            variants.append({"label": option["label"], "route": route, "order": order})
    else:
        variants.append({"label": "Default", "route": "all", "order": ["common", "impact", "finance"]})

    return {
        "value": respondent["value"],
        "label": respondent["label"],
        "selector": selector,
        "sections": sections,
        "variants": variants,
    }


def buildSurveyPayload(template: dict) -> dict:
    return {
        "meta": template["meta"],
        "respondents": {
            "employee":   buildRespondent(template, "employee"),
            "management": buildRespondent(template, "management"),
            "external":   buildRespondent(template, "external"),
        },
        "version": "v2",
    }


# ── Internal helpers ─────────────────────────────────────────────────────────

def _writeSurveyFormWorkflowStatus(
    *,
    runId: int,
    overallStatus: str,
    currentStage: str,
    progressPercent: int,
    startedYn: bool = False,
    completedYn: bool = False,
    errorStage: "str | None" = None,
    errorMessage: "str | None" = None,
) -> None:
    upsertDmaWorkflowStatus(
        runId=runId,
        workflowType=SURVEY_FORM_WORKFLOW_TYPE,
        overallStatus=overallStatus,
        currentStage=currentStage,
        progressPercent=progressPercent,
        startedYn=startedYn,
        completedYn=completedYn,
        errorStage=errorStage,
        errorMessage=errorMessage,
    )


def _recordSurveyFormWorkflowFailureBestEffort(
    *, runId: int, currentStage: str, progressPercent: int, error: Exception
) -> None:
    try:
        _writeSurveyFormWorkflowStatus(
            runId=runId,
            overallStatus="FAILED",
            currentStage=currentStage,
            progressPercent=progressPercent,
            errorStage=currentStage,
            errorMessage=str(error)[:1000],
        )
    except Exception as inner:
        print(f"[WARN] _recordSurveyFormWorkflowFailureBestEffort failed: {inner}")


def _extractSurveyUrls(forms: dict) -> "tuple[str, str, str]":
    def _single(val, label: str) -> str:
        if isinstance(val, str):
            return val
        if isinstance(val, dict):
            has_url = "url" in val
            has_form_url = "formUrl" in val
            if has_url and has_form_url:
                raise RuntimeError(
                    f"Multiple URL variants (url + formUrl) in {label!r} form entry"
                )
            if has_url:
                return val["url"]
            if has_form_url:
                return val["formUrl"]
            raise RuntimeError(f"No url or formUrl key in {label!r} form entry")
        raise RuntimeError(f"Unexpected form entry type {type(val).__name__!r} for {label!r}")

    # employee
    emp_primary = forms.get("employee")
    emp_alias   = forms.get("emp")
    if emp_primary is not None and emp_alias is not None:
        raise RuntimeError("Multiple employee URL variants (employee + emp)")
    emp_val = emp_primary if emp_primary is not None else emp_alias
    if emp_val is None:
        raise RuntimeError("Missing employee/emp URL in Apps Script response")
    employee_url = _single(emp_val, "employee")

    # management
    mgmt_primary = forms.get("management")
    mgmt_alias   = forms.get("exec")
    if mgmt_primary is not None and mgmt_alias is not None:
        raise RuntimeError("Multiple management URL variants (management + exec)")
    mgmt_val = mgmt_primary if mgmt_primary is not None else mgmt_alias
    if mgmt_val is None:
        raise RuntimeError("Missing management/exec URL in Apps Script response")
    management_url = _single(mgmt_val, "management")

    # external
    ext_primary = forms.get("external")
    ext_alias   = forms.get("ext")
    if ext_primary is not None and ext_alias is not None:
        raise RuntimeError("Multiple external URL variants (external + ext)")
    ext_val = ext_primary if ext_primary is not None else ext_alias
    if ext_val is None:
        raise RuntimeError("Missing external/ext URL in Apps Script response")
    external_url = _single(ext_val, "external")

    if not employee_url or not employee_url.strip():
        raise RuntimeError("employee URL is blank")
    if not management_url or not management_url.strip():
        raise RuntimeError("management URL is blank")
    if not external_url or not external_url.strip():
        raise RuntimeError("external URL is blank")

    return employee_url, management_url, external_url


# ── Main service function ────────────────────────────────────────────────────

def ensureSurveyFormForRun(runId: int) -> dict:
    if isinstance(runId, bool) or not isinstance(runId, int):
        raise ValueError(f"runId must be a strict int, got {type(runId).__name__}")
    if runId <= 0:
        raise ValueError(f"runId must be > 0, got {runId}")

<<<<<<< HEAD
    # 2단계: 실행 컨텍스트 조회 (companyId / year 획득)
=======
    # Step 2: Verify run exists (also gets companyId/year for payload injection)
>>>>>>> origin/skm_test
    runContext = findSurveyRunContext(runId)

    currentStage    = _STAGE_TOP20_FREEZE
    currentProgress = _PROGRESS_TOP20_FREEZE

<<<<<<< HEAD
    # 3단계: 워크플로우 상태 갱신 (RUNNING / TOP20_FREEZE / 20%)
=======
    # Step 3: Workflow RUNNING / TOP20_FREEZE / 20 / startedYn
>>>>>>> origin/skm_test
    _writeSurveyFormWorkflowStatus(
        runId=runId,
        overallStatus="RUNNING",
        currentStage=currentStage,
        progressPercent=currentProgress,
        startedYn=True,
    )

    formId   = None
    snapshot = None

    try:
<<<<<<< HEAD
        # 4단계: 스냅샷 Freeze 트랜잭션
=======
        # Step 4: Snapshot Freeze TX
>>>>>>> origin/skm_test
        freeze = getOrFreezeSurveyFormSnapshotTx(
            runId=runId, templateVersion=SURVEY_TEMPLATE_VERSION
        )
        formId   = freeze["id"]
        snapshot = freeze["snapshot"]

<<<<<<< HEAD
        # 5단계: 이미 READY 상태 — 멱등 반환
=======
        # Step 5: Already READY — idempotent return
>>>>>>> origin/skm_test
        if freeze.get("surveyStatus") == "READY" or freeze.get("survey_status") == "READY":
            _writeSurveyFormWorkflowStatus(
                runId=runId,
                overallStatus="COMPLETED",
                currentStage=_STAGE_COMPLETED,
                progressPercent=_PROGRESS_COMPLETED,
                completedYn=True,
            )
            existing_row = getSurveyFormByRunId(runId)
            if existing_row:
                return toSurveyFormResponse(existing_row)
            return toSurveyFormResponse(freeze)

<<<<<<< HEAD
        # 6단계: RETRYABLE 상태 — 스냅샷 재사용 claim
        if freeze.get("surveyStatus") == "RETRYABLE" or freeze.get("survey_status") == "RETRYABLE":
            claimRetryableSurveyFormTx(formId)

        # 8단계: PAYLOAD_BUILD / 45%
=======
        # Step 6: RETRYABLE — claim and reuse snapshot
        if freeze.get("surveyStatus") == "RETRYABLE" or freeze.get("survey_status") == "RETRYABLE":
            claimRetryableSurveyFormTx(formId)

        # Step 8: PAYLOAD_BUILD / 45
>>>>>>> origin/skm_test
        currentStage    = _STAGE_PAYLOAD_BUILD
        currentProgress = _PROGRESS_PAYLOAD_BUILD
        _writeSurveyFormWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

<<<<<<< HEAD
        # 9-10단계: 템플릿 로드 및 컨텍스트 주입
=======
        # Step 9-10: Load template, inject context
>>>>>>> origin/skm_test
        template = loadSurveyTemplate()
        issues_for_template = [
            {
                "code": item["subIssueCode"],
                "name": item["subIssueName"],
                "rank": item["rankNo"],
            }
            for item in snapshot
        ]
        template["meta"]["companyId"] = runContext["companyId"]
        template["meta"]["runId"]     = runId
        template["meta"]["year"]      = runContext["reportingYear"]
        template["meta"]["issues"]    = issues_for_template

<<<<<<< HEAD
        # 11단계: 페이로드 빌드
        payload = buildSurveyPayload(template)

        # 12단계: FORM_CREATE / 70%
=======
        # Step 11: Build payload
        payload = buildSurveyPayload(template)

        # Step 12: FORM_CREATE / 70
>>>>>>> origin/skm_test
        currentStage    = _STAGE_FORM_CREATE
        currentProgress = _PROGRESS_FORM_CREATE
        _writeSurveyFormWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

<<<<<<< HEAD
        # 13단계: Apps Script POST 요청
=======
        # Step 13: Apps Script POST
>>>>>>> origin/skm_test
        try:
            response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=600)
        except Exception as req_err:
            raise RuntimeError(f"Apps Script request failed: {req_err}") from req_err

<<<<<<< HEAD
        # 14단계: 응답 파싱
=======
        # Step 14: Strict response parse
>>>>>>> origin/skm_test
        try:
            data = response.json()
        except Exception:
            raise RuntimeError(
                f"Apps Script did not return JSON. status={response.status_code}"
                f" body={response.text[:200]!r}"
            )

        if data.get("status") != "success":
            raise RuntimeError(
                f"Apps Script returned non-success status: {data.get('status')!r}"
                f" detail={json.dumps(data)[:500]}"
            )

        master_sheet_id = data.get("data", {}).get("masterSheetId")
        if not master_sheet_id or not str(master_sheet_id).strip():
            raise RuntimeError("Apps Script response missing masterSheetId")

        forms = data.get("data", {}).get("forms")
        if forms is None:
            raise RuntimeError("Apps Script response missing forms")

        employee_url, management_url, external_url = _extractSurveyUrls(forms)

<<<<<<< HEAD
        # 15단계: URL_SAVE / 90%
=======
        # Step 15: URL_SAVE / 90
>>>>>>> origin/skm_test
        currentStage    = _STAGE_URL_SAVE
        currentProgress = _PROGRESS_URL_SAVE
        _writeSurveyFormWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

<<<<<<< HEAD
        # 16단계: DB에 READY 상태 저장
=======
        # Step 16: Mark READY in DB
>>>>>>> origin/skm_test
        markSurveyFormReadyTx(
            formId=formId,
            masterSheetId=str(master_sheet_id),
            employeeFormUrl=employee_url,
            managementFormUrl=management_url,
            externalFormUrl=external_url,
        )

<<<<<<< HEAD
        # 17단계: 워크플로우 COMPLETED / 100%
=======
        # Step 17: Workflow COMPLETED / 100
>>>>>>> origin/skm_test
        _writeSurveyFormWorkflowStatus(
            runId=runId,
            overallStatus="COMPLETED",
            currentStage=_STAGE_COMPLETED,
            progressPercent=_PROGRESS_COMPLETED,
            completedYn=True,
        )

<<<<<<< HEAD
        # 18단계: 저장된 행 반환
=======
        # Step 18: Return saved row
>>>>>>> origin/skm_test
        saved_row = getSurveyFormByRunId(runId)
        if saved_row:
            return toSurveyFormResponse(saved_row)

        return {
            "id": formId,
            "runId": runId,
            "templateVersion": SURVEY_TEMPLATE_VERSION,
            "surveyStatus": "READY",
            "top20Snapshot": snapshot,
            "masterSheetId": str(master_sheet_id),
            "employeeFormUrl": employee_url,
            "managementFormUrl": management_url,
            "externalFormUrl": external_url,
            "errorMessage": None,
            "generatedAt": None,
            "updatedAt": None,
        }

    except Exception as err:
        # Snapshot Freeze 이후 실패: RETRYABLE
        if formId is not None:
            try:
                markSurveyFormRetryableBestEffort(
                    formId=formId, errorMessage=str(err)
                )
            except Exception as _be_err:
                print(f"[WARN] markSurveyFormRetryableBestEffort raised: {_be_err}")
            try:
                _writeSurveyFormWorkflowStatus(
                    runId=runId,
                    overallStatus="RETRYABLE",
                    currentStage=currentStage,
                    progressPercent=currentProgress,
                    errorStage=currentStage,
                    errorMessage=str(err)[:1000],
                )
            except Exception as wf_err:
                print(f"[WARN] workflow RETRYABLE write failed: {wf_err}")
        else:
<<<<<<< HEAD
            # Freeze 이전 실패: FAILED
=======
            # Pre-freeze failure: FAILED
>>>>>>> origin/skm_test
            _recordSurveyFormWorkflowFailureBestEffort(
                runId=runId,
                currentStage=currentStage,
                progressPercent=currentProgress,
                error=err,
            )
        raise


# ── Manual API compatibility wrapper ────────────────────────────────────────

async def createFormProcess(req, token) -> dict:
    return ensureSurveyFormForRun(req.runId)
<<<<<<< HEAD


def getSurveyFormDetail(runId: int) -> dict | None:
    row = getSurveyFormByRunId(runId)
    if row is None:
        return None
    return toSurveyFormResponse(row)
=======
>>>>>>> origin/skm_test
