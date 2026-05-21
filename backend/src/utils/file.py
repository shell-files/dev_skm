import uuid
import shutil
from pathlib import Path
from src.utils.settings import settings
from src.utils.db import save, findOne
from src.models.model import ResponseModel, FileModel, UserModel
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
            insert into skm.`TE_{fileModel.page}_FILE` (`origin`, `file_name`, `type`,`company_name`, create_user_id)
            values ( aes_e( ? , '{settings.maria_db_key}' )
                    ,aes_e( ? , '{settings.maria_db_key}' )
                    ,aes_e( ? , '{settings.maria_db_key}' )
                    ,aes_e( ? , '{settings.maria_db_key}' )
                    ,?)
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
def findSr(fileName, page, userModel: UserModel):
    UPLOAD_DIR = Path(settings.file_dir)
    fileIdSql = f"""
            SELECT id, aes_d(file_name, '{settings.maria_db_key}') as file_name, aes_d(origin, '{settings.maria_db_key}') as origin, aes_d(type, '{settings.maria_db_key}') as type, aes_d(company_name, '{settings.maria_db_key}') as company_name
            FROM skm.`TE_{page}_FILE`
            WHERE file_name = aes_e(?, '{settings.maria_db_key}') AND create_user_id = aes_e(?, '{settings.maria_db_key}') AND delete_yn = 0;"""
    fileIdParams = (fileName, userModel.id)
    # fileIdParams = (fileName,)
    result = findOne(fileIdSql, fileIdParams)
    print(result)
    if result:
        db_file_name = result["file_name"]
        filePath = UPLOAD_DIR / db_file_name
        if not filePath.exists():
            return ResponseModel(False, "서버에서 파일을 찾을 수 없습니다.")
        file = open(filePath, 'rb')
        finalResult = gemini(file)
        return ResponseModel(True, "", finalResult)
    else:
        return ResponseModel(False, "존재하지 않는 파일입니다.")
    
