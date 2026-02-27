"""
Database operations for Minecraft Education resources
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import config


class MinecraftEducationDB:
    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """데이터베이스 연결"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        return self.connection

    def close(self):
        """데이터베이스 연결 종료"""
        if self.connection:
            self.connection.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def initialize_schema(self):
        """스키마 초기화"""
        if not config.DB_SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema file not found: {config.DB_SCHEMA_PATH}")

        with open(config.DB_SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        self.connection.executescript(schema_sql)
        self.connection.commit()
        print(f"✅ Database initialized at {self.db_path}")

    def insert_resource(self, resource: Dict[str, Any]) -> str:
        """리소스 삽입"""
        cursor = self.connection.cursor()

        # Generate ID from URL
        resource_id = self._generate_id(resource['url'])

        cursor.execute("""
            INSERT OR REPLACE INTO resources
            (id, title, type, description, short_description, url, thumbnail_url, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            resource_id,
            resource['title'],
            resource['type'],
            resource.get('description', ''),
            resource.get('short_description', ''),
            resource['url'],
            resource.get('thumbnail_url'),
            datetime.now().isoformat()
        ))

        # Insert subjects
        if 'subjects' in resource:
            self._insert_subjects(cursor, resource_id, resource['subjects'])

        # Insert tags
        if 'tags' in resource:
            self._insert_tags(cursor, resource_id, resource['tags'])

        # Insert details
        if 'details' in resource:
            self._insert_details(cursor, resource_id, resource['details'])

        self.connection.commit()
        return resource_id

    def _generate_id(self, url: str) -> str:
        """URL에서 고유 ID 생성"""
        # Extract the last part of URL as ID
        parts = url.rstrip('/').split('/')
        return parts[-1]

    def _insert_subjects(self, cursor, resource_id: str, subjects: List[str]):
        """과목 삽입"""
        for subject in subjects:
            # Insert subject if not exists
            cursor.execute(
                "INSERT OR IGNORE INTO subjects (name) VALUES (?)",
                (subject,)
            )

            # Get subject ID
            cursor.execute("SELECT id FROM subjects WHERE name = ?", (subject,))
            subject_id = cursor.fetchone()[0]

            # Link resource to subject
            cursor.execute(
                "INSERT OR IGNORE INTO resource_subjects (resource_id, subject_id) VALUES (?, ?)",
                (resource_id, subject_id)
            )

    def _insert_tags(self, cursor, resource_id: str, tags: List[str]):
        """태그 삽입"""
        for tag in tags:
            cursor.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                (tag,)
            )

            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
            tag_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT OR IGNORE INTO resource_tags (resource_id, tag_id) VALUES (?, ?)",
                (resource_id, tag_id)
            )

    def _insert_details(self, cursor, resource_id: str, details: Dict[str, Any]):
        """상세 정보 삽입"""
        cursor.execute("""
            INSERT OR REPLACE INTO resource_details
            (resource_id, objectives, materials, instructions, assessment,
             duration_minutes, difficulty, full_content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            resource_id,
            json.dumps(details.get('objectives', []), ensure_ascii=False),
            json.dumps(details.get('materials', []), ensure_ascii=False),
            details.get('instructions', ''),
            details.get('assessment', ''),
            details.get('duration_minutes'),
            details.get('difficulty'),
            details.get('full_content', '')
        ))

    def get_all_resources(self) -> List[Dict]:
        """모든 리소스 조회"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT r.*,
                   GROUP_CONCAT(DISTINCT s.name) as subjects
            FROM resources r
            LEFT JOIN resource_subjects rs ON r.id = rs.resource_id
            LEFT JOIN subjects s ON rs.subject_id = s.id
            WHERE r.is_active = 1
            GROUP BY r.id
            ORDER BY r.crawled_at DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def search_resources(self, query: str) -> List[Dict]:
        """전체 텍스트 검색"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT r.*,
                   GROUP_CONCAT(DISTINCT s.name) as subjects
            FROM resources r
            JOIN resources_fts fts ON r.rowid = fts.rowid
            LEFT JOIN resource_subjects rs ON r.id = rs.resource_id
            LEFT JOIN subjects s ON rs.subject_id = s.id
            WHERE resources_fts MATCH ?
            GROUP BY r.id
            ORDER BY rank
        """, (query,))

        return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보"""
        cursor = self.connection.cursor()

        stats = {}

        # Total resources
        cursor.execute("SELECT COUNT(*) FROM resources WHERE is_active = 1")
        stats['total_resources'] = cursor.fetchone()[0]

        # By type
        cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM resources
            WHERE is_active = 1
            GROUP BY type
        """)
        stats['by_type'] = {row['type']: row['count'] for row in cursor.fetchall()}

        # By subject
        cursor.execute("""
            SELECT s.name, COUNT(*) as count
            FROM subjects s
            JOIN resource_subjects rs ON s.id = rs.subject_id
            JOIN resources r ON rs.resource_id = r.id
            WHERE r.is_active = 1
            GROUP BY s.name
            ORDER BY count DESC
        """)
        stats['by_subject'] = {row['name']: row['count'] for row in cursor.fetchall()}

        return stats

    def export_to_json(self, output_path: Path):
        """JSON으로 내보내기"""
        resources = self.get_all_resources()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(resources, f, ensure_ascii=False, indent=2)

        print(f"✅ Exported {len(resources)} resources to {output_path}")


if __name__ == "__main__":
    # Test database initialization
    with MinecraftEducationDB() as db:
        db.initialize_schema()
        print("\n📊 Database Statistics:")
        print(json.dumps(db.get_statistics(), indent=2, ensure_ascii=False))
