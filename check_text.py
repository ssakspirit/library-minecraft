"""
수집된 텍스트 데이터 확인
"""
import sys
import io
import json
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def check_collected_text():
    path = Path('data/resources_with_text.json')

    if not path.exists():
        print(f"❌ 파일이 없습니다: {path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=" * 80)
    print("📊 수집된 텍스트 데이터 분석")
    print("=" * 80)

    # 통계
    total = len(data)
    with_text = sum(1 for r in data if r.get('text'))
    text_lengths = [len(r.get('text', '')) for r in data if r.get('text')]

    print(f"\n총 리소스: {total}개")
    print(f"텍스트 있음: {with_text}개")

    if text_lengths:
        print(f"\n텍스트 길이 통계:")
        print(f"  평균: {sum(text_lengths)/len(text_lengths):.0f}자")
        print(f"  최소: {min(text_lengths)}자")
        print(f"  최대: {max(text_lengths)}자")

    # 샘플 출력
    print("\n" + "=" * 80)
    print("📄 샘플 3개")
    print("=" * 80)

    for i, resource in enumerate(data[:3]):
        text = resource.get('text', '')
        print(f"\n{i+1}. {resource['title']}")
        print(f"   URL: {resource['url']}")
        print(f"   텍스트 길이: {len(text)}자")
        print(f"   텍스트 미리보기:")
        print(f"   {text[:300]}...")
        print("-" * 80)


if __name__ == "__main__":
    check_collected_text()
