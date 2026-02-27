# 📊 데이터 업데이트 가이드

Minecraft Education 웹사이트에 새로운 리소스가 추가되면 대시보드 데이터를 최신화하는 방법입니다.

---

## 🔄 업데이트 방법

### 방법 1: 수동 업데이트 (가장 간단)

#### 단계:

1. **크롤링 스크립트 실행**
   ```bash
   cd "C:\Users\ssaks\OneDrive - main\0nowcoding\library-minecraft"
   python parse_html.py
   ```

2. **결과 확인**
   ```bash
   python check_text.py
   ```

3. **Git 푸시**
   ```bash
   git add data/resources.json
   git commit -m "📊 데이터 업데이트: 새로운 리소스 추가"
   git push
   ```

4. **자동 재배포**
   - Streamlit Cloud가 자동으로 감지하고 재배포 (1-2분 소요)

---

### 방법 2: 원클릭 업데이트 스크립트 (편리함)

```bash
python update_data.py
```

**이 스크립트가 자동으로:**
1. ✅ 크롤링 실행
2. ✅ 변경사항 확인
3. ✅ Git 커밋 & 푸시
4. ✅ 완료 메시지 출력

---

### 방법 3: GitHub Actions 자동화 (🌟 최고!)

**이미 설정됨! `.github/workflows/update-data.yml`**

#### 자동 실행:
- 📅 **매주 일요일 00:00 (UTC)** 자동 크롤링
- 🔄 변경사항 있으면 자동 커밋 & 푸시
- 🚀 Streamlit Cloud 자동 재배포

#### 수동 실행:
1. GitHub 저장소 방문
2. **Actions** 탭 클릭
3. **Update Minecraft Resources** 선택
4. **Run workflow** 클릭

---

## 📋 현재 데이터 상태 확인

### 로컬에서:
```bash
python analyze_data.py
```

### 웹에서:
- 대시보드: https://libraryminecraft.streamlit.app
- 최하단에 마지막 업데이트 시간 표시

---

## ⚠️ 주의사항

### 크롤링 제한사항:
- 현재 `parse_html.py`는 **기존 HTML 파일**에서만 작동
- 웹 직접 크롤링(`playwright_text_fetcher.py`)은 타임아웃 문제로 실패 중

### 해결 방법:
1. **수동 HTML 다운로드:**
   - https://education.minecraft.net/ko-kr/resources 방문
   - 브라우저 개발자 도구로 HTML 저장
   - `minecraft-education-dashboard.html` 교체

2. **API 확인:**
   - Minecraft Education에 공식 API 있는지 확인
   - 있다면 API 기반 크롤러로 전환

3. **크롤링 개선:**
   - 프록시 사용
   - 요청 헤더 개선
   - 재시도 로직 강화

---

## 🔧 GitHub Actions 활성화

**이미 푸시하면 자동으로 활성화됩니다!**

확인 방법:
1. GitHub 저장소: https://github.com/ssakspirit/library-minecraft
2. **Actions** 탭
3. **Update Minecraft Resources** 워크플로우 확인

처음 실행 테스트:
1. **Actions** 탭
2. **Update Minecraft Resources** 클릭
3. **Run workflow** → **Run workflow** 버튼 클릭

---

## 📊 업데이트 주기 변경

`.github/workflows/update-data.yml` 파일 수정:

```yaml
# 현재: 매주 일요일
- cron: '0 0 * * 0'

# 매일:
- cron: '0 0 * * *'

# 매월 1일:
- cron: '0 0 1 * *'

# 매주 월요일, 목요일:
- cron: '0 0 * * 1,4'
```

---

## 🚀 빠른 사용법

**가장 쉬운 방법:**

```bash
# 한 줄로 업데이트
python update_data.py
```

**또는:**

GitHub Actions에서 수동 실행 (버튼 한 번 클릭!)

---

## 💡 향후 개선 계획

1. **실시간 데이터 fetch** - 크롤링 안정화 후
2. **변경 알림** - 새 리소스 추가 시 이메일/Discord 알림
3. **증분 업데이트** - 전체가 아닌 새로운 것만 수집
4. **데이터 검증** - 업데이트 전후 비교 및 검증

---

문의사항이나 문제가 있으면 GitHub Issues에 등록해주세요!
