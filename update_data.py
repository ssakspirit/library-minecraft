"""
데이터 자동 업데이트 스크립트
- 새로운 리소스 감지 (HTML 재파싱)
- 누락된 썸네일/태그 보완 (배치 크롤링)
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

# 배치 크기 설정 (환경 변수로 조정 가능)
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '50'))  # 기본 50개


def fetch_latest_resources():
    """최신 리소스 목록 가져오기 (HTML 재파싱)"""
    print("📥 Fetching latest resource list from website...")

    # 기존 HTML 파일이 있으면 사용, 없으면 다운로드 필요
    # 여기서는 간단히 기존 data/resources.json 사용
    # TODO: 실제로는 HTML을 다시 다운로드하고 파싱해야 함

    with open('data/resources.json', 'r', encoding='utf-8') as f:
        resources = json.load(f)

    print(f"   Found {len(resources)} resources in base data")
    return resources


def crawl_resource(page, url, retries=3):
    """리소스 하나 크롤링"""
    for attempt in range(retries):
        try:
            page.goto(url, timeout=30000, wait_until='domcontentloaded')
            time.sleep(2)
            break
        except Exception as e:
            if attempt < retries - 1:
                wait_time = 15 * (attempt + 1)  # 점진적 백오프
                print(f"   ⚠️  Retry {attempt + 1}/{retries - 1} (waiting {wait_time}s): {str(e)[:60]}", flush=True)
                time.sleep(wait_time)
                continue
            else:
                print(f"   ❌ Failed after {retries} attempts: {str(e)[:80]}", flush=True)
                return None

    try:
        # JavaScript로 정보 추출
        data = page.evaluate("""() => {
            const info = {};

            // 썸네일 - meta 태그에서 추출
            const ogImage = document.querySelector('meta[property="og:image"]');
            const twitterImage = document.querySelector('meta[name="twitter:image"]');
            const metaImage = ogImage?.content || twitterImage?.content;

            if (metaImage) {
                if (metaImage.startsWith('/')) {
                    info.thumbnail_url = 'https://education.minecraft.net' + metaImage;
                } else if (metaImage.startsWith('http')) {
                    info.thumbnail_url = metaImage;
                } else {
                    info.thumbnail_url = 'https://education.minecraft.net/' + metaImage;
                }
            }

            // 태그
            const h1Element = document.querySelector('h1');
            if (h1Element) {
                const parent = h1Element.parentElement;
                if (parent) {
                    const list = parent.querySelector('ul');
                    if (list) {
                        const items = Array.from(list.querySelectorAll('li'));
                        info.tags = items.map(li => li.textContent.trim()).filter(t => t && t.length < 20);
                    }
                }
            }

            // Submitted by
            const bodyText = document.body.innerText;
            const submittedText = bodyText.match(/Submitted by[:\\s]*([^\\n]+)/i);
            if (submittedText) info.submitted_by = submittedText[1].trim();

            // Updated
            const updatedText = bodyText.match(/Updated[:\\s]*([^\\n]+)/i);
            if (updatedText) info.updated = updatedText[1].trim();

            return info;
        }""")

        return data

    except Exception as e:
        print(f"   ❌ Extraction error: {str(e)[:80]}")
        return None


def main():
    print("=" * 70)
    print("🔄 Minecraft Education Resource Update")
    print("=" * 70)
    print()

    # 기존 enhanced 데이터 로드
    try:
        with open('data/resources_enhanced.json', 'r', encoding='utf-8') as f:
            enhanced = json.load(f)
        print(f"✅ Loaded existing enhanced data: {len(enhanced)} resources")
    except FileNotFoundError:
        # resources.json을 기반으로 시작
        with open('data/resources.json', 'r', encoding='utf-8') as f:
            enhanced = json.load(f)
        print(f"⚠️  No enhanced data found, starting from base: {len(enhanced)} resources")

    # 최신 리소스 목록 가져오기
    latest_resources = fetch_latest_resources()

    # 새로운 리소스 감지
    existing_urls = {r['url'] for r in enhanced}
    new_resources = [r for r in latest_resources if r['url'] not in existing_urls]

    if new_resources:
        print(f"🆕 Found {len(new_resources)} new resources!")
        enhanced.extend(new_resources)
    else:
        print("✓ No new resources found")

    # 누락된 데이터가 있는 리소스 찾기
    missing_data = [(i, r) for i, r in enumerate(enhanced) if not r.get('thumbnail_url')]

    print()
    print(f"📊 Current status:")
    print(f"   Total: {len(enhanced)}")
    print(f"   Complete: {len(enhanced) - len(missing_data)} ({(len(enhanced) - len(missing_data)) * 100 // len(enhanced)}%)")
    print(f"   Missing data: {len(missing_data)}")
    print()

    if not missing_data:
        print("🎉 All resources have complete data! No crawling needed.")
        return

    # 배치 크롤링
    batch = missing_data[:BATCH_SIZE]
    print(f"🕷️  Crawling batch: {len(batch)} resources (max: {BATCH_SIZE})")
    print(f"   Remaining after this batch: {max(0, len(missing_data) - BATCH_SIZE)}")
    print()

    # Playwright 시작
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # CI 환경에서는 headless
        page = browser.new_page()

        success = 0
        failed = 0

        for count, (idx, resource) in enumerate(batch, 1):
            url = resource['url']

            print(f"[{count}/{len(batch)}] {resource['title'][:50]}")
            print(f"  🔗 {url}")

            data = crawl_resource(page, url)

            if data and data.get('thumbnail_url'):
                # 데이터 업데이트
                enhanced[idx]['thumbnail_url'] = data['thumbnail_url']
                print(f"  ✅ Thumbnail: {data['thumbnail_url'][:60]}")

                if data.get('tags'):
                    enhanced[idx]['tags'] = ', '.join(data['tags'])
                    print(f"  🏷️  Tags: {enhanced[idx]['tags']}")

                if data.get('submitted_by'):
                    enhanced[idx]['submitted_by'] = data['submitted_by']

                if data.get('updated'):
                    enhanced[idx]['updated'] = data['updated']

                success += 1

                # 10개마다 중간 저장
                if success % 10 == 0:
                    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
                        json.dump(enhanced, f, ensure_ascii=False, indent=2)
                    print(f"  💾 Progress saved: {success}/{len(batch)}")
            else:
                failed += 1
                print(f"  ⚠️  Failed to extract data")

            print()

            # Rate limiting 방지
            time.sleep(8)  # 요청 간 8초 대기

            # 20개마다 긴 휴식
            if count % 20 == 0 and count < len(batch):
                print(f"⏸️  Break time (progress: {success} success, {failed} failed)")
                print(f"   Waiting 90 seconds to avoid rate limiting...")
                print()
                time.sleep(90)

        browser.close()

    # 최종 저장
    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(enhanced, f, ensure_ascii=False, indent=2)

    # 결과 요약
    print()
    print("=" * 70)
    print("✨ Update Complete!")
    print("=" * 70)
    print(f"Batch results: {success} success, {failed} failed")
    print(f"Total progress: {len(enhanced) - len(missing_data) + success}/{len(enhanced)} ({((len(enhanced) - len(missing_data) + success) * 100 // len(enhanced))}%)")
    print(f"Remaining: {max(0, len(missing_data) - success)}")
    print()


if __name__ == "__main__":
    main()
