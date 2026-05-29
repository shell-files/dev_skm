from fastapi import FastAPI, UploadFile, File
from google import genai
from google.genai import types
from pypdf import PdfReader, PdfWriter

from settings import settings

import tempfile
import asyncio
import traceback
import logging
import os
import time
import json

from pathlib import Path


# =========================
# 설정
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

log = logging.getLogger(__name__)

geminiKey = settings.gemini_api_key

modelName = settings.gemini_model

maxWait = 120
retryCount = 3

pageBatch = 10

saveDir = Path("storage/ocr")
chunkDir = saveDir / "chunks"

saveDir.mkdir(
    parents=True,
    exist_ok=True
)

chunkDir.mkdir(
    parents=True,
    exist_ok=True
)

app = FastAPI()

client = genai.Client(
    api_key=geminiKey
)


# =========================
# OCR 프롬프트 (camelCase 반영)
# =========================

PROMPT = """
You are OCR engine.

Extract ALL visible text.

Rules:

- Preserve page order
- No summarize
- No interpretation
- No omit
- Return RAW TEXT ONLY

IMPORTANT:
- Output each page with marker:
==Page N==
- Page numbers MUST continue sequentially
- NEVER restart page numbering
- NEVER duplicate page numbers
- Keep original page order
"""


# =========================
# 시간
# =========================

def getElapsedTime(startTime):
    return round(
        time.time() - startTime,
        2
    )


# =========================
# 업로드 대기
# =========================

async def waitActive(uploadedFile):

    startTime = time.time()

    while True:

        uploadedFile = client.files.get(
            name=uploadedFile.name
        )

        log.info(
            f"WAIT {uploadedFile.state}"
        )

        if uploadedFile.state == types.FileState.ACTIVE:
            return uploadedFile

        if uploadedFile.state == types.FileState.FAILED:
            raise Exception(
                "upload failed"
            )

        if getElapsedTime(startTime) > maxWait:
            raise Exception(
                "upload timeout"
            )

        await asyncio.sleep(2)


# =========================
# PDF 분할
# =========================

def splitPdf(pdfPath):

    reader = PdfReader(
        pdfPath
    )

    totalPage = len(
        reader.pages
    )

    pdfChunks = []

    for startPage in range(
        0,
        totalPage,
        pageBatch
    ):

        writer = PdfWriter()

        endPage = min(
            startPage + pageBatch,
            totalPage
        )

        for i in range(
            startPage,
            endPage
        ):
            writer.add_page(
                reader.pages[i]
            )

        tempFile = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        )

        with open(
            tempFile.name,
            "wb"
        ) as f:
            writer.write(f)

        pdfChunks.append({
            "filePath": tempFile.name,
            "startPage": startPage + 1,
            "endPage": endPage
        })

    return pdfChunks


# =========================
# OCR 호출
# =========================

async def generateContent(uploadedFile):

    for currentRetry in range(
        retryCount
    ):

        try:

            startTime = time.time()

            response = (
                client.models.generate_content(
                    model=modelName,
                    contents=[
                        uploadedFile,
                        PROMPT
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=65536
                    )
                )
            )

            extractedText = (
                response.text
                or ""
            ).strip()

            usageMetadata = getattr(
                response,
                "usage_metadata",
                None
            )

            if usageMetadata:
                log.info(
                    usageMetadata
                )

            log.info(
                f"OCR chars={len(extractedText)}"
            )

            if extractedText:

                return {
                    "text": extractedText,
                    "elapsedSec": getElapsedTime(startTime)
                }

        except Exception as e:
            traceback.print_exc()
            if "429" in str(e):
                log.info(
                    "quota wait 60 sec"
                )
                await asyncio.sleep(
                    60
                )
            else:
                await asyncio.sleep(
                    5
                )

    raise Exception(
        "OCR empty"
    )


# =========================
# OCR 배치
# =========================

async def processChunk(
    pdfPath,
    startPage,
    endPage
):

    uploadedFile = None

    try:

        with open(
            pdfPath,
            "rb"
        ) as f:

            uploadedFile = (
                client.files.upload(
                    file=f,
                    config=types.UploadFileConfig(
                        mime_type="application/pdf"
                    )
                )
            )

        uploadedFile = await waitActive(
            uploadedFile
        )

        ocrResult = await generateContent(
            uploadedFile
        )

        return {
            "pages": f"{startPage}-{endPage}",
            "text": ocrResult["text"],
            "generateSec": ocrResult["elapsedSec"]
        }

    finally:

        if uploadedFile:

            try:
                client.files.delete(
                    name=uploadedFile.name
                )
            except:
                pass


# =========================
# JSON 저장
# =========================

def saveJson(
    filename,
    pages,
    stats
):

    outputPath = (
        saveDir
        /
        f"{filename}.json"
    )

    jsonData = {
        "document": filename,
        "createdAt": time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "stats": stats,
        "pages": pages
    }

    with open(
        outputPath,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            jsonData,
            f,
            ensure_ascii=False,
            indent=2
        )

    return str(outputPath)


# =========================
# 전체 OCR
# =========================

async def runOcr(
    pdfPath,
    filename
):

    splitChunks = splitPdf(pdfPath)

    totalResults = []

    for idx, chunk in enumerate(
        splitChunks,
        start=1
    ):

        startPage = chunk["startPage"]
        endPage = chunk["endPage"]

        savePath = (
            chunkDir
            /
            f"{filename}_{startPage}_{endPage}.txt"
        )

        if savePath.exists():

            log.info(
                f"[SKIP] {startPage}~{endPage}"
            )

            continue

        log.info(
            f"[RUN {idx}/{len(splitChunks)}] {startPage}~{endPage}"
        )

        try:

            chunkResult = await processChunk(
                pdfPath=chunk["filePath"],
                startPage=startPage,
                endPage=endPage
            )

            with open(
                savePath,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    chunkResult["text"]
                )

            totalResults.append(
                chunkResult
            )

        finally:

            if os.path.exists(
                chunk["filePath"]
            ):
                os.remove(
                    chunk["filePath"]
                )

    return totalResults


# =========================
# API
# =========================

@app.post("/ocr")
async def ocr(
    file: UploadFile = File(...)
):

    tempFile = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    )

    try:

        tempFile.write(
            await file.read()
        )

        tempFile.close()

        fileStemName = (
            Path(
                file.filename
            )
            .stem
        )

        finalResult = await runOcr(
            tempFile.name,
            fileStemName
        )

        return {
            "status": True,
            "data": finalResult
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "status": False,
            "message": str(e)
        }

    finally:

        if os.path.exists(
            tempFile.name
        ):
            os.remove(
                tempFile.name
            )