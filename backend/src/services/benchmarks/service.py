import uuid
import shutil
import os
from typing import Optional

from fastapi import UploadFile
from pathlib import Path
from src.utils.settings import settings
from src.utils.db import save, findOne
from src.models.model import ResponseModel, UserModel
from src.models.benchmk import FileModel, FileFindModel
from src.utils.ocraiv8 import gemini
from src.utils import dmaruleregistry
from src.utils.dmarepository import (
    saveSignals,
    step4ReplaceBenchmarkShadowTracesTx,
)
from src.utils.dmaworkflowrepository import upsertDmaWorkflowStatus
from src.utils.dmascoring import scoreSignals
from src.services.benchmarks.adapter import convertToDmaSignals, step0NormalizeBenchmarkFacts
from src.services.benchmarks.pg_service import fetchBenchmarkFromPg
from src.services.materialities.orchestrator import (
    step0BuildFactTrace,
    step2BuildBenchmarkScreeningPayloads,
)
from src.utils.subissuemaster import subissueMaster


def _writeBenchmarkWorkflowStatus(
    *,
    runId: int,
    overallStatus: str,
    currentStage: str,
    progressPercent: int,
    progressMode: str = "MILESTONE",
    processedCount=None,
    totalCount=None,
    errorStage=None,
    errorMessage=None,
    startedYn: bool = False,
    completedYn: bool = False,
) -> None:
    upsertDmaWorkflowStatus(
        runId=runId,
        workflowType="BENCHMARK",
        overallStatus=overallStatus,
        currentStage=currentStage,
        progressPercent=progressPercent,
        progressMode=progressMode,
        processedCount=processedCount,
        totalCount=totalCount,
        errorStage=errorStage,
        errorMessage=errorMessage,
        startedYn=startedYn,
        completedYn=completedYn,
    )


def _recordBenchmarkWorkflowFailureBestEffort(
    *,
    runId: int,
    currentStage: str,
    progressPercent: int,
    error: Exception,
) -> None:
    try:
        _writeBenchmarkWorkflowStatus(
            runId=runId,
            overallStatus="FAILED",
            currentStage=currentStage,
            progressPercent=progressPercent,
            errorStage=currentStage,
            errorMessage=str(error)[:1000],
        )
    except Exception as statusError:
        print(
            f"Warning: BENCHMARK workflow FAILED status write failed: {statusError}"
        )


def _resolvePgMode(requestFlag: Optional[bool]) -> bool:
    if requestFlag is not None:
        return requestFlag
    return settings.use_pg_pipeline


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
        "own": "own_sr",
        "owner": "own_sr",
        "자사": "own_sr",
        "자회사": "own_sr",
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


# (normalized DMA type, PGDB에 실제 저장된 type 값 목록)
_PG_SR_TYPES = [
    ("leader_sr", ["리더", "Leader", "leader"]),
    ("peer_sr",   ["피어",  "Peer",   "peer"]),
    ("own_sr",    ["자회사", "자사", "Own", "own", "owner"]),
]


