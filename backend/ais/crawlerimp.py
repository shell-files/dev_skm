from selenium import webdriver
from selenium.webdriver.common.by import By

import pandas as pd
import time
import re
import json

from datetime import datetime

# =========================================================
# 공통 설정
# =========================================================

TARGET_DATE = datetime(2023, 1, 1)

EXCLUDE_KEYWORD = "<임팩트온>은 지난주 지속가능경영"

SAVE_JSONL = "esg_ai_training_dataset.jsonl"

# =========================================================
# Chrome 옵션
# =========================================================

options = webdriver.ChromeOptions()

options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")


def get_driver():
    return webdriver.Chrome(options=options)

# =========================================================
# ESG 카테고리 매핑
# =========================================================

CATEGORY_MAP = {
    "Environment": "E",
    "환경": "E",
    "Social": "S",
    "사회": "S",
    "Governance": "G",
    "지배구조": "G",
    "Supply Chain": "SC",
    "공급망": "SC",
    "ESG Investing": "INV",
    "ESG 투자": "INV"
}

# =========================================================
# 텍스트 정리
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = text.replace("\n", " ")

    # 따옴표 제거
    text = text.replace('"', "")
    text = text.replace("'", "")

    # 특수문자 제거
    text = re.sub(
        r"[◆■□▶▲△▼▽★☆※☎☞➜➤✔✓•·▪︎]",
        " ",
        text
    )

    # AI 학습용 문자만 유지
    text = re.sub(
        r"[^가-힣a-zA-Z0-9\s\.\,\%\-\(\)]",
        " ",
        text
    )

    # 공백 정리
    text = re.sub(r"\s+", " ", text)

    return text.strip()

# =========================================================
# ESG 카테고리 추출
# =========================================================

def extract_category(text):

    for keyword, category in CATEGORY_MAP.items():

        if keyword in text:
            return category

    return None

# =========================================================
# Row 생성
# =========================================================

def create_row(
    source,
    date,
    title,
    url,
    category,
    sub_issue,
    paragraph
):

    return {
        "source": source,
        "date": date,
        "title": clean_text(title),
        "url": url,
        "category": category,
        "sub_issue": clean_text(sub_issue),
        "paragraph": clean_text(paragraph)
    }

# =========================================================
# 임팩트온
# =========================================================

def crawl_impacton(driver):

    print("\n--- [임팩트온] 크롤링 시작 ---")

    base_url = (
        "https://www.impacton.net/news/articleList.html"
        "?page={}&sc_sub_section_code=S2N14&view_type=sm"
    )

    links_data = []

    rows = []

    error_links = []

    MAX_PAGE = 1

    page = 1

    stop_crawling = False

    # =====================================================
    # 링크 수집
    # =====================================================

    while True:

        url = base_url.format(page)

        driver.get(url)

        time.sleep(1)

        articles = driver.find_elements(
            By.CSS_SELECTOR,
            "ul.type2 li"
        )

        if not articles:
            break

        for article in articles:

            try:

                title_el = article.find_element(
                    By.CSS_SELECTOR,
                    "h2.titles a"
                )

                title = title_el.text.strip()

                link = title_el.get_attribute("href")

                date_text = article.find_element(
                    By.CSS_SELECTOR,
                    "span.byline em:last-child"
                ).text.strip()

                article_date = datetime.strptime(
                    date_text.split()[0],
                    "%Y.%m.%d"
                )

                if article_date < TARGET_DATE:

                    stop_crawling = True

                    break

                links_data.append({
                    "title": title,
                    "link": link,
                    "date": date_text
                })

            except Exception:
                continue

        print(f"[임팩트온] {page}페이지 완료")

        if stop_crawling:
            break

        page += 1

    # =====================================================
    # 본문 수집
    # =====================================================

    for item in links_data:

        try:

            driver.get(item["link"])

            time.sleep(1)

            body = driver.find_element(
                By.CSS_SELECTOR,
                "article#article-view-content-div"
            )

            children = body.find_elements(
                By.XPATH,
                "./*"
            )

            current_category = None

            current_sub_issue = None

            for child in children:

                try:

                    tag_name = child.tag_name.lower()

                    element_id = child.get_attribute("id") or ""

                    text = clean_text(child.text)

                    if not text:
                        continue

                    # =====================================
                    # 불필요 문구 제거
                    # =====================================

                    if EXCLUDE_KEYWORD in text:
                        continue

                    # =====================================
                    # ESG 카테고리
                    # tem-type-2
                    # =====================================

                    if (
                        tag_name == "div"
                        and "tem-type-2" in element_id
                    ):

                        detected_category = extract_category(text)

                        if detected_category:

                            current_category = detected_category

                            current_sub_issue = None

                        continue

                    # =====================================
                    # p > strong
                    # 소제목
                    # =====================================

                    if tag_name == "p":

                        strong_tags = child.find_elements(
                            By.TAG_NAME,
                            "strong"
                        )

                        # -----------------------------
                        # strong 존재
                        # -----------------------------

                        if strong_tags:

                            current_sub_issue = clean_text(
                                strong_tags[0].text
                            )

                            continue

                        # -----------------------------
                        # 일반 문단
                        # -----------------------------

                        paragraph = text

                        if len(paragraph) < 20:
                            continue

                        if not current_category:
                            continue

                        if not current_sub_issue:
                            continue

                        rows.append(
                            create_row(
                                source="impacton",
                                date=item["date"],
                                title=item["title"],
                                url=item["link"],
                                category=current_category,
                                sub_issue=current_sub_issue,
                                paragraph=paragraph
                            )
                        )

                except Exception:
                    continue

        except Exception as e:

            error_links.append({
                **item,
                "error": str(e)
            })

    return rows, error_links

# =========================================================
# JSONL 저장
# =========================================================

def save_jsonl(data, filename):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        for row in data:

            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False
                ) + "\n"
            )

# =========================================================
# 실행
# =========================================================

def run():
    driver = get_driver()
    try:
        impacton_rows, impacton_errors = crawl_impacton(driver)
    finally:
        driver.quit()

    # =====================================================
    # DataFrame
    # =====================================================

    if impacton_rows:

        df = pd.DataFrame(impacton_rows)

        # 중복 제거
        df.drop_duplicates(
            subset=[
                "title",
                "sub_issue",
                "paragraph"
            ],
            inplace=True
        )

        # CSV 저장
        df.to_csv(
            "esg_ai_training_dataset.csv",
            index=False,
            encoding="utf-8-sig"
        )

        # JSONL 저장
        save_jsonl(
            df.to_dict(orient="records"),
            SAVE_JSONL
        )

        print("\n✅ ESG AI 학습 데이터 저장 완료")
        print(f"총 데이터 수: {len(df)}")

        print("\n컬럼:")
        print(df.columns.tolist())

    else:

        print("\n❌ 저장할 데이터 없음")

    # =====================================================
    # 에러 저장
    # =====================================================

    if impacton_errors:

        err_df = pd.DataFrame(impacton_errors)

        err_df.to_csv(
            "errors.csv",
            index=False,
            encoding="utf-8-sig"
        )
        print(f"⚠️ 에러 {len(err_df)}건 저장 완료")
    else:
        print("✨ 에러 없음")


if __name__ == "__main__":
    run()