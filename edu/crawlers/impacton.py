import time
from datetime import datetime
from selenium.webdriver.common.by import By
from core.cleaner import cleanText
from core.utils import createRow

# 설정값
TARGET_DATE = datetime(2023, 1, 1)
EXCLUDE_KEYWORD = "<임팩트온>은 지난주 지속가능경영"
CATEGORY_MAP = {
    "Environment": "E", "환경": "E",
    "Social": "S", "사회": "S",
    "Governance": "G", "지배구조": "G",
    "Supply Chain": "SC", "공급망": "SC",
    "ESG Investing": "INV", "ESG 투자": "INV"
}
def extractCategory(text):

    for keyword, category in CATEGORY_MAP.items():

        if keyword in text:
            return category

    return None

def crawl(driver):

    print("\n--- [임팩트온] 크롤링 시작 ---")

    base_url = (
        "https://www.impacton.net/news/articleList.html"
        "?page={}&sc_sub_section_code=S2N14&view_type=sm"
    )

    linksData = []

    rows = []

    errorLinks = []

    MAX_PAGE = 3

    page = 1

    stopCrawling = False

    # =====================================================
    # 링크 수집
    # =====================================================

    while True:

        url = base_url.format(page)

        driver.get(url)

        time.sleep(0.4)

        articles = driver.find_elements(
            By.CSS_SELECTOR,
            "ul.type2 li"
        )

        if not articles:
            break

        for article in articles:

            try:

                titleEl = article.find_element(
                    By.CSS_SELECTOR,
                    "h2.titles a"
                )

                title = titleEl.text.strip()

                link = titleEl.get_attribute("href")

                dateText = article.find_element(
                    By.CSS_SELECTOR,
                    "span.byline em:last-child"
                ).text.strip()

                articleDate = datetime.strptime(
                    dateText.split()[0],
                    "%Y.%m.%d"
                )

                if articleDate < TARGET_DATE:

                    stopCrawling = True

                    break

                linksData.append({
                    "title": title,
                    "link": link,
                    "date": dateText
                })

            except Exception:
                continue

        print(f"[임팩트온] {page}페이지 완료")

        if stopCrawling:
            break

        page += 1

    # =====================================================
    # 본문 수집
    # =====================================================

    for item in linksData:

        try:

            driver.get(item["link"])

            time.sleep(0.4)

            body = driver.find_element(
                By.CSS_SELECTOR,
                "article#article-view-content-div"
            )

            children = body.find_elements(
                By.XPATH,
                "./*"
            )

            currentCategory = None

            currentSubIssue = None

            for child in children:

                try:

                    tagName = child.tag_name.lower()

                    elementId = child.get_attribute("id") or ""

                    text = cleanText(child.text)

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
                        tagName == "div"
                        and "tem-type-2" in elementId
                    ):

                        detectedCategory = extractCategory(text)

                        if detectedCategory:

                            currentCategory = detectedCategory

                            currentSubIssue = None

                        continue

                    # =====================================
                    # p > strong
                    # 소제목
                    # =====================================

                    if tagName == "p":

                        strongTags = child.find_elements(
                            By.TAG_NAME,
                            "strong"
                        )

                        # -----------------------------
                        # strong 존재
                        # -----------------------------

                        if strongTags:

                            currentSubIssue = cleanText(
                                strongTags[0].text
                            )

                            continue

                        # -----------------------------
                        # 일반 문단
                        # -----------------------------

                        paragraph = text

                        if len(paragraph) < 20:
                            continue

                        if not currentCategory:
                            continue

                        if not currentSubIssue:
                            continue

                        rows.append(
                            createRow(
                                source="impacton",
                                date=item["date"],
                                title=item["title"],
                                url=item["link"],
                                category=currentCategory,
                                subIssue=currentSubIssue,
                                paragraph=paragraph
                            )
                        )

                except Exception:
                    continue

        except Exception as e:

            errorLinks.append({
                **item,
                "error": str(e)
            })

    return rows, errorLinks