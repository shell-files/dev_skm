from google import genai
from google.genai import types
import uuid
import json
from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from pathlib import Path
from pypdf import PdfReader
from src.utils.settings import settings
from src.utils.file import findSr
from src.models.model import UserModel

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
def clean(response_text: str) -> list:
    try:
        # 1. 문자열 내의 이스케이프나 불필요한 공백을 파이썬 객체(List[Dict])로 변환
        data = json.loads(response_text.strip())
    except json.JSONDecodeError:
        # 혹시 문자열 처리가 더 필요할 경우를 대비한 가공
        cleaned_str = response_text.replace('\\n', '').replace('\\"', '"')
        data = json.loads(cleaned_str)
    return data

@router.post("") # 테스트용. api는 날릴거임
# Ollama LLM 호출용 함수
async def gemini(file: UploadFile = File(..., description="분석할 PDF 파일"),
model: str = Form(modelName, description="사용할 Gemini 모델명")) -> str:
    
# 테스트용 시간 및 메모리 기록
    start_time = time.time()
    process = psutil.Process(os.getpid())
    start_mem = process.memory_info().rss / (1024 * 1024) # MB 단위    
    
    # PDF 파일 저장
    temp_file_path = f"temp_{uuid.uuid4()}.pdf"
    
    # file_response = findSr(fileName, page)
    
    try:
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())
        uploaded_file = client.files.upload(file=temp_file_path)
        max_attempts = 120  # 2초 * 120 = 최대 240초 대기
        attempts = 0
        while uploaded_file.state == types.FileState.PROCESSING:
            if attempts >= max_attempts:
                raise Exception("구글 서버의 파일 가공 대기 시간이 초과되었습니다. (Timeout)")
                
            time.sleep(2)  # 2초마다 상태 재확인
            uploaded_file = client.files.get(name=uploaded_file.name)
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
        generation_config = types.GenerateContentConfig(temperature=0.1)
        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, refinedPrompt],
            config=generation_config
        )
        # ollama 모델 호출
        # response = client.models.generate_content(
        #     model=model,
        #     contents=[uploaded_file, refined_prompt],
        #     config={
        #     "temperature": 0.1,  
        #     "num_ctx": 16384     # 대용량 PDF 문서가 잘리지 않도록 컨텍스트 창 확장
        # },
        # stream=False
        # ) 

        # 업로드한 파일 삭제 (임시 파일 서버에 안 남게)
        client.files.delete(name=uploaded_file.name)
        output = clean(response.text)
        result = json.dumps(output, ensure_ascii=False, indent=2)
        
        # 테스트용 시간 및 메모리 기록 성공 시 호출
        log_performance_to_csv(
            model_name=model, 
            start_time=start_time, 
            start_mem=start_mem, 
            target_file_name=file.filename, 
            result_data=result
        )
        return result
        
    except Exception as e:
    # [측정 종료 및 CSV 기록] 실패 시에도 기록을 남김
        log_performance_to_csv(model_name=settings.gemini_model, start_time=start_time, start_mem=start_mem, target_file_name=file.filename, result_data=f"오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM 파일 분석 중 오류 발생: {str(e)}")
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


