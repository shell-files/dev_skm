from src.utils.settings import settings

from googleapiclient.discovery import build
from google.oauth2 import service_account

import csv
import os

from src.services.surveys.formservice import (
    buildQuestion,
    buildRespondent,
    buildSurveyPayload,
    createFormProcess,
    loadSurveyTemplate,
)

# =========================
# Google Sheets API — Lazy Init
# =========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]


def _getSheetsService():
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_APPLICATION_CREDENTIALS,
        scopes=SCOPES,
    )
    return build("sheets", "v4", credentials=creds)


# =========================
# EXPORT CSV (Sheet 조회 API)
# =========================
async def exportCsvProcess(sheet_id, token):
    sheetsService = _getSheetsService()
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

            if not header_added:
                merged_rows.append(["response_sheet"] + header)
                header_added = True

            for row in data_rows:
                merged_rows.append([sheet_name] + row)

        if not merged_rows:
            return {"status": "empty", "message": "No response data found"}

        os.makedirs("exports", exist_ok=True)
        file_path = f"exports/{sheet_id}.csv"

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(merged_rows)

        return {
            "status": "success",
            "filePath": file_path,
            "sheetCount": len(sheet_names),
            "rowCount": len(merged_rows) - 1,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# =========================
# 템플릿 조회
# =========================
def getRawProcess():
    return loadSurveyTemplate()
