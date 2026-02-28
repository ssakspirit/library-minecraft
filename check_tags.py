"""
tags 누락 확인
"""
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

data = json.load(open('data/resources_complete.json', 'r', encoding='utf-8'))

no_tags = [r for r in data if not r.get('tags')]
with_tags = [r for r in data if r.get('tags')]

print(f"총 리소스: {len(data)}")
print(f"Tags 있음: {len(with_tags)} ({len(with_tags)*100//len(data)}%)")
print(f"Tags 없음: {len(no_tags)} ({len(no_tags)*100//len(data)}%)")
print()

print("Tags 없는 리소스 샘플 5개:")
for r in no_tags[:5]:
    print(f"  - {r['title'][:50]} ({r['type']})")
    print(f"    URL: {r['url']}")
print()

print("Tags 있는 리소스 샘플 5개:")
for r in with_tags[:5]:
    print(f"  - {r['title'][:50]} ({r['type']})")
    print(f"    Tags: {r['tags']}")
