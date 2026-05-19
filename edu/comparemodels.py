import json
from pathlib import Path

# core.paths에서 이미 올바르게 지정된 경로 변수들을 가져옵니다.
from core.paths import similarityJsonl

# 1. AS-IS BGE-M3 결과: 기존에 생성된 공식 유사도 결과 (output/embeddings/similarityResults.jsonl)
BGE_RESULT_FILE = similarityJsonl 

# 2. TO-BE KR-SBERT 결과: 동일 폴더 내 SBERT 전용 최종 유사도 파일명 지정
# (유사도 분석 단계인 similarity.py의 OUTPUT_FILE 명칭과 완벽히 일치해야 합니다)
SBERT_RESULT_FILE = Path(similarityJsonl).parent / "similaritySbert.jsonl"

def padKorean(text, totalWidth):
    """ 한글 정렬 폭을 맞추기 위한 카멜 형식의 헬퍼 함수 """
    if not text:
        text = "미분류"
    # 한글(멀티바이트)은 2칸, 영문/숫자는 1칸 계산
    currentWidth = sum(2 if ord(char) > 128 else 1 for char in text)
    padding = totalWidth - currentWidth
    return text + (" " * max(0, padding))

def loadJsonl(filePath):
    """ JSONL 파일을 읽어오는 카멜 형식의 함수 """
    records = []
    try:
        with open(filePath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except FileNotFoundError:
        print(f"[경고] 파일을 찾을 수 없습니다: {filePath}")
    return records

def runComparison():
    """ 모델 결과 비교 분석 실행 메인 함수 """
    bgeRecords = loadJsonl(BGE_RESULT_FILE)
    sbertRecords = loadJsonl(SBERT_RESULT_FILE)

    if not bgeRecords or not sbertRecords:
        print("❌ 비교할 데이터가 부족합니다. 두 모델의 similarity 결과 파일 위치를 확인해 주세요.")
        print(f"   - BGE 경로: {BGE_RESULT_FILE} (존재 여부: {Path(BGE_RESULT_FILE).exists()})")
        print(f"   - SBERT 경로: {SBERT_RESULT_FILE} (존재 여부: {Path(SBERT_RESULT_FILE).exists()})")
        return

    print("=" * 90)
    print(f"  ★ 임베딩 모델 비교 분석 테이블 (BGE-M3 vs KR-SBERT-V40K) ★")
    print("=" * 90)

    mismatchCount = 0
    totalChunks = min(len(bgeRecords), len(sbertRecords))

    for i in range(totalChunks):
        bge = bgeRecords[i]
        sbert = sbertRecords[i]

        chunkText = bge.get("chunk", "")
        shortChunk = chunkText[:60] + "..." if len(chunkText) > 60 else chunkText

        # ==================================================================================
        # [카멜 케이스 필드 매칭] JSONL 내부에 저장된 카멜 케이스 키 값을 정확히 매칭합니다.
        # ==================================================================================
        bgeId = bge.get("bestSubIssueId") or "Unknown"
        bgeName = str(bge.get("bestSubIssueNameKr") or "미분류")
        bgeScoreRaw = bge.get("bestSimilarityScore")
        bgeScore = float(bgeScoreRaw) if bgeScoreRaw is not None else 0.0

        sbertId = sbert.get("bestSubIssueId") or "Unknown"
        sbertName = str(sbert.get("bestSubIssueNameKr") or "미분류")
        sbertScoreRaw = sbert.get("bestSimilarityScore")
        sbertScore = float(sbertScoreRaw) if sbertScoreRaw is not None else 0.0

        # 두 모델이 예측한 서브이슈 ID 비교
        isMismatch = (bgeId != sbertId)
        if isMismatch:
            mismatchCount += 1
            statusFlag = "⚠️ [결과 다름]"
        else:
            statusFlag = "✅ [결과 일치]"

        # 콘솔 정렬용 공백 패딩 적용
        bgeNamePadded = padKorean(bgeName, 30)
        sbertNamePadded = padKorean(sbertName, 30)

        # 에러가 나던 출력문 영역 수정 완료
        print(f"📌 [청크 {i+1}] {statusFlag}")
        print(f"   | 원문: {shortChunk}")
        print(f"   | [AS-IS] BGE-M3   -> 분류: {bgeNamePadded} | 유사도 점수: {bgeScore:.4f}")
        print(f"   | [TO-BE] KR-SBERT -> 분류: {sbertNamePadded} | 유사도 점수: {sbertScore:.4f}")
        
        # 점수 편차 계산
        scoreDiff = sbertScore - bgeScore
        print(f"   | 점수 변동폭: {scoreDiff:+.4f} (KR-SBERT가 점수를 더 {'높게' if scoreDiff > 0 else '낮게'} 줌)")
        print("-" * 90)

    print("\n" + "=" * 90)
    print(f"📊 최종 실험 요약")
    print(f"   - 총 비교 청크 수: {totalChunks}개")
    print(f"   - 두 모델의 분류 일치율: {((totalChunks - mismatchCount) / totalChunks) * 100:.1f}%")
    print(f"   - 다른 판단을 한 ⚠️ 케이스 수: {mismatchCount}개")
    print("=" * 90)

if __name__ == "__main__":
    runComparison()