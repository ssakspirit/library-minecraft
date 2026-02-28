"""
Tags 누락 수정 - 원본 subjects를 tags로 복사
"""
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 원본 데이터 로드
with open('data/resources.json', 'r', encoding='utf-8') as f:
    original = json.load(f)

# 크롤링된 데이터 로드
with open('data/resources_complete.json', 'r', encoding='utf-8') as f:
    complete = json.load(f)

# URL로 매핑
original_map = {r['url']: r for r in original}

# Tags 보완
before_tags = len([r for r in complete if r.get('tags')])

for resource in complete:
    url = resource['url']

    # 크롤링된 tags가 없으면
    if not resource.get('tags'):
        # 원본 subjects가 있으면 tags로 사용
        if url in original_map and original_map[url].get('subjects'):
            resource['tags'] = original_map[url]['subjects']

    # 크롤링된 tags가 있지만 리스트 형태면 문자열로 변환
    elif isinstance(resource.get('tags'), list):
        resource['tags'] = ', '.join(resource['tags'])

after_tags = len([r for r in complete if r.get('tags')])

# 저장
with open('data/resources_complete.json', 'w', encoding='utf-8') as f:
    json.dump(complete, f, ensure_ascii=False, indent=2)

print(f"✅ Tags 보완 완료!")
print(f"Before: {before_tags}/{len(complete)} ({before_tags*100//len(complete)}%)")
print(f"After:  {after_tags}/{len(complete)} ({after_tags*100//len(complete)}%)")
print(f"Added:  {after_tags - before_tags} resources")
