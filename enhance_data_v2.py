"""
리소스 상세 정보 크롤링 스크립트 v2
MCP Playwright 방식을 사용하여 HTTP2 오류 회피
"""
import json
import sys
import io
from playwright.sync_api import sync_playwright
import time
import re

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def extract_resource_details(page, url):
    """리소스 페이지에서 상세 정보 추출"""
    try:
        # 페이지 이동
        page.goto(url, timeout=60000)
        time.sleep(3)  # 페이지 로딩 대기

        # JavaScript로 정보 추출
        details = page.evaluate("""() => {
            const info = {};
            const bodyText = document.body.innerText;

            // Ages 찾기
            const agesMatch = bodyText.match(/ages?\\s*(\\d+[-–]\\d+)/i);
            if (agesMatch) info.ages = agesMatch[1];

            // Submitted by 찾기
            const submittedMatch = bodyText.match(/Submitted by[:\\s]*([^\\n]+)/i);
            if (submittedMatch) info.submitted_by = submittedMatch[1].trim();

            // Updated 찾기
            const updatedMatch = bodyText.match(/Updated[:\\s]*([^\\n]+)/i);
            if (updatedMatch) info.updated = updatedMatch[1].trim();

            // Available languages 찾기 (첫 5개 언어만)
            const langMatch = bodyText.match(/Available languages?[:\\s]*([^\\n]+)/i);
            if (langMatch) {
                const langs = langMatch[1].trim();
                // 언어 목록이 너무 길면 간단히 정리
                if (langs.length > 100) {
                    const langList = langs.match(/[A-Z][a-zäöüß]+/g) || [];
                    info.available_languages = langList.slice(0, 5).join(', ');
                    if (langList.length > 5) info.available_languages += ', ...';
                } else {
                    info.available_languages = langs;
                }
            }

            return info;
        }""")

        return details

    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return None


def enhance_resources_data(limit=None, start_from=0):
    """리소스 데이터에 상세 정보 추가"""
    # 기존 데이터 로드
    with open('data/resources.json', 'r', encoding='utf-8') as f:
        all_resources = json.load(f)

    # 이미 처리된 데이터가 있으면 로드
    try:
        with open('data/resources_enhanced.json', 'r', encoding='utf-8') as f:
            enhanced_resources = json.load(f)
            print(f"📂 기존 enhanced 데이터 로드: {len(enhanced_resources)}개")
    except FileNotFoundError:
        enhanced_resources = []
        print(f"📂 새로운 enhanced 데이터 시작")

    # 이미 처리된 URL 목록
    enhanced_urls = {r['url'] for r in enhanced_resources}

    # 처리할 리소스 선택
    resources_to_process = []
    for resource in all_resources[start_from:]:
        if resource['url'] not in enhanced_urls:
            resources_to_process.append(resource)
        if limit and len(resources_to_process) >= limit:
            break

    if not resources_to_process:
        print("✅ 모든 리소스가 이미 처리되었습니다!")
        return

    print(f"📚 처리할 리소스: {len(resources_to_process)}개")
    print(f"📚 이미 처리됨: {len(enhanced_urls)}개")
    print(f"📚 총 리소스: {len(all_resources)}개")
    print()

    # Playwright 초기화
    with sync_playwright() as p:
        # Chromium 브라우저 시작 (headless)
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        success_count = 0

        for idx, resource in enumerate(resources_to_process, 1):
            url = resource['url']
            print(f"[{idx}/{len(resources_to_process)}] {resource['title'][:50]}...")
            print(f"   URL: {url}")

            # 상세 정보 추출
            details = extract_resource_details(page, url)

            if details:
                # 데이터 업데이트
                resource['ages'] = details.get('ages')
                resource['submitted_by'] = details.get('submitted_by')
                resource['updated'] = details.get('updated')
                resource['available_languages'] = details.get('available_languages')

                print(f"   ✅ Ages: {details.get('ages')}")
                print(f"   ✅ Submitted: {details.get('submitted_by')}")
                print(f"   ✅ Updated: {details.get('updated')}")
                print(f"   ✅ Languages: {details.get('available_languages', '')[:50]}...")

                enhanced_resources.append(resource)
                success_count += 1

                # 진행 상황 저장 (5개마다)
                if idx % 5 == 0:
                    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
                        json.dump(enhanced_resources, f, ensure_ascii=False, indent=2)
                    print(f"   💾 중간 저장 ({len(enhanced_resources)}개)")
            else:
                print(f"   ⚠️ 정보 추출 실패")

            print()
            time.sleep(2)  # Rate limiting

        context.close()
        browser.close()

    # 최종 저장
    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(enhanced_resources, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 완료!")
    print(f"   시도: {len(resources_to_process)}개")
    print(f"   성공: {success_count}개")
    print(f"   총 enhanced: {len(enhanced_resources)}개")
    print(f"   저장: data/resources_enhanced.json")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='리소스 상세 정보 크롤링')
    parser.add_argument('--limit', type=int, default=10, help='처리할 최대 개수 (기본: 10)')
    parser.add_argument('--start', type=int, default=0, help='시작 인덱스 (기본: 0)')
    parser.add_argument('--all', action='store_true', help='전체 리소스 처리')

    args = parser.parse_args()

    limit = None if args.all else args.limit

    print("🚀 리소스 상세 정보 크롤링 시작")
    print()

    if limit:
        print(f"📌 모드: 테스트 ({limit}개)")
    else:
        print(f"📌 모드: 전체 (1,123개)")

    print()

    enhance_resources_data(limit=limit, start_from=args.start)
