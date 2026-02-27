# 🚀 배포 가이드

## Streamlit Community Cloud 배포 (추천)

### 1단계: 계정 생성
1. https://streamlit.io/cloud 방문
2. "Sign up" 클릭
3. GitHub 계정으로 로그인

### 2단계: 앱 배포
1. "New app" 클릭
2. Repository 선택: `ssakspirit/library-minecraft`
3. Branch: `main`
4. Main file path: `dashboard.py`
5. "Deploy!" 클릭

### 3단계: 대기
- 약 2-3분 후 자동 배포 완료
- URL 생성: `https://your-app-name.streamlit.app`

### 주의사항
- `requirements.txt` 파일이 있어야 함 ✅ (이미 있음)
- 무료 플랜: 1GB 메모리, 1 CPU
- 데이터베이스는 매번 새로 생성됨

---

## 대안: HTML 정적 대시보드 → Netlify

Netlify를 꼭 사용하고 싶다면 정적 HTML 대시보드를 만들어야 합니다.

### 필요한 작업:
1. Streamlit 대신 순수 HTML/JavaScript 대시보드 작성
2. Chart.js 또는 D3.js 사용
3. `resources.json` 파일을 정적으로 로드
4. 검색/필터링을 JavaScript로 구현

### 장단점:
- ✅ Netlify 무료 호스팅
- ✅ 빠른 로딩 속도
- ❌ Python 기능 사용 불가
- ❌ 실시간 데이터베이스 쿼리 불가
- ❌ 개발 시간 추가 필요

---

## 추천 방법

**1순위: Streamlit Community Cloud**
- 가장 빠르고 쉬움
- Python 코드 그대로 사용
- 무료

**2순위: Railway 또는 Render**
- Python 앱 호스팅
- 무료 플랜 제공
- 조금 더 복잡

**3순위: 정적 HTML → Netlify**
- 완전히 새로 만들어야 함
- 시간이 많이 걸림

어떤 방법을 선택하시겠습니까?
