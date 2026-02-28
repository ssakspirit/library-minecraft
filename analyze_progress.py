"""
크롤링 진행 상황 분석
"""
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 데이터 로드
with open('data/resources_enhanced.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

completed = [r for r in data if r.get('thumbnail_url')]
failed_indices = [i for i, r in enumerate(data, 1) if not r.get('thumbnail_url')]
completed_indices = [i for i, r in enumerate(data, 1) if r.get('thumbnail_url')]

print(f"총 리소스: {len(data)}")
print(f"완료: {len(completed)} ({len(completed)*100//len(data)}%)")
print(f"미완료: {len(data) - len(completed)}")
print()

if completed_indices:
    print(f"완료된 첫 리소스: #{completed_indices[0]}")
    print(f"완료된 마지막 리소스: #{completed_indices[-1]}")
    print(f"  {data[completed_indices[-1]-1]['title'][:60]}")
    print()

# 실패 구간 분석
print("실패 구간 분석:")
if failed_indices:
    # 첫 실패 구간
    first_failed = failed_indices[0]
    print(f"  첫 실패 리소스: #{first_failed}")

    # 연속 실패 구간 찾기
    consecutive_fails = []
    start = None
    prev = None

    for idx in failed_indices:
        if start is None:
            start = idx
            prev = idx
        elif idx == prev + 1:
            prev = idx
        else:
            consecutive_fails.append((start, prev, prev - start + 1))
            start = idx
            prev = idx

    if start is not None:
        consecutive_fails.append((start, prev, prev - start + 1))

    # 가장 큰 연속 실패 구간 10개
    consecutive_fails.sort(key=lambda x: x[2], reverse=True)
    print(f"\n  큰 연속 실패 구간 Top 5:")
    for i, (start, end, count) in enumerate(consecutive_fails[:5], 1):
        print(f"    {i}. #{start}-{end} ({count}개)")
        print(f"       {data[start-1]['title'][:50]} ~ {data[end-1]['title'][:50]}")

print()
print(f"실패한 리소스 파일 저장: failed_resources.json")

# 실패한 리소스만 저장
failed_resources = [r for r in data if not r.get('thumbnail_url')]
with open('failed_resources.json', 'w', encoding='utf-8') as f:
    json.dump(failed_resources, f, ensure_ascii=False, indent=2)

print(f"완료!")
