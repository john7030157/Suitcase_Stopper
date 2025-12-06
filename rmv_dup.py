import os
import hashlib

def calculate_md5(file_path):
    """파일의 내용을 읽어서 고유한 해시값(지문)을 생성합니다."""
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            # 용량이 큰 파일도 처리할 수 있도록 조금씩 읽습니다.
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"파일 읽기 오류 ({file_path}): {e}")
        return None

def remove_duplicate_images(target_folder):
    if not os.path.exists(target_folder):
        print(f"폴더를 찾을 수 없습니다: {target_folder}")
        print("폴더 이름이 정확한지 코드를 확인해주세요.")
        return

    print(f"'{target_folder}' 폴더의 중복 검사를 시작합니다...")
    
    # 해시값을 저장할 딕셔너리 {해시값: 원본파일명}
    unique_hashes = {}
    duplicates_count = 0
    
    # 폴더 내의 모든 파일 목록을 가져와서 정렬
    file_list = sorted(os.listdir(target_folder))
    
    for filename in file_list:
        file_path = os.path.join(target_folder, filename)
        
        # 파일이 아니거나(폴더 등), 숨김 파일(.DS_Store 등)은 건너뜀
        if not os.path.isfile(file_path) or filename.startswith('.'):
            continue
            
        file_hash = calculate_md5(file_path)
        
        if file_hash is None:
            continue

        # 이미 같은 해시값(내용)을 가진 파일이 목록에 있다면 -> 중복임
        if file_hash in unique_hashes:
            print(f"[삭제] 중복 발견: {filename} (원본: {unique_hashes[file_hash]})")
            try:
                os.remove(file_path)
                duplicates_count += 1
            except Exception as e:
                print(f"삭제 실패: {e}")
        else:
            # 새로운 해시값이면 목록에 등록 (이게 원본이 됨)
            unique_hashes[file_hash] = filename

    print("-" * 30)
    print(f"작업 완료! 총 {duplicates_count}개의 중복 파일을 삭제했습니다.")

if __name__ == "__main__":
    # 방금 다운로드 받은 폴더 이름으로 설정해 두었습니다.
    folder_name = "escalator_history_decades_30" 
    
    remove_duplicate_images(folder_name)