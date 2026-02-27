"""
Enhanced Crawler - 리소스 상세 정보 크롤링
Skills, Learning objectives, Performance expectations 등 수집
"""
import sys
import io
import asyncio
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page
from tqdm import tqdm
import config
from database import MinecraftEducationDB

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class EnhancedCrawler:
    def __init__(self):
        self.db = MinecraftEducationDB()

    async def crawl_resource_details(self, url: str) -> Dict:
        """개별 리소스의 상세 정보 크롤링"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=config.USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            try:
                print(f"🔍 Crawling: {url}")
                await page.goto(url, timeout=60000, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)  # Wait for dynamic content

                # Extract detailed information
                details = await page.evaluate("""
                    () => {
                        const getText = (selector) => {
                            const el = document.querySelector(selector);
                            return el ? el.textContent.trim() : '';
                        };

                        const getTexts = (selector) => {
                            return Array.from(document.querySelectorAll(selector))
                                .map(el => el.textContent.trim())
                                .filter(text => text.length > 0);
                        };

                        // Try multiple possible selectors for each field
                        const findSkills = () => {
                            // Try common patterns
                            let skills = getTexts('[class*="skill"] li, [data-test*="skill"] li');
                            if (!skills.length) skills = getTexts('.skills li, .skill-list li');
                            if (!skills.length) {
                                // Look for Skills heading and get next list
                                const heading = Array.from(document.querySelectorAll('h2, h3, h4, strong'))
                                    .find(el => el.textContent.toLowerCase().includes('skill'));
                                if (heading) {
                                    const list = heading.nextElementSibling?.querySelectorAll('li');
                                    if (list) skills = Array.from(list).map(li => li.textContent.trim());
                                }
                            }
                            return skills;
                        };

                        const findTime = () => {
                            let time = getText('[class*="time"], [class*="duration"], [data-test*="time"]');
                            if (!time) {
                                const heading = Array.from(document.querySelectorAll('h2, h3, h4, strong, label'))
                                    .find(el => el.textContent.toLowerCase().includes('time') ||
                                               el.textContent.toLowerCase().includes('duration'));
                                if (heading) {
                                    time = heading.nextElementSibling?.textContent.trim() ||
                                           heading.parentElement?.textContent.replace(heading.textContent, '').trim();
                                }
                            }
                            return time;
                        };

                        const findObjectives = () => {
                            let objectives = getTexts('[class*="objective"] li, [class*="learning-objective"] li');
                            if (!objectives.length) {
                                const heading = Array.from(document.querySelectorAll('h2, h3, h4'))
                                    .find(el => el.textContent.toLowerCase().includes('objective'));
                                if (heading) {
                                    const list = heading.nextElementSibling?.querySelectorAll('li');
                                    if (list) objectives = Array.from(list).map(li => li.textContent.trim());
                                }
                            }
                            return objectives;
                        };

                        const findOverview = () => {
                            let overview = getText('[class*="overview"], [class*="theme"]');
                            if (!overview) {
                                const heading = Array.from(document.querySelectorAll('h2, h3, h4'))
                                    .find(el => el.textContent.toLowerCase().includes('overview') ||
                                               el.textContent.toLowerCase().includes('theme'));
                                if (heading) {
                                    overview = heading.nextElementSibling?.textContent.trim() ||
                                              heading.parentElement?.querySelector('p')?.textContent.trim();
                                }
                            }
                            return overview;
                        };

                        const findActivities = () => {
                            let activities = getTexts('[class*="activity"] li, [class*="student-activity"] li');
                            if (!activities.length) {
                                const heading = Array.from(document.querySelectorAll('h2, h3, h4'))
                                    .find(el => el.textContent.toLowerCase().includes('activit'));
                                if (heading) {
                                    const list = heading.nextElementSibling?.querySelectorAll('li');
                                    if (list) activities = Array.from(list).map(li => li.textContent.trim());
                                }
                            }
                            return activities;
                        };

                        const findExpectations = () => {
                            let expectations = getTexts('[class*="expectation"] li, [class*="performance"] li');
                            if (!expectations.length) {
                                const heading = Array.from(document.querySelectorAll('h2, h3, h4'))
                                    .find(el => el.textContent.toLowerCase().includes('expectation') ||
                                               el.textContent.toLowerCase().includes('performance'));
                                if (heading) {
                                    const list = heading.nextElementSibling?.querySelectorAll('li');
                                    if (list) expectations = Array.from(list).map(li => li.textContent.trim());
                                }
                            }
                            return expectations;
                        };

                        // Get full description (first paragraph or meta description)
                        const fullDescription = getText('meta[name="description"]') ||
                                              getText('.description, .overview, article p:first-of-type') ||
                                              getText('main p:first-of-type');

                        return {
                            skills: findSkills(),
                            estimated_time: findTime(),
                            learning_objectives: findObjectives(),
                            theme_overview: findOverview(),
                            student_activities: findActivities(),
                            performance_expectations: findExpectations(),
                            full_description: fullDescription,
                            full_text: document.body.innerText.substring(0, 5000)  // First 5000 chars
                        };
                    }
                """)

                await browser.close()
                return details

            except Exception as e:
                print(f"❌ Error crawling {url}: {e}")
                await browser.close()
                return {}

    async def update_existing_resources(self, limit: int = None):
        """기존 리소스들의 상세 정보 업데이트"""
        self.db.connect()

        cursor = self.db.connection.cursor()
        query = "SELECT id, url, title FROM resources WHERE is_active = 1"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        resources = cursor.fetchall()

        print(f"\n📊 총 {len(resources)}개 리소스 업데이트 시작...")
        print("=" * 80)

        success_count = 0
        error_count = 0

        for resource in tqdm(resources, desc="Crawling resources"):
            resource_id, url, title = resource

            try:
                # Crawl details
                details = await self.crawl_resource_details(url)

                if not details:
                    error_count += 1
                    continue

                # Update database
                cursor.execute("""
                    UPDATE resources
                    SET description = COALESCE(NULLIF(?, ''), description)
                    WHERE id = ?
                """, (details.get('full_description', ''), resource_id))

                # Update or insert details
                cursor.execute("""
                    INSERT OR REPLACE INTO resource_details
                    (resource_id, objectives, materials, instructions, assessment,
                     duration_minutes, difficulty, full_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    resource_id,
                    json.dumps(details.get('learning_objectives', []), ensure_ascii=False),
                    json.dumps(details.get('student_activities', []), ensure_ascii=False),
                    details.get('theme_overview', ''),
                    json.dumps(details.get('performance_expectations', []), ensure_ascii=False),
                    self._parse_duration(details.get('estimated_time', '')),
                    None,  # difficulty
                    details.get('full_text', '')
                ))

                # Add skills as tags
                if details.get('skills'):
                    for skill in details['skills']:
                        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (skill,))
                        cursor.execute("SELECT id FROM tags WHERE name = ?", (skill,))
                        tag_id = cursor.fetchone()[0]
                        cursor.execute(
                            "INSERT OR IGNORE INTO resource_tags (resource_id, tag_id) VALUES (?, ?)",
                            (resource_id, tag_id)
                        )

                self.db.connection.commit()
                success_count += 1

                # Delay to be respectful
                await asyncio.sleep(2)

            except Exception as e:
                print(f"\n❌ Error updating {title}: {e}")
                error_count += 1
                continue

        print(f"\n✅ 완료: {success_count}개 성공, {error_count}개 실패")
        self.db.close()

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """시간 문자열을 분 단위로 변환"""
        if not duration_str:
            return None

        duration_str = duration_str.lower()
        match = re.search(r'(\d+)', duration_str)
        if match:
            num = int(match.group(1))
            if 'hour' in duration_str:
                return num * 60
            return num
        return None


async def main():
    print("=" * 80)
    print("🚀 Enhanced Crawler - 상세 정보 수집")
    print("=" * 80)

    # Test with one resource first
    print("\n1️⃣ 테스트: 샘플 리소스 1개 크롤링")
    print("-" * 80)

    crawler = EnhancedCrawler()
    test_url = "https://education.minecraft.net/en-us/lessons/cyber-fundamentals-3-cloud-champions"

    details = await crawler.crawl_resource_details(test_url)

    print("\n📄 크롤링 결과:")
    print(json.dumps(details, indent=2, ensure_ascii=False))

    # Ask user to continue
    print("\n" + "=" * 80)
    response = input("\n모든 리소스를 업데이트하시겠습니까? (y/n, 또는 숫자 입력): ").strip().lower()

    if response == 'y':
        await crawler.update_existing_resources()
    elif response.isdigit():
        limit = int(response)
        print(f"\n처음 {limit}개 리소스만 업데이트합니다...")
        await crawler.update_existing_resources(limit=limit)
    else:
        print("취소되었습니다.")


if __name__ == "__main__":
    asyncio.run(main())
