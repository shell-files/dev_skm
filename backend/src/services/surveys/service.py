from src.utils.settings import settings

from googleapiclient.discovery import build
from google.oauth2 import service_account

import requests
import json
import csv
import os
import copy

from src.utils.db import findAll, saveMany

from datetime import datetime

# =========================
# Google Sheets API
# =========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

creds = service_account.Credentials.from_service_account_file(
    settings.GOOGLE_APPLICATION_CREDENTIALS,
    scopes=SCOPES
)

sheetsService = build(
    "sheets",
    "v4",
    credentials=creds
)

EMPLOYEE_SHEETS = [
    "전략기획",
    "재무·회계",
    "구매·공급망",
    "환경·안전",
    "법무·컴플라이언스",
    "리스크관리·내부감사",
    "인사·노무",
    "생산·연구개발·품질",
    "영업·홍보·일반지원·기타"
]

MANAGEMENT_SHEETS = [
    "경영진"
]

EXTERNAL_SHEETS = [
    "지역사회·시민사회",
    "투자자·금융기관",
    "산업·ESG 전문가"
]
ALL_SURVEY_SHEETS = (
    EMPLOYEE_SHEETS
    + MANAGEMENT_SHEETS
    + EXTERNAL_SHEETS
)
# =========================
# Apps Script URL
# =========================
APPS_SCRIPT_URL = settings.APPS_SCRIPT_URL

# =========================
# Load Template 
# =========================
def loadSurveyTemplate():
    with open(settings.surveyTemplate, "r", encoding="utf-8") as f:
        return json.load(f)


def getTop20Issues(runId: int):

    sql = """
        SELECT
            s.sub_issue_code,
            m.sub_issue_name_kr,
            s.rank_no
        FROM ESG_DMA_SCORE_SUMMARY s
        INNER JOIN ESG_SUB_ISSUE_MASTER m
            ON s.sub_issue_code = m.sub_issue_code
        WHERE s.esg_materiality_run_id = ?
        ORDER BY s.rank_no ASC
        LIMIT 20
    """

    rows = findAll(sql, (runId,))

    return [
        {
            "code": row["sub_issue_code"],
            "name": row["sub_issue_name_kr"],
            "rank": row["rank_no"]
        }
        for row in rows
    ]
def buildQuestion(question, issues):
    if question.get("type") == "top5":
        return {
            "type": "top5",
            "code": question["code"],
            "title": question["title"],
            "description": question.get("description", ""),
            "options": [
                {
                    "code": issue["code"],
                    "name": issue["name"]
                }
                for issue in issues
            ]
        }

    return {
        "type": "grid",
        "code": question["code"],
        "title": question["title"],
        "description": question.get("description", ""),
        "group": question["group"],
        "rows": [
            {
                "code": issue["code"],
                "label": issue["name"]
            }
            for issue in issues
        ],
        "columns": [
            "1",
            "2",
            "3",
            "4",
            "5",
        ]
    }
    
