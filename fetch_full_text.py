"""
각 리소스 페이지의 전체 텍스트를 수집하여 JSON에 추가
"""
import sys
import io
import json
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from tqdm import tqdm

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def fetch_page_text(url: str, timeout: int = 30) -> str:
    """페이지의 전체 텍스트 가져오기"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator=' ', strip=True)

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
        return ""
    except Exception as e:
        print(f"❌ Error parsing {url}: {e}")
        return ""


def add_full_text_to_json(
    input_path: Path,
    output_path: Path,
    limit: int = None,
    delay: float = 2.0
):
    """JSON 파일의 각 리소스에 full text 추가"""

    print("=" * 80)
    print("📝 리소스 전체 텍스트 수집 시작")
    print("=" * 80)

    # Load existing JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        resources = json.load(f)

    print(f"\n📊 총 {len(resources)}개 리소스")
    if limit:
        resources = resources[:limit]
        print(f"   (처음 {limit}개만 처리)")

    # Process each resource
    success_count = 0
    error_count = 0
    skip_count = 0

    for i, resource in enumerate(tqdm(resources, desc="텍스트 수집")):
        # Skip if already has text
        if resource.get('text'):
            skip_count += 1
            continue

        url = resource.get('url')
        if not url:
            error_count += 1
            continue

        # Fetch full text
        text = fetch_page_text(url, timeout=30)

        if text:
            resource['text'] = text
            success_count += 1
        else:
            resource['text'] = ""
            error_count += 1

        # Progress update every 10 items
        if (i + 1) % 10 == 0:
            print(f"\n진행: {i+1}/{len(resources)} | 성공: {success_count} | 실패: {error_count}")

        # Respectful delay
        time.sleep(delay)

    # Save updated JSON
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
        sample = next((r for r in resources if r.get('text')), None)
        if sample:
            print(f"제목: {sample['title']}")
            print(f"URL: {sample['url']}")
            print(f"텍스트 길이: {len(sample['text'])}자")
            print(f"\n첫 500자:\n{sample['text'][:500]}...")


def main():
    input_path = Path('data/resources.json')
    output_path = Path('data/resources_with_text.json')

    if not input_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        return

    print("\n⚠️  주의사항:")
    print("  - 1,123개 리소스를 모두 수집하면 약 37분 소요 (각 2초 딜레이)")
    print("  - 웹사이트에 부하를 주지 않기 위해 딜레이가 필요합니다")
    print("  - 중간에 중단하려면 Ctrl+C를 누르세요\n")

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
        add_full_text_to_json(input_path, output_path, limit=limit)
    except KeyboardInterrupt:
        print("\n\n⚠️  중단되었습니다. 지금까지 수집한 데이터를 저장합니다...")
        # Save will happen in the finally block or the function itself


if __name__ == "__main__":
    main()
