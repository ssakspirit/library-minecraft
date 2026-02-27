"""
데이터 업데이트 스크립트
Minecraft Education 리소스 최신화
"""
import sys
import io
import subprocess
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def update_data():
    """데이터 업데이트 및 Git 푸시"""

    print("=" * 80)
    print("🔄 Minecraft Education 리소스 업데이트")
    print("=" * 80)

    print("\n1️⃣ 크롤링 스크립트 실행...")
    try:
        # HTML 파일이 있으면 parse_html.py 실행
        result = subprocess.run(
            ["python", "parse_html.py"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ 크롤링 완료")
        else:
            print(f"❌ 크롤링 실패: {result.stderr}")
            return

    except Exception as e:
        print(f"❌ 오류: {e}")
        return

    print("\n2️⃣ Git 변경사항 확인...")
    result = subprocess.run(
        ["git", "diff", "data/resources.json"],
        capture_output=True,
        text=True
    )

    if not result.stdout.strip():
        print("ℹ️  변경사항 없음 - 데이터가 이미 최신입니다.")
        return

    print("\n3️⃣ Git 커밋 및 푸시...")
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # Add
        subprocess.run(["git", "add", "data/resources.json"], check=True)

        # Commit
        commit_message = f"📊 데이터 업데이트: {today}\n\n🤖 Generated with Claude Code\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=True
        )

        # Push
        subprocess.run(["git", "push"], check=True)

        print("\n✅ 업데이트 완료!")
        print("🚀 Streamlit Cloud가 자동으로 재배포됩니다 (1-2분 소요)")

    except subprocess.CalledProcessError as e:
        print(f"❌ Git 작업 실패: {e}")


if __name__ == "__main__":
    update_data()
