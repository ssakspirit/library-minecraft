"""
실패한 리소스만 재시도 크롤러 - 매우 보수적 설정
- 대기 시간: 10초
- 휴식: 25개마다 2분
- 배치 크롤링: 최대 100개만 처리하고 중단
"""
import json
import time
import sys
import io
from playwright.sync_api import sync_playwright

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def crawl_resource(page, url, retries=3):
    """리소스 하나 크롤링"""
    for attempt in range(retries):
        try:
            page.goto(url, timeout=30000)
            time.sleep(3)
            break
        except Exception as e:
            if attempt < retries - 1:
                print(f"   Retry {attempt + 1}/{retries - 1}: {str(e)[:80]}", flush=True)
                time.sleep(15)  # 재시도 전 15초 대기 (10초 -> 15초)
                continue
            else:
                print(f"   Error: {str(e)[:100]}", flush=True)
                return None

    try:
        # JavaScript로 정보 추출
        data = page.evaluate("""() => {
            const info = {};

            // 제목
            const h1 = document.querySelector('h1');
            if (h1) info.title = h1.textContent.trim();

            // 썸네일 - meta 태그에서 추출 (og:image 또는 twitter:image)
            const ogImage = document.querySelector('meta[property="og:image"]');
            const twitterImage = document.querySelector('meta[name="twitter:image"]');
            const metaImage = ogImage?.content || twitterImage?.content;

            if (metaImage) {
                // 상대 경로면 절대 경로로 변환
                if (metaImage.startsWith('/')) {
                    info.thumbnail_url = 'https://education.minecraft.net' + metaImage;
                } else if (metaImage.startsWith('http')) {
                    info.thumbnail_url = metaImage;
                } else {
                    info.thumbnail_url = 'https://education.minecraft.net/' + metaImage;
                }
            }

            // 태그 - h1 바로 다음에 있는 list의 listitem들
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
        print(f"   Error: {str(e)[:100]}")
        return None


def main():
    # 전체 데이터 로드
    with open('data/resources_enhanced.json', 'r', encoding='utf-8') as f:
        resources = json.load(f)

    # 실패한 리소스만 필터링
    failed = [(i, r) for i, r in enumerate(resources) if not r.get('thumbnail_url')]

    print(f"Total resources: {len(resources)}")
    print(f"Failed resources: {len(failed)}")
    print(f"Already completed: {len(resources) - len(failed)}")
    print()

    # 배치 크롤링 설정
    BATCH_SIZE = 100  # 한 번에 최대 100개만
    batch_failed = failed[:BATCH_SIZE]

    print(f"This batch: {len(batch_failed)} resources")
    print(f"Remaining after this: {len(failed) - BATCH_SIZE if len(failed) > BATCH_SIZE else 0}")
    print()

    # Playwright 시작
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False로 HTTP2 에러 회피
        page = browser.new_page()

        success = 0
        failed_count = 0

        for count, (idx, resource) in enumerate(batch_failed, 1):
            url = resource['url']

            print(f"[{count}/{len(batch_failed)}] #{idx+1}/{len(resources)} {resource['title'][:50]}", flush=True)
            print(f"  URL: {url}", flush=True)

            data = crawl_resource(page, url)

            if data:
                # 데이터 업데이트
                if data.get('thumbnail_url'):
                    resources[idx]['thumbnail_url'] = data['thumbnail_url']
                    print(f"  OK Thumbnail: {data['thumbnail_url'][:60]}", flush=True)

                if data.get('tags'):
                    resources[idx]['tags'] = ', '.join(data['tags'])
                    print(f"  OK Tags: {resources[idx]['tags']}", flush=True)

                if data.get('submitted_by'):
                    resources[idx]['submitted_by'] = data['submitted_by']
                    print(f"  OK Submitted: {data['submitted_by']}", flush=True)

                if data.get('updated'):
                    resources[idx]['updated'] = data['updated']
                    print(f"  OK Updated: {data['updated']}", flush=True)

                success += 1

                # 5개마다 저장
                if success % 5 == 0:
                    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
                        json.dump(resources, f, ensure_ascii=False, indent=2)
                    print(f"  [SAVE] {success} done", flush=True)
            else:
                failed_count += 1

            print(flush=True)
            time.sleep(10)  # 대기 (5초 -> 10초로 증가)

            # 25개마다 2분 휴식
            if count % 25 == 0:
                print(f"--- Progress: {success}/{len(batch_failed)} success, {failed_count} failed ---", flush=True)
                print(f"--- Taking a 2-minute break to avoid rate limiting... ---", flush=True)
                time.sleep(120)  # 2분 휴식

        browser.close()

    # 최종 저장
    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(resources, f, ensure_ascii=False, indent=2)

    print(f"\nBatch completed!")
    print(f"Success: {success}/{len(batch_failed)}")
    print(f"Failed: {failed_count}/{len(batch_failed)}")
    print(f"Remaining: {len(failed) - BATCH_SIZE if len(failed) > BATCH_SIZE else 0} resources")


if __name__ == "__main__":
    main()
