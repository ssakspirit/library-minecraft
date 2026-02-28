# 📝 데이터 업데이트 가이드

Minecraft Education 리소스 데이터를 최신 상태로 유지하는 방법입니다.

## 🤖 자동 업데이트 (GitHub Actions)

### 기본 설정

- **실행 주기**: 매주 일요일 오전 12시 (UTC)
- **배치 크기**: 50개 리소스
- **작동 방식**:
  1. 누락된 썸네일/태그가 있는 리소스 탐지
  2. 최대 50개씩 크롤링
  3. 변경사항이 있으면 자동 커밋 & 푸시
  4. Streamlit Cloud 자동 재배포

### 수동 실행 방법

1. GitHub 저장소 이동
2. **Actions** 탭 클릭
3. **Update Minecraft Education Resources** 워크플로우 선택
4. **Run workflow** 버튼 클릭
5. (선택) 배치 크기 조정 (기본: 50)
6. **Run workflow** 확인

### 배치 크기 권장 사항

- **50개 (기본)**: 안전한 기본값, rate limiting 최소화
- **100개**: 빠른 업데이트가 필요할 때
- **25개**: 매우 보수적, rate limiting이 우려될 때

## 🖥️ 로컬 수동 업데이트

### 1. 기본 사용

```bash
# 50개 리소스 크롤링 (기본)
python update_data.py
```

### 2. 배치 크기 조정

```bash
# Windows
set BATCH_SIZE=100
python update_data.py

# Linux/Mac
BATCH_SIZE=100 python update_data.py
```

### 3. 실패한 리소스만 재시도

```bash
# retry_crawler.py 사용 (100개씩)
python retry_crawler.py
```

## 📊 현황 확인

### 진행 상황 분석

```bash
python analyze_progress.py
```

출력 예시:
```
총 리소스: 1,123
완료: 240 (21%)
미완료: 883

실패 구간 분석:
  ...
```

## ⚙️ Rate Limiting 방지 전략

### update_data.py 설정

- **요청 간격**: 8초
- **휴식 주기**: 20개마다 90초
- **재시도**: 3회 (점진적 백오프)
- **배치 크기**: 기본 50개

### retry_crawler.py 설정 (더 보수적)

- **요청 간격**: 10초
- **휴식 주기**: 25개마다 2분
- **재시도**: 3회
- **배치 크기**: 100개

### 차단되었을 때

1. **즉시 중단**: Ctrl+C로 크롤러 중지
2. **대기**: 2-4시간 후 재시도
3. **배치 크기 축소**: 50 → 25로 줄이기

## 🔄 업데이트 워크플로우

### 초기 설정 (첫 실행)

```bash
# 1. 배치 크롤링
python retry_crawler.py  # 100개 크롤링
# 2-4시간 대기...
python retry_crawler.py  # 다음 100개
# 반복...

# 2. 진행 상황 확인
python analyze_progress.py

# 3. 커밋 & 푸시
git add data/resources_enhanced.json
git commit -m "✨ 전체 리소스 크롤링 완료"
git push
```

### 정기 업데이트 (자동화 이후)

GitHub Actions가 자동으로 실행:
- 매주 일요일에 50개씩 크롤링
- 누락된 데이터 자동 보완
- 변경사항 자동 커밋 & 배포

## 📈 완료까지 예상 시간

현재 883개 미완료 기준:

- **자동 (주간)**: 약 18주 (4.5개월)
- **수동 (적극적)**: 약 4-5일
- **혼합 (권장)**: 약 1-2주

## 🛠️ 트러블슈팅

### HTTP2 Protocol Error

```
❌ Failed: net::ERR_HTTP2_PROTOCOL_ERROR
```

**해결책**:
1. 크롤러 중지
2. 2-4시간 대기
3. 배치 크기 절반으로 줄이기
4. 재시도

## 📁 파일 설명

- `update_data.py` - 자동 업데이트 메인 스크립트
- `retry_crawler.py` - 실패 리소스 재시도
- `analyze_progress.py` - 진행 상황 분석
- `failed_resources.json` - 실패 리소스 목록
- `.github/workflows/update-data.yml` - GitHub Actions

## 💡 팁

1. **점진적 크롤링**: 한 번에 많이 하지 말고 여러 번 나누어 실행
2. **시간대 활용**: 트래픽 적은 시간대 사용
3. **모니터링**: GitHub Actions 로그 확인
4. **백업**: Git 커밋으로 자동 백업

## 🎯 목표

- ✅ **단기**: 883개 미완료 리소스 크롤링
- ✅ **중기**: 주간 자동 업데이트 안정화
- ✅ **장기**: 신규 리소스 자동 감지 & 크롤링
