"""
통합 크롤러 - 모든 리소스 데이터를 한 번에 수집
usage:
    python crawl.py              # 누락된 데이터만 크롤링 (기본)
    python crawl.py --full       # 전체 새로 크롤링
    python crawl.py --retry      # 실패한 리소스만 재시도
    python crawl.py --batch 100  # 배치 크기 조정
    python crawl.py --help       # 도움말
"""
import json
import time
import sys
import io
import os
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 경로 설정
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ENHANCED_PATH = DATA_DIR / "resources_enhanced.json"
BACKUP_PATH = DATA_DIR / "resources_enhanced.backup.json"
FAILED_PATH = DATA_DIR / "crawl_failed.json"
LOG_PATH = BASE_DIR / "crawl.log"

# 크롤링 대상 URL (en-us)
BASE_URL = "https://education.minecraft.net"
RESOURCE_LIST_URL = f"{BASE_URL}/en-us/resources"


# ─── JavaScript 추출 코드 (12개 필드 모두 수집) ───────────────────────────
EXTRACT_JS = """() => {
    const result = {};

    // 1. thumbnail_url - og:image 메타태그
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

    // 2. tags - category-box-list (주로 World 페이지)
    const tagUl = document.querySelector('ul.category-box-list');
    if (tagUl) {
        const items = Array.from(tagUl.querySelectorAll('li.item'));
        const tags = items.map(li => li.textContent.trim()).filter(t => t);
        result.tags = tags;
    } else {
        result.tags = [];
    }

    // 3. subjects - 과목
    const subjectLinks = document.querySelectorAll('a[href*="subjects="]');
    result.subjects_list = Array.from(subjectLinks).map(a => a.textContent.trim()).filter(t => t);

    // 4. ages - 대상 연령
    const ageLinks = document.querySelectorAll('a[href*="ages="]');
    result.ages = Array.from(ageLinks).map(a => a.textContent.trim()).filter(t => t);

    // 5. skills - 역량
    const allHeadings = document.querySelectorAll('h2, h3');
    for (const h of allHeadings) {
        if (h.textContent.trim().toLowerCase() === 'skills') {
            const container = h.closest('div') || h.parentElement;
            if (container) {
                const ul = container.querySelector('ul');
                if (ul) {
                    result.skills = Array.from(ul.querySelectorAll('li'))
                        .map(li => li.textContent.trim()).filter(t => t);
                }
            }
            break;
        }
    }
    if (!result.skills) result.skills = [];

    // 6. estimated_time - 예상 소요 시간
    for (const h of allHeadings) {
        const text = h.textContent.trim().toLowerCase();
        if (text.includes('estimated time') || text.includes('time to complete')) {
            const next = h.nextElementSibling;
            if (next) {
                result.estimated_time = next.textContent.trim();
            } else {
                const container = h.closest('div') || h.parentElement;
                const p = container?.querySelector('p');
                if (p) result.estimated_time = p.textContent.trim();
            }
            break;
        }
    }

    // 7. languages - 사용 가능 언어
    const langLinks = document.querySelectorAll('a[href*="languages="]');
    result.languages = Array.from(langLinks).map(a => a.textContent.trim()).filter(t => t);

    // 8. submitted_by - 제출자
    const bodyText = document.body.innerText;
    const submittedMatch = bodyText.match(/Submitted by[:\\s]*([^\\n]+)/i);
    if (submittedMatch) result.submitted_by = submittedMatch[1].trim();

    // 9. updated - 업데이트 날짜
    const updatedMatch = bodyText.match(/Updated[:\\s]*([^\\n]+)/i);
    if (updatedMatch) result.updated = updatedMatch[1].trim();

    // 10. full_description - 전체 설명
    const ogDesc = document.querySelector('meta[property="og:description"]');
    if (ogDesc) result.full_description = ogDesc.content;

    // 11. download_url - .mcworld/.zip 다운로드 링크
    const allLinks = document.querySelectorAll('a[href]');
    for (const a of allLinks) {
        const href = a.href || '';
        if (href.includes('.mcworld') || href.includes('.zip') || href.includes('/world/')) {
            // "Open in Minecraft" 또는 다운로드 링크
            const text = a.textContent.trim().toLowerCase();
            if (text.includes('open in minecraft') || text.includes('download') 
                || href.includes('.mcworld') || href.includes('.zip')) {
                result.download_url = href;
                break;
            }
        }
    }

    // 12. supporting_files - 교안 PDF, PPT 등
    const fileLinks = document.querySelectorAll(
        'a[href*="lessonsupportfiles"], a[href*="LessonZipFiles"]'
    );
    result.supporting_files = Array.from(fileLinks).map(a => ({
        name: a.textContent.trim(),
        url: a.href
    })).filter(f => f.name && f.url);

    return result;
}"""


