"""
빠른 크롤러 - requests + BeautifulSoup 사용 (Playwright 없이)
썸네일과 태그는 HTML meta 태그에 있어서 JavaScript 렌더링 불필요
"""
import json
import time
import sys
import io
import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 배치 크기 설정
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '5'))  # 동시 크롤링 개수


def crawl_resource(url, retries=3):
    """단일 리소스 크롤링 - requests 사용"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            data = {}

            # 썸네일 - meta 태그에서 추출
            og_image = soup.find('meta', property='og:image')
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})

            meta_image = None
            if og_image and og_image.get('content'):
                meta_image = og_image['content']
            elif twitter_image and twitter_image.get('content'):
                meta_image = twitter_image['content']

            if meta_image:
                # 상대 경로면 절대 경로로 변환
                if meta_image.startswith('/'):
                    data['thumbnail_url'] = 'https://education.minecraft.net' + meta_image
                elif meta_image.startswith('http'):
                    data['thumbnail_url'] = meta_image
                else:
                    data['thumbnail_url'] = 'https://education.minecraft.net/' + meta_image

            # 태그 - h1 다음 ul의 li들
            h1 = soup.find('h1')
            if h1:
                parent = h1.find_parent()
                if parent:
                    ul = parent.find('ul')
                    if ul:
                        tags = []
                        for li in ul.find_all('li'):
                            tag_text = li.get_text(strip=True)
                            if tag_text and len(tag_text) < 20:
                                tags.append(tag_text)
                        if tags:
                            data['tags'] = tags

            # Submitted by
            body_text = soup.get_text()
            import re
            submitted_match = re.search(r'Submitted by[:\s]*([^\n]+)', body_text, re.IGNORECASE)
            if submitted_match:
                data['submitted_by'] = submitted_match.group(1).strip()

            # Updated
            updated_match = re.search(r'Updated[:\s]*([^\n]+)', body_text, re.IGNORECASE)
            if updated_match:
                data['updated'] = updated_match.group(1).strip()

            return {'success': True, 'data': data, 'url': url}

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                wait_time = 5 * (attempt + 1)
                time.sleep(wait_time)
                continue
            else:
                return {'success': False, 'error': str(e)[:100], 'url': url}

    return {'success': False, 'error': 'Max retries exceeded', 'url': url}


def crawl_batch(resources_to_crawl, max_workers=5):
    """배치 크롤링 - 멀티스레딩 사용"""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 작업 제출
        future_to_resource = {
            executor.submit(crawl_resource, resource['url']): resource
            for resource in resources_to_crawl
        }

        # 결과 수집
        for future in as_completed(future_to_resource):
            resource = future_to_resource[future]
            try:
                result = future.result()
                result['resource'] = resource
                results.append(result)

                # 진행 상황 출력
                if result['success']:
                    print(f"✅ {resource['title'][:50]}")
                    if result['data'].get('thumbnail_url'):
                        print(f"   Thumbnail: {result['data']['thumbnail_url'][:60]}")
                else:
                    print(f"❌ {resource['title'][:50]} - {result.get('error', 'Unknown error')}")

            except Exception as e:
                print(f"❌ {resource['title'][:50]} - Exception: {str(e)[:100]}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'url': resource['url'],
                    'resource': resource
                })

    return results


def main():
    print("=" * 70)
    print("🚀 Fast Crawler - requests + BeautifulSoup")
    print("=" * 70)
    print()

    # 데이터 로드 - resources_complete.json 우선, 없으면 resources_enhanced.json
    output_file = 'data/resources_complete.json'
    if os.path.exists(output_file):
        print(f"📂 Loading from {output_file}")
        with open(output_file, 'r', encoding='utf-8') as f:
            resources = json.load(f)
    else:
        print(f"📂 Loading from data/resources_enhanced.json")
        with open('data/resources_enhanced.json', 'r', encoding='utf-8') as f:
            resources = json.load(f)

    # 누락된 데이터 찾기
    missing = [(i, r) for i, r in enumerate(resources) if not r.get('thumbnail_url')]

    print(f"📊 Status:")
    print(f"   Total: {len(resources)}")
    print(f"   Complete: {len(resources) - len(missing)} ({(len(resources) - len(missing)) * 100 // len(resources)}%)")
    print(f"   Missing: {len(missing)}")
    print()

    if not missing:
        print("🎉 All resources complete!")
        return

    # 배치 설정
    batch = missing[:BATCH_SIZE]
    print(f"🕷️  Crawling batch: {len(batch)} resources")
    print(f"   Workers: {MAX_WORKERS} concurrent threads")
    print(f"   Remaining: {max(0, len(missing) - BATCH_SIZE)}")
    print()

    # 크롤링
    resources_to_crawl = [r for i, r in batch]
    start_time = time.time()

    results = crawl_batch(resources_to_crawl, max_workers=MAX_WORKERS)

    elapsed = time.time() - start_time
    print()
    print(f"⏱️  Crawling completed in {elapsed:.1f} seconds")
    print()

    # 결과 업데이트
    success_count = 0
    failed_count = 0

    for result in results:
        if result['success'] and result['data'].get('thumbnail_url'):
            resource_url = result['url']
            # resources에서 해당 URL 찾아서 업데이트
            for i, r in enumerate(resources):
                if r['url'] == resource_url:
                    resources[i]['thumbnail_url'] = result['data']['thumbnail_url']
                    if result['data'].get('tags'):
                        resources[i]['tags'] = ', '.join(result['data']['tags'])
                    if result['data'].get('submitted_by'):
                        resources[i]['submitted_by'] = result['data']['submitted_by']
                    if result['data'].get('updated'):
                        resources[i]['updated'] = result['data']['updated']
                    success_count += 1
                    break
        else:
            failed_count += 1

    # 새로운 파일로 저장
    output_file = 'data/resources_complete.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(resources, f, ensure_ascii=False, indent=2)

    # 결과 요약
    print("=" * 70)
    print("✨ Results")
    print("=" * 70)
    print(f"Success: {success_count}/{len(batch)} ({success_count * 100 // len(batch)}%)")
    print(f"Failed: {failed_count}/{len(batch)}")
    print(f"Speed: {len(batch) / elapsed:.1f} resources/second")
    print(f"Total progress: {len(resources) - len(missing) + success_count}/{len(resources)} ({((len(resources) - len(missing) + success_count) * 100) // len(resources)}%)")
    print()
    print(f"💾 Saved to: {output_file}")
    print()

    # Playwright와 비교
    playwright_time = len(batch) * 10  # Playwright는 리소스당 약 10초
    print(f"💡 Time saved vs Playwright: {playwright_time - elapsed:.0f} seconds (~{(playwright_time - elapsed) / 60:.1f} minutes)")
    print()


if __name__ == "__main__":
    main()
