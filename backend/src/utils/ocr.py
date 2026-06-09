import os
import io
import re
from fastapi import HTTPException
from google.cloud import vision
from src.utils.settings import settings
from src.models.model import ResponseModel

# --------------------------
# OCR 로직 (구글 클라우드 비전 API 사용)
# --------------------------

def ocr(data):
    keyPath = settings.ocr_key_path
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyPath
    client = vision.ImageAnnotatorClient()
    filePath = f'licenseFiles/{data["fileUuid"]}.{data["ext"]}'

    if not os.path.exists(filePath):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    try:
        # 1. 파일 읽기
        with io.open(filePath, 'rb') as file:
            content = file.read()

        image = vision.Image(content=content)

        # 2. 텍스트 감지
        response = client.text_detection(image=image)
        texts = response.text_annotations

        if response.error.message:
            raise HTTPException(status_code=500, detail=response.error.message)

        if not texts:
            return ResponseModel(False, "텍스트를 감지할 수 없습니다.")

        # 3. 결과 반환
        return ResponseModel(True, "텍스트를 성공적으로 감지했습니다.", {"text": texts[0].description.replace('\n', ' ').replace('-', '').strip()})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# --------------------------
# OCR로 추출된 텍스트에서 사업자등록증 주요 정보 추출 로직
# --------------------------

def licenseInfo(text):
    # 1. 입력이 딕셔너리 형태인 경우 'text' 키의 값을 사용, 그렇지 않으면 입력 자체를 텍스트로 간주
    if isinstance(text, dict):
        text = text.get("text", "") 
    else:
        text = text

    # 2. 가독성을 위해 불필요한 공백 및 줄바꿈 정리
    cleanText = re.sub(r'\s+', ' ', text)

    result = {
        "사업자등록번호": "",
        "상호": "",
        "성명": "",
        "개업연월일": "",
        "사업장소재지": "",
        "발급날짜": "",
        "발급세무서": ""
    }
    
    
    # 3. 각 항목별 정규표현식 패턴 설정
    try:
        # 1. 입력 유효성 검사 및 텍스트 추출
        if isinstance(text, dict):
            text = text.get("text", "")
        
        if not text or not isinstance(text, str):
            return result # 읽을 내용이 없으면 즉시 빈 결과 반환

        # 2. 가독성을 위해 불필요한 공백 및 줄바꿈 정리
        cleanText = re.sub(r'\s+', ' ', text)
        
        # 3. 각 항목별 정규표현식 패턴 설정
        patterns = {
            "사업자등록번호": r"등록번호\s*:\s*([\d-]+)",
            "상호": r"호\s*[:]?\s*([가-힣A-Za-z\d]+(?!\d{3}-\d{2}))",
            "성명": r"명\s*:\s*([^\s]+)",
            "개업연월일": r"개업연월일\s*:\s*([\d년\s*월\s*일]+)",
            "사업장소재지": r"사업장소재지\s*:\s*(.*?)(?=사업의|$)",
            "발급날짜": r"(\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일)",
            "발급세무서": r"([가-힣\s]+세무서)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, cleanText)
            if match:
                val = match.group(1).strip()

        # 4. 특정 항목 공백 제거 및 날짜 포맷팅
                if key in ["개업연월일", "발급날짜", "사업자등록번호"]:
                    val = re.sub(r'\s+', '', val)

                if key in ["개업연월일", "발급날짜"]:
                    val = val.replace("년", "-").replace("월", "-").replace("일", "").strip("-")

                result[key] = val

    except Exception as e:
        print(f"Error parsing license info: {e}")
        return result
            
    return result
