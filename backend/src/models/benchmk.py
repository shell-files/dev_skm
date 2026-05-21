import uuid
import shutil
import os
from fastapi import UploadFile
from pathlib import Path
from src.utils.settings import settings
from src.utils.db import save, findOne
from src.models.model import ResponseModel, FileModel, UserModel, FileFindModel
from src.utils.ocrai import gemini

# 파일 업로드 및 저장
def uploadSr(fileModel:FileModel, userModel: UserModel):
    files = fileModel.file
    if len(files) == 0:
        return ResponseModel(False, "업로드된 파일이 없습니다.")
    if len(files) > 3:
        return ResponseModel(False, "파일은 최대 3개까지만 업로드 가능합니다.")
    for file in files:
        origin = file.filename
        ext = origin.split(".")[-1].lower()
        if ext != "pdf":
            return ResponseModel(False, "PDF 파일만 업로드 가능합니다.")
    UPLOAD_DIR = Path(settings.file_dir)
    UPLOAD_DIR.mkdir(exist_ok=True)
    for file in files:
        id = uuid.uuid4().hex
        fileName = f"{id}.{ext}"
        sql = f"""
            INSERT INTO skm.`TE_SR_FILE` (`origin`, `file_name`, `type`, `company_name`, `create_user_id`)
            values ( aes_e( ? , '{settings.maria_db_key}' )
                    ,aes_e( ? , '{settings.maria_db_key}' )
                    ,aes_e( ? , '{settings.maria_db_key}' )
                    ,aes_e( ? , '{settings.maria_db_key}' )
                    ,?);
            """
        params = (origin, fileName, fileModel.fileType, fileModel.companyName, userModel.id)
        saveResult = save(sql, params)
    # 동시에 로컬 폴더에도 파일 저장
    if saveResult:
        path = UPLOAD_DIR / fileName
        with path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        if saveResult:        
            return ResponseModel(True, "파일이 성공적으로 업로드되었습니다.", {"fileName": fileName, "origin": origin, "page":fileModel.page})
        else:
            return ResponseModel(False, "파일 업로드에 실패하였습니다. 다시 시도해주세요.")
    
#  파일 찾기
async def findSr(fileFindModel:FileFindModel, userModel: UserModel):
    UPLOAD_DIR = Path(settings.file_dir)
    results =[]
    filePaths = []
    for file in fileFindModel.file:
        fileIdSql = f"""
                SELECT aes_d( `origin` , '{settings.maria_db_key}' ) AS `origin`
                    ,aes_d( `file_name` , '{settings.maria_db_key}' ) AS `file_name`
                    ,aes_d( `type` , '{settings.maria_db_key}' ) AS `type`
                    ,aes_d( `company_name` , '{settings.maria_db_key}' ) AS `company_name`
                    ,`create_user_id`
                FROM skm.`TE_{fileFindModel.page}_FILE`
                WHERE file_name = aes_e(?, '{settings.maria_db_key}') AND create_user_id = ? AND delete_yn = 0;            
                """
        fileIdParams = (file, userModel.id)
        result = findOne(fileIdSql, fileIdParams)

        if not result:
            return ResponseModel(False, f"존재하지 않는 파일이 포함되어 있습니다: {file}")

        
        dbFileName = result["file_name"]

        if isinstance(dbFileName, bytes):
            dbFileName = dbFileName.decode('utf-8')
        dbFileName = dbFileName.replace('\x00', '').strip()
        filePath = UPLOAD_DIR / dbFileName
        
        if not filePath.exists():
            return ResponseModel(False, f"서버에서 {dbFileName}파일을 찾을 수 없습니다.")
        results.append(result)
        filePaths.append(str(filePath))
    finalResult = await gemini(results, filePaths)
    return ResponseModel(True, "", finalResult)