async def _findSrFromPg(fileFindModel: FileFindModel, runId: int):
    # srYear 미지정 시 pg_service 쪽에서 기본 범위(2022-2024) 적용
    srYear = fileFindModel.pgSrYear or None

    currentStage = "PREPARE"
    currentProgress = 10
    _writeBenchmarkWorkflowStatus(
        runId=runId,
        overallStatus="RUNNING",
        currentStage=currentStage,
        progressPercent=currentProgress,
        startedYn=True,
    )
    try:
        allScoredSignals = []
        allRawResults = []
        allFactPayloads = []
        aiPolicy = dmaruleregistry.getPolicy("ai_fact_validation_policy")

        for idx, (srType, dbTypes) in enumerate(_PG_SR_TYPES):
            currentStage = "DOCUMENT_ANALYSIS"
            currentProgress = 20 + idx * 20
            _writeBenchmarkWorkflowStatus(
                runId=runId,
                overallStatus="RUNNING",
                currentStage=currentStage,
                progressPercent=currentProgress,
            )

            signals, rawResultList, sourceTitle = fetchBenchmarkFromPg(
                srType=srType,
                srTypes=dbTypes,
                srYear=srYear,
            )

            scoredSignals = scoreSignals(signals)
            if scoredSignals:
                saveSignals(
                    runId=runId,
                    signals=scoredSignals,
                    fileId=None,
                    sourceTitle=sourceTitle,
                )
                allScoredSignals.extend(scoredSignals)

            shadowFacts = step0NormalizeBenchmarkFacts(
                rawResultList,
                fileId=None,
                sourceType=srType,
                aiPolicy=aiPolicy,
            )
            for fact in shadowFacts:
                allFactPayloads.append(
                    step0BuildFactTrace(extractedFact=fact, sourceChannel="benchmark")
                )
            allRawResults.extend(rawResultList)

        currentStage = "BENCHMARK_SHADOW"
        currentProgress = 90
        _writeBenchmarkWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

        universeSubIssueCodes = [
            code for code, meta in subissueMaster.items()
            if meta.get("materiality_issue_pool_yn") == "Y"
        ]
        screeningPayloads = step2BuildBenchmarkScreeningPayloads(allFactPayloads, universeSubIssueCodes)
        step4ReplaceBenchmarkShadowTracesTx(
            runId=runId,
            factPayloads=allFactPayloads,
            screeningPayloads=screeningPayloads,
            expectedScreeningCount=len(universeSubIssueCodes),
        )

        currentStage = "COMPLETED"
        currentProgress = 100
        _writeBenchmarkWorkflowStatus(
            runId=runId,
            overallStatus="COMPLETED",
            currentStage=currentStage,
            progressPercent=currentProgress,
            completedYn=True,
        )

        return ResponseModel(
            True,
            f"PG 모드: 벤치마킹 분석 완료 ({len(allScoredSignals)}건)",
            {"savedCount": len(allScoredSignals), "srYear": srYear},
        )

    except Exception as e:
        _recordBenchmarkWorkflowFailureBestEffort(
            runId=runId,
            currentStage=currentStage,
            progressPercent=currentProgress,
            error=e,
        )
        raise


