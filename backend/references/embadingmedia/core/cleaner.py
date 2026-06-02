import re

def cleanText(text):
    """텍스트 정제 및 특수문자 제거"""
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