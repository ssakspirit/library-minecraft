-- Minecraft Education Resources Database Schema

-- 리소스 메타데이터 테이블
CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('World', 'Challenge', 'Lesson')),
    description TEXT,
    short_description TEXT,
    url TEXT UNIQUE NOT NULL,
    thumbnail_url TEXT,
    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- 과목 테이블
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- 리소스-과목 연결 테이블 (다대다 관계)
CREATE TABLE IF NOT EXISTS resource_subjects (
    resource_id TEXT,
    subject_id INTEGER,
    PRIMARY KEY (resource_id, subject_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- 학년 수준 테이블
CREATE TABLE IF NOT EXISTS grade_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- 리소스-학년 연결 테이블
CREATE TABLE IF NOT EXISTS resource_grades (
    resource_id TEXT,
    grade_id INTEGER,
    PRIMARY KEY (resource_id, grade_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (grade_id) REFERENCES grade_levels(id) ON DELETE CASCADE
);

-- 스킬/역량 테이블
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category TEXT -- 예: 'coding', 'critical-thinking', 'collaboration'
);

-- 리소스-스킬 연결 테이블
CREATE TABLE IF NOT EXISTS resource_skills (
    resource_id TEXT,
    skill_id INTEGER,
    PRIMARY KEY (resource_id, skill_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- 태그 테이블
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- 리소스-태그 연결 테이블
CREATE TABLE IF NOT EXISTS resource_tags (
    resource_id TEXT,
    tag_id INTEGER,
    PRIMARY KEY (resource_id, tag_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 상세 콘텐츠 테이블
CREATE TABLE IF NOT EXISTS resource_details (
    resource_id TEXT PRIMARY KEY,
    objectives TEXT, -- JSON 배열
    materials TEXT, -- JSON 배열
    instructions TEXT,
    assessment TEXT,
    duration_minutes INTEGER,
    difficulty TEXT CHECK(difficulty IN ('beginner', 'intermediate', 'advanced')),
    full_content TEXT,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
);

-- 검색 최적화를 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type);
CREATE INDEX IF NOT EXISTS idx_resources_title ON resources(title);
CREATE INDEX IF NOT EXISTS idx_resources_crawled_at ON resources(crawled_at);
CREATE INDEX IF NOT EXISTS idx_resource_subjects_subject ON resource_subjects(subject_id);
CREATE INDEX IF NOT EXISTS idx_resource_tags_tag ON resource_tags(tag_id);

-- 전체 텍스트 검색을 위한 FTS5 테이블
CREATE VIRTUAL TABLE IF NOT EXISTS resources_fts USING fts5(
    title,
    description,
    full_content,
    content=resources
);

-- FTS 트리거 (자동 업데이트)
CREATE TRIGGER IF NOT EXISTS resources_ai AFTER INSERT ON resources BEGIN
    INSERT INTO resources_fts(rowid, title, description, full_content)
    VALUES (new.rowid, new.title, new.description,
            (SELECT full_content FROM resource_details WHERE resource_id = new.id));
END;

CREATE TRIGGER IF NOT EXISTS resources_ad AFTER DELETE ON resources BEGIN
    DELETE FROM resources_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS resources_au AFTER UPDATE ON resources BEGIN
    UPDATE resources_fts
    SET title = new.title,
        description = new.description,
        full_content = (SELECT full_content FROM resource_details WHERE resource_id = new.id)
    WHERE rowid = new.rowid;
END;