def log(msg):
    """콘솔 + 파일 로그"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass


def load_resources():
    """리소스 JSON 로드 (빈 파일/없는 파일 방어)"""
    if not ENHANCED_PATH.exists():
        log(f"⚠️  {ENHANCED_PATH} 파일이 없습니다.")
        return None

    try:
        content = ENHANCED_PATH.read_text(encoding='utf-8').strip()
        if not content:
            log(f"⚠️  {ENHANCED_PATH} 파일이 비어있습니다.")
            return None
        resources = json.loads(content)
        if not isinstance(resources, list):
            log(f"⚠️  {ENHANCED_PATH}가 배열이 아닙니다.")
            return None
        return resources
    except json.JSONDecodeError as e:
        log(f"❌ JSON 파싱 에러: {e}")
        return None


def save_resources(resources):
    """안전한 저장 (백업 후 저장)"""
    # 백업
    if ENHANCED_PATH.exists():
        try:
            shutil.copy2(ENHANCED_PATH, BACKUP_PATH)
        except:
            pass

    with open(ENHANCED_PATH, 'w', encoding='utf-8') as f:
        json.dump(resources, f, ensure_ascii=False, indent=2)


def save_failed(failed_list):
    """실패 리소스 저장"""
    with open(FAILED_PATH, 'w', encoding='utf-8') as f:
        json.dump(failed_list, f, ensure_ascii=False, indent=2)


def find_missing(resources, mode='default'):
    """크롤링이 필요한 리소스 인덱스 찾기"""
    missing = []
    for i, r in enumerate(resources):
        if mode == 'full':
            # 전체 재크롤링
            missing.append(i)
        elif mode == 'retry':
            # 실패한 리소스만
            if r.get('_crawl_failed'):
                missing.append(i)
        else:
            # 기본: thumbnail_url이 없거나 tags가 한번도 수집 안 된 리소스
            needs_crawl = (
                not r.get('thumbnail_url')
                or r.get('_crawl_status') is None  # 한번도 크롤링 안 됨
            )
            if needs_crawl:
                missing.append(i)
    return missing


def extract_data(page, url, retries=3):
    """페이지에서 12개 필드 추출"""
    for attempt in range(retries):
        try:
            page.goto(url, timeout=30000, wait_until='domcontentloaded')
            time.sleep(2)  # JS 렌더링 대기
            break
        except Exception as e:
            if attempt < retries - 1:
                wait_time = 5 * (attempt + 1)  # 5초, 10초 점진적 대기
                log(f"     ⟳ 재시도 ({attempt + 1}/{retries})... {wait_time}초 대기")
                time.sleep(wait_time)
                continue
            else:
                return None, str(e)[:120]

    try:
        data = page.evaluate(EXTRACT_JS)
        return data, None
    except Exception as e:
        return None, str(e)[:120]


def apply_data(resource, data):
    """추출된 데이터를 리소스에 적용"""
    fields_updated = []

    # 1. thumbnail_url
    if data.get('thumbnail_url'):
        resource['thumbnail_url'] = data['thumbnail_url']
        fields_updated.append('thumbnail')

    # 2. tags (배열 → 쉼표 문자열)
    resource['tags'] = ', '.join(data.get('tags', [])) if data.get('tags') else ''
    fields_updated.append('tags')

    # 3. subjects (크롤링 결과로 업데이트, 기존값 유지 가능)
    if data.get('subjects_list'):
        resource['subjects'] = ', '.join(data['subjects_list'])
        fields_updated.append('subjects')

    # 4. ages
    resource['ages'] = ', '.join(data.get('ages', [])) if data.get('ages') else ''
    if data.get('ages'):
        fields_updated.append('ages')

    # 5. skills
    resource['skills'] = ', '.join(data.get('skills', [])) if data.get('skills') else ''
    if data.get('skills'):
        fields_updated.append('skills')

    # 6. estimated_time
    if data.get('estimated_time'):
        resource['estimated_time'] = data['estimated_time']
        fields_updated.append('time')

    # 7. languages
    resource['languages'] = ', '.join(data.get('languages', [])) if data.get('languages') else ''
    if data.get('languages'):
        fields_updated.append('languages')

    # 8. submitted_by
    if data.get('submitted_by'):
        resource['submitted_by'] = data['submitted_by']
        fields_updated.append('submitted')

    # 9. updated
    if data.get('updated'):
        resource['updated'] = data['updated']
        fields_updated.append('updated')

    # 10. full_description
    if data.get('full_description'):
        resource['full_description'] = data['full_description']
        fields_updated.append('desc')

    # 11. download_url
    if data.get('download_url'):
        resource['download_url'] = data['download_url']
        fields_updated.append('download')

    # 12. supporting_files
    if data.get('supporting_files'):
        resource['supporting_files'] = data['supporting_files']
        fields_updated.append('files')

    # 크롤링 상태 표시
    resource['_crawl_status'] = 'done'
    resource['_crawl_at'] = datetime.now().isoformat()
    resource.pop('_crawl_failed', None)

    return fields_updated


def format_eta(remaining, avg_time):
    """남은 시간 포맷팅"""
    if avg_time <= 0:
        return "계산 중..."
    total_sec = remaining * avg_time
    if total_sec < 60:
        return f"{total_sec:.0f}초"
    elif total_sec < 3600:
        return f"{total_sec / 60:.0f}분"
    else:
        hours = int(total_sec // 3600)
        mins = int((total_sec % 3600) // 60)
        return f"{hours}시간 {mins}분"


def progress_bar(current, total, width=30):
    """프로그레스 바"""
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = '━' * filled + '░' * (width - filled)
    return f"{bar} {pct * 100:.1f}%"


def crawl(resources, indices, batch_size=0, delay=3.0, rest_interval=20, rest_duration=30, headless=False):
    """메인 크롤링 루프

    Args:
        resources: 전체 리소스 리스트
        indices: 크롤링할 인덱스 리스트
        batch_size: 0이면 전체, 양수면 해당 개수만
        delay: 요청 간 딜레이 (초)
        rest_interval: N개마다 휴식
        rest_duration: 휴식 시간 (초)
        headless: headless 모드 (CI용)
    """
    if batch_size > 0:
        targets = indices[:batch_size]
    else:
        targets = indices

    total = len(targets)
    if total == 0:
        log("🎉 크롤링할 리소스가 없습니다. 모두 완료!")
        return

    log(f"🕷️  크롤링 시작: {total}개 리소스")
    log(f"   딜레이: {delay}초, {rest_interval}개마다 {rest_duration}초 휴식")
    log("")

    success_count = 0
    failed_count = 0
    failed_list = []
    start_time = time.time()

    try:
        from playwright.sync_api import sync_playwright

        def create_context(browser):
            """새 브라우저 컨텍스트 생성"""
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            return ctx, ctx.new_page()

        with sync_playwright() as p:
            # CI 환경 자동 감지
            is_headless = headless or os.getenv('CI') == 'true'
            browser_args = ['--disable-http2']
            if is_headless:
                browser_args.append('--no-sandbox')
            
            log(f"🌐 브라우저 모드: {'headless' if is_headless else 'headed'}")
            browser = p.chromium.launch(
                headless=is_headless,
                args=browser_args
            )
            context, page = create_context(browser)
            consecutive_failures = 0

            for seq, idx in enumerate(targets, 1):
                resource = resources[idx]
                url = resource['url']
                # en-us URL 확인 (ko-kr → en-us 변환)
                if '/ko-kr/' in url:
                    url = url.replace('/ko-kr/', '/en-us/')
                elif '/en-us/' not in url:
                    # education.minecraft.net/worlds/xxx → /en-us/worlds/xxx
                    url = url.replace('education.minecraft.net/', 'education.minecraft.net/en-us/')

                title = resource.get('title', 'Unknown')[:45]
                elapsed = time.time() - start_time
                avg_time = elapsed / seq if seq > 1 else delay + 2
                eta = format_eta(total - seq, avg_time)

                log(f"[{seq}/{total}] {progress_bar(seq, total)} ETA: {eta}")
                log(f"  📄 {title}")

                # 50개마다 컨텍스트 재생성 (연결 갱신)
                if seq > 1 and seq % 50 == 0:
                    log(f"  🔄 브라우저 컨텍스트 갱신...")
                    try:
                        context.close()
                    except:
                        pass
                    context, page = create_context(browser)
                    time.sleep(3)

                # 크롤링
                data, error = extract_data(page, url)

                if data:
                    fields = apply_data(resource, data)
                    log(f"  ✅ {', '.join(fields)}")
                    success_count += 1
                    consecutive_failures = 0
                else:
                    log(f"  ❌ {error}")
                    resource['_crawl_failed'] = True
                    resource['_crawl_error'] = error
                    failed_count += 1
                    failed_list.append({
                        'index': idx,
                        'url': url,
                        'title': title,
                        'error': error
                    })
                    consecutive_failures += 1

                    # 5회 연속 실패 시 컨텍스트 재생성 + 장시간 대기
                    if consecutive_failures >= 5:
                        log(f"  ⚠️ {consecutive_failures}회 연속 실패 - 60초 대기 후 컨텍스트 재생성")
                        time.sleep(60)
                        try:
                            context.close()
                        except:
                            pass
                        context, page = create_context(browser)
                        consecutive_failures = 0
                        time.sleep(5)

                # 자동 저장 (10개마다)
                if seq % 10 == 0:
                    save_resources(resources)
                    log(f"  💾 자동 저장 완료 ({seq}/{total})")

                # 휴식 (rest_interval마다)
                if seq % rest_interval == 0 and seq < total:
                    log(f"  ☕ {rest_duration}초 휴식...")
                    time.sleep(rest_duration)
                else:
                    time.sleep(delay)

            browser.close()

    except KeyboardInterrupt:
        log("")
        log("⚠️  Ctrl+C 감지 - 현재까지의 결과를 저장합니다...")
    except Exception as e:
        log(f"❌ 예상치 못한 에러: {e}")
    finally:
        # 항상 저장
        save_resources(resources)
        if failed_list:
            save_failed(failed_list)

        elapsed = time.time() - start_time
        processed = success_count + failed_count

        log("")
        log("=" * 60)
        log("📊 크롤링 결과")
        log("=" * 60)
        log(f"  성공: {success_count}")
        log(f"  실패: {failed_count}")
        log(f"  소요 시간: {elapsed:.1f}초 ({elapsed / 60:.1f}분)")
        if processed > 0:
            log(f"  속도: {processed / elapsed:.2f} 리소스/초")
        log(f"  전체 진행률: {len(resources) - len(indices) + success_count}/{len(resources)}")
        log(f"  💾 저장: {ENHANCED_PATH}")
        if failed_list:
            log(f"  ❌ 실패 목록: {FAILED_PATH}")
        log("")


def main():
    parser = argparse.ArgumentParser(
        description="🕷️ Minecraft Education 통합 크롤러",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python crawl.py              누락된 데이터만 크롤링
  python crawl.py --full       전체 리소스 재크롤링
  python crawl.py --retry      실패한 리소스만 재시도
  python crawl.py --batch 50   50개만 크롤링
  python crawl.py --delay 5    5초 간격으로 크롤링
        """
    )
    parser.add_argument('--full', action='store_true',
                        help='모든 리소스 재크롤링')
    parser.add_argument('--retry', action='store_true',
                        help='실패한 리소스만 재시도')
    parser.add_argument('--batch', type=int, default=0,
                        help='크롤링할 개수 (0=전체)')
    parser.add_argument('--delay', type=float, default=3.0,
                        help='요청 간 딜레이 초 (기본: 3)')
    parser.add_argument('--rest-interval', type=int, default=20,
                        help='N개마다 휴식 (기본: 20)')
    parser.add_argument('--rest-duration', type=int, default=30,
                        help='휴식 시간 초 (기본: 30)')
    parser.add_argument('--headless', action='store_true',
                        help='headless 모드 (CI/서버용)')

    args = parser.parse_args()

    print("=" * 60)
    print("🕷️  Minecraft Education 통합 크롤러")
    print("   12개 필드 수집: thumbnail, tags, subjects, ages,")
    print("   skills, estimated_time, languages, submitted_by,")
    print("   updated, full_description, download_url, supporting_files")
    print("=" * 60)
    print()

    # 데이터 로드
    resources = load_resources()
    if resources is None:
        log("❌ resources_enhanced.json을 불러올 수 없습니다.")
        log("   먼저 기본 리소스 데이터가 필요합니다.")
        log("   data/resources_enhanced.json에 리소스 목록 JSON을 넣어주세요.")
        sys.exit(1)

    log(f"📊 전체 리소스: {len(resources)}개")

    # 크롤링 대상 찾기
    mode = 'full' if args.full else ('retry' if args.retry else 'default')
    missing = find_missing(resources, mode)

    # 현재 상태 표시
    has_thumbnail = sum(1 for r in resources if r.get('thumbnail_url'))
    has_tags = sum(1 for r in resources if r.get('tags'))
    has_subjects = sum(1 for r in resources if r.get('subjects'))
    has_ages = sum(1 for r in resources if r.get('ages'))
    has_skills = sum(1 for r in resources if r.get('skills'))
    crawled = sum(1 for r in resources if r.get('_crawl_status') == 'done')

    log(f"   크롤링 완료: {crawled}개")
    log(f"   thumbnail: {has_thumbnail}개")
    log(f"   tags: {has_tags}개")
    log(f"   subjects: {has_subjects}개")
    log(f"   ages: {has_ages}개")
    log(f"   skills: {has_skills}개")
    log(f"")
    log(f"🔍 크롤링 대상 ({mode}): {len(missing)}개")
    log("")

    if not missing:
        log("🎉 크롤링할 리소스가 없습니다!")
        return

    # 크롤링 시작
    crawl(
        resources=resources,
        indices=missing,
        batch_size=args.batch,
        delay=args.delay,
        rest_interval=args.rest_interval,
        rest_duration=args.rest_duration,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
