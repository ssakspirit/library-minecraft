"""
Playwright를 사용한 리소스 상세 정보 크롤링
thumbnail_url, tags, ages, submitted_by, updated, available_languages 추출
"""
import json
import sys
import io
from playwright.sync_api import sync_playwright
import time

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def extract_all_info(page, url):
    """페이지에서 모든 필요한 정보 추출"""
    try:
        # 페이지 이동
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        time.sleep(2)  # 대기 시간 단축

        # JavaScript로 모든 정보 추출
        info = page.evaluate(r"""() => {
            const data = {};

            // 1. 썸네일 이미지
            const images = Array.from(document.querySelectorAll('img')).filter(img => {
                const src = img.src;
                return !src.includes('logo') &&
                       !src.includes('icon') &&
                       !src.includes('arrow') &&
                       !src.includes('clientlib') &&
                       img.naturalWidth > 200;
            });

            if (images.length > 0) {
                const largestImg = images.sort((a, b) =>
                    (b.naturalWidth * b.naturalHeight) - (a.naturalWidth * a.naturalHeight)
                )[0];
                data.thumbnail_url = largestImg ? largestImg.src : null;
            }

            // Open Graph 이미지 (백업)
            const ogImage = document.querySelector('meta[property="og:image"]');
            if (ogImage && !data.thumbnail_url) {
                const ogUrl = ogImage.content;
                data.thumbnail_url = ogUrl.startsWith('http') ? ogUrl : 'https://education.minecraft.net' + ogUrl;
            }

            // 2. 태그 추출
            const bodyText = document.body.innerText;
            const tags = [];

            // "BuildCreative" 같은 연결된 태그 분리
            const tagLine = bodyText.match(/\n([A-Z][a-z]+[A-Z][a-z]+)\n/);
            if (tagLine) {
                const combined = tagLine[1];
                const separated = combined.split(/(?=[A-Z])/);
                tags.push(...separated);
            }

            data.tags = [...new Set(tags)];

            // 3. Ages
            const agesMatch = bodyText.match(/ages?\s*(\d+[-–]\d+)/i);
            if (agesMatch) data.ages = agesMatch[1];

            // 4. Submitted by
            const submittedMatch = bodyText.match(/Submitted by[:\s]*([^\n]+)/i);
            if (submittedMatch) data.submitted_by = submittedMatch[1].trim();

            // 5. Updated
            const updatedMatch = bodyText.match(/Updated[:\s]*([^\n]+)/i);
            if (updatedMatch) data.updated = updatedMatch[1].trim();

            // 6. Available languages (첫 5개만)
            const langMatch = bodyText.match(/Available languages?[:\s]*([^\n]+)/i);
            if (langMatch) {
                const langs = langMatch[1].trim();
                if (langs.length > 100) {
                    const langList = langs.match(/[A-Z][a-zäöüß]+/g) || [];
                    data.available_languages = langList.slice(0, 5).join(', ');
                    if (langList.length > 5) data.available_languages += ' ...';
                } else {
                    data.available_languages = langs;
                }
            }

            return data;
        }""")

        return info

    except Exception as e:
        print(f"   ❌ 오류: {str(e)[:100]}")
        return None


def enhance_resources(limit=10):
    """리소스 데이터 보강"""
    # 기존 데이터 로드
    with open('data/resources.json', 'r', encoding='utf-8') as f:
        resources = json.load(f)

    print(f"📚 총 {len(resources)}개 리소스")
    if limit:
        print(f"🔍 처음 {limit}개만 처리합니다.\n")
    else:
        print(f"🔍 전체 {len(resources)}개를 처리합니다.\n")

    # Playwright 시작
    with sync_playwright() as p:
        # 전체 크롤링 시 headless 모드, 테스트 시 브라우저 표시
        is_headless = (limit is None or limit > 50)
        browser = p.chromium.launch(
            headless=is_headless,
            args=[
                '--disable-http2',
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        page = context.new_page()

        enhanced_count = 0
        total_to_process = limit if limit else len(resources)

        for idx, resource in enumerate(resources[:limit], 1):
            url = resource['url']
            print(f"[{idx}/{total_to_process}] {resource['title'][:60]}")
            print(f"   URL: {url}")

            info = extract_all_info(page, url)

            if info:
                if info.get('thumbnail_url'):
                    resource['thumbnail_url'] = info['thumbnail_url']
                    print(f"   ✅ Thumbnail: {info['thumbnail_url'][:60]}...")

                if info.get('tags'):
                    resource['tags'] = ', '.join(info['tags'])
                    print(f"   ✅ Tags: {resource['tags']}")

                if info.get('ages'):
                    resource['ages'] = info['ages']
                    print(f"   ✅ Ages: {info['ages']}")

                if info.get('submitted_by'):
                    resource['submitted_by'] = info['submitted_by']
                    print(f"   ✅ Submitted by: {info['submitted_by']}")

                if info.get('updated'):
                    resource['updated'] = info['updated']
                    print(f"   ✅ Updated: {info['updated']}")

                if info.get('available_languages'):
                    resource['available_languages'] = info['available_languages']
                    print(f"   ✅ Languages: {info['available_languages'][:50]}")

                enhanced_count += 1
            else:
                print(f"   ⚠️ 정보 추출 실패")

            print()
            time.sleep(1)  # 대기 시간 단축

        context.close()
        browser.close()

    # 저장
    with open('data/resources_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(resources, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 완료!")
    print(f"   처리: {limit}개")
    print(f"   성공: {enhanced_count}개")
    print(f"   저장: data/resources_enhanced.json")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    # 인자가 있으면 전체 크롤링, 없으면 10개만
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        print("🚀 전체 리소스 크롤링 시작 (1,123개)")
        print("⏱️ 예상 소요 시간: 약 1.5시간")
        print()
        enhance_resources(limit=None)
    else:
        enhance_resources(limit=10)
