import time
from datetime import datetime
from selenium.webdriver.common.by import By
from core.cleaner import cleanText
from core.utils import createRow
import gc

# 수집 기준 날짜
TARGET_DATE = datetime(2023, 1, 1)

def crawl(driver):
    print("\n--- [ESG경제] 크롤링 시작 ---")
    rows = []
    page = 1
    currentYear = datetime.now().year
    keepCrawling = True

    while True:
        url = f"https://www.esgeconomy.com/news/articleList.html?page={page}"
        
        try:
            driver.get(url)
            # 페이지 로드 후 브라우저가 안정을 찾을 시간을 충분히 줌
            time.sleep(1.2) 
        except Exception as e:
            print(f"[{page}페이지] 로드 타임아웃 발생. 재시도 중...: {e}")
            time.sleep(5)
            continue # 다음 페이지로 넘어가거나 재시도

        articles = driver.find_elements(By.CSS_SELECTOR, "#section-list ul.type1 > li")
        
        if not articles:
            print(f"[{page}페이지] 더 이상 기사가 없습니다.")
            break

        pageLinks = []
        
        for article in articles:
            try:
                dateText = article.find_element(By.CSS_SELECTOR, ".info.dated").text.strip()
                
                # 날짜 파싱
                try:
                    if len(dateText.split('.')[0]) <= 2: # "05.13 14:29"
                        articleDate = datetime.strptime(f"{currentYear}.{dateText}", "%Y.%m.%d %H:%M")
                    else: # "2023.12.31 10:00"
                        articleDate = datetime.strptime(dateText, "%Y.%m.%d %H:%M")
                except ValueError:
                    continue

                # 기준 날짜보다 과거 기사면 중단 플래그 설정
                if articleDate < TARGET_DATE:
                    keepCrawling = False
                    break # 현재 페이지의 남은 기사 수집 중단

                titleEl = article.find_element(By.CSS_SELECTOR, ".titles a")
                pageLinks.append({
                    "title": titleEl.text.strip(), 
                    "link": titleEl.get_attribute("href"), 
                    "date": dateText
                })
            except Exception:
                continue

        print(f"[{page}페이지] {len(pageLinks)}건의 유효 기사 발견")

        # 기사 상세 페이지 수집
        for item in pageLinks:
            try:
                driver.get(item["link"])
                time.sleep(0.6)
                
                body = driver.find_element(By.ID, "article-view-content-div")
                
                # 불필요한 요소 제거
                driver.execute_script("""
                    const junk = document.querySelectorAll('.ad-template, style, script, figure');
                    junk.forEach(el => el.remove());
                """)
                paragraphs = body.find_elements(By.TAG_NAME, "p")
                for p in paragraphs:
                    text = cleanText(p.text)
                    
                    # 필터링 키워드
                    excludeKeywords = ["무단전재", "재배포금지", "기자", "©", "Copyright", "사진=", "제보"]
                    if any(kw in text for kw in excludeKeywords):
                        continue
                        
                    if len(text) < 35:
                        continue
                    
                    rows.append(createRow(
                        source="esgeconomy",
                        date=item["date"],
                        title=item["title"],
                        url=item["link"],
                        paragraph=text
                    ))
            except Exception:
                continue
        if page % 10 == 0:
            print(f"[{page}페이지] 메모리 최적화 수행 중...")
            gc.collect()
        if page % 50 == 0:
            print(f"--- 현재 {page}페이지 완료 (수집된 문단: {len(rows)}개) ---")
            # 브라우저가 과부하 걸리지 않게 잠시 쉬어줍니다.
            time.sleep(5)

        # 페이지 증가 및 종료 체크
        if not keepCrawling:
            print(f"--- {TARGET_DATE} 이전 기사에 도달하여 수집을 종료합니다. ---")
            break
            
        page += 1

    print(f"--- [ESG경제] 수집 완료: 총 {len(rows)}개 문단 ---")
    return rows, []