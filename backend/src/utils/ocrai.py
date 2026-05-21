from google import genai
from google.genai import types
import uuid
import json
import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Form, Path, UploadFile, File
from src.utils.settings import settings
from src.models.model import ResponseModel

# 모델 테스트용 
# psutil 설치함. uv remove psutil 필요
import time
import os
import csv
import psutil

# 테스트용
def log_performance_to_csv(model_name: str, start_time: float, start_mem: float, target_file_name: str, result_data: str):
    # 현재 시점의 측정값 계산
    end_time = time.time()
    process = psutil.Process(os.getpid())
    end_mem = process.memory_info().rss / (1024 * 1024)  # MB 단위 변환

    elapsed_time = end_time - start_time
    mem_used = end_mem - start_mem

    # 1. 콘솔 출력
    print(f"\n[Performance Log - {target_file_name}]")
    print(f"- 소요 시간: {elapsed_time:.2f}초")
    print(f"- 메모리 변화량: {mem_used:.2f} MB (최종: {end_mem:.2f} MB)")

    # ★ 수정 포인트: 로그를 기록할 CSV 파일명을 고정합니다.
    log_csv_path = "perf_log.csv"
    file_exists = os.path.exists(log_csv_path)
    
    with open(log_csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Model_Name", "Timestamp", "File_Name", "Elapsed_Time_Sec", "Memory_Used_MB", "Final_Memory_MB", "Result_Data"])
        
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        writer.writerow([
            f"모델명:{model_name}", 
            f"시점:{current_timestamp}", 
            f"파일명:{target_file_name}", 
            f"걸린시간:{elapsed_time:.2f}", 
            f"사용 메모리:{mem_used:.2f}", 
            f"최종 메모리:{end_mem:.2f}",
            f"결과:{result_data}"
        ])

router = APIRouter()

# Ollama Client 설정
# client = ollama.Client(host=settings.ollama_host)
# modelName = "gemma3:4b"

# Gemini Client 설정
client = genai.Client(api_key=settings.gemini_api_key)
modelName = settings.gemini_model

# JSON 응답 정제용 함수
def clean(responseText: str) -> list:
    if not responseText:
        return []
    try:
        # 1. 문자열 내의 이스케이프나 불필요한 공백을 파이썬 객체(List[Dict])로 변환
        data = json.loads(responseText.strip())
    except json.JSONDecodeError:
        # 혹시 문자열 처리가 더 필요할 경우를 대비한 가공
        cleanedStr = responseText.replace('\\n', '').replace('\\"', '"')
        data = json.loads(cleanedStr)
    return data

# 오류 방지를 위하여 Max 파일 수 제한 및 재시도 로직
MAX_TASKS = 3
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Ollama LLM 호출용 함수
async def gemini(results: List[Dict[str, Any]], filePaths: List[str]) -> List[Dict[str, Any]]:
    
    semaphore = asyncio.Semaphore(MAX_TASKS)
    # 개별 파일 분석 함수
    async def oneGemini(result: Dict[str, Any], filePath: str) -> Dict[str, Any]:
        # 테스트용 시간 및 메모리 기록
        async with semaphore:
            displayFilename = os.path.basename(filePath)
            for attempt in range(1, MAX_RETRIES + 1):
                start_time = time.time()
                process = psutil.Process(os.getpid())
                start_mem = process.memory_info().rss / (1024 * 1024) # MB 단위 
                uploadedFile = None

                try:
                    if attempt > 1:
                            print(f"[RETRY] {displayFilename} - 분석 실패로 인해 {attempt}번째 재시도를 시작합니다.")
                    fileConfig = types.UploadFileConfig(mime_type="application/pdf")
                    with open(filePath, "rb") as f:
                        uploadedFile = client.files.upload(file=f, config=fileConfig)

                    maxAttempts = 120  # 2초 * 120 = 최대 240초 대기
                    attempts = 0
                    
                    # 업로드 실패 예외처리
                    while True:
                        uploadedFile = client.files.get(name=uploadedFile.name)
                        if uploadedFile.state == types.FileState.ACTIVE:
                            break
                        elif uploadedFile.state == types.FileState.FAILED:
                            raise Exception("파일 업로드에 실패했습니다.")
                        elif attempts >= maxAttempts:
                            raise Exception("구글 서버의 파일 가공 대기 시간이 초과되었습니다.")
                        # 파일 읽다 죽지 않도록 3초 간격으로 상태 체크    
                        await asyncio.sleep(3)
                        uploadedFile = client.files.get(name=uploadedFile.name)
                        attempts += 1
                
                    prompt=f"""
                    Perform the role of a Double Materiality Assessment consultant.
                    Analyze the Double Materiality section of the provided file and extract the following information:  
                    
                    1. **Key Issues**:
                    - Identify between 5 and 15 key issues.
                    - List them in order of importance.
                    - Extract the corresponding sub-issues.

                    2. **Restrictions**:
                    - Responses must be limited to the `output format` provided below. Conversation content or additional text is not allowed.
                    - **You must return the final response strictly as a raw JSON list.** Do not include any markdown code block wrappers or extra text outside the JSON array.

                    **RETURN KOREAN**

                    ** **Output Format**:
                    __OUTPUT_FORMAT__

                    **OUTPUT EXAMPLE**=__OUTPUT_EXAMPLE__
                    """

                    # 문장 replace용
                    outputFormat = [{"issue": [str], "sub_issue": [str]}, {"issue": [str], "sub_issue": [str]}]
                    outputExample = [{"issue": "기후변화 대응", "sub_issue": "제조 공정, 공급망, 제품 포트폴리오 및 제품 사용 등 가치사슬 전반에 걸쳐 관여하며, 비즈니스 모델 및 재무 성과 영향과 관련됨"}]
                    
                    # for index, chunk in enumerate(text_chunks): 
                    refinedPrompt = prompt.replace("__OUTPUT_FORMAT__", str(outputFormat)).replace("__OUTPUT_EXAMPLE__", str(outputExample))
                

                    # gemini 모델 호출
                    # LLM API에 파일 데이터를 직접 전달
                    generationConfig = types.GenerateContentConfig(temperature=0.1)
                    response = client.models.generate_content(
                        model=settings.gemini_model,
                        contents=[uploadedFile, refinedPrompt],
                        config=generationConfig
                    )

                    # 업로드한 파일 삭제 (임시 파일 서버에 안 남게)
                    if uploadedFile:
                        client.files.delete(name=uploadedFile.name)
                        uploadedFile = None

                    data = {"companyName": result["company_name"], "type": result["type"], "result": clean(response.text)}
                    
                    # 테스트용 시간 및 메모리 기록 성공 시 호출
                    result = json.dumps(data, ensure_ascii=False, indent=2)
                    log_performance_to_csv(
                        model_name=settings.gemini_model, 
                        start_time=start_time, 
                        start_mem=start_mem, 
                        target_file_name=displayFilename, 
                        result_data=result
                    )
                    return ResponseModel(True, "분석이 완료되었습니다.", data)
                    
                except Exception as e:
                    if uploadedFile:
                        try:
                            client.files.delete(name=uploadedFile.name)
                        except Exception:
                            pass
                    # [측정 종료 및 CSV 기록] 실패 시에도 기록을 남김
                    errorMsg = f"오류 발생: {str(e)}"
                    log_performance_to_csv(
                        model_name=settings.gemini_model, 
                        start_time=start_time, 
                        start_mem=start_mem, 
                        target_file_name=displayFilename, 
                        result_data=errorMsg
                    )
                    raise HTTPException(status_code=500, detail=f"LLM 파일 분석 중 오류 발생: {str(e)}")
        
    tasks = [oneGemini(results[i], filePaths[i]) for i in range(len(filePaths))]
    
    totalOutputs = await asyncio.gather(*tasks, return_exceptions=True)
    print("총 분석 결과:", totalOutputs)  # 디버깅용 전체 결과 출력
    finalResults = []
    for res in totalOutputs:
        if isinstance(res, Exception):
            finalResults.append({
                "companyName": "SYSTEM",
                "type": "ERROR",
                "result": [],
                "status": f"CRITICAL_SYSTEM_ERROR: {str(res)}"
            })
        else:
            finalResults.append(res)
    return ResponseModel(True, "분석이 완료되었습니다.", finalResults)


