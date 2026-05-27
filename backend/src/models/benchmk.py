import uuid
import shutil
import os
from fastapi import UploadFile
from pathlib import Path
from src.utils.settings import settings
from src.utils.db import save, findOne
from src.models.model import ResponseModel, FileModel, UserModel, FileFindModel
from src.utils.ocrai_v8 import gemini
from src.utils.dma_repository import save_dma_signals
from src.utils.dma_scoring import score_dma_signals
from src.models.dma_engine import DMASignal

def normalize_source_type(value: str) -> str:
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
            return ResponseModel(False, f"파일 업로드에 실패하였습니다: {file.filename}")
            
    return ResponseModel(True, "파일이 성공적으로 업로드되었습니다.", {"files": saved_files, "page": fileModel.page})
    
#  파일 찾기
async def findSr(fileFindModel:FileFindModel, userModel: UserModel):
    UPLOAD_DIR = Path(settings.file_dir)
    results =[]
    filePaths = []
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
        
        # result 딕셔너리에 id와 origin을 원본으로 남겨둠
        file_id = result["id"]
        source_title = result["origin"]

        if isinstance(dbFileName, bytes):
            dbFileName = dbFileName.decode('utf-8')
        dbFileName = dbFileName.replace('\x00', '').strip()
        filePath = UPLOAD_DIR / dbFileName
        
        if not filePath.exists():
            return ResponseModel(False, f"서버에서 {dbFileName}파일을 찾을 수 없습니다.")
            
        # source_type 처리: 입력값이 없으면 DB의 type 사용
        source_type_raw = fileFindModel.source_type if fileFindModel.source_type else result.get("type")
        
        # 결과 리스트에 source_step, source_type 주입
        result["source_step"] = fileFindModel.source_step
        result["source_type"] = normalize_source_type(source_type_raw)
        
        results.append(result)
        filePaths.append(str(filePath))
        
    finalResult = await gemini(results, filePaths)

    if not finalResult:
        return ResponseModel(False, "파일 분석에 실패하였습니다. 다시 시도해주세요.")
    

    # 결과(BENCHMK TABLE)DB 저장
    # 판단 ai 붙여서 도메인 넣기
    # 도메인 뽑 domainResult
    if finalResult:
        for item in finalResult["data"]:
            if item == None:
                continue
            dbFileName = item.get("fileName")
            domainResult = "test" # 이건 나중에 AI 연결하면 변경
            resultList = item.get("result",[])

            # 파일 저장 실패시 알림
            if not resultList or item.get("type") == "ERROR":
                raise Exception(f"{dbFileName} 파일 분석 중 AI 엔진 내부 오류가 발생했습니다.")
            
            # dbFileName을 이용해 원본 result 딕셔너리에서 file_id와 source_title을 찾음
            file_id = None
            source_title = dbFileName
            for res_dict in results:
                if res_dict.get("file_name") == dbFileName:
                    file_id = res_dict.get("id")
                    source_title = res_dict.get("origin", dbFileName)
                    break
                    
            # DMASignal 객체 리스트로 변환
            signals_to_save = []
            for res_dict in resultList:
                try:
                    # te_sr_file_id 를 주입
                    res_dict["te_sr_file_id"] = file_id
                    # ocrai_v8가 이제 DMASignal dict를 반환함
                    sig = DMASignal(**res_dict)
                    signals_to_save.append(sig)
                except Exception as e:
                    print(f"DMASignal parse error: {e}")
            
            # Rule Engine을 호출하여 점수 산출
            scored_signals = score_dma_signals(signals_to_save)
                    
            # Repository를 통해 DB에 저장 (동적으로 run_id 전달)
            try:
                save_dma_signals(
                    run_id=fileFindModel.esg_materiality_run_id, 
                    signals=scored_signals,
                    file_id=file_id,
                    source_title=source_title
                )
            except Exception as e:
                raise Exception(f"{dbFileName} 파일 분석 중 DB 저장 중 오류가 발생했습니다: {e}")
                
        return ResponseModel(True, "파일 분석에 성공하였습니다.", finalResult)
           
    return finalResult

    
