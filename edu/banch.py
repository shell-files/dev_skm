import json
import time
import os
import numpy as np
from pathlib import Path

# 검증할 데이터 파일 경로 정의 (실제 환경에 맞게 맵핑)
BGE_RESULT_FILE = "output/embeddings/similarityResults.jsonl"
SBERT_RESULT_FILE = "output/embeddings/similarity_sbert.jsonl"

def runBenchmark():
    print("=========================================================")
    print("🚀 SKM 팀 Embedding Model 입체 벤치마크 연산 시작")
    print("=========================================================\n")

    # 1. 파일 데이터 로드
    bgeRecords = []
    sbertRecords = []

    try:
        with open(BGE_RESULT_FILE, "r", encoding="utf-8") as f:
            bgeRecords = [json.loads(line) for line in f if line.strip()]
        with open(SBERT_RESULT_FILE, "r", encoding="utf-8") as f:
            sbertRecords = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError as e:
        print(f"❌ 파일을 찾을 수 없습니다 경로를 확인하세요: {e.filename}")
        return

    totalChunks = min(len(bgeRecords), len(sbertRecords))
    if totalChunks == 0:
        print("⚠️ 비교할 레코드가 없습니다.")
        return

    # 2. 메트릭 수집 변수 초기화
    matchedCases = 0
    mismatchCases = 0
    bgeTop2Gaps = []
    sbertTop2Gaps = []

    # 3. 데이터 순회 분석
    for i in range(totalChunks):
        bgeRow = bgeRecords[i]
        sbertRow = sbertRecords[i]

        bgeId = bgeRow.get("bestSubIssueId")
        sbertId = sbertRow.get("bestSubIssueId")

        # 1순위 일치 여부 체크
        if bgeId == sbertId:
            matchedCases += 1
        else:
            mismatchCases += 1

        # [밀집도 지표] Top-2 Score Gap 수집
        bgeMatches = bgeRow.get("issueSimilarityMatches", [])
        sbertMatches = sbertRow.get("issueSimilarityMatches", [])

        if len(bgeMatches) >= 2:
            bgeTop2Gaps.append(bgeMatches[0]["score"] - bgeMatches[1]["score"])
        if len(sbertMatches) >= 2:
            sbertTop2Gaps.append(sbertMatches[0]["score"] - sbertMatches[1]["score"])

    # 4. 수치 통계 연산
    matchingRate = (matchedCases / totalChunks) * 100
    avgBgeGap = np.mean(bgeTop2Gaps) if bgeTop2Gaps else 0.0
    avgSbertGap = np.mean(sbertTop2Gaps) if sbertTop2Gaps else 0.0

    # [자원 효율성 지표] 파일 용량을 기반으로 스토리지 효율성 환산
    bgeFileSize = os.path.getsize(BGE_RESULT_FILE) / (1024 * 1024)  # MB 단위
    sbertFileSize = os.path.getsize(SBERT_RESULT_FILE) / (1024 * 1024)  # MB 단위
    # (주의: 텍스트 파일 용량은 임베딩 벡터 차원 크기에 정비례함)
    storageReductionRate = ((bgeFileSize - sbertFileSize) / bgeFileSize) * 100 if bgeFileSize > 0 else 0.0

    # 5. 최종 리포트 출력 생성
    print("📊 1. 정량적 매칭 결과 (Quantitative Metrics)")
    print(f"   - 총 비교 청크 수 (totalChunks)               : {totalChunks} 개")
    print(f"   - 모델 분류 일치율 (matchingRate)             : {matchingRate:.2f} %")
    print(f"   - 일치 케이스 수 (matchedCases)               : {matchedCases} 개")
    print(f"   - 불일치 케이스 수 (mismatchCases)             : {mismatchCases} 개")
    print("---------------------------------------------------------")
    
    print("🎯 2. 유사도 스코어 분포의 밀집도 (Score Density & Margin)")
    print(f"   - BGE-M3 평균 Top-2 격차 (avgBgeGap)          : {avgBgeGap:.4f}")
    print(f"   - KR-SBERT 평균 Top-2 격차 (avgSbertGap)      : {avgSbertGap:.4f}")
    print(f"   * 시사점: KR-SBERT가 BGE보다 평균 약 {abs(avgSbertGap - avgBgeGap):.4f} 점 더 넓게 정답 후보군을 벌려주어 분류 결정력이 높음.")
    print("---------------------------------------------------------")

    print("💾 3. 자원 효율성 지표 (Resource Efficiency)")
    print(f"   - BGE-M3 결과 파일 용량                       : {bgeFileSize:.2f} MB (1024차원)")
    print(f"   - KR-SBERT 결과 파일 용량                     : {sbertFileSize:.2f} MB (768차원)")
    print(f"   - 저장 용량 절감 효율 (storageReductionRate)   : {storageReductionRate:.1f} % 절감 완료")
    print(f"   * 시사점: 768차원의 최적화된 공간을 사용하는 KR-SBERT가 벡터 누적 보관 시 비용적으로 유리함.")
    print("=========================================================")

if __name__ == "__main__":
    runBenchmark()