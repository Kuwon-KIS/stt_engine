#!/usr/bin/env python3
"""
해시 기반 분석 로직 검증 테스트
"""

import sys
sys.path.insert(0, '/Users/a113211/workspace/stt_engine/web_ui')

from app.services.analysis_service import AnalysisService
from app.models.analysis_schemas import AnalysisStartRequest, AnalysisStartResponse
from app.models.database import Employee, FileUpload, AnalysisJob
from app.utils.db import SessionLocal
from datetime import datetime

def test_hash_logic():
    """해시 로직 테스트"""
    print("\n" + "="*60)
    print("1. 해시 로직 테스트")
    print("="*60)
    
    # Test case 1: Same files
    files1 = ['file1.wav', 'file2.wav', 'file3.wav']
    hash1 = AnalysisService.calculate_files_hash(files1)
    
    files2 = ['file3.wav', 'file1.wav', 'file2.wav']  # Different order
    hash2 = AnalysisService.calculate_files_hash(files2)
    
    assert hash1 == hash2, "Same files with different order should have same hash"
    print(f"✅ Same files, different order: {hash1 == hash2}")
    
    # Test case 2: Different files
    files3 = ['file1.wav', 'file2.wav', 'file4.wav']
    hash3 = AnalysisService.calculate_files_hash(files3)
    
    assert hash1 != hash3, "Different files should have different hash"
    print(f"✅ Different files: {hash1 != hash3}")
    
    # Test case 3: File added
    files4 = ['file1.wav', 'file2.wav', 'file3.wav', 'file4.wav']
    hash4 = AnalysisService.calculate_files_hash(files4)
    
    assert hash1 != hash4, "Added file should produce different hash"
    print(f"✅ File added: {hash1 != hash4}")
    
    print("\n✅ Hash logic validation passed")
    return True


def test_database_schema():
    """데이터베이스 스키마 검증"""
    print("\n" + "="*60)
    print("2. 데이터베이스 스키마 검증")
    print("="*60)
    
    # Check if files_hash column exists
    from sqlalchemy import inspect
    
    db = SessionLocal()
    inspector = inspect(AnalysisJob)
    columns = [col.name for col in inspector.columns]
    
    print(f"AnalysisJob columns: {columns}")
    
    assert 'files_hash' in columns, "files_hash column not found"
    print(f"✅ files_hash column exists")
    
    # Check column properties
    files_hash_col = next(col for col in inspector.columns if col.name == 'files_hash')
    print(f"   Type: {files_hash_col.type}")
    print(f"   Nullable: {files_hash_col.nullable}")
    
    db.close()
    print("\n✅ Database schema validation passed")
    return True


def test_response_schema():
    """응답 스키마 검증"""
    print("\n" + "="*60)
    print("3. 응답 스키마 검증")
    print("="*60)
    
    # Test AnalysisStartResponse with new fields
    response1 = AnalysisStartResponse(
        success=True,
        job_id="job_123456",
        message="분석이 시작되었습니다",
        status="started",
        analysis_available=True
    )
    
    print(f"Response (started):")
    print(f"  - success: {response1.success}")
    print(f"  - job_id: {response1.job_id}")
    print(f"  - message: {response1.message}")
    print(f"  - status: {response1.status}")
    print(f"  - analysis_available: {response1.analysis_available}")
    
    assert response1.status == "started"
    assert response1.analysis_available == True
    print(f"✅ started response valid")
    
    # Test unchanged response
    response2 = AnalysisStartResponse(
        success=True,
        job_id="job_654321",
        message="이미 분석이 완료되었습니다",
        status="unchanged",
        analysis_available=False
    )
    
    print(f"\nResponse (unchanged):")
    print(f"  - success: {response2.success}")
    print(f"  - job_id: {response2.job_id}")
    print(f"  - message: {response2.message}")
    print(f"  - status: {response2.status}")
    print(f"  - analysis_available: {response2.analysis_available}")
    
    assert response2.status == "unchanged"
    assert response2.analysis_available == False
    print(f"✅ unchanged response valid")
    
    print("\n✅ Response schema validation passed")
    return True


def test_request_schema():
    """요청 스키마 검증"""
    print("\n" + "="*60)
    print("4. 요청 스키마 검증")
    print("="*60)
    
    # Test AnalysisStartRequest with new field
    request1 = AnalysisStartRequest(
        folder_path="2026-02-20",
        include_classification=True,
        include_validation=True,
        force_reanalysis=False
    )
    
    print(f"Request (normal):")
    print(f"  - folder_path: {request1.folder_path}")
    print(f"  - include_classification: {request1.include_classification}")
    print(f"  - include_validation: {request1.include_validation}")
    print(f"  - force_reanalysis: {request1.force_reanalysis}")
    
    assert request1.force_reanalysis == False
    print(f"✅ normal request valid")
    
    # Test force reanalysis request
    request2 = AnalysisStartRequest(
        folder_path="2026-02-20",
        include_classification=True,
        include_validation=True,
        force_reanalysis=True
    )
    
    print(f"\nRequest (force reanalysis):")
    print(f"  - folder_path: {request2.folder_path}")
    print(f"  - force_reanalysis: {request2.force_reanalysis}")
    
    assert request2.force_reanalysis == True
    print(f"✅ force reanalysis request valid")
    
    print("\n✅ Request schema validation passed")
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("분석 시스템 해시 로직 검증 테스트")
    print("="*60)
    
    try:
        test_hash_logic()
        test_database_schema()
        test_response_schema()
        test_request_schema()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 통과!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
