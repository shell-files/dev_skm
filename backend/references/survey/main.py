from fastapi import FastAPI
from pydantic import BaseModel

from googleapiclient.discovery import build
from google.oauth2 import service_account

from settings import settings

import requests
import json
import csv
import os
import time

app = FastAPI()


# =========================
# Apps Script URL
# =========================
APPS_SCRIPT_URL = settings.APPS_SCRIPT_URL

# =========================
# Google Sheets API
# =========================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = service_account.Credentials.from_service_account_file(
    "googleKey.json",
    scopes=SCOPES
)

sheetsService = build("sheets", "v4", credentials=creds)


# =========================
# Request Model
# =========================
class SurveyRequest(BaseModel):
    companyId: str


# =========================
# Load Template (그대로 전달용)
# =========================
def loadSurveyTemplate():
    with open("surveyTemplate.json", "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# CREATE FORM (핵심: 가공 없음)
# =========================
@app.post("/api/forms/create")
def create_form(req: SurveyRequest):

    template = loadSurveyTemplate()

    payload = {
        "title": f"{req.companyId} ESG Survey {int(time.time())}",
        "description": template.get("description", ""),
        "meta": template.get("meta", {}),

        # 핵심: 가공 없이 그대로 전달
        "sections": template["sections"]
    }

    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            timeout=180
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
            "formId": data.get("formId"),
            "formUrl": data.get("formUrl"),
            "editUrl": data.get("editUrl"),
            "sheetId": data.get("sheetId"),
            "sheetUrl": data.get("sheetUrl")
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# =========================
# EXPORT CSV (Sheet 조회 API)
# =========================
@app.get("/api/forms/export/{sheet_id}")
def export_to_csv(sheet_id: str):

    try:
        result = sheetsService.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="A:ZZ"
        ).execute()

        values = result.get("values", [])

        if not values:
            return {
                "status": "empty",
                "message": "No data found"
            }

        os.makedirs("exports", exist_ok=True)
        file_path = f"exports/{sheet_id}.csv"

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(values)

        return {
            "status": "success",
            "filePath": file_path,
            "rowCount": len(values)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# =========================
# DEBUG TEMPLATE
# =========================
@app.get("/api/survey/raw")
def get_raw():
    return loadSurveyTemplate()