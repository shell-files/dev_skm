from fastapi import APIRouter, Depends, Response, Request
from src.utils.auth import get_token
from src.utils.settings import settings
from googleapiclient.discovery import build
from google.oauth2 import service_account
from src.models.model import CompanyModel

import requests
import json
import csv
import os
import time

router = APIRouter()


# =========================
# Apps Script URL
# =========================
APPS_SCRIPT_URL = settings.APPS_SCRIPT_URL

# =========================
# Google Sheets API
# =========================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = service_account.Credentials.from_service_account_file(
    settings.GOOGLE_APPLICATION_CREDENTIALS,
    scopes=SCOPES
)

sheetsService = build("sheets", "v4", credentials=creds)


# =========================
# Load Template (그대로 전달용)
# =========================
def loadSurveyTemplate():
    with open(settings.surveyTemplate, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# CREATE FORM (핵심: 가공 없음)
# =========================
@router.post("/create")
async def create_form(
    req: CompanyModel,
    token=Depends(get_token)
):
    template = loadSurveyTemplate()

    payload = {
        "title": f"{req.companyId} ESG Survey {int(time.time())}",
        "description": template.get("description", ""),
        "meta": template.get("meta", {}),

        "commonSections": template.get("commonSections", []),
        "employeeSections": template.get("employeeSections", []),
        "managerSections": template.get("managerSections", []),
        "externalSections": template.get("externalSections", [])
    }

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

        return {
            "status": "success",

            "employeeForm": {
                "id": data.get("employeeFormId"),
                "url": data.get("employeeFormUrl")
            },

            "managerForm": {
                "id": data.get("managerFormId"),
                "url": data.get("managerFormUrl")
            },

            "externalForm": {
                "id": data.get("externalFormId"),
                "url": data.get("externalFormUrl")
            },

            "sheet": {
                "id": data.get("sheetId"),
                "url": data.get("sheetUrl")
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# =========================
# EXPORT CSV (Sheet 조회 API)
# =========================
@router.get("/export/{sheet_id}")
async def export_to_csv(
    sheet_id: str,
    token=Depends(get_token)
):
    try:

        spreadsheet = sheetsService.spreadsheets().get(
            spreadsheetId=sheet_id
        ).execute()

        sheet_names = [
            s["properties"]["title"]
            for s in spreadsheet["sheets"]
            if "응답" in s["properties"]["title"]
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
# DEBUG TEMPLATE
# =========================
@router.get("/raw")
def get_raw():
    return loadSurveyTemplate()