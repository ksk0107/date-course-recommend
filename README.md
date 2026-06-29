# DateMate AI Agent

날씨, 위치, 영업 여부, 이동 거리를 함께 고려해 데이트 코스를 추천하는 AI Agent입니다.

## 핵심 기능

- 사용자가 `잠실 데이트코스 추천좀`처럼 자연어로 요청하면 지역을 기준으로 코스 추천
- 기상청 단기예보 API를 이용해 비/흐림이면 실내 코스 우선 추천
- Google Places API를 이용해 장소 평점, 영업 상태, 주소, Google Maps URL 확인
- 장소 간 도보 거리 기준으로 가까운 동선 우선 정렬
- `저번에 간 곳 제외` 체크 기능과 방문 기록 저장 기능 제공
- API 키가 없어도 시연 가능한 데모 데이터 모드 포함

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## API 키 설정

로컬 실행 시 `.streamlit/secrets.example.toml`을 `.streamlit/secrets.toml`로 복사한 뒤 키를 입력합니다.

```toml
GOOGLE_MAPS_API_KEY = "..."
KMA_SERVICE_KEY = "..."
```

배포 시에는 Streamlit Community Cloud의 Advanced settings > Secrets에 같은 내용을 입력합니다.

## 제출 전 확인 체크리스트

- [ ] 외부 PC/휴대폰에서 앱 URL 접속 가능
- [ ] API 키가 GitHub에 공개되지 않음
- [ ] `잠실 데이트코스 추천좀` 입력 시 결과가 표시됨
- [ ] 영업 종료 장소가 제외되거나 하단 로그에 사유가 표시됨
- [ ] 방문 기록 저장 후 `저번에 간 곳 제외` 체크가 작동함

## 권장 배포 방식

1. GitHub에 이 폴더를 업로드합니다. 단, `.streamlit/secrets.toml`은 올리지 않습니다.
2. Streamlit Community Cloud에서 `app.py`를 entrypoint로 선택합니다.
3. Advanced settings에서 `GOOGLE_MAPS_API_KEY`, `KMA_SERVICE_KEY`를 등록합니다.
4. 배포 URL을 과제 양식의 `에이전트 URL` 칸에 입력합니다.

## 구조

```text
app.py                 # Streamlit UI
 datemate_agent.py      # 위치/날씨/장소/동선 추천 로직
requirements.txt       # 배포 의존성
.streamlit/config.toml # 화면 테마
.streamlit/secrets.example.toml
 data/visited_places.json
```
