import os
import shutil
from bing_image_downloader import downloader

def download_escalator_decades_30():
    # 저장될 폴더 이름
    base_dir = "escalator_history_decades_30"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    print("Bing에서 10년 단위로 30장씩 다운로드를 시작합니다... (1900s ~ 2020s)")

    # 1900부터 2020까지 10년 단위로 반복 (1900, 1910, 1920...)
    for decade in range(1900, 2030, 10):
        # 검색어: "1900s escalator" (1900년대 에스컬레이터)
        query_string = f"{decade}s escalator"
        
        try:
            # 30장씩 다운로드
            downloader.download(
                query_string, 
                limit=30, 
                output_dir=base_dir, 
                adult_filter_off=True, 
                force_replace=False, 
                timeout=10, 
                verbose=False
            )
            
            # 다운로드된 임시 폴더 경로
            source_folder = os.path.join(base_dir, query_string)
            
            if os.path.exists(source_folder):
                files = os.listdir(source_folder)
                
                count = 0
                for file_name in files:
                    src_file = os.path.join(source_folder, file_name)
                    
                    if os.path.isfile(src_file):
                        count += 1
                        ext = os.path.splitext(file_name)[1]
                        
                        # 파일 이름: 1900s_1.jpg, 1900s_2.jpg ... 형식
                        new_filename = f"{decade}s_{count}{ext}"
                        dst_file = os.path.join(base_dir, new_filename)
                        
                        # 파일 이동 및 이름 변경
                        shutil.move(src_file, dst_file)

                # 임시 폴더 삭제
                shutil.rmtree(source_folder)
                print(f"[성공] {decade}년대: {count}장 저장 완료")
            else:
                print(f"[실패] {decade}년대: 이미지를 찾지 못했습니다.")

        except Exception as e:
            print(f"[에러] {decade}년대 처리 중 문제 발생: {e}")

    print(f"\n모든 작업이 완료되었습니다! '{base_dir}' 폴더를 확인해주세요.")

if __name__ == "__main__":
    download_escalator_decades_30()