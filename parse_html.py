"""
Parse existing HTML file and import data to database
"""
import sys
import io
import re
import json
from pathlib import Path
from database import MinecraftEducationDB
import config

# Fix Windows console encoding issue
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def parse_html_file(html_path: Path):
    """HTML 파일에서 데이터 추출"""
    print(f"📖 Reading HTML file: {html_path}")

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # JavaScript 데이터 배열 추출
    pattern = r'const D=(\[.*?\]);'
    match = re.search(pattern, html_content, re.DOTALL)

    if not match:
        print("❌ Could not find data array in HTML")
        return []

    try:
        data_str = match.group(1)
        resources = json.loads(data_str)
        print(f"✅ Found {len(resources)} resources")
        return resources
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return []


def transform_resource(raw_resource: dict) -> dict:
    """원본 데이터를 DB 스키마에 맞게 변환"""
    return {
        'title': raw_resource.get('t', ''),
        'type': raw_resource.get('ty', 'Unknown'),
        'description': raw_resource.get('d', ''),
        'short_description': raw_resource.get('d', ''),
        'url': raw_resource.get('u', ''),
        'subjects': raw_resource.get('s', []),
        'thumbnail_url': None,
        'tags': [],
        'details': {
            'objectives': [],
            'materials': [],
            'instructions': '',
            'assessment': '',
            'duration_minutes': None,
            'difficulty': None,
            'full_content': raw_resource.get('d', '')
        }
    }


def import_to_database(resources: list, db: MinecraftEducationDB):
    """데이터베이스에 리소스 임포트"""
    print(f"\n💾 Importing {len(resources)} resources to database...")

    success_count = 0
    error_count = 0

    for raw_resource in resources:
        try:
            resource = transform_resource(raw_resource)
            db.insert_resource(resource)
            success_count += 1
        except Exception as e:
            print(f"❌ Error importing {raw_resource.get('t', 'Unknown')}: {e}")
            error_count += 1

    print(f"\n✅ Import completed: {success_count} successful, {error_count} errors")


def main():
    html_path = Path(r"c:\Users\ssaks\OneDrive - main\0nowcoding\library-minecraft\minecraft-education-dashboard.html")

    if not html_path.exists():
        print(f"❌ HTML file not found: {html_path}")
        return

    # HTML에서 데이터 추출
    resources = parse_html_file(html_path)

    if not resources:
        print("No resources found to import")
        return

    # 데이터베이스에 임포트
    with MinecraftEducationDB() as db:
        db.initialize_schema()
        import_to_database(resources, db)

        # 통계 출력
        print("\n📊 Database Statistics:")
        stats = db.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))

        # JSON으로 내보내기
        output_path = config.DATA_DIR / "resources.json"
        db.export_to_json(output_path)


if __name__ == "__main__":
    main()
