# DateMate AI Agent 배포 가이드

## 1. API 준비

### Google Maps Platform
필요 API: Places API (New), Geocoding API.

### 기상청 공공데이터포털
필요 API: 기상청_단기예보 조회서비스. 상세 기능은 초단기예보(getUltraSrtFcst)를 사용합니다.

## 2. GitHub 업로드

```bash
git init
git add app.py datemate_agent.py requirements.txt README.md .streamlit/config.toml .streamlit/secrets.example.toml data/visited_places.json
git commit -m "Add DateMate AI Agent"
git branch -M main
git remote add origin https://github.com/<YOUR_ID>/datemate-ai-agent.git
git push -u origin main
```

`.streamlit/secrets.toml`은 절대 올리지 마세요.

## 3. Streamlit Community Cloud 배포

- New app 생성
- Repository: 위 GitHub 저장소
- Branch: main
- Main file path: app.py
- Advanced settings > Secrets에 아래 형식 입력

```toml
GOOGLE_MAPS_API_KEY = "..."
KMA_SERVICE_KEY = "..."
```

## 4. 과제 제출 전 테스트

1. 배포 URL을 시크릿 창에서 열기
2. 휴대폰 LTE/5G에서 열기
3. `잠실 데이트코스 추천좀`으로 실행
4. 방문 기록 저장 후 `저번에 간 곳 제외` 체크 확인
5. URL 클릭 시 Google Maps가 열리는지 확인
