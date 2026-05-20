import ollama
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

router = APIRouter()

# Ollama Client 설정

client = genai.Client(api_key=settings.gemini_api_key)
modelName = "gemini-3.5-flash" 

#  청크용 함수
def chunk_text(text: str, chunk_size: int = 3000, overlap: int = 300) -> list:
    """
    텍스트를 지정된 크기(chunk_size)로 자르고, 문맥 유지를 위해 일정 부분(overlap)을 겹치게 분할합니다.
    """
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
        
    return chunks

# JSON 응답 정제용 함수
def clean_and_parse_json(response_text: str) -> list:
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
        
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        return []
    except Exception:
        # 정형 JSON 파싱 실패 시 빈 배열 반환하여 500 에러를 방지
        return []

@router.post("/llm_cal")
# Ollama LLM 호출용 함수
async def llm_cal(file: UploadFile = File(..., description="분석할 현대모비스 PDF 파일"),
model: str = Form(modelName, description="사용할 Gemini 모델명")) -> str:
# def llm_cal(fileName: str, page: str = "SR",  model: str = modelName) -> str:
    temp_file_path = f"temp_{uuid.uuid4()}.pdf"
    with open(temp_file_path, "wb") as f:
        f.write(await file.read())
    # file_response = findSr(fileName, page)
    
    try:
        # 2. PDF 파일을 바이너리(bytes) 형태로 읽기
        # reader = PdfReader(file_path)
        # pdf_text = ""
        # for page in reader.pages:
        #     text = page.extract_text()
        #     if text:
        #         pdf_text += text + "\n"
        # if not pdf_text.strip():
        #     raise ValueError("PDF 내부에서 텍스트를 추출할 수 없습니다.")
            
        # text_chunks = chunk_text(pdf_text, chunk_size=3500, overlap=350)
        # merged_issues = []

        uploaded_file = client.files.upload(file=temp_file_path)
        
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
        refined_prompt = prompt.replace("__OUTPUT_FORMAT__", str(outputFormat)).replace("__OUTPUT_EXAMPLE__", str(outputExample))
    
        # 3. LLM API에 파일 데이터를 직접 전달 (Ollama 멀티모달 표준 스펙)
        generation_config = types.GenerateContentConfig(temperature=0.1)

# 2. generate_content 호출
        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, refined_prompt],
            config=generation_config,
            stream=False
        )
        result = client.files.delete(name=uploaded_file.name)
        
        print("LLM Response:", result)  # 디버깅용 응답 출력
        return response.text
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 파일 분석 중 오류 발생: {str(e)}")


