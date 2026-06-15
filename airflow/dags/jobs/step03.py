import json
from collections import defaultdict
from jobs.core.paths import (
    trainJsonl,
    mergedTrainJsonl
)


def step03(**context):

    # url을 키로 하여 병합할 딕셔너리
    articles = defaultdict(lambda: {
        "title": "",
        "date": "",
        "paragraphs": [],
        "source": ""
    })

    output_rows = []

    with open(trainJsonl, "r", encoding="utf-8") as f:

        for line in f:
            data = json.loads(line)

            if data.get("source") == "esgeconomy":

                url = data.get("url")

                articles[url]["title"] = data.get("title")
                articles[url]["date"] = data.get("date")
                articles[url]["source"] = data.get("source")

                articles[url]["paragraphs"].append(
                    data.get("paragraph", "")
                )

            else:
                output_rows.append(data)

    with open(mergedTrainJsonl, "w", encoding="utf-8") as f:

        for row in output_rows:
            f.write(
                json.dumps(row, ensure_ascii=False)
                + "\n"
            )

        for url, content in articles.items():
            merged_data = {
                "source": content["source"],
                "date": content["date"],
                "title": content["title"],
                "url": url,
                "category": "",
                "sub_issue": "",
                "paragraph": "\n".join(content["paragraphs"])
            }
            f.write(json.dumps(merged_data, ensure_ascii=False) + '\n')

    print(f"병합 완료: {len(articles)}개의 기사 데이터가 '{mergedTrainJsonl}'로 저장되었습니다.")
