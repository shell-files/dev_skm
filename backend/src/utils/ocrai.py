from google import genai
from google.genai import types
import json
import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter
from src.utils.settings import settings
from src.models.model import ResponseModel

router = APIRouter()

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
MAX_TASKS = 1
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Ollama LLM 호출용 함수
async def gemini(results: List[Dict[str, Any]], filePaths: List[str]) -> List[Dict[str, Any]]:
    
    semaphore = asyncio.Semaphore(MAX_TASKS)
    # 개별 파일 분석 함수
    async def oneGemini(result: Dict[str, Any], filePath: str) -> Dict[str, Any]:
        async with semaphore:
            uploadedFile = None
            fileName = result.get("file_name", "")
            companyName = result.get("company_name", "")
            type = result.get("type", "")
            try:
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
                
                data = {"fileName": result["file_name"], "companyName": result["company_name"], "type": result["type"], "result": clean(response.text)}
                return data
                
            except Exception as e:
                # 어느 파일에서 에러나는지 확인용
                print(f'{fileName}:', {str(e)})
                if uploadedFile:
                    try:
                        client.files.delete(name=uploadedFile.name)
                    except Exception:
                        pass  
                data = {"fileName": fileName, "companyName": companyName, "type": type, "result": []} 
                return data         
        
    tasks = [oneGemini(results[i], filePaths[i]) for i in range(len(filePaths))]
    
    totalOutputs = await asyncio.gather(*tasks, return_exceptions=True)

    finalResults = []
    for res in totalOutputs:
        if isinstance(res, Exception):
            finalResults.append({
                "fileName": "", 
                "companyName": "SYSTEM",
                "type": "ERROR",
                "result": [],
                "status": f"CRITICAL_SYSTEM_ERROR: {str(res)}"
            })
        else:
            finalResults.append(res)
    return ResponseModel(True, "분석이 완료되었습니다.", finalResults)


