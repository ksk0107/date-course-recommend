import math
import random
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="DateMate AI Agent", page_icon="💙", layout="wide")

# -----------------------------
# Demo data: 실제 API 키 없이도 제출/시연 가능한 버전
# -----------------------------
PLACES = {
    "잠실": [
        {"name": "석촌호수 산책로", "type": "산책", "indoor": False, "lat": 37.5112, "lon": 127.1002, "rating": 4.6, "open": True, "time": "24시간", "cost": "무료", "desc": "대화하며 걷기 좋은 대표 산책 코스"},
        {"name": "롯데월드몰", "type": "쇼핑/실내", "indoor": True, "lat": 37.5125, "lon": 127.1025, "rating": 4.5, "open": True, "time": "10:30~22:00", "cost": "선택", "desc": "비 오거나 더울 때 안정적인 실내 데이트"},
        {"name": "송리단길 카페거리", "type": "카페", "indoor": True, "lat": 37.5107, "lon": 127.1074, "rating": 4.4, "open": True, "time": "11:00~22:00", "cost": "1~2만원", "desc": "분위기 좋은 카페와 디저트 선택지가 많음"},
        {"name": "방이먹자골목", "type": "식사", "indoor": True, "lat": 37.5147, "lon": 127.1111, "rating": 4.2, "open": True, "time": "17:00~24:00", "cost": "2~4만원", "desc": "저녁 식사 후보가 많아 취향 맞추기 쉬움"},
        {"name": "서울스카이", "type": "전망", "indoor": True, "lat": 37.5126, "lon": 127.1026, "rating": 4.5, "open": True, "time": "10:30~22:00", "cost": "유료", "desc": "기념일이나 특별한 날에 어울리는 전망 코스"},
        {"name": "잠실한강공원", "type": "산책", "indoor": False, "lat": 37.5186, "lon": 127.0874, "rating": 4.5, "open": True, "time": "24시간", "cost": "무료", "desc": "야경과 한강 산책을 함께 즐기기 좋음"},
    ],
    "홍대": [
        {"name": "경의선숲길", "type": "산책", "indoor": False, "lat": 37.5576, "lon": 126.9253, "rating": 4.5, "open": True, "time": "24시간", "cost": "무료", "desc": "가볍게 걷고 대화하기 좋은 코스"},
        {"name": "연남동 카페거리", "type": "카페", "indoor": True, "lat": 37.5623, "lon": 126.9256, "rating": 4.4, "open": True, "time": "11:00~22:00", "cost": "1~2만원", "desc": "감성 카페와 디저트 선택지가 많음"},
        {"name": "홍대 소품샵 거리", "type": "쇼핑", "indoor": True, "lat": 37.5558, "lon": 126.9236, "rating": 4.2, "open": True, "time": "12:00~21:00", "cost": "선택", "desc": "가볍게 구경하며 취향을 알아가기 좋음"},
        {"name": "상수 맛집거리", "type": "식사", "indoor": True, "lat": 37.5478, "lon": 126.9227, "rating": 4.3, "open": True, "time": "17:00~23:00", "cost": "2~4만원", "desc": "저녁 식사 후보가 많은 지역"},
    ],
    "성수": [
        {"name": "서울숲", "type": "산책", "indoor": False, "lat": 37.5445, "lon": 127.0374, "rating": 4.7, "open": True, "time": "05:30~21:30", "cost": "무료", "desc": "낮 데이트와 피크닉 분위기에 적합"},
        {"name": "성수 카페거리", "type": "카페", "indoor": True, "lat": 37.5440, "lon": 127.0557, "rating": 4.4, "open": True, "time": "11:00~22:00", "cost": "1~2만원", "desc": "트렌디한 카페와 베이커리가 많음"},
        {"name": "성수 편집샵 거리", "type": "쇼핑", "indoor": True, "lat": 37.5432, "lon": 127.0528, "rating": 4.2, "open": True, "time": "12:00~21:00", "cost": "선택", "desc": "브랜드 팝업과 편집샵 구경 가능"},
        {"name": "뚝섬한강공원", "type": "산책", "indoor": False, "lat": 37.5295, "lon": 127.0665, "rating": 4.5, "open": True, "time": "24시간", "cost": "무료", "desc": "저녁 야경 코스로 마무리하기 좋음"},
    ],
}

WEATHER_PRESETS = {
    "맑음": "야외 산책과 전망 코스를 포함해도 좋습니다.",
    "비": "실내 카페, 쇼핑몰, 전시 위주로 추천합니다.",
    "더움": "실내 이동 비중을 높이고 야외는 짧게 구성합니다.",
    "추움": "실내 체류 시간을 길게 잡는 코스가 좋습니다.",
}


