"""
파일 관리 서비스
Phase 2: 파일 업로드, 조회, 삭제 등의 비즈니스 로직
"""

from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.models.database import FileUpload, Employee
from app.models.file_schemas import FileUploadResponse, FileListResponse, FolderListResponse
from app.utils import file_utils
from config import UPLOAD_DIR


class FileService:
    """파일 관리 서비스"""
    
    @staticmethod
    def upload_file(
        emp_id: str,
        file: UploadFile,
        folder_name: str = None,
        db: Session = None
    ) -> FileUploadResponse:
        """
        파일 업로드
        
        Args:
            emp_id: 사번
            file: 업로드 파일
            folder_name: 폴더 이름 (선택)
            db: DB 세션
        
        Returns:
            FileUploadResponse: 업로드 결과
        
        Raises:
            HTTPException: 업로드 실패
        """
        try:
            # 1. 사용자 검증
            if db:
                employee = db.query(Employee).filter(
                    Employee.emp_id == emp_id
                ).first()
                if not employee:
                    raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다")
            
            # 2. 파일명 검증
            filename = file_utils.validate_filename(file.filename)
            
            # 3. 폴더 경로 생성
            folder_path = file_utils.create_folder_path(emp_id, folder_name)
            
            # 4. 파일 저장
            user_dir = file_utils.get_user_upload_dir(emp_id)
            full_folder_path = user_dir / folder_path
            full_file_path = full_folder_path / filename
            
            # 파일 크기 제한 검증 (읽기 전에)
            file_content = file.file.read()
            file_utils.validate_file_size(len(file_content))
            
            # 파일 저장
            with open(full_file_path, 'wb') as f:
                f.write(file_content)
            
            # 파일 크기 계산
            file_size_mb = file_utils.get_file_size_mb(full_file_path)
            
            # 5. DB에 기록
            if db:
                file_record = FileUpload(
                    emp_id=emp_id,
                    folder_path=folder_path,
                    filename=filename,
                    file_size_mb=file_size_mb,
                    uploaded_at=datetime.utcnow()
                )
                db.add(file_record)
                db.commit()
            
            return FileUploadResponse(
                success=True,
                filename=filename,
                file_size_mb=file_size_mb,
                folder_path=folder_path,
                uploaded_at=datetime.utcnow(),
                message="파일 업로드 성공"
            )
        
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileExistsError:
            raise HTTPException(status_code=409, detail="파일이 이미 존재합니다")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")
    
    @staticmethod
    def list_files(
        emp_id: str,
        folder_path: str = None,
        db: Session = None
    ) -> FileListResponse:
        """
        파일 목록 조회
        
        Args:
            emp_id: 사번
            folder_path: 폴더 경로 (선택, 없으면 모든 파일)
            db: DB 세션
        
        Returns:
            FileListResponse: 파일 목록
        
        Raises:
            HTTPException: 조회 실패
        """
        try:
            # 사용자 검증
            if db:
                employee = db.query(Employee).filter(
                    Employee.emp_id == emp_id
                ).first()
                if not employee:
                    raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다")
            
            # DB에서 파일 목록 조회
            query = db.query(FileUpload).filter(FileUpload.emp_id == emp_id)
            
            if folder_path:
                query = query.filter(FileUpload.folder_path == folder_path)
                display_folder = folder_path
            else:
                display_folder = "전체"
            
            files = query.order_by(FileUpload.uploaded_at.desc()).all()
            
            # 응답 형식
            file_info_list = [
                {
                    "filename": f.filename,
                    "file_size_mb": f.file_size_mb,
                    "uploaded_at": f.uploaded_at
                }
                for f in files
            ]
            
            # 총 크기 계산
            total_size_mb = sum(f.file_size_mb for f in files)
            
            return FileListResponse(
                folder_path=display_folder,
                files=file_info_list,
                total_size_mb=total_size_mb
            )
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")
    
    @staticmethod
    def list_folders(emp_id: str, db: Session = None) -> FolderListResponse:
        """
        폴더 목록 조회
        
        Args:
            emp_id: 사번
            db: DB 세션
        
        Returns:
            FolderListResponse: 폴더 목록
        
        Raises:
            HTTPException: 조회 실패
        """
        try:
            # 사용자 검증
            if db:
                employee = db.query(Employee).filter(
                    Employee.emp_id == emp_id
                ).first()
                if not employee:
                    raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다")
            
            # DB에서 고유한 폴더 목록 조회
            folder_paths = db.query(FileUpload.folder_path).filter(
                FileUpload.emp_id == emp_id
            ).distinct().all()
            
            # 폴더명 추출 및 정렬
            folders = sorted(
                [fp[0] for fp in folder_paths],
                reverse=True  # 최근 폴더 먼저
            )
            
            return FolderListResponse(folders=folders)
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")
    
    @staticmethod
    def delete_file(
        emp_id: str,
        filename: str,
        folder_path: str,
        db: Session = None
    ) -> dict:
        """
        파일 삭제
        
        Args:
            emp_id: 사번
            filename: 파일명
            folder_path: 폴더 경로
            db: DB 세션
        
        Returns:
            dict: 삭제 결과
        
        Raises:
            HTTPException: 삭제 실패
        """
        try:
            # 사용자 검증
            if db:
                employee = db.query(Employee).filter(
                    Employee.emp_id == emp_id
                ).first()
                if not employee:
                    raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다")
            
            # 파일 경로 검증
            file_path = file_utils.validate_file_path(emp_id, folder_path, filename)
            
            # 파일 삭제
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
            
            file_utils.delete_file(file_path)
            
            # DB에서 삭제
            if db:
                db.query(FileUpload).filter(
                    FileUpload.emp_id == emp_id,
                    FileUpload.filename == filename,
                    FileUpload.folder_path == folder_path
                ).delete()
                db.commit()
                
                # 폴더가 비어있으면 정리
                user_dir = file_utils.get_user_upload_dir(emp_id)
                file_utils.cleanup_empty_folders(user_dir)
            
            return {
                "success": True,
                "message": "파일 삭제됨"
            }
        
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"삭제 실패: {str(e)}")
