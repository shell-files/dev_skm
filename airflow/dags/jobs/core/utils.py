import json
from pathlib import Path
from selenium import webdriver
from jobs.core.cleaner import cleanText


def getDriver():
    """Chrome WebDriver 설정 및 생성"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    remote_url = "http://selenium-chrome:4444/wd/hub"
    return webdriver.Remote(command_executor=remote_url, options=options)


def createRow(
    source,
    date,
    title,
    url,
    paragraph,
    category=None,
    subIssue=None
):
    """표준 데이터 Row 생성 (category, subIssue 기본값 설정)"""
    return {
        "source": source,
        "date": date,
        "title": cleanText(title),
        "url": url,
        "category": category,
        "sub_issue": cleanText(subIssue),
        "paragraph": cleanText(paragraph)
    }


def clearJsonl(filename):
    file_path = Path(filename)
    if file_path.is_file():
        file_path.unlink()  # 파일 삭제
        print(f"기존 파일({filename})을 삭제했습니다.")


def saveJsonl(data, filename):
    """데이터를 JSONL 형식으로 저장"""
    with open(
        filename,
        "a",
        encoding="utf-8"
    ) as f:
        for row in data:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False
                ) + "\n"
            )
