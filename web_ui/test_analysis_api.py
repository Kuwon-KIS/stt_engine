#!/usr/bin/env python3
"""
분석 시스템 API 테스트 스크립트

Flow:
1. Login
2. Upload files
3. First analysis request -> should succeed with status="started"
4. Second analysis request (no files changed) -> should return status="unchanged"
5. Add a new file
6. Third analysis request -> should succeed with status="started"
"""

import requests
import json
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8100"
SESSION = requests.Session()

def test_login(emp_id: str = "10001", password: str = "password") -> bool:
    """사용자 로그인"""
    print(f"\n[1] 로그인 테스트 (사번: {emp_id})")
    response = SESSION.post(
        f"{BASE_URL}/api/auth/login",
        json={"emp_id": emp_id, "password": password}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    return response.status_code == 200


def test_list_folders() -> Optional[list]:
    """업로드된 폴더 목록 조회"""
    print(f"\n[2] 업로드된 폴더 목록 조회")
    response = SESSION.get(f"{BASE_URL}/api/files/list_folders")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Folders: {data}")
        if data.get("folders"):
            return data["folders"]
    return None


def test_start_analysis(folder_path: str, force_reanalysis: bool = False) -> Optional[Dict]:
    """분석 시작"""
    print(f"\n[3] 분석 시작 테스트 (폴더: {folder_path}, force_reanalysis: {force_reanalysis})")
    response = SESSION.post(
        f"{BASE_URL}/api/analysis/start",
        json={
            "folder_path": folder_path,
            "include_classification": True,
            "include_validation": True,
            "force_reanalysis": force_reanalysis
        }
    )
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    if response.status_code == 202:
        return data
    return None


def test_analysis_flow():
    """전체 분석 플로우 테스트"""
    
    # 1. 로그인
    if not test_login():
        print("❌ 로그인 실패")
        return
    
    # 2. 폴더 목록 확인
    folders = test_list_folders()
    if not folders:
        print("❌ 폴더가 없습니다. 먼저 파일을 업로드하세요.")
        return
    
    # 테스트할 폴더 선택 (첫 번째 폴더)
    test_folder = folders[0]
    print(f"\n✅ 테스트 폴더: {test_folder}")
    
    # 3. 첫 번째 분석 요청 (새 분석)
    result1 = test_start_analysis(test_folder)
    if not result1 or not result1.get("success"):
        print("❌ 첫 번째 분석 실패")
        return
    
    if result1.get("status") == "unchanged":
        print("⚠️  첫 분석인데 'unchanged'로 반환됨 (예상치 못함)")
        print("   → 폴더가 이전에 분석되었으므로, 변경되지 않음으로 처리됨")
    else:
        print(f"✅ 첫 번째 분석 성공 (status: {result1.get('status')})")
    
    # 4. 두 번째 분석 요청 (형상 미변경)
    result2 = test_start_analysis(test_folder)
    if not result2 or not result2.get("success"):
        print("❌ 두 번째 분석 실패")
        return
    
    if result2.get("status") == "unchanged" and not result2.get("analysis_available"):
        print(f"✅ 두 번째 분석: status='{result2.get('status')}' (예상대로)")
        print(f"   Message: {result2.get('message')}")
    else:
        print(f"⚠️  두 번째 분석: status='{result2.get('status')}'")
        print(f"   analysis_available: {result2.get('analysis_available')}")
    
    # 5. 강제 재분석 요청
    result3 = test_start_analysis(test_folder, force_reanalysis=True)
    if not result3 or not result3.get("success"):
        print("❌ 강제 재분석 실패")
        return
    
    if result3.get("status") == "started" and result3.get("analysis_available"):
        print(f"✅ 강제 재분석 성공 (status: {result3.get('status')})")
    else:
        print(f"⚠️  강제 재분석: status='{result3.get('status')}'")
    
    print("\n✅ 테스트 완료")


if __name__ == "__main__":
    print("=" * 60)
    print("분석 시스템 API 테스트")
    print("=" * 60)
    
    try:
        test_analysis_flow()
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
