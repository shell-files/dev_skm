import pandas as pd
from core.utils import getDriver, saveJsonl
from crawlers import impacton, esgeconomy
import time
from core.paths import (
    trainCsv,
    trainJsonl,
    errorCsv
)

# 저장 설정
SAVE_JSONL = "esg_ai_training_dataset.jsonl"
INPUT_FILE = "esg_ai_training_dataset.jsonl"
OUTPUT_FILE = "processed_esg_chunks.jsonl"

def crawlNewsSource3(driver):
    print("\n--- [소스 3] 크롤링 시작 ---")
    return [], []

CRAWLERS = [
    impacton.crawl,
    esgeconomy.crawl
]

def run():
    rows = []
    errors = []

    for crawlFunc in CRAWLERS:
        driver = getDriver()
        try:
            sourceRows, sourceErrors = crawlFunc(driver)
            
            # 소스 하나 끝날 때마다 즉시 리스트에 추가하고 메모리 점검
            rows.extend(sourceRows)
            errors.extend(sourceErrors)
            
            # [중간 저장] 소스 하나가 끝날 때마다 파일에 써두면 안정적입니다.
            tempDf = pd.DataFrame(sourceRows)
            tempDf.to_csv(f"temp_{crawlFunc.__name__}.csv", index=False, encoding="utf-8-sig")
            
        finally:
            driver.quit() # 브라우저를 닫아 메모리 점유 해제
            time.sleep(3)

    # 최종 결과 저장
    if rows:
        df = pd.DataFrame(rows)

        # 중복 제거
        # df.drop_duplicates(
        #     subset=["title", "sub_issue", "paragraph"],
        #     inplace=True
        # )

        # CSV 저장
        df.to_csv(
            trainCsv,
            index=False,
            encoding="utf-8-sig"
        )

        # JSONL 저장
        saveJsonl(
            df.to_dict(orient="records"),
            trainJsonl
        )

        print("\n✅ ESG AI 학습 데이터 저장 완료")
        print(f"총 데이터 수: {len(df)}")
        print(f"컬럼: {df.columns.tolist()}")

    else:
        print("\n❌ 저장할 데이터 없음")

    # 에러 로그 저장
    if errors:
        errDf = pd.DataFrame(errors)
        errDf.to_csv(
            errorCsv,
            index=False,
            encoding="utf-8-sig"
        )
        print(f"⚠️ 에러 {len(errDf)}건 저장 완료")
    else:
        print("✨ 에러 없음")

if __name__ == "__main__":
    run()