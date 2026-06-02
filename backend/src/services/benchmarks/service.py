import uuid
import shutil
import os
from fastapi import UploadFile
from pathlib import Path
from src.utils.settings import settings
from src.utils.db import save, findOne
from src.models.model import ResponseModel, UserModel
from src.models.benchmk import FileModel, FileFindModel
from src.utils.ocraiv8 import gemini
from src.utils.dmarepository import saveSignals
from src.utils.dmascoring import scoreSignals
from src.services.benchmarks.adapter import convertToDmaSignals

def normalizeSourceType(value: str) -> str:
    if not value:
        raise ValueError("sourceType is required. Provide sourceType or TE_SR_FILE.type.")
        
    mapping = {
        "Leader": "leader_sr",
        "leader": "leader_sr",
        "리더": "leader_sr",
        "Peer": "peer_sr",
        "peer": "peer_sr",
        "피어": "peer_sr",
        "Own": "own_sr",
        "owner": "own_sr",
        "자사": "own_sr",
        "news": "news",
        "agency": "agency",
        "regulation": "regulation",
    }
    normalized = mapping.get(value, value)
    
    ALLOWED_SOURCE_TYPES = {
        "leader_sr", "peer_sr", "own_sr",
        "news", "agency", "regulation",
        "survey_employee", "survey_management", "survey_external"
    }
    
    if normalized not in ALLOWED_SOURCE_TYPES:
        raise ValueError(f"Invalid source_type: {value} (normalized to: {normalized})")
        
    return normalized

def uploadSr(fileModel: FileModel, userModel: UserModel):
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
    saved_files = []
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
        params = (file.filename, fileName, fileModel.fileType, fileModel.companyName, userModel.id)
        saveResult = save(sql, params)
        if saveResult:
            path = UPLOAD_DIR / fileName
            with path.open("wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_files.append({"fileName": fileName, "origin": file.filename})
        else:
            return ResponseModel(False, f"파일 업로드에 실패했습니다. {file.filename}")
            
    return ResponseModel(True, "파일이 성공적으로 업로드되었습니다.", {"files": saved_files, "page": fileModel.page})
    
# 파일 찾기
async def findSr(fileFindModel: FileFindModel, userModel: UserModel):
    UPLOAD_DIR = Path(settings.file_dir)
    results = []
    filePaths = []
    fileMetaByName = {}
    
    for file in fileFindModel.file:
        fileIdSql = f"""
                SELECT id, aes_d( `origin` , '{settings.maria_db_key}' ) AS `origin`
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
        
        fileId = result["id"]
        sourceTitle = result["origin"]

        if isinstance(dbFileName, bytes):
            dbFileName = dbFileName.decode('utf-8')
        dbFileName = dbFileName.replace('\x00', '').strip()
        filePath = UPLOAD_DIR / dbFileName
        
        if not filePath.exists():
            return ResponseModel(False, f"서버에서 {dbFileName}파일을 찾을 수 없습니다.")
            
        # source_type 처리: DB type 우선, request sourceType은 fallback
        sourceTypeRaw = result.get("type") or fileFindModel.sourceType
        sourceType = normalizeSourceType(sourceTypeRaw)
        
        # 결과 리스트에 source_step, source_type 주입
        result["source_step"] = fileFindModel.sourceStep
        result["source_type"] = sourceType
        
        results.append(result)
        filePaths.append(str(filePath))
        
        # 메타데이터 맵에 저장
        fileMetaByName[dbFileName] = {
            "fileId": fileId,
            "sourceTitle": sourceTitle,
            "sourceType": sourceType,
        }
        
    finalResult = await gemini(results, filePaths)

    if not finalResult:
        return ResponseModel(False, "파일 분석에 실패했습니다. 다시 시도해주세요.")
    
    # 결과(BENCHMK TABLE)DB 저장
    if finalResult:
        for item in finalResult["data"]:
            if item == None:
                continue
            dbFileName = item.get("fileName")
            domainResult = "test" # 이건 나중에 AI 연결하면 변경
            resultList = item.get("result",[])

            # 파일 저장 실패 알림
            if not resultList or item.get("type") == "ERROR":
                raise Exception(f"{dbFileName} 파일 분석 중 AI 엔진 내부 오류가 발생했습니다.")
            
            # fileMetaByName에서 메타데이터 찾기
            fileMeta = fileMetaByName.get(dbFileName, {})
            fileId = fileMeta.get("fileId")
            sourceTitle = fileMeta.get("sourceTitle", dbFileName)
                    
            # DMASignal 객체 리스트로 변환
            signalsToSave = convertToDmaSignals(resultList, fileId)
            
            # Rule Engine을 호출하여 점수 산출
            scoredSignals = scoreSignals(signalsToSave)
                    
            # Repository를 통해 DB에 저장(동적으로 run_id 전달)
            try:
                saveSignals(
                    runId=fileFindModel.esgMaterialityRunId, 
                    signals=scoredSignals,
                    fileId=fileId,
                    sourceTitle=sourceTitle
                )
            except Exception as e:
                raise Exception(f"{dbFileName} 파일 분석 후 DB 저장 중 오류가 발생했습니다: {e}")
                
        return ResponseModel(True, "분석이 성공적으로 완료되었습니다.", finalResult)
           
    return finalResult
