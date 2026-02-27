# 🚀 Streamlit Cloud 배포 가이드

## 빠른 배포 (5분)

### 1️⃣ Streamlit Cloud 계정 생성

1. https://streamlit.io/cloud 접속
2. **"Sign up"** 또는 **"Get started"** 클릭
3. **GitHub 계정으로 로그인**
4. Streamlit에 GitHub 저장소 접근 권한 부여

### 2️⃣ 새 앱 배포

1. Streamlit Cloud 대시보드에서 **"New app"** 클릭
2. 다음 정보 입력:
   - **Repository:** `ssakspirit/library-minecraft`
   - **Branch:** `main`
   - **Main file path:** `dashboard.py`
   - **App URL:** 원하는 URL 선택 (예: `minecraft-edu-library`)

3. **"Deploy!"** 클릭

### 3️⃣ 배포 완료 대기

- 약 2-3분 소요
- 자동으로 `requirements.txt`의 패키지 설치
- 배포 로그 실시간 확인 가능

### 4️⃣ 앱 접속

배포 완료 후 생성되는 URL:
```
https://your-app-name.streamlit.app
```

---

## 📋 체크리스트

배포 전 확인사항:

- ✅ `requirements.txt` 파일 존재
- ✅ `dashboard.py` 파일 존재
- ✅ GitHub에 코드 푸시 완료
- ✅ `data/resources.json` 파일 포함

---

## ⚙️ 설정 파일

### `.streamlit/config.toml`

이미 설정되어 있습니다:
```toml
[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false
```

---

## 🔧 문제 해결

### 1. 앱이 시작되지 않음

**증상:** "Oh no. 😞" 오류

**해결:**
- Streamlit Cloud 로그 확인
- `requirements.txt`에 모든 패키지 포함 확인
- Python 버전 호환성 확인 (3.9-3.12)

### 2. 데이터가 로드되지 않음

**증상:** "파일을 찾을 수 없습니다" 오류

**해결:**
- `data/resources.json` 파일이 Git에 포함되어 있는지 확인
- `.gitignore`에서 제외되지 않았는지 확인

### 3. 메모리 부족

**증상:** "Memory limit exceeded"

**해결:**
- Streamlit Cloud 무료 플랜: 1GB RAM
- `@st.cache_data` 데코레이터 사용 (이미 적용됨)
- 필요시 유료 플랜으로 업그레이드

---

## 🎨 커스터마이징

### 테마 변경

`.streamlit/config.toml`에 추가:

```toml
[theme]
primaryColor = "#2E7D32"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### 시크릿 관리

민감한 정보(API 키 등)는 Streamlit Cloud의 **Secrets** 기능 사용:

1. 앱 설정 → **Secrets** 탭
2. TOML 형식으로 입력:
   ```toml
   api_key = "your-secret-key"
   ```
3. 코드에서 접근:
   ```python
   import streamlit as st
   api_key = st.secrets["api_key"]
   ```

---

## 📊 사용량 모니터링

Streamlit Cloud 대시보드에서 확인 가능:
- 👥 방문자 수
- 📈 리소스 사용량
- 🕒 앱 가동 시간
- 📝 배포 로그

---

## 🔄 업데이트 배포

**자동 배포:**
- GitHub에 푸시하면 자동으로 재배포됨
- `main` 브랜치 변경 감지

**수동 재시작:**
1. Streamlit Cloud 대시보드
2. 앱 선택
3. **"Reboot app"** 클릭

---

## 💡 최적화 팁

1. **캐싱 활용:**
   ```python
   @st.cache_data
   def load_data():
       # 데이터 로드
   ```

2. **느린 작업 최소화:**
   - 필요한 데이터만 로드
   - 페이지네이션 사용

3. **세션 상태 관리:**
   ```python
   if 'key' not in st.session_state:
       st.session_state.key = value
   ```

---

## 🌐 도메인 연결 (Pro 플랜)

커스텀 도메인 사용 가능:
1. Streamlit Pro 플랜 구독
2. 도메인 설정에서 CNAME 레코드 추가
3. 예: `dashboard.yourdomain.com`

---

## 📚 추가 자료

- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Streamlit Cloud 가이드](https://docs.streamlit.io/streamlit-community-cloud)
- [커뮤니티 포럼](https://discuss.streamlit.io/)

---

**배포 후 URL을 README.md에 추가하는 것을 잊지 마세요!** 🎉