def haversine_km(a, b):
    r = 6371
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lon"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def walking_minutes(km):
    return max(3, round(km / 4.2 * 60))


def extract_area(text):
    for area in PLACES:
        if area in text:
            return area
    return "잠실"


def build_course(area, weather, exclude_visited, visited_names, prefer_open, date_type):
    places = list(PLACES.get(area, PLACES["잠실"]))

    if prefer_open:
        places = [p for p in places if p["open"]]

    if exclude_visited:
        places = [p for p in places if p["name"] not in visited_names]

    if weather in ["비", "더움", "추움"]:
        indoor = [p for p in places if p["indoor"]]
        outdoor = [p for p in places if not p["indoor"]]
        places = indoor + outdoor
    else:
        places = sorted(places, key=lambda p: (-p["rating"], p["type"] != "산책"))

    if date_type == "기념일":
        places = sorted(places, key=lambda p: (p["type"] not in ["전망", "식사", "카페"], -p["rating"]))
    elif date_type == "가성비":
        places = sorted(places, key=lambda p: ("무료" not in p["cost"], -p["rating"]))

    # 가까운 동선을 만들기 위한 greedy ordering
    if not places:
        return []
    course = [places[0]]
    remain = places[1:]
    while remain and len(course) < 4:
        cur = course[-1]
        nxt = min(remain, key=lambda p: haversine_km(cur, p))
        course.append(nxt)
        remain.remove(nxt)
    return course


# -----------------------------
# UI
# -----------------------------
st.title("💙 DateMate AI Agent")
st.caption("날씨·영업상태·동선·이전 방문지를 고려해 데이트 코스를 추천하는 AI Agent 데모")

with st.sidebar:
    st.header("설정")
    weather = st.selectbox("오늘 날씨", list(WEATHER_PRESETS.keys()))
    date_type = st.selectbox("데이트 성향", ["무난한 코스", "기념일", "가성비"])
    prefer_open = st.checkbox("영업 중인 곳만 추천", value=True)
    exclude_visited = st.checkbox("저번에 간 곳 제외", value=True)
    visited_names = st.multiselect(
        "이전에 방문한 장소",
        sorted({p["name"] for area in PLACES.values() for p in area}),
        default=["롯데월드몰"] if exclude_visited else [],
    )
    st.info("실제 서비스에서는 기상청 API, Google Places API, GPS 위치를 연결해 자동화할 수 있습니다.")

query = st.text_input("원하는 데이트 코스를 입력하세요", value="잠실 데이트코스 추천좀")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("날씨 판단", weather)
with col2:
    st.metric("영업 필터", "ON" if prefer_open else "OFF")
with col3:
    st.metric("방문지 제외", "ON" if exclude_visited else "OFF")

if st.button("데이트 코스 추천받기", type="primary"):
    area = extract_area(query)
    course = build_course(area, weather, exclude_visited, visited_names, prefer_open, date_type)

    st.subheader(f"📍 {area} 추천 데이트 코스")
    st.write(f"**추천 기준:** {WEATHER_PRESETS[weather]} 영업 중인 장소와 도보 이동이 가까운 순서를 우선 반영했습니다.")

    if not course:
        st.warning("조건에 맞는 장소가 부족합니다. 방문지 제외 옵션을 해제하거나 지역을 바꿔보세요.")
    else:
        total_walk = 0
        for i, place in enumerate(course, start=1):
            with st.container(border=True):
                st.markdown(f"### {i}. {place['name']}")
                st.write(f"**유형:** {place['type']}  |  **평점:** {place['rating']}  |  **영업:** {place['time']}  |  **예상 비용:** {place['cost']}")
                st.write(place["desc"])
                if i > 1:
                    km = haversine_km(course[i-2], place)
                    mins = walking_minutes(km)
                    total_walk += mins
                    st.caption(f"이전 장소에서 도보 약 {mins}분")

        st.success(f"예상 총 도보 이동 시간: 약 {total_walk}분")
        st.markdown("#### Agent 판단 요약")
        st.write(
            "이 코스는 ① 날씨에 따른 실내/야외 비중, ② 현재 영업 여부, "
            "③ 이전 방문지 제외, ④ 장소 간 도보 이동 시간을 함께 고려해 구성했습니다."
        )
else:
    st.write("예시: `잠실 데이트코스 추천좀`, `홍대에서 비 오는 날 데이트`, `성수 가성비 데이트 추천`")

st.divider()
st.caption("DateMate AI Agent demo | API 키 없이도 제출용 URL 확인이 가능하도록 구성된 단일 파일 버전")