def saveSurveyFormMap(run_id, company_id, year, master_sheet_id, forms):

    rows = []

    for respondent_type, respondent_data in forms.items():
        for respondent_name, form in respondent_data.items():

            rows.append((
                run_id,
                company_id,
                year,
                master_sheet_id,
                form["formId"],
                respondent_type,
                respondent_name,
                form.get("route", "all")   # ⭐ 수정 핵심
            ))

    sql = """
        INSERT INTO ESG_SURVEY_FORM_MAP (
            run_id,
            company_id,
            reporting_year,
            master_sheet_id,
            form_id,
            respondent_type,
            respondent_name,
            route
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    saveMany(sql, rows)
    
def buildRespondent(template, respondentType):

    respondent = next(
        (
            x
            for x in template["respondentTypes"]
            if x["value"] == respondentType
        ),
        None
    )

    if not respondent:
        return None

    issues = template["meta"]["issues"]

    sections = {}

    for questionKey in respondent["questionSet"]:

        question = copy.deepcopy(
            template["questions"][questionKey]
        )

        group = question.get(
            "group",
            "common"
        )

        if group not in sections:
            sections[group] = []

        sections[group].append(
            buildQuestion(
                question,
                issues
            )
        )

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

            variants.append({
                "label": option["label"],
                "route": route,
                "order": order
            })

    else:

        variants.append({
            "label": respondent["label"],
            "route": "all",
            "order": [
                "common",
                "impact",
                "finance"
            ]
        })

    return {
        "value": respondent["value"],
        "label": respondent["label"],
        "selector": selector,
        "sections": sections,
        "variants": variants
    }
    
def buildSurveyPayload(template):

    return {
        "meta": template["meta"],

        "respondents": {
            "employee": buildRespondent(
                template,
                "employee"
            ),

            "management": buildRespondent(
                template,
                "management"
            ),

            "external": buildRespondent(
                template,
                "external"
            )
        },

        "version": "v2"
    }
    
def getSheetType(sheet_name):

    if sheet_name in EMPLOYEE_SHEETS:
        return "employee"

    if sheet_name in MANAGEMENT_SHEETS:
        return "management"

    if sheet_name in EXTERNAL_SHEETS:
        return "external"

    return "unknown"

def getSurveyResultProcess(sheet_id, token):

    sql = """
        SELECT form_id, respondent_type, respondent_name
        FROM ESG_SURVEY_FORM_MAP
        WHERE master_sheet_id = ?
    """

    forms = findAll(sql, (sheet_id,))

    summary = {
        "employee": 0,
        "management": 0,
        "external": 0
    }

    sheet_results = []

    for f in forms:

        values = sheetsService.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{f['respondent_name']}!A:ZZ"
        ).execute().get("values", [])

        count = max(len(values) - 1, 0)

        summary[f["respondent_type"]] += count

        sheet_results.append({
            "form_id": f["form_id"],
            "respondent_name": f["respondent_name"],
            "type": f["respondent_type"],
            "count": count
        })

    return {
        "status": "success",
        "summary": summary,
        "forms": sheet_results
    }
    
# =========================
# CREATE FORM 
# =========================
async def createFormProcess(req, token):

    template = loadSurveyTemplate()

    issues = getTop20Issues(req.runId)

    template["meta"]["companyId"] = req.companyId
    template["meta"]["runId"] = req.runId
    template["meta"]["year"] = req.year
    template["meta"]["issues"] = issues

    payload = buildSurveyPayload(template)

    
    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            timeout=600
        )

        try:
            data = response.json()
        except Exception:
            return {
                "status": "error",
                "message": "Apps Script did not return JSON",
                "raw": response.text
            }

        if data.get("status") != "success":
            return {
                "status": "error",
                "message": "Apps Script error",
                "detail": data
            }
        saveSurveyFormMap(
            req.runId,
            req.companyId,
            req.year,
            data["data"]["masterSheetId"],
            data["data"]["forms"]
        )
        return {
            "status": "success",
            "masterSheetId": data["data"]["masterSheetId"],
            "forms": data["data"]["forms"]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
        
# =========================
# EXPORT CSV (Sheet 조회 API) 아직 DB 저장 X
# =========================

async def exportCsvProcess(sheet_id, token):
    try:

            spreadsheet = sheetsService.spreadsheets().get(
                spreadsheetId=sheet_id
            ).execute()

            sheet_names = [
                s["properties"]["title"]
                for s in spreadsheet["sheets"]
                if s["properties"]["title"] in ALL_SURVEY_SHEETS
            ]

            merged_rows = []
            header_added = False

            for sheet_name in sheet_names:

                result = sheetsService.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=f"{sheet_name}!A:ZZ"
                ).execute()

                values = result.get("values", [])

                if not values:
                    continue

                header = values[0]
                data_rows = values[1:]

                # 첫 번째 응답 시트의 헤더만 사용
                if not header_added:
                    merged_rows.append(
                        ["response_sheet"] + header
                    )
                    header_added = True

                # 데이터 추가
                for row in data_rows:
                    merged_rows.append(
                        [sheet_name] + row
                    )

            if not merged_rows:
                return {
                    "status": "empty",
                    "message": "No response data found"
                }

            os.makedirs("exports", exist_ok=True)

            file_path = f"exports/{sheet_id}.csv"

            with open(
                file_path,
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as f:

                writer = csv.writer(f)
                writer.writerows(merged_rows)

            return {
                "status": "success",
                "filePath": file_path,
                "sheetCount": len(sheet_names),
                "rowCount": len(merged_rows) - 1
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
# =========================
# 템플릿 조회 
# =========================
def getRawProcess():
    return loadSurveyTemplate()