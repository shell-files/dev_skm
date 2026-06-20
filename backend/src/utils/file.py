"""
file.py
레이어: Utils
역할: 파일 업로드·저장·삭제 유틸리티.
"""
import uuid
import shutil
from pathlib import Path
import httpx
import json
from src.utils.settings import settings
from src.utils.db import save, findOne
from src.models.model import ResponseModel

# --------------------------
# 파일명 분리, 암호화 로직
# --------------------------

def licenseFile(file):
    """업로드된 라이선스 파일을 licenseFiles 디렉터리에 UUID 이름으로 저장하고 DB에 메타데이터를 기록한다."""
    UPLOAD_DIR = Path("licenseFiles")
    UPLOAD_DIR.mkdir(exist_ok=True)
    origin = file.filename
    ext = origin.split(".")[-1].lower()
    id = uuid.uuid4().hex
    newName = f"{id}.{ext}"
    folderPath = str(UPLOAD_DIR)
    sql = f"""
        insert into `skm`.`LICENSE_FILE` (`origin`, `ext`, `fileName`)
        values (?,?,?)
        """
    params = (origin, ext, newName)
    result = save(sql, params)
    fileIdSql = f"""
        SELECT id
        FROM `skm`.`LICENSE_FILE`
        WHERE fileName = ? AND delete_yn = 0;"""
    fileIdParams = (newName,)
    fileId = findOne(fileIdSql, fileIdParams)
    if result:
        path = UPLOAD_DIR / newName
        with path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        return ResponseModel(result, "성공", {"fileName": id, "ext": ext, "fileId": fileId})
    else:
        return ResponseModel(result, "실패", None)


# --------------------------
# 공공데이터포털 API 호출 로직 (사업자 등록증 진위여부 확인)
# --------------------------
async def checkBusinessStatus(businessNumber: str):
    """공공데이터포털 API로 사업자등록번호의 유효성과 사업 상태를 확인한다."""
    serviceKey = settings.service_key
    url = f"https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey={serviceKey}"
    payload = {
       "b_no": [businessNumber]
       }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )
        except Exception as e:
            return ResponseModel(False, f"네트워크 오류: {str(e)}")

    if response.status_code == 200:
        responseData = response.json()

        if responseData.get("data"):
            businessInfo = responseData["data"][0]

            if not businessInfo.get("tax_type_cd"):
                return ResponseModel(False, businessInfo.get("tax_type"))

            if businessInfo.get("b_stt_cd") == "03":
                return ResponseModel(False, "폐업 상태입니다.")

            return ResponseModel(True, "사업자 정보가 확인되었습니다.")

        return ResponseModel(False, "응답 데이터가 올바르지 않습니다.")
    else:
        return ResponseModel(False, "API 서버 응답 실패", {"code": response.status_code})
