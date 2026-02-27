# Minecraft Education Resources Crawler

Minecraft Education 웹사이트의 모든 교육 리소스를 크롤링하여 데이터베이스화하고, 챗봇과 대시보드를 구축하기 위한 프로젝트입니다.

## 📋 목차

- [기능](#기능)
- [설치](#설치)
- [사용법](#사용법)
- [데이터 구조](#데이터-구조)
- [활용 방안](#활용-방안)

## ✨ 기능

- 🕷️ **자동 크롤링**: Playwright를 사용한 JavaScript 렌더링 지원
- 💾 **구조화된 데이터**: SQLite 데이터베이스에 체계적으로 저장
- 🔍 **전체 텍스트 검색**: FTS5를 활용한 빠른 검색
- 📊 **통계 분석**: 리소스 타입, 과목, 태그별 분석
- 📤 **데이터 내보내기**: JSON 형식으로 내보내기 지원

## 🚀 설치

### 1. Python 환경 설정

Python 3.9 이상이 필요합니다.

```bash
# 가상환경 생성 (선택사항)
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. Playwright 브라우저 설치

```bash
playwright install chromium
```

## 📖 사용법

### 방법 1: 기존 HTML 파일에서 데이터 추출 (빠름, 추천)

이미 가지고 있는 HTML 파일에서 데이터를 추출합니다:

```bash
python parse_html.py
```

결과:
- `data/minecraft_education.db` - SQLite 데이터베이스 생성
- `data/resources.json` - JSON 형식으로 내보내기

### 방법 2: 웹사이트 직접 크롤링 (느림, 상세 정보 수집)

웹사이트를 직접 크롤링하여 상세 정보까지 수집합니다:

```bash
python crawler.py
```

⚠️ 주의:
- 실행 시간이 오래 걸릴 수 있습니다 (리소스 수 × 2초)
- 네트워크 연결이 필요합니다
- 웹사이트 부하를 고려하여 적절한 딜레이를 설정했습니다

### 데이터베이스 직접 사용

```python
from database import MinecraftEducationDB

with MinecraftEducationDB() as db:
    # 모든 리소스 조회
    resources = db.get_all_resources()

    # 검색
    results = db.search_resources("coding")

    # 통계
    stats = db.get_statistics()
    print(stats)
```

## 📊 데이터 구조

### 주요 테이블

#### resources (리소스)
```sql
- id: 고유 ID
- title: 제목
- type: 타입 (World/Challenge/Lesson)
- description: 설명
- url: 원본 링크
- thumbnail_url: 썸네일
- crawled_at: 수집 시간
```

#### subjects (과목)
- Computer Science
- Science
- Mathematics
- Language Arts
- Arts & Design
- Social Studies
- SEL / Wellness
- Career / STEM

#### resource_details (상세 정보)
```sql
- objectives: 학습 목표 (JSON)
- materials: 필요 자료 (JSON)
- instructions: 수업 가이드
- difficulty: 난이도
- duration_minutes: 소요 시간
```

### 데이터 예시

```json
{
  "id": "archipelago-town",
  "title": "Archipelago Town",
  "type": "World",
  "description": "How did this village develop way out in the middle of the ocean...",
  "url": "https://education.minecraft.net/worlds/archipelago-town",
  "subjects": "Computer Science,Science,Social Studies,SEL / Wellness",
  "crawled_at": "2026-02-26T..."
}
```

## 🎯 활용 방안

### 1. 챗봇 구축

**추천 스택:**
- **LangChain + OpenAI**: 강력한 대화형 AI
- **RAG (Retrieval-Augmented Generation)**: 데이터베이스 검색 + LLM 생성

```python
# 예시: 간단한 챗봇 로직
from database import MinecraftEducationDB

def chatbot_search(query: str):
    with MinecraftEducationDB() as db:
        # FTS5 검색
        results = db.search_resources(query)

        # LLM에 컨텍스트로 제공
        context = "\n".join([
            f"- {r['title']}: {r['description']}"
            for r in results[:5]
        ])

        return context
```

**기능 제안:**
- "코딩을 배울 수 있는 레슨 추천해줘"
- "초등학생을 위한 과학 활동이 있어?"
- "30분 안에 할 수 있는 챌린지는?"

### 2. 대시보드 구축

**추천 스택:**
- **Streamlit**: 빠른 프로토타이핑
- **Plotly/Chart.js**: 인터랙티브 차트
- **React + Flask/FastAPI**: 프로덕션 레벨

**대시보드 기능:**
- 📊 리소스 통계 (타입별, 과목별)
- 🔍 고급 검색 및 필터링
- 📈 트렌드 분석
- 🏷️ 태그 클라우드
- 📥 CSV/JSON 다운로드

### 3. API 서버

FastAPI를 사용한 RESTful API:

```python
from fastapi import FastAPI
from database import MinecraftEducationDB

app = FastAPI()

@app.get("/api/resources")
def get_resources(
    type: str = None,
    subject: str = None,
    search: str = None
):
    with MinecraftEducationDB() as db:
        if search:
            return db.search_resources(search)
        return db.get_all_resources()

@app.get("/api/stats")
def get_stats():
    with MinecraftEducationDB() as db:
        return db.get_statistics()
```

### 4. 추천 시스템

콘텐츠 기반 추천 알고리즘:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def recommend_resources(resource_id: str, top_n: int = 5):
    """유사한 리소스 추천"""
    with MinecraftEducationDB() as db:
        resources = db.get_all_resources()

        # TF-IDF 벡터화
        descriptions = [r['description'] for r in resources]
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(descriptions)

        # 코사인 유사도 계산
        similarities = cosine_similarity(tfidf_matrix)

        # 추천
        # ... (유사도 기반 정렬 및 반환)
```

## 📁 프로젝트 구조

```
library-minecraft/
├── config.py              # 설정 파일
├── database.py            # 데이터베이스 작업
├── crawler.py             # 웹 크롤러
├── parse_html.py          # HTML 파서
├── schema.sql             # DB 스키마
├── requirements.txt       # Python 패키지
├── README.md              # 이 파일
├── data/                  # 데이터 디렉토리
│   ├── minecraft_education.db
│   └── resources.json
└── minecraft-education-dashboard.html  # 원본 HTML
```

## 🔧 다음 단계

### 즉시 가능한 작업:
1. ✅ 데이터 수집 완료
2. 📊 Streamlit 대시보드 구축
3. 🤖 OpenAI API를 사용한 챗봇 구현
4. 🌐 FastAPI 서버 구축

### 고급 기능:
- 🔄 정기적 크롤링 (cron/scheduler)
- 🎨 이미지/썸네일 다운로드
- 🌍 다국어 지원
- 📱 모바일 앱 연동
- 🔐 사용자 인증 및 즐겨찾기

## 💡 기술 스택 추천

### 챗봇
- **프레임워크**: LangChain, LlamaIndex
- **LLM**: OpenAI GPT-4, Anthropic Claude
- **벡터 DB**: Pinecone, Weaviate, ChromaDB
- **UI**: Streamlit, Gradio, React

### 대시보드
- **프론트엔드**: React, Vue.js, Streamlit
- **백엔드**: FastAPI, Flask
- **차트**: Plotly, Chart.js, D3.js
- **배포**: Vercel, Netlify, Heroku

## 📝 라이센스

이 프로젝트는 교육 목적으로 만들어졌습니다.

⚠️ **주의**: Minecraft Education 콘텐츠의 저작권은 Microsoft/Mojang에 있습니다. 상업적 사용 시 적절한 허가를 받으시기 바랍니다.

## 🤝 기여

버그 리포트나 기능 제안은 환영합니다!

---

Made with ❤️ for Minecraft Education Community
