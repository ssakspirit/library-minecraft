"""
Playwright를 사용한 전체 텍스트 수집 (HTTP2 오류 우회)
"""
import sys
import io
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from tqdm import tqdm

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def fetch_page_text(page, url: str, max_retries: int = 3) -> str:
    """Playwright로 페이지 전체 텍스트 가져오기"""

    for attempt in range(max_retries):
        try:
            # Navigate with faster strategy
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)

            # Wait for content to load
            await page.wait_for_timeout(2000)

            # Extract all text from the page
            text = await page.evaluate("""
                () => {
                    // Remove unwanted elements
                    const unwanted = document.querySelectorAll('script, style, nav, footer, header, .cookie-banner, .advertisement');
                    unwanted.forEach(el => el.remove());

                    // Get main content if available
                    const main = document.querySelector('main, article, .content, .main-content');
                    const content = main || document.body;

                    return content.innerText.trim();
                }
            """)

            return text

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"\n⚠️  재시도 {attempt + 1}/{max_retries} for {url}")
                await asyncio.sleep(2)
            else:
                print(f"\n❌ 실패: {url} - {str(e)[:100]}")
                return ""

    return ""


async def add_text_to_resources(input_path: Path, output_path: Path, limit: int = None):
    """리소스에 전체 텍스트 추가"""

    print("=" * 80)
    print("🚀 Playwright 텍스트 수집 시작")
    print("=" * 80)

    # Load existing JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        resources = json.load(f)

    print(f"\n📊 총 {len(resources)}개 리소스")

    if limit:
        resources = resources[:limit]
        print(f"   (처음 {limit}개만 처리)")

    async with async_playwright() as p:
        # Launch browser with custom settings to avoid HTTP2 issues
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-http2',  # Disable HTTP2 to avoid protocol errors
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )

        page = await context.new_page()

        success_count = 0
        error_count = 0
        skip_count = 0

        for i, resource in enumerate(tqdm(resources, desc="텍스트 수집")):
            # Skip if already has text
            if resource.get('text') and len(resource['text']) > 100:
                skip_count += 1
                continue

            url = resource.get('url')
            if not url:
                error_count += 1
                continue

            # Fetch text
            text = await fetch_page_text(page, url)

            if text and len(text) > 100:  # Minimum 100 chars to be valid
                resource['text'] = text
                success_count += 1

                # Show progress every 5 items
                if (success_count) % 5 == 0:
                    print(f"\n✅ {success_count}개 수집 완료 | 텍스트 길이 예시: {len(text)}자")
            else:
                resource['text'] = ""
                error_count += 1

            # Small delay
            await asyncio.sleep(1)

            # Save progress every 10 items
            if (i + 1) % 10 == 0:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(resources, f, ensure_ascii=False, indent=2)
                print(f"\n💾 중간 저장 완료 ({i + 1}/{len(resources)})")

        await browser.close()

    # Final save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resources, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("✅ 완료!")
    print("=" * 80)
    print(f"성공: {success_count}개")
    print(f"실패: {error_count}개")
    print(f"건너뜀: {skip_count}개")
    print(f"\n💾 저장 위치: {output_path}")

    # Show sample
    if success_count > 0:
        print("\n📄 샘플 텍스트 (첫 번째 성공한 리소스):")
        print("-" * 80)
        sample = next((r for r in resources if r.get('text') and len(r['text']) > 100), None)
        if sample:
            print(f"제목: {sample['title']}")
            print(f"URL: {sample['url']}")
            print(f"텍스트 길이: {len(sample['text'])}자")
            print(f"\n첫 500자:\n{sample['text'][:500]}...")


async def main():
    input_path = Path('data/resources.json')
    output_path = Path('data/resources_with_text.json')

    if not input_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        return

    print("\n⚠️  주의사항:")
    print("  - Playwright를 사용하여 JavaScript 콘텐츠를 수집합니다")
    print("  - 1,123개 리소스를 모두 수집하면 약 20분 소요")
    print("  - 중간에 중단해도 진행 상황이 저장됩니다\n")

    # Get user input
    user_input = input("몇 개를 수집하시겠습니까? (숫자 입력, 전체는 'all'): ").strip().lower()

    if user_input == 'all':
        limit = None
        print(f"\n모든 리소스를 수집합니다...")
    elif user_input.isdigit():
        limit = int(user_input)
        print(f"\n처음 {limit}개 리소스를 수집합니다...")
    else:
        print("취소되었습니다.")
        return

    try:
        await add_text_to_resources(input_path, output_path, limit=limit)
    except KeyboardInterrupt:
        print("\n\n⚠️  중단되었습니다. 지금까지 수집한 데이터가 저장되었습니다.")


if __name__ == "__main__":
    asyncio.run(main())
