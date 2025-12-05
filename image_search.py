import os
import shutil
from bing_image_downloader import downloader

def download_escalator_3_images():
    # 저장될 메인 폴더
    base_dir = "escalator_history_v2"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    print("Bing에서 연도별 3장씩 다운로드를 시작합니다... (1900 ~ 2024)")

    for year in range(1900, 2025):
        query_string = f"{year} escalator"
        
        try:
            # 1. 이미지 다운로드 (limit=3 : 3장씩 다운로드)
            downloader.download(
                query_string, 
                limit=3, 
                output_dir=base_dir, 
                adult_filter_off=True, 
                force_replace=False, 
                timeout=5, 
                verbose=False
            )
            
            # 2. 파일 이름 변경 및 정리
            # 다운로더는 'base_dir/1900 escalator/' 폴더 안에 저장하므로 경로를 잡습니다.
            source_folder = os.path.join(base_dir, query_string)
            
            if os.path.exists(source_folder):
                files = os.listdir(source_folder)
                
                # 파일 처리 (Image_1.jpg, Image_2.jpg ...)
                count = 0
                for file_name in files:
                    # 원본 파일 경로
                    src_file = os.path.join(source_folder, file_name)
                    
                    if os.path.isfile(src_file):
                        count += 1
                        ext = os.path.splitext(file_name)[1] # 확장자(.jpg) 추출
                        
                        # 최종 파일명: 1900_1.jpg, 1900_2.jpg ...
                        new_filename = f"{year}_{count}{ext}"
                        dst_file = os.path.join(base_dir, new_filename)
                        
                        # 파일을 상위 폴더로 이동하며 이름 변경
                        shutil.move(src_file, dst_file)

                # 3장 처리가 끝난 빈 폴더 삭제
                shutil.rmtree(source_folder)
                print(f"[성공] {year}년: {count}장 저장 완료")
            else:
                print(f"[실패] {year}년: 이미지를 찾지 못했습니다.")

        except Exception as e:
            print(f"[에러] {year}년 처리 중 문제 발생: {e}")

    print(f"\n모든 작업이 완료되었습니다! '{base_dir}' 폴더를 확인해주세요.")

if __name__ == "__main__":
    download_escalator_3_images()