async def findSr(fileFindModel: FileFindModel, userModel: UserModel):
    runId = fileFindModel.esgMaterialityRunId

    if _resolvePgMode(fileFindModel.usePgPipeline):
        return await _findSrFromPg(fileFindModel, runId)

    UPLOAD_DIR = Path(settings.file_dir)
    results = []
    filePaths = []
    fileMetaByName = {}

    currentStage = "PREPARE"
    currentProgress = 20

    _writeBenchmarkWorkflowStatus(
        runId=runId,
        overallStatus="RUNNING",
        currentStage=currentStage,
        progressPercent=currentProgress,
        startedYn=True,
    )

    try:
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
                raise RuntimeError(f"존재하지 않는 파일이 포함되어 있습니다: {file}")

            dbFileName = result["file_name"]
            fileId = result["id"]
            sourceTitle = result["origin"]

            if isinstance(dbFileName, bytes):
                dbFileName = dbFileName.decode('utf-8')
            dbFileName = dbFileName.replace('\x00', '').strip()
            filePath = UPLOAD_DIR / dbFileName

            if not filePath.exists():
                raise RuntimeError(f"서버에서 {dbFileName}파일을 찾을 수 없습니다.")

            sourceTypeRaw = result.get("type") or fileFindModel.sourceType
            try:
                sourceType = normalizeSourceType(sourceTypeRaw)
            except ValueError as e:
                raise RuntimeError(str(e)) from e

            result["source_step"] = fileFindModel.sourceStep
            result["source_type"] = sourceType

            results.append(result)
            filePaths.append(str(filePath))

            fileMetaByName[dbFileName] = {
                "fileId": fileId,
                "sourceTitle": sourceTitle,
                "sourceType": sourceType,
            }

        currentStage = "DOCUMENT_ANALYSIS"
        currentProgress = 35

        _writeBenchmarkWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

        finalResult = await gemini(results, filePaths)

        if not finalResult:
            raise RuntimeError("파일 분석에 실패했습니다. 다시 시도해주세요.")

        currentStage = "BENCHMARK_SCORING"
        currentProgress = 80

        _writeBenchmarkWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

        factPayloads = []
        totalCount = len(finalResult["data"])
        processedCount = 0

        for item in finalResult["data"]:
            if item is None:
                continue
            dbFileName = item.get("fileName")
            resultList = item.get("result", [])

            if not resultList or item.get("type") == "ERROR":
                raise Exception(f"{dbFileName} 파일 분석 중 AI 엔진 내부 오류가 발생했습니다.")

            fileMeta = fileMetaByName.get(dbFileName, {})
            fileId = fileMeta.get("fileId")
            sourceTitle = fileMeta.get("sourceTitle", dbFileName)
            sourceType = fileMeta.get("sourceType")

            signalsToSave = convertToDmaSignals(resultList, fileId)
            scoredSignals = scoreSignals(signalsToSave)

            try:
                saveSignals(
                    runId=fileFindModel.esgMaterialityRunId,
                    signals=scoredSignals,
                    fileId=fileId,
                    sourceTitle=sourceTitle
                )
                try:
                    aiPolicy = dmaruleregistry.getPolicy("ai_fact_validation_policy")
                    shadowFacts = step0NormalizeBenchmarkFacts(
                        resultList,
                        fileId=fileId,
                        sourceType=sourceType,
                        aiPolicy=aiPolicy,
                    )
                    for fact in shadowFacts:
                        factPayloads.append(step0BuildFactTrace(
                            extractedFact=fact,
                            sourceChannel="benchmark",
                        ))
                except Exception as shadowError:
                    raise RuntimeError(f"Benchmark v1.3 shadow fact build failed: {shadowError}") from shadowError
            except RuntimeError:
                raise
            except Exception as e:
                raise Exception(f"{dbFileName} 파일 분석 후 DB 저장 중 오류가 발생했습니다: {e}")

            processedCount += 1
            currentProgress = 80 + min(10, int(processedCount / max(totalCount, 1) * 10))

            _writeBenchmarkWorkflowStatus(
                runId=runId,
                overallStatus="RUNNING",
                currentStage=currentStage,
                progressPercent=currentProgress,
                progressMode="ACTUAL_COUNT",
                processedCount=processedCount,
                totalCount=totalCount,
            )

        currentStage = "BENCHMARK_SHADOW"
        currentProgress = 95

        _writeBenchmarkWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

        try:
            universeSubIssueCodes = [
                code for code, meta in subissueMaster.items()
                if meta.get("materiality_issue_pool_yn") == "Y"
            ]
            screeningPayloads = step2BuildBenchmarkScreeningPayloads(factPayloads, universeSubIssueCodes)
            step4ReplaceBenchmarkShadowTracesTx(
                runId=fileFindModel.esgMaterialityRunId,
                factPayloads=factPayloads,
                screeningPayloads=screeningPayloads,
                expectedScreeningCount=len(universeSubIssueCodes),
            )
        except Exception as shadowError:
            raise RuntimeError(f"Benchmark v1.3 shadow replace transaction failed: {shadowError}") from shadowError

        currentStage = "COMPLETED"
        currentProgress = 100

        _writeBenchmarkWorkflowStatus(
            runId=runId,
            overallStatus="COMPLETED",
            currentStage=currentStage,
            progressPercent=currentProgress,
            completedYn=True,
        )

        return ResponseModel(True, "분석이 성공적으로 완료되었습니다.", finalResult)

    except Exception as e:
        _recordBenchmarkWorkflowFailureBestEffort(
            runId=runId,
            currentStage=currentStage,
            progressPercent=currentProgress,
            error=e,
        )
        raise
