from src.utils.settings import settings


_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


def getSheetsService():
    from googleapiclient.discovery import build
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_APPLICATION_CREDENTIALS,
        scopes=[_READONLY_SCOPE],
    )
    return build("sheets", "v4", credentials=creds)
