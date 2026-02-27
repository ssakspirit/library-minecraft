"""
Minecraft Education 리소스 추천 시스템
"""
import sys
import io
import json
from typing import List, Dict, Optional
from database import MinecraftEducationDB

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ResourceRecommender:
    def __init__(self):
        self.db = MinecraftEducationDB()
        self.db.connect()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def search_by_keyword(
        self,
        keyword: str,
        subject: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """키워드로 리소스 검색 및 추천"""

        cursor = self.db.connection.cursor()

        # Base query
        query = """
            SELECT
                r.id,
                r.title,
                r.type,
                r.description,
                r.url,
                GROUP_CONCAT(DISTINCT s.name) as subjects,
                0 as score
            FROM resources r
            LEFT JOIN resource_subjects rs ON r.id = rs.resource_id
            LEFT JOIN subjects s ON rs.subject_id = s.id
            WHERE r.is_active = 1
        """

        params = []

        # 과목 필터
        if subject:
            query += " AND s.name = ?"
            params.append(subject)

        # 타입 필터
        if resource_type:
            query += " AND r.type = ?"
            params.append(resource_type)

        query += " GROUP BY r.id"

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        # 키워드 점수 계산
        keyword_lower = keyword.lower()
        scored_results = []

        for resource in results:
            score = 0

            # 제목 매칭 (가중치 3)
            if keyword_lower in resource['title'].lower():
                score += 3

            # 설명 매칭 (가중치 2)
            if keyword_lower in resource.get('description', '').lower():
                score += 2

            # 과목 매칭 (가중치 1)
            if keyword_lower in resource.get('subjects', '').lower():
                score += 1

            if score > 0:
                resource['score'] = score
                scored_results.append(resource)

        # 점수순 정렬
        scored_results.sort(key=lambda x: x['score'], reverse=True)

        return scored_results[:limit]

    def recommend_by_subject(self, subject: str, limit: int = 10) -> List[Dict]:
        """과목별 추천"""
        return self.search_by_keyword("", subject=subject, limit=limit)

    def recommend_by_type(self, resource_type: str, limit: int = 10) -> List[Dict]:
        """타입별 추천"""
        cursor = self.db.connection.cursor()

        cursor.execute("""
            SELECT
                r.id,
                r.title,
                r.type,
                r.description,
                r.url,
                GROUP_CONCAT(DISTINCT s.name) as subjects
            FROM resources r
            LEFT JOIN resource_subjects rs ON r.id = rs.resource_id
            LEFT JOIN subjects s ON rs.subject_id = s.id
            WHERE r.is_active = 1 AND r.type = ?
            GROUP BY r.id
            ORDER BY r.crawled_at DESC
            LIMIT ?
        """, (resource_type, limit))

        return [dict(row) for row in cursor.fetchall()]

    def recommend_similar(self, resource_id: str, limit: int = 5) -> List[Dict]:
        """유사한 리소스 추천 (같은 과목 기반)"""
        cursor = self.db.connection.cursor()

        # 원본 리소스의 과목 가져오기
        cursor.execute("""
            SELECT s.name
            FROM resource_subjects rs
            JOIN subjects s ON rs.subject_id = s.id
            WHERE rs.resource_id = ?
        """, (resource_id,))

        subjects = [row[0] for row in cursor.fetchall()]

        if not subjects:
            return []

        # 같은 과목을 가진 다른 리소스 찾기
        placeholders = ','.join('?' * len(subjects))
        cursor.execute(f"""
            SELECT
                r.id,
                r.title,
                r.type,
                r.description,
                r.url,
                GROUP_CONCAT(DISTINCT s.name) as subjects,
                COUNT(DISTINCT s.id) as common_subjects
            FROM resources r
            JOIN resource_subjects rs ON r.id = rs.resource_id
            JOIN subjects s ON rs.subject_id = s.id
            WHERE r.is_active = 1
              AND r.id != ?
              AND s.name IN ({placeholders})
            GROUP BY r.id
            ORDER BY common_subjects DESC, r.crawled_at DESC
            LIMIT ?
        """, (resource_id, *subjects, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_popular_by_subject(self) -> Dict[str, int]:
        """과목별 인기도 (리소스 수)"""
        return self.db.get_statistics()['by_subject']


def demo():
    """데모 실행"""
    print("=" * 80)
    print("🎯 Minecraft Education 리소스 추천 시스템 데모")
    print("=" * 80)

    with ResourceRecommender() as recommender:

        # 1. 키워드 검색
        print("\n\n1️⃣ 키워드 검색: 'coding'")
        print("-" * 80)
        results = recommender.search_by_keyword("coding", limit=5)
        for i, r in enumerate(results, 1):
            print(f"\n{i}. [{r['type']}] {r['title']} (점수: {r['score']})")
            print(f"   📚 과목: {r['subjects']}")
            print(f"   📝 {r['description'][:100]}...")
            print(f"   🔗 {r['url']}")

        # 2. 과목 + 키워드 필터링
        print("\n\n2️⃣ 과목 필터: 'Mathematics' + 키워드 'geometry'")
        print("-" * 80)
        results = recommender.search_by_keyword("geometry", subject="Mathematics", limit=5)
        if results:
            for i, r in enumerate(results, 1):
                print(f"\n{i}. {r['title']}")
                print(f"   {r['description'][:100]}...")
        else:
            print("검색 결과가 없습니다. 다른 키워드로 시도:")
            results = recommender.recommend_by_subject("Mathematics", limit=5)
            for i, r in enumerate(results, 1):
                print(f"\n{i}. {r['title']}")
                print(f"   {r['description'][:100]}...")

        # 3. 타입별 추천
        print("\n\n3️⃣ 타입별 추천: 'Challenge' (빌드 챌린지)")
        print("-" * 80)
        results = recommender.recommend_by_type("Challenge", limit=5)
        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r['title']}")
            print(f"   📚 {r['subjects']}")
            print(f"   📝 {r['description'][:100]}...")

        # 4. 유사 리소스 추천
        print("\n\n4️⃣ 유사 리소스 추천")
        print("-" * 80)
        # 첫 번째 coding 리소스 가져오기
        sample = recommender.search_by_keyword("AI", limit=1)
        if sample:
            sample_resource = sample[0]
            print(f"기준 리소스: {sample_resource['title']}")
            print(f"과목: {sample_resource['subjects']}")

            similar = recommender.recommend_similar(sample_resource['id'], limit=5)
            print(f"\n비슷한 리소스 {len(similar)}개:")
            for i, r in enumerate(similar, 1):
                print(f"\n{i}. {r['title']}")
                print(f"   📚 {r['subjects']}")
                print(f"   공통 과목 수: {r.get('common_subjects', 0)}")

        # 5. 과목별 통계
        print("\n\n5️⃣ 과목별 리소스 통계")
        print("-" * 80)
        stats = recommender.get_popular_by_subject()
        for subject, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {subject}: {count}개")

    print("\n" + "=" * 80)
    print("✅ 데모 완료!")
    print("=" * 80)


def interactive_search():
    """인터랙티브 검색 모드"""
    print("\n" + "=" * 80)
    print("🔍 인터랙티브 검색 모드")
    print("=" * 80)
    print("명령어:")
    print("  - 키워드 입력: 검색")
    print("  - 'quit' 또는 'exit': 종료")
    print("  - 'subjects': 과목 목록 보기")
    print("-" * 80)

    with ResourceRecommender() as recommender:
        while True:
            try:
                query = input("\n🔍 검색어 입력: ").strip()

                if not query:
                    continue

                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 종료합니다.")
                    break

                if query.lower() == 'subjects':
                    stats = recommender.get_popular_by_subject()
                    print("\n📚 사용 가능한 과목:")
                    for subject in sorted(stats.keys()):
                        print(f"  - {subject}")
                    continue

                # 검색 실행
                results = recommender.search_by_keyword(query, limit=10)

                if not results:
                    print(f"❌ '{query}'에 대한 검색 결과가 없습니다.")
                    continue

                print(f"\n✅ 검색 결과: {len(results)}개")
                print("-" * 80)

                for i, r in enumerate(results, 1):
                    print(f"\n{i}. [{r['type']}] {r['title']} ⭐{r['score']}")
                    print(f"   📚 {r['subjects']}")
                    print(f"   📝 {r['description']}")
                    print(f"   🔗 {r['url']}")

            except KeyboardInterrupt:
                print("\n\n👋 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류: {e}")


if __name__ == "__main__":
    # 데모 실행
    demo()

    # 인터랙티브 모드
    try:
        interactive_search()
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
