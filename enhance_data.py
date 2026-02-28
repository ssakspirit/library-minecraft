"""
리소스 상세 정보 크롤링 스크립트
각 리소스 페이지에서 ages, submitted_by, updated, available_languages 추출
"""
import json
import sys
import io
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time
import re

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def extract_resource_details(page, url):
    """리소스 페이지에서 상세 정보 추출"""
    try:
        page.goto(url, wait_until='networkidle', timeout=30000)
        time.sleep(2)  # 페이지 로딩 대기

        details = {
            'ages': None,
            'submitted_by': None,
            'updated': None,
            'available_languages': None
        }

        # 페이지 HTML 가져오기
        content = page.content()

        # Ages 추출 (예: "ages 8-10")
        ages_match = re.search(r'ages?\s*(\d+[-–]\d+)', content, re.IGNORECASE)
        if ages_match:
            details['ages'] = ages_match.group(1)

        # Submitted by 추출
        submitted_match = re.search(r'Submitted by[:\s]*([^<\n]+)', content, re.IGNORECASE)
        if submitted_match:
            details['submitted_by'] = submitted_match.group(1).strip()

        # Updated 추출 (다양한 날짜 형식)
        updated_match = re.search(r'Updated[:\s]*([^<\n]+)', content, re.IGNORECASE)
        if updated_match:
            details['updated'] = updated_match.group(1).strip()

        # Available languages 추출
        lang_match = re.search(r'Available languages?[:\s]*([^<\n]+)', content, re.IGNORECASE)
        if lang_match:
            details['available_languages'] = lang_match.group(1).strip()

        return details

    except PlaywrightTimeout:
        print(f"⏱️ 타임아웃: {url}")
        return None
    except Exception as e:
        print(f"❌ 오류 ({url}): {e}")
        return None


def enhance_resources_data(limit=None):
    """리소스 데이터에 상세 정보 추가"""
    # 기존 데이터 로드
    with open('data/resources.json', 'r', encoding='utf-8') as f:
        resources = json.load(f)

    print(f"📚 총 {len(resources)}개 리소스")

    if limit:
        resources = resources[:limit]
        print(f"🔍 테스트: 처음 {limit}개만 처리")

    # Playwright 초기화
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        enhanced_count = 0

        for idx, resource in enumerate(resources, 1):
            url = resource['url']
            print(f"\n[{idx}/{len(resources)}] {resource['title'][:50]}...")
            print(f"   URL: {url}")

            # 상세 정보 추출
            details = extract_resource_details(page, url)

            if details:
                # 데이터 업데이트
                resource['ages'] = details['ages']
                resource['submitted_by'] = details['submitted_by']
                resource['updated'] = details['updated']
                resource['available_languages'] = details['available_languages']

                print(f"   ✅ Ages: {details['ages']}")
                print(f"   ✅ Submitted: {details['submitted_by']}")
                print(f"   ✅ Updated: {details['updated']}")
                print(f"   ✅ Languages: {details['available_languages']}")

                enhanced_count += 1
            else:
                print(f"   ⚠️ 정보 추출 실패")

            # 진행 상황 저장 (10개마다)
            if idx % 10 == 0:
                with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
                    json.dump(resources, f, ensure_ascii=False, indent=2)
                print(f"\n💾 중간 저장 완료 ({idx}/{len(resources)})")

            time.sleep(1)  # Rate limiting

        browser.close()

    # 최종 저장
    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(resources, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 완료!")
    print(f"   처리: {len(resources)}개")
    print(f"   성공: {enhanced_count}개")
    print(f"   저장: data/resources_enhanced.json")
    print("=" * 60)


if __name__ == "__main__":
    # 테스트: 처음 5개만
    print("🧪 테스트 모드: 처음 5개 리소스만 크롤링")
    print()
    enhance_resources_data(limit=5)

    # 전체 실행하려면:
    # enhance_resources_data()
