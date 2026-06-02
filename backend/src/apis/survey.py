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
    try:
        template = loadSurveyTemplate()

        payload = {
            "title": f"{req.companyId} ESG Survey {int(time.time())}",
            "description": template.get("description", ""),
            "meta": template.get("meta", {}),
            "sections": template["sections"]
        }

        response = requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            timeout=180
        )

        data = response.json()

        if data.get("status") != "success":
            return {
                "status": False,
                "message": "Apps Script error",
                "data": data
            }

        return {
            "status": True,
            "message": "폼 생성 완료",
            "data": {
                "formId": data.get("formId"),
                "formUrl": data.get("formUrl"),
                "editUrl": data.get("editUrl"),
                "sheetId": data.get("sheetId"),
                "sheetUrl": data.get("sheetUrl")
            }
        }

    except Exception as e:
        return {
            "status": False,
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
        result = sheetsService.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="A:ZZ"
        ).execute()

        values = result.get("values", [])

        if not values:
            return {
                "status": False,
                "message": "No data found"
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
            writer.writerows(values)

        return {
            "status": True,
            "message": "CSV 생성 완료",
            "data": {
                "filePath": file_path,
                "rowCount": len(values)
            }
        }

    except Exception as e:
        return {
            "status": False,
            "message": str(e)
        }


# =========================
# DEBUG TEMPLATE
# =========================
@router.get("/raw")
def get_raw():
    return loadSurveyTemplate()