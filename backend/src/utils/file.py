import uuid
import shutil
from pathlib import Path
from src.utils.db import save, findOne
from src.models.model import ResponseModel, FileModel
from src.utils.settings import settings

# 파일 업로드 및 저장
def uploadSr(fileModel:FileModel):
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
            insert into skm.`TE_{fileModel.page}_FILE` (`origin`, `file_name`, `type`,`company_name`)
            values (?,?,?,?)
            """
        params = (origin, fileName, fileModel.fileType, fileModel.companyName)
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
def findSr(fileName, page):
    UPLOAD_DIR = Path(settings.file_dir)
    fileIdSql = f"""
            SELECT id, file_name, origin, type, company_name
            FROM skm.`TE_{page}_FILE`
            WHERE file_name = ? AND delete_yn = 0;"""
    fileIdParams = (fileName,)
    result = findOne(fileIdSql, fileIdParams)
    if result:
        db_file_name = result["file_name"]
        local_file_path = UPLOAD_DIR / db_file_name
        if not local_file_path.exists():
            return ResponseModel(False, "서버에서 파일을 찾을 수 없습니다.")
        result = str(local_file_path.resolve())
        return ResponseModel(True, "", result)
    else:
        return ResponseModel(False, "존재하지 않는 파일입니다.")
    
# return에 파일 읽어온 값 주고 AI API에서 이 함수들 부르면 됨
