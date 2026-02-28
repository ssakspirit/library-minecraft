import json
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('data/resources_enhanced.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"총 {len(data)}개 리소스\n")
print("샘플 리소스 (#5):")
print("=" * 60)
print(json.dumps(data[4], indent=2, ensure_ascii=False))
