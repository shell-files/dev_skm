import json
import re
import os

def reconstruct_report():
    # 1. 파일이 있는 폴더 경로를 명시적으로 설정 (현재 스크립트가 있는 폴더)
    target_dir = r"D:\IDE\workspaces\WEB_STUDY-main\day\ESG_SR\storage\ocr\chunks\2023"
    
    # 2. 전체 경로(full path)를 포함한 파일 리스트 생성
    all_files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith('.txt')]
    
    if not all_files:
        print(f"경고: {target_dir} 폴더에서 .txt 파일을 찾을 수 없습니다!")
        return

    print(f"총 {len(all_files)}개의 파일을 처리합니다...")

    master_pages = {i: None for i in range(1, 168)}
    page_pattern = re.compile(r'(?:## Page|==Start of OCR for page|==Page|Page)\s*(\d+)', re.IGNORECASE)
    
    for file_path in all_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                parts = re.split(page_pattern, content)
                for i in range(1, len(parts), 2):
                    try:
                        p_num = int(parts[i])
                        text = parts[i+1].strip()
                        if 1 <= p_num <= 167:
                            if master_pages[p_num] is None or len(text) > len(master_pages[p_num]):
                                master_pages[p_num] = text
                    except:
                        continue
        except Exception as e:
            print(f"파일 읽기 오류 ({file_path}): {e}")

    final_output = []
    for i in range(1, 168):
        final_output.append({
            "page": i,
            "text": master_pages[i] if master_pages[i] else "[데이터 없음]"
        })
    
    output_filename = os.path.join(target_dir, "SR_2023_FINAL_RECONSTRUCTED.json")
    with open(output_filename, "w", encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    print(f"완료: {output_filename} 파일이 생성되었습니다.")

if __name__ == "__main__":
    reconstruct_report()