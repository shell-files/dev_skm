# main.py
import os
import psutil
import time
import crawler_manager
import rag
import embedding

runSimilarity = False

def getMemoryUsage():
    """현재 프로세스의 메모리 사용량을 MB 단위로 반환"""
    process = psutil.Process(os.getpid())
    memBytes = process.memory_info().rss
    return memBytes / (1024 * 1024)

def runWithMonitoring(stepName, taskFunction):
    """각 단계를 실행하면서 시간과 메모리 변화를 측정 및 출력"""
    print(f"\n==================================================")
    print(f" [시작] {stepName}")
    print(f"==================================================")
    
    # 실행 전 상태 기록
    startTime = time.time()
    startMem = getMemoryUsage()
    print(f"  - 실행 전 메모리: {startMem:.2f} MB")
    
    # 작업 실행
    taskFunction()
    
    # 실행 후 상태 기록
    endTime = time.time()
    endMem = getMemoryUsage()
    
    elapsedTime = endTime - startTime
    memDelta = endMem - startMem
    
    print(f"--------------------------------------------------")
    print(f"  - 실행 후 메모리: {endMem:.2f} MB")
    print(f"  -  메모리 변동: {memDelta:+.2f} MB")
    print(f"  -  소요 시간  : {elapsedTime:.2f}초")
    print(f"==================================================\n")
    
    return {
        "step": stepName,
        "start_mem": startMem,
        "end_mem": endMem,
        "delta": memDelta,
        "time": elapsedTime
    }

def main():
    # psutil 설치 확인 안내
    try:
        import psutil
    except ImportError:
        print("메모리 측정을 위해 'psutil' 라이브러리가 필요합니다.")
        return

    initialMem = getMemoryUsage()
    print(f" 파이프라인 초기 구동 메모리: {initialMem:.2f} MB")
    
    reports = []

    # # 1/3 Crawler Step
    # reports.append(
    #     runWithMonitoring("1/3 크롤러 매니저 (crawler_manager.run)", crawler_manager.run)
    # )

    # 2/3 RAG Preprocessing Step (사전 기반 필터링 및 청크 분할)
    reports.append(
        runWithMonitoring("2/3 RAG 전처리 (rag.run)", rag.run)
    )

    # 3/3 Embedding Step (임베딩 모델 로드 및 벡터화)
    # ※ 이 단계에서 모델이 메모리에 로드되므로 메모리 증가 수치가 크게 나타날 것입니다.
    reports.append(
        runWithMonitoring("3/3 임베딩 모델링 (embedding.run)", embedding.run)
    )

    if runSimilarity:
        import similarity
        reports.append(
            runWithMonitoring("4/4 유사도 분석 (similarity.run)", similarity.run)
        )

    # 파이프라인 최종 메모리 리포트 출력
    finalMem = getMemoryUsage()
    print("\n==================================================")
    print(" [최종 파이프라인 메모리 실행 리포트]")
    print("==================================================")
    print(f"{'단계별 작업명':<30} | {'메모리 변화 (MB)':<12} | {'소요 시간':<8}")
    print("-" * 60)
    for r in reports:
        print(f"{r['step'][:25]:<30} | {r['delta']:>+11.2f} MB | {r['time']:>6.1f}초")
    print("-" * 60)
    print(f"총 누적 메모리 변동: {finalMem - initialMem:+.2f} MB (최종: {finalMem:.2f} MB)")
    print("==================================================")

if __name__ == "__main__":
    main()