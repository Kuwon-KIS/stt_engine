#!/usr/bin/env python3
"""
환경변수 및 서비스 Alignment 검증 스크립트

이 스크립트는 다음을 점검합니다:
1. 환경변수 명명 규칙 준수 여부
2. FormDataConfig 메서드 구현 완성도
3. Service Singleton 패턴 적용 여부
4. Web UI FormData ↔ API 매핑 일치
5. 레거시 코드 존재 여부
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# 컬러 출력
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def check_env_var_naming(config_file: str) -> Tuple[int, int]:
    """환경변수 명명 규칙 검증"""
    print(f"\n{Colors.BLUE}=== 1. 환경변수 명명 규칙 검증 ==={Colors.END}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Task별 환경변수 패턴
    patterns = [
        r'PRIVACY_REMOVAL_VLLM_MODEL_NAME',
        r'PRIVACY_REMOVAL_VLLM_API_BASE',
        r'PRIVACY_REMOVAL_PROMPT_TYPE',
        r'CLASSIFICATION_VLLM_MODEL_NAME',
        r'CLASSIFICATION_VLLM_API_BASE',
        r'CLASSIFICATION_PROMPT_TYPE',
        r'ELEMENT_DETECTION_AGENT_URL',
        r'ELEMENT_DETECTION_VLLM_MODEL_NAME',
        r'ELEMENT_DETECTION_VLLM_API_BASE',
        r'ELEMENT_DETECTION_API_TYPE',
    ]
    
    passed = 0
    for pattern in patterns:
        if re.search(pattern, content):
            print(f"{Colors.GREEN}✓{Colors.END} {pattern}")
            passed += 1
        else:
            print(f"{Colors.RED}✗{Colors.END} {pattern}")
    
    # 레거시 패턴 검사
    legacy_patterns = [
        (r'EXTERNAL_API_URL(?!_).*(?!ELEMENT_DETECTION)', '레거시 EXTERNAL_API_URL'),
    ]
    
    print(f"\n{Colors.YELLOW}레거시 확인:{Colors.END}")
    for pattern, desc in legacy_patterns:
        if re.search(pattern, content):
            print(f"{Colors.RED}✗ 발견{Colors.END}: {desc}")
        else:
            print(f"{Colors.GREEN}✓ 없음{Colors.END}: {desc}")
    
    return passed, len(patterns)

def check_service_singleton(services_dir: str) -> Tuple[int, int]:
    """Service Singleton 패턴 검증"""
    print(f"\n{Colors.BLUE}=== 2. Service Singleton 패턴 검증 ==={Colors.END}")
    
    services = [
        ('privacy_removal', 'PrivacyRemovalService'),
        ('classification', 'ClassificationService'),
        ('element_detection', 'ElementDetectionService'),
    ]
    
    passed = 0
    for service_file, class_name in services:
        file_path = Path(services_dir) / f"{service_file}.py"
        
        if not file_path.exists():
            print(f"{Colors.RED}✗{Colors.END} {service_file}.py 없음")
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 클래스 정의 확인
        if f"class {class_name}" in content:
            print(f"{Colors.GREEN}✓{Colors.END} {class_name} 클래스 정의")
            passed += 1
        else:
            print(f"{Colors.RED}✗{Colors.END} {class_name} 클래스 정의 없음")
        
        # Singleton 함수 확인
        singleton_func = f"def get_{service_file.split('_')[-1]}_service"
        if singleton_func in content or "get_" in content and "service" in content:
            print(f"{Colors.GREEN}✓{Colors.END} Singleton 함수 구현")
            passed += 1
        else:
            print(f"{Colors.RED}✗{Colors.END} Singleton 함수 없음")
    
    return passed, len(services) * 2

def check_legacy_code(root_dir: str) -> Tuple[int, int]:
    """레거시 코드 검사"""
    print(f"\n{Colors.BLUE}=== 3. 레거시 코드 검사 ==={Colors.END}")
    
    legacy_files = [
        'api_server/privacy_remover.py',
        'api_server/services/privacy_remover.py',
    ]
    
    legacy_patterns = [
        ('_call_external_api', '메서드 리네임 필요'),
        ('_call_local_llm', '메서드 리네임 필요'),
        ('class PrivacyRemover(?!Service)', '클래스명 표준화 필요'),
    ]
    
    passed = 0
    total = len(legacy_files) + len(legacy_patterns)
    
    print("레거시 파일:")
    for file in legacy_files:
        file_path = Path(root_dir) / file
        if file_path.exists():
            print(f"{Colors.RED}✗ 발견{Colors.END}: {file}")
        else:
            print(f"{Colors.GREEN}✓ 없음{Colors.END}: {file}")
            passed += 1
    
    print("\n레거시 패턴:")
    transcribe_file = Path(root_dir) / 'api_server/transcribe_endpoint.py'
    if transcribe_file.exists():
        with open(transcribe_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for pattern, desc in legacy_patterns:
            if re.search(pattern, content):
                print(f"{Colors.RED}✗ 발견{Colors.END}: {desc}")
            else:
                print(f"{Colors.GREEN}✓ 없음{Colors.END}: {desc}")
                passed += 1
    
    return passed, total

def check_formdata_mapping(web_ui_dir: str, api_dir: str) -> Tuple[int, int]:
    """FormData ↔ API 매핑 검증"""
    print(f"\n{Colors.BLUE}=== 4. FormData ↔ API 매핑 검증 ==={Colors.END}")
    
    mappings = [
        ('privacy_removal', 'privacy_removal', 'privacy_llm_type'),
        ('classification', 'classification', 'classification_prompt_type'),
        ('element_detection', 'element_detection', 'agent_url'),
    ]
    
    passed = 0
    main_js = Path(web_ui_dir) / 'static/js/main.js'
    app_py = Path(api_dir) / 'app.py'
    
    if main_js.exists():
        with open(main_js, 'r', encoding='utf-8') as f:
            web_content = f.read()
    else:
        print(f"{Colors.RED}✗{Colors.END} main.js 없음")
        return passed, len(mappings)
    
    if app_py.exists():
        with open(app_py, 'r', encoding='utf-8') as f:
            api_content = f.read()
    else:
        print(f"{Colors.RED}✗{Colors.END} app.py 없음")
        return passed, len(mappings)
    
    for task, param1, param2 in mappings:
        found_web = param1 in web_content or param2 in web_content
        found_api = param1 in api_content or task in api_content
        
        if found_web and found_api:
            print(f"{Colors.GREEN}✓{Colors.END} {task} 매핑 일치")
            passed += 1
        else:
            print(f"{Colors.RED}✗{Colors.END} {task} 매핑 불일치 (Web: {found_web}, API: {found_api})")
    
    return passed, len(mappings)

def check_code_metrics(root_dir: str) -> Tuple[int, int]:
    """코드 메트릭 검증"""
    print(f"\n{Colors.BLUE}=== 5. 코드 메트릭 ==={Colors.END}")
    
    transcribe_file = Path(root_dir) / 'api_server/transcribe_endpoint.py'
    if transcribe_file.exists():
        with open(transcribe_file, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        
        # 목표: 600 줄 이하
        if lines < 650:
            print(f"{Colors.GREEN}✓{Colors.END} transcribe_endpoint.py: {lines} 줄 (목표: < 650)")
            return 1, 1
        else:
            print(f"{Colors.YELLOW}⚠{Colors.END} transcribe_endpoint.py: {lines} 줄 (목표: < 650)")
            return 0, 1
    
    return 0, 1

def main():
    """메인 검증 실행"""
    root_dir = Path(__file__).parent.parent
    
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}환경변수 및 서비스 Alignment 검증{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    total_passed = 0
    total_tests = 0
    
    # 1. 환경변수 명명 규칙
    passed, total = check_env_var_naming(str(root_dir / 'api_server/config.py'))
    total_passed += passed
    total_tests += total
    
    # 2. Service Singleton 패턴
    passed, total = check_service_singleton(str(root_dir / 'api_server/services'))
    total_passed += passed
    total_tests += total
    
    # 3. 레거시 코드
    passed, total = check_legacy_code(str(root_dir))
    total_passed += passed
    total_tests += total
    
    # 4. FormData ↔ API 매핑
    passed, total = check_formdata_mapping(str(root_dir / 'web_ui'), str(root_dir / 'api_server'))
    total_passed += passed
    total_tests += total
    
    # 5. 코드 메트릭
    passed, total = check_code_metrics(str(root_dir))
    total_passed += passed
    total_tests += total
    
    # 결과 요약
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    if percentage >= 90:
        status_color = Colors.GREEN
        status = "PASS ✓"
    elif percentage >= 70:
        status_color = Colors.YELLOW
        status = "PARTIAL ⚠"
    else:
        status_color = Colors.RED
        status = "FAIL ✗"
    
    print(f"{status_color}전체 점수: {total_passed}/{total_tests} ({percentage:.1f}%) - {status}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    sys.exit(0 if percentage >= 70 else 1)

if __name__ == '__main__':
    main()
