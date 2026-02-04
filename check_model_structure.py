#!/usr/bin/env python3
"""
모델을 faster_whisper가 인식하는 형식으로 정렬
"""
import shutil
from pathlib import Path

print("🔄 모델 디렉토리 구조 정렬")
print("=" * 60)

models_dir = Path("/Users/a113211/workspace/stt_engine/models")
hf_cache_dir = models_dir / "models--openai--whisper-large-v3-turbo"
snapshot_dir = None

# 스냅샷 디렉토리 찾기
if hf_cache_dir.exists():
    snapshots = list((hf_cache_dir / "snapshots").glob("*/"))
    if snapshots:
        snapshot_dir = snapshots[0]

print(f"📁 모델 디렉토리: {models_dir}")
print(f"📁 캐시 디렉토리: {hf_cache_dir}")
print(f"📁 스냅샷 디렉토리: {snapshot_dir}")
print()

# 현재 파일 구조 확인
print("1️⃣ 현재 파일 구조:")
print("-" * 60)

files_at_root = list(models_dir.glob("*.json")) + list(models_dir.glob("*.txt"))
print(f"models_dir의 파일: {len(files_at_root)}개")
for f in sorted(files_at_root):
    print(f"   - {f.name}")

if snapshot_dir:
    files_in_snapshot = list(snapshot_dir.glob("*"))
    print(f"\nSnapshot 디렉토리의 파일: {len(files_in_snapshot)}개")
    for f in sorted(files_in_snapshot):
        if f.is_file():
            print(f"   - {f.name}")
        else:
            print(f"   - {f.name}/ (심볼릭 링크)")

print("\n2️⃣ 검증 결과:")
print("-" * 60)

# 필수 파일 확인
required = ["model.safetensors", "config.json", "preprocessor_config.json", "tokenizer.json"]
all_present = True

for filename in required:
    at_root = (models_dir / filename).exists()
    at_snapshot = (snapshot_dir / filename).exists() if snapshot_dir else False
    
    if at_root or at_snapshot:
        loc = "models_dir" if at_root else "snapshot_dir"
        size = (models_dir / filename).stat().st_size if at_root else (snapshot_dir / filename).stat().st_size
        print(f"✅ {filename:30s} ({loc}, {size / (1024**2):.1f} MB)")
    else:
        print(f"❌ {filename:30s} (NOT FOUND)")
        all_present = False

print()
if all_present:
    print("✅ 모든 필수 파일 확인됨!")
    print("\n📦 모델 디렉토리 구조 정상")
else:
    print("❌ 일부 파일이 누락되었습니다")

print("=" * 60)
