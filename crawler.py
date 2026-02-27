"""
Minecraft Education Resources Crawler using Playwright
"""
import asyncio
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from tqdm import tqdm
import config
from database import MinecraftEducationDB


class MinecraftEducationCrawler:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.db = MinecraftEducationDB()

    async def start(self):
        """크롤러 시작"""
        print("🚀 Starting Minecraft Education Crawler...")
        self.db.connect()
        self.db.initialize_schema()

    async def stop(self):
        """크롤러 종료"""
        if self.browser:
            await self.browser.close()
        self.db.close()
        print("✅ Crawler stopped.")

    async def crawl_all(self):
        """모든 리소스 크롤링"""
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=False)  # headless=True for production
            context = await self.browser.new_context(
                user_agent=config.USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )

            # 메인 리스트 페이지에서 리소스 수집
            all_resources = []

            print("\n📋 Crawling resource lists...")
            for category, url in config.RESOURCE_URLS.items():
                print(f"\n  Crawling {category}: {url}")
                resources = await self._crawl_list_page(context, url)
                all_resources.extend(resources)
                print(f"  ✅ Found {len(resources)} resources in {category}")
                await asyncio.sleep(config.REQUEST_DELAY)

            print(f"\n📊 Total resources found: {len(all_resources)}")

            # 각 리소스의 상세 페이지 크롤링
            print("\n📄 Crawling resource details...")
            for resource in tqdm(all_resources, desc="Processing resources"):
                try:
                    detailed_resource = await self._crawl_detail_page(context, resource)
                    self.db.insert_resource(detailed_resource)
                    await asyncio.sleep(config.REQUEST_DELAY)
                except Exception as e:
                    print(f"\n❌ Error crawling {resource.get('url')}: {e}")
                    continue

            await context.close()

        print("\n✨ Crawling completed!")

    async def _crawl_list_page(self, context, url: str) -> List[Dict]:
        """리스트 페이지에서 리소스 목록 추출"""
        page = await context.new_page()

        try:
            await page.goto(url, timeout=config.TIMEOUT, wait_until='networkidle')

            # Wait for content to load
            await page.wait_for_selector('body', timeout=config.TIMEOUT)

            # JavaScript에서 데이터 추출 시도
            resources = await page.evaluate("""
                () => {
                    // 페이지에 있는 데이터 배열 찾기
                    const scriptTags = document.querySelectorAll('script');
                    for (let script of scriptTags) {
                        const text = script.textContent;
                        if (text.includes('const D=') || text.includes('lessons')) {
                            // 데이터 배열 파싱 시도
                            const match = text.match(/const D=(\[.*?\]);/s);
                            if (match) {
                                try {
                                    return JSON.parse(match[1]);
                                } catch (e) {
                                    console.error('Parse error:', e);
                                }
                            }
                        }
                    }

                    // 대안: DOM에서 카드 요소 추출
                    const cards = [];
                    const cardElements = document.querySelectorAll('[data-resource], .resource-card, .card');

                    cardElements.forEach(card => {
                        const title = card.querySelector('h2, h3, .title')?.textContent?.trim();
                        const link = card.querySelector('a')?.href;
                        const description = card.querySelector('p, .description')?.textContent?.trim();
                        const type = card.dataset.type || 'Unknown';

                        if (title && link) {
                            cards.push({
                                t: title,
                                u: link,
                                d: description || '',
                                ty: type,
                                s: []
                            });
                        }
                    });

                    return cards.length > 0 ? cards : null;
                }
            """)

            if resources:
                # 데이터 형식 변환
                formatted_resources = []
                for r in resources:
                    formatted_resources.append({
                        'title': r.get('t', ''),
                        'url': r.get('u', ''),
                        'short_description': r.get('d', ''),
                        'type': r.get('ty', 'Unknown'),
                        'subjects': r.get('s', [])
                    })
                return formatted_resources

            return []

        except Exception as e:
            print(f"❌ Error in _crawl_list_page: {e}")
            return []
        finally:
            await page.close()

    async def _crawl_detail_page(self, context, resource: Dict) -> Dict:
        """상세 페이지에서 전체 콘텐츠 추출"""
        page = await context.new_page()

        try:
            await page.goto(resource['url'], timeout=config.TIMEOUT, wait_until='domcontentloaded')

            # 페이지 콘텐츠 추출
            details = await page.evaluate("""
                () => {
                    const getTextContent = (selector) => {
                        const el = document.querySelector(selector);
                        return el ? el.textContent.trim() : '';
                    };

                    const getArrayContent = (selector) => {
                        return Array.from(document.querySelectorAll(selector))
                            .map(el => el.textContent.trim())
                            .filter(text => text.length > 0);
                    };

                    return {
                        full_description: getTextContent('.description, .overview, [class*="description"]'),
                        objectives: getArrayContent('.objective, .learning-objective, [class*="objective"] li'),
                        materials: getArrayContent('.material, .required-material, [class*="material"] li'),
                        instructions: getTextContent('.instructions, .steps, [class*="instruction"]'),
                        duration: getTextContent('.duration, [class*="duration"]'),
                        difficulty: getTextContent('.difficulty, [class*="difficulty"]'),
                        grade_levels: getArrayContent('.grade, [class*="grade"]'),
                        tags: getArrayContent('.tag, [class*="tag"]'),
                        full_content: document.body.innerText
                    };
                }
            """)

            # 리소스 데이터와 상세 정보 병합
            resource['description'] = details.get('full_description') or resource.get('short_description', '')
            resource['details'] = {
                'objectives': details.get('objectives', []),
                'materials': details.get('materials', []),
                'instructions': details.get('instructions', ''),
                'assessment': '',
                'duration_minutes': self._parse_duration(details.get('duration', '')),
                'difficulty': self._parse_difficulty(details.get('difficulty', '')),
                'full_content': details.get('full_content', '')
            }

            # 추가 메타데이터
            if details.get('tags'):
                resource['tags'] = details['tags']
            if details.get('grade_levels'):
                resource['grade_levels'] = details['grade_levels']

            return resource

        except Exception as e:
            print(f"❌ Error crawling detail page {resource['url']}: {e}")
            # 실패해도 기본 정보는 반환
            return resource
        finally:
            await page.close()

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """시간 문자열을 분 단위로 변환"""
        if not duration_str:
            return None

        # "30 minutes", "1 hour", "1-2 hours" 등 파싱
        match = re.search(r'(\d+)', duration_str)
        if match:
            num = int(match.group(1))
            if 'hour' in duration_str.lower():
                return num * 60
            return num
        return None

    def _parse_difficulty(self, difficulty_str: str) -> Optional[str]:
        """난이도 문자열 정규화"""
        if not difficulty_str:
            return None

        difficulty_str = difficulty_str.lower()
        if 'beginner' in difficulty_str or '초급' in difficulty_str:
            return 'beginner'
        elif 'intermediate' in difficulty_str or '중급' in difficulty_str:
            return 'intermediate'
        elif 'advanced' in difficulty_str or '고급' in difficulty_str:
            return 'advanced'
        return None


async def main():
    crawler = MinecraftEducationCrawler()

    try:
        await crawler.start()
        await crawler.crawl_all()

        # 통계 출력
        print("\n📊 Crawling Statistics:")
        stats = crawler.db.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))

        # JSON 내보내기
        output_path = config.DATA_DIR / "resources.json"
        crawler.db.export_to_json(output_path)

    finally:
        await crawler.stop()


if __name__ == "__main__":
    asyncio.run(main())
