"""
완전 크롤러 - Playwright로 썸네일과 태그 모두 추출
resources_enhanced.json의 누락된 데이터만 크롤링
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


def extract_data(page, url, retries=2):
    """썸네일과 태그 추출"""
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
        # JavaScript로 모든 정보 추출
        data = page.evaluate("""() => {
            const result = {};

            // 제목
            const h1 = document.querySelector('h1');
            if (h1) result.title = h1.textContent.trim();

            // 썸네일 - meta 태그에서 추출
            const ogImage = document.querySelector('meta[property="og:image"]');
            const twitterImage = document.querySelector('meta[name="twitter:image"]');
            const metaImage = ogImage?.content || twitterImage?.content;

            if (metaImage) {
                if (metaImage.startsWith('/')) {
                    result.thumbnail_url = 'https://education.minecraft.net' + metaImage;
                } else if (metaImage.startsWith('http')) {
                    result.thumbnail_url = metaImage;
                } else {
                    result.thumbnail_url = 'https://education.minecraft.net/' + metaImage;
                }
            }

            // 태그 - category-box-list
            const ul = document.querySelector('ul.category-box-list');
            if (ul) {
                const items = Array.from(ul.querySelectorAll('li.item'));
                const tags = items.map(li => li.textContent.trim()).filter(t => t);
                if (tags.length > 0) {
                    result.tags = tags;
                }
            }

            // Submitted by
            const bodyText = document.body.innerText;
            const submittedText = bodyText.match(/Submitted by[:\s]*([^\n]+)/i);
            if (submittedText) result.submitted_by = submittedText[1].trim();

            // Updated
            const updatedText = bodyText.match(/Updated[:\s]*([^\n]+)/i);
            if (updatedText) result.updated = updatedText[1].trim();

            return result;
        }""")

        if data and len(data) > 0:
            return {'success': True, 'data': data, 'url': url}
        else:
            return {'success': False, 'error': 'No data found', 'url': url}

    except Exception as e:
        return {'success': False, 'error': str(e)[:100], 'url': url}


def main():
    print("=" * 70)
    print("🕷️  Complete Crawler - Thumbnail, Tags, Submitted, Updated")
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

            result = extract_data(page, url)

            if result['success']:
                data = result['data']

                # 모든 추출된 정보 저장
                if data.get('title'):
                    resources[idx]['title'] = data['title']

                if data.get('thumbnail_url'):
                    resources[idx]['thumbnail_url'] = data['thumbnail_url']
                    print(f"  ✅ Thumbnail")

                if data.get('tags'):
                    resources[idx]['tags'] = ', '.join(data['tags'])
                    print(f"  ✅ Tags: {', '.join(data['tags'])}")

                if data.get('submitted_by'):
                    resources[idx]['submitted_by'] = data['submitted_by']
                    print(f"  ✅ Submitted by: {data['submitted_by']}")

                if data.get('updated'):
                    resources[idx]['updated'] = data['updated']
                    print(f"  ✅ Updated: {data['updated']}")

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
