"""
데이터 품질 분석 및 추천 가능성 평가
"""
import sys
import io
import json
import random
from pathlib import Path
from collections import Counter

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def analyze_data_quality():
    """데이터 품질 분석"""

    with open('data/resources.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=" * 80)
    print("📊 데이터 품질 분석 리포트")
    print("=" * 80)

    # 기본 통계
    print(f"\n✅ 총 리소스 수: {len(data)}")

    # 타입별 분포
    types = Counter(r['type'] for r in data)
    print(f"\n📋 타입별 분포:")
    for type_name, count in types.items():
        print(f"  - {type_name}: {count}개")

    # Description 길이 분석
    desc_lengths = [len(r.get('description', '')) for r in data]
    avg_desc_length = sum(desc_lengths) / len(desc_lengths)
    print(f"\n📝 Description 분석:")
    print(f"  - 평균 길이: {avg_desc_length:.0f}자")
    print(f"  - 최소 길이: {min(desc_lengths)}자")
    print(f"  - 최대 길이: {max(desc_lengths)}자")

    # 빈 description 체크
    empty_desc = sum(1 for r in data if not r.get('description', '').strip())
    print(f"  - 빈 description: {empty_desc}개 ({empty_desc/len(data)*100:.1f}%)")

    # Subjects 분석
    all_subjects = []
    for r in data:
        subjects = r.get('subjects', '')
        if subjects:
            all_subjects.extend(subjects.split(','))

    subject_counts = Counter(all_subjects)
    print(f"\n🎯 과목 분석 (상위 10개):")
    for subject, count in subject_counts.most_common(10):
        print(f"  - {subject}: {count}개")

    # 샘플 데이터 출력
    print("\n" + "=" * 80)
    print("📄 랜덤 샘플 5개")
    print("=" * 80)

    samples = random.sample(data, min(5, len(data)))
    for i, resource in enumerate(samples, 1):
        print(f"\n{i}. [{resource['type']}] {resource['title']}")
        print(f"   과목: {resource.get('subjects', 'N/A')}")
        print(f"   설명: {resource.get('description', 'N/A')[:150]}...")
        print(f"   URL: {resource['url']}")

    # 키워드 추천 가능성 평가
    print("\n" + "=" * 80)
    print("🤔 키워드 기반 추천 가능성 평가")
    print("=" * 80)

    # 현재 데이터로 가능한 것
    print("\n✅ 현재 데이터로 가능한 추천:")
    print("  1. 과목 기반 필터링 (매우 정확)")
    print("  2. 타입 기반 필터링 (World/Challenge/Lesson)")
    print("  3. 제목 키워드 검색 (보통)")
    print("  4. 짧은 설명 기반 키워드 매칭 (제한적)")
    print("  5. SQLite FTS5 전체 텍스트 검색 (빠름)")

    # 현재 데이터의 한계
    print("\n⚠️ 현재 데이터의 한계:")
    print("  1. Description이 너무 짧음 (~100자, 잘림)")
    print("  2. 학습 목표(objectives) 없음")
    print("  3. 난이도(difficulty) 정보 없음")
    print("  4. 소요 시간(duration) 정보 없음")
    print("  5. 전체 콘텐츠(full_content) 없음")

    # 개선 방안
    print("\n💡 추천 품질 개선 방안:")
    print("  1. 웹 크롤링으로 상세 정보 수집 (crawler.py)")
    print("  2. 키워드 임베딩 (OpenAI Embeddings)")
    print("  3. 콘텐츠 기반 유사도 분석 (TF-IDF)")
    print("  4. 협업 필터링 (사용자 데이터 필요)")
    print("  5. LLM 활용 추천 (GPT-4, Claude)")

    return data


def test_keyword_search(data, keyword):
    """키워드 검색 테스트"""
    print(f"\n🔍 키워드 검색 테스트: '{keyword}'")
    print("-" * 80)

    results = []
    keyword_lower = keyword.lower()

    for resource in data:
        score = 0

        # 제목에서 검색
        if keyword_lower in resource['title'].lower():
            score += 3

        # 설명에서 검색
        if keyword_lower in resource.get('description', '').lower():
            score += 2

        # 과목에서 검색
        if keyword_lower in resource.get('subjects', '').lower():
            score += 1

        if score > 0:
            results.append((score, resource))

    # 점수순 정렬
    results.sort(reverse=True, key=lambda x: x[0])

    print(f"검색 결과: {len(results)}개")
    print(f"\n상위 5개:")
    for i, (score, resource) in enumerate(results[:5], 1):
        print(f"\n{i}. [{resource['type']}] {resource['title']} (점수: {score})")
        print(f"   과목: {resource.get('subjects', 'N/A')}")
        print(f"   설명: {resource.get('description', 'N/A')[:100]}...")


def main():
    data = analyze_data_quality()

    # 키워드 검색 테스트
    test_keywords = ['coding', 'math', 'science', 'AI', 'chemistry']

    print("\n" + "=" * 80)
    print("🧪 키워드 검색 테스트")
    print("=" * 80)

    for keyword in test_keywords[:2]:  # 처음 2개만 테스트
        test_keyword_search(data, keyword)

    # 결론
    print("\n" + "=" * 80)
    print("📌 결론")
    print("=" * 80)
    print("""
현재 데이터로 키워드 기반 추천이 가능한가?

✅ 가능함! (단, 제한적)
- 과목, 타입, 제목 기반 필터링은 매우 잘 작동
- 간단한 키워드 검색은 충분히 가능
- SQLite FTS5로 빠른 검색 지원

⚠️ 하지만 품질 개선이 필요함:
- 현재: 기본적인 키워드 매칭 수준
- 개선 후: 의미 기반 추천, 컨텍스트 이해

🚀 추천 개선 단계:
1단계 (현재): 키워드 + 과목 필터링 ✅
2단계: 크롤링으로 상세 정보 수집
3단계: TF-IDF 유사도 분석
4단계: 임베딩 기반 의미 검색
5단계: LLM 기반 자연어 추천

지금 바로 만들 수 있는 것:
- 기본 검색 챗봇 (키워드 + 필터)
- 과목별 리소스 브라우저
- 간단한 추천 시스템
""")


if __name__ == "__main__":
    main()
