import asyncio
import os
import sys

# 프로젝트 루트 경로 추가 (src 모듈 임포트 가능하도록)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.ocrai_v8 import gemini

async def main():
    print("Testing ocrai.py Gemini Pipeline...")
    
    # 더미 데이터 구성
    results = [
        {"file_name": "dummy.pdf", "company_name": "TestCorp", "type": "SR"}
    ]
    filePaths = ["dummy.pdf"]
    
    try:
        response = await gemini(results, filePaths)
        print("\n=== Test Results ===")
        print(f"Status: {response.get('status')}")
        print(f"Message: {response.get('message')}")
        print("\nData:")
        for res in response.get('data', []):
            print(f"- Company: {res.get('companyName')}")
            print(f"- File: {res.get('fileName')}")
            print("- Results:")
            for item in res.get('result', []):
                print(f"  * Issue: {item.get('issue')}")
                print(f"    Sub Issue: {item.get('sub_issue')}")
                print(f"    Impact Score: {item.get('impact_score')}")
                print(f"    Financial Score: {item.get('financial_score')}")
            
    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
