"""
현재 resources.json 데이터 구조 확인
"""
import json
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 데이터 로드
with open('data/resources.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"총 리소스 개수: {len(data)}")
print("\n샘플 리소스 (첫 번째):")
print("=" * 60)
print(json.dumps(data[0], indent=2, ensure_ascii=False))
print("=" * 60)
print("\n현재 키(key) 목록:")
print(list(data[0].keys()))
