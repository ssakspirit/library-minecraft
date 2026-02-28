"""
태그 전용 크롤러 - Playwright로 category-box-list만 추출
resources_complete.json의 태그 누락 리소스만 크롤링
"""
import json
import time
import sys
import io
import os
from playwright.sync_api import sync_playwright

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 배치 크기
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '50'))


def extract_tags(page, url, retries=2):
    """태그만 추출"""
    for attempt in range(retries):
        try:
            page.goto(url, timeout=20000, wait_until='domcontentloaded')
            time.sleep(1)  # DOM 로딩 대기
            break
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            else:
                return {'success': False, 'error': str(e)[:100], 'url': url}

    try:
        # JavaScript로 태그 추출 - category-box-list 사용
        tags_data = page.evaluate("""() => {
            const ul = document.querySelector('ul.category-box-list');
            if (ul) {
                const items = Array.from(ul.querySelectorAll('li.item'));
                return items.map(li => li.textContent.trim()).filter(t => t);
            }
            return null;
        }""")

        if tags_data:
            return {'success': True, 'tags': tags_data, 'url': url}
        else:
            return {'success': False, 'error': 'No category-box-list found', 'url': url}

    except Exception as e:
        return {'success': False, 'error': str(e)[:100], 'url': url}


def main():
    print("=" * 70)
    print("🏷️  Tags-Only Crawler - Playwright with category-box-list")
    print("=" * 70)
    print()

    # 데이터 로드
    with open('data/resources_enhanced.json', 'r', encoding='utf-8') as f:
        resources = json.load(f)

    # 태그 누락 리소스 찾기
    missing_tags = [(i, r) for i, r in enumerate(resources) if not r.get('tags')]

    print(f"📊 Status:")
    print(f"   Total: {len(resources)}")
    print(f"   Has tags: {len(resources) - len(missing_tags)} ({(len(resources) - len(missing_tags)) * 100 // len(resources)}%)")
    print(f"   Missing tags: {len(missing_tags)}")
    print()

    if not missing_tags:
        print("🎉 All resources have tags!")
        return

    # 배치 설정
    batch = missing_tags[:BATCH_SIZE]
    print(f"🕷️  Crawling batch: {len(batch)} resources")
    print(f"   Remaining: {max(0, len(missing_tags) - BATCH_SIZE)}")
    print()

    # Playwright 시작
    success_count = 0
    failed_count = 0
    start_time = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False로 HTTP2 에러 회피
        page = browser.new_page()

        for idx, resource in batch:
            url = resource['url']
            title = resource.get('title', 'Unknown')[:50]

            print(f"[{success_count + failed_count + 1}/{len(batch)}] {title}")

            result = extract_tags(page, url)

            if result['success']:
                tags = result['tags']
                resources[idx]['tags'] = ', '.join(tags)
                print(f"  ✅ Tags: {', '.join(tags)}")
                success_count += 1
            else:
                print(f"  ❌ {result.get('error', 'Unknown error')}")
                failed_count += 1

            time.sleep(3)  # 대기

            # 10개마다 저장
            if (success_count + failed_count) % 10 == 0:
                with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
                    json.dump(resources, f, ensure_ascii=False, indent=2)
                print(f"  💾 Auto-saved")

        browser.close()

    # 최종 저장
    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(resources, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time

    # 결과 요약
    print()
    print("=" * 70)
    print("✨ Results")
    print("=" * 70)
    print(f"Success: {success_count}/{len(batch)} ({success_count * 100 // len(batch) if len(batch) > 0 else 0}%)")
    print(f"Failed: {failed_count}/{len(batch)}")
    print(f"Time: {elapsed:.1f} seconds")
    print(f"Speed: {len(batch) / elapsed:.2f} resources/second")
    print()
    print(f"Total progress: {len(resources) - len(missing_tags) + success_count}/{len(resources)} ({((len(resources) - len(missing_tags) + success_count) * 100) // len(resources)}%)")
    print()
    print(f"💾 Saved to: data/resources_enhanced.json")
    print()


if __name__ == "__main__":
    main()
