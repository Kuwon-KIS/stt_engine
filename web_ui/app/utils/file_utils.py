"""
파일 관리 유틸리티
Phase 2: 파일 경로 생성, 검증, 크기 계산 등
"""

import os
import pathlib
from datetime import datetime
from pathlib import Path
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB


def get_user_upload_dir(emp_id: str) -> Path:
    """
    사용자별 업로드 디렉토리 경로 반환
    
    Args:
        emp_id: 사번
    
    Returns:
        Path: 사용자 업로드 디렉토리 (data/uploads/{emp_id})
    """
    return Path(UPLOAD_DIR) / emp_id


def create_folder_path(emp_id: str, folder_name: str = None) -> str:
    """
    폴더 경로 생성 및 폴더 자동 생성
    
    folder_name이 없으면 오늘 날짜로 폴더 생성
    folder_name이 있으면 해당 이름으로 폴더 생성
    
    Args:
        emp_id: 사번
        folder_name: 폴더 이름 (선택사항, None이면 오늘 날짜)
    
    Returns:
        str: 폴더 경로 (예: "2026-02-20" 또는 "부당권유_검토")
    
    Raises:
        ValueError: 잘못된 폴더명
    """
    # 기본값: 오늘 날짜
    if folder_name is None:
        folder_path = datetime.now().strftime("%Y-%m-%d")
    else:
        # 폴더명 검증
        if not folder_name or len(folder_name) > 100:
            raise ValueError("폴더명은 1-100자 사이여야 합니다")
        
        # 위험한 문자 제거
        invalid_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\x00']
        for char in invalid_chars:
            if char in folder_name:
                raise ValueError(f"폴더명에 사용할 수 없는 문자: {char}")
        
        folder_path = folder_name
    
    # 전체 경로 생성
    user_dir = get_user_upload_dir(emp_id)
    full_folder_path = user_dir / folder_path
    
    # 폴더 생성 (존재하지 않으면)
    full_folder_path.mkdir(parents=True, exist_ok=True)
    
    return folder_path


def validate_file_path(emp_id: str, folder_path: str, filename: str) -> Path:
    """
    파일 경로 검증 (경로 traversal 공격 방지)
    
    Args:
        emp_id: 사번
        folder_path: 폴더 경로 (예: "2026-02-20", None이면 최상위)
        filename: 파일명
    
    Returns:
        Path: 안전한 절대 경로
    
    Raises:
        ValueError: 잘못된 경로
    """
    # 기본 경로
    base_dir = Path(UPLOAD_DIR).resolve()
    user_dir = (base_dir / emp_id).resolve()
    
    # 사용자 디렉토리가 기본 경로 내에 있는지 확인
    try:
        user_dir.relative_to(base_dir)
    except ValueError:
        raise ValueError("Invalid emp_id")
    
    # 전체 파일 경로 (folder_path가 None이면 사용자 디렉토리 직하)
    if folder_path:
        file_path = (user_dir / folder_path / filename).resolve()
    else:
        file_path = (user_dir / filename).resolve()
    
    # 파일 경로가 사용자 디렉토리 내에 있는지 확인
    try:
        file_path.relative_to(user_dir)
    except ValueError:
        raise ValueError("경로 traversal 공격이 감지되었습니다")
    
    return file_path


def validate_filename(filename: str) -> str:
    """
    파일명 검증
    
    Args:
        filename: 파일명
    
    Returns:
        str: 검증된 파일명
    
    Raises:
        ValueError: 잘못된 파일명
    """
    # 파일명 길이 검사
    if not filename or len(filename) > 255:
        raise ValueError("파일명은 1-255자 사이여야 합니다")
    
    # 확장자 검증
    ext = pathlib.Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EXTENSIONS)
        raise ValueError(f"허용되지 않는 파일 형식입니다. 허용: {allowed}")
    
    # 위험한 문자 제거
    invalid_chars = ['/', '\\', '<', '>', ':', '"', '|', '?', '*', '\x00']
    for char in invalid_chars:
        if char in filename:
            raise ValueError(f"파일명에 사용할 수 없는 문자: {char}")
    
    return filename


def get_file_size_mb(file_path: Path) -> float:
    """
    파일 크기를 MB 단위로 반환
    
    Args:
        file_path: 파일 경로
    
    Returns:
        float: 파일 크기 (MB)
    """
    if not file_path.exists():
        return 0.0
    
    size_bytes = file_path.stat().st_size
    size_mb = round(size_bytes / (1024 * 1024), 2)
    
    return size_mb


def validate_file_size(file_size_bytes: int) -> bool:
    """
    파일 크기 제한 검증
    
    Args:
        file_size_bytes: 파일 크기 (바이트)
    
    Returns:
        bool: 유효 여부
    
    Raises:
        ValueError: 파일 크기 초과
    """
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    if file_size_bytes > max_bytes:
        raise ValueError(
            f"파일 크기 초과 (최대: {MAX_UPLOAD_SIZE_MB}MB, "
            f"제한: {MAX_UPLOAD_SIZE_MB}MB)"
        )
    
    return True


def list_folders(emp_id: str) -> list:
    """
    사용자의 폴더 목록 조회
    
    Args:
        emp_id: 사번
    
    Returns:
        list: 폴더명 목록 (정렬)
    """
    user_dir = get_user_upload_dir(emp_id)
    
    if not user_dir.exists():
        return []
    
    folders = [
        d.name for d in user_dir.iterdir()
        if d.is_dir()
    ]
    
    # 날짜 폴더가 먼저 오도록 정렬
    folders.sort(reverse=True)
    
    return folders


def list_files(folder_path: Path) -> list:
    """
    폴더의 파일 목록 조회
    
    Args:
        folder_path: 폴더 경로
    
    Returns:
        list: 파일명 목록 (정렬)
    """
    if not folder_path.exists() or not folder_path.is_dir():
        return []
    
    files = [
        f.name for f in folder_path.iterdir()
        if f.is_file() and not f.name.startswith('.')
    ]
    
    # 파일명으로 정렬
    files.sort()
    
    return files


def get_folder_size_mb(folder_path: Path) -> float:
    """
    폴더의 총 크기 계산 (MB)
    
    Args:
        folder_path: 폴더 경로
    
    Returns:
        float: 총 크기 (MB)
    """
    if not folder_path.exists():
        return 0.0
    
    total_bytes = 0
    
    for file_path in folder_path.rglob('*'):
        if file_path.is_file():
            total_bytes += file_path.stat().st_size
    
    total_mb = round(total_bytes / (1024 * 1024), 2)
    
    return total_mb


def delete_file(file_path: Path) -> bool:
    """
    파일 삭제
    
    Args:
        file_path: 파일 경로
    
    Returns:
        bool: 성공 여부
    
    Raises:
        FileNotFoundError: 파일이 없음
    """
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path.name}")
    
    if not file_path.is_file():
        raise ValueError(f"파일이 아닙니다: {file_path.name}")
    
    file_path.unlink()
    
    return True


def cleanup_empty_folders(user_dir: Path) -> int:
    """
    비어있는 폴더 삭제
    
    Args:
        user_dir: 사용자 디렉토리
    
    Returns:
        int: 삭제된 폴더 수
    """
    deleted_count = 0
    
    # 하위 폴더부터 순회
    for folder in reversed(list(user_dir.rglob('*'))):
        if folder.is_dir() and not any(folder.iterdir()):
            try:
                folder.rmdir()
                deleted_count += 1
            except OSError:
                pass
    
    return deleted_count
