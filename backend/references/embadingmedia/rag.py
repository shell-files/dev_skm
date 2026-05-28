"""
RAG pipeline의 전처리/필터링 모듈 (v4.2 사전 대응 버전)

이 모듈은 SUBISSUE_MASTER 사전에 정의된 키워드들을 기반으로 뉴스 청크를 필터링하고,
해당 서브이슈의 상세 메타데이터를 결합하여 임베딩 단계로 전달합니다.
"""

import json
import re
from preprocess import splitChunk
from subissuemaster import subissueMaster
from core.paths import (
    trainJsonl,
    processedJsonl
)

INPUT_FILE = trainJsonl
OUTPUT_FILE = processedJsonl

def mapSubissues(text):
    matchedIds = []
    # 텍스트를 미리 소문자로 변환하여 비교 효율성 증대
    lowerText = text.lower() 
    
    for subId, info in subissueMaster.items():
        keywords = info.get("keywordKr", []) + info.get("keywordForeignEn", [])
        
        for keyword in keywords:
            if not keyword: continue
            
            # 영문/숫자 키워드의 경우 독립된 단어인지 검사 (예: SS, ESS 구분)
            if keyword.isalnum():
                # \b는 단어 경계를 의미함 (공백, 문장 부호 등)
                pattern = rf"\b{re.escape(keyword.lower())}\b"
                if re.search(pattern, lowerText):
                    matchedIds.append(subId)
                    break
            else:
                # 한글의 경우 품사 분석이 없으면 단순 포함을 쓰되, 
                # 필요 시 ' SS '처럼 앞뒤 공백을 명시하는 로직 추가
                if keyword.lower() in lowerText:
                    matchedIds.append(subId)
                    break
                    
    return list(dict.fromkeys(matchedIds))


def formatProcessedRecord(source, title, chunk, subId, domain):
    """
    v4.3 사전에 맞춰 메타데이터 키를 추출하고 
    최종 카멜 케이스(camelCase) 형식의 레코드를 생성하는 함수
    """
    metadata = subissueMaster.get(subId, {})
    
    
    return {
        "source": source,
        "title": title,
        "chunk": chunk,
        # v4.3 개편된 Kr 명칭 매핑 (KeyError 방지를 위해 get 기본값 설정)
        "issueGroup": metadata.get("issueGroupNameKr", "미분류"), 
        "issueGroupDomain": domain,
        "subIssueId": subId,
        "subIssueName": metadata.get("subIssueNameKr", "미분류")
    }


def run():
    print("RAG 단계: 최신 사전 기반 자동 키워드 매핑 및 필터링 수행")
    results = []

    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                paragraphs = data.get("paragraph", "")
                
                # 1. 텍스트 청크 분할
                chunks = splitChunk(paragraphs)

                for chunk in chunks:
                    # --- [추가] 필수 포함 키워드 필터링 ---
                    required_keywords = ["현대모비스", "자동차 부품", "자동차부품"]
                    if not any(k in chunk for k in required_keywords):
                        continue  # 이 키워드들이 없으면 다음 청크로 넘어감 (매칭 시도조차 안 함)
                    # ------------------------------------

                    # 2. 사전 기반 자동 매핑
                    subIds = mapSubissues(chunk)
                    
                    if not subIds:
                        continue  # 매칭되는 키워드가 없는 청크는 버림 (필터링)

                    # 3. 매칭된 각 서브이슈별로 레코드 생성
                    for subId in subIds:
                        metadata = subissueMaster.get(subId, {})
                        domain = metadata.get("domain", "Unknown")

                        record = formatProcessedRecord(
                            source=data.get("source"),
                            title=data.get("title"),
                            chunk=chunk,
                            subId=subId,
                            domain=domain,

                        )
                        results.append(record)

        # 4. 결과 저장
        with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
            for record in results:
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"RAG 완료: {len(results)}개 매칭된 청크 생성 -> {OUTPUT_FILE}")
        
    except FileNotFoundError:
        print(f"오류: 입력 파일 {INPUT_FILE}을 찾을 수 없습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    run()