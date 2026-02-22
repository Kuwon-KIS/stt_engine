#!/usr/bin/env python3
"""
해시 로직 테스트
"""

import hashlib
from typing import List

def calculate_files_hash(file_list: List[str]) -> str:
    """
    파일 목록의 해시 계산 (SHA256)
    
    Args:
        file_list: 파일명 목록
    
    Returns:
        SHA256 해시값 (16진수 문자열)
    """
    # 파일명 정렬
    sorted_files = sorted(file_list)
    
    # '|'로 연결
    file_string = '|'.join(sorted_files)
    
    # SHA256 해시 계산
    return hashlib.sha256(file_string.encode()).hexdigest()


if __name__ == '__main__':
    # 테스트 케이스 1: 동일한 파일 목록
    files1 = ['file1.wav', 'file2.wav', 'file3.wav']
    hash1 = calculate_files_hash(files1)
    print(f"Files 1: {files1}")
    print(f"Hash 1: {hash1}\n")
    
    # 테스트 케이스 2: 동일한 파일지만 순서 다름
    files2 = ['file3.wav', 'file1.wav', 'file2.wav']
    hash2 = calculate_files_hash(files2)
    print(f"Files 2: {files2}")
    print(f"Hash 2: {hash2}")
    print(f"Same as Hash 1? {hash1 == hash2}\n")
    
    # 테스트 케이스 3: 다른 파일 목록
    files3 = ['file1.wav', 'file2.wav', 'file4.wav']
    hash3 = calculate_files_hash(files3)
    print(f"Files 3: {files3}")
    print(f"Hash 3: {hash3}")
    print(f"Different from Hash 1? {hash1 != hash3}\n")
    
    # 테스트 케이스 4: 파일 추가
    files4 = ['file1.wav', 'file2.wav', 'file3.wav', 'file4.wav']
    hash4 = calculate_files_hash(files4)
    print(f"Files 4: {files4}")
    print(f"Hash 4: {hash4}")
    print(f"Different from Hash 1? {hash1 != hash4}\n")
