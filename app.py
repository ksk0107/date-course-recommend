from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from datemate_agent import (
    DatePlan,
    estimate_walk_minutes,
    flatten_history_names,
    get_secret,
    load_history,
    make_plain_summary,
    plan_date_course,
    save_history_entry,
)

try:
    from streamlit_js_eval import get_geolocation
except Exception:  # pragma: no cover
    get_geolocation = None

st.set_page_config(page_title="DateMate AI Agent", page_icon="💙", layout="wide")

st.markdown(
    """
    <style>
    .main-card {border: 1px solid #E6EEF8; border-radius: 16px; padding: 18px; background: #FFFFFF; box-shadow: 0 2px 8px rgba(31, 78, 121, 0.06);}
    .small-muted {color: #667085; font-size: 0.9rem;}
    .step-card {border-left: 6px solid #2E6DF6; padding: 14px 16px; margin-bottom: 12px; background: #F8FBFF; border-radius: 10px;}
    </style>
    """,
    unsafe_allow_html=True,
)


def read_secrets() -> Dict[str, Any]:
    secrets = {}
    try:
        secrets = dict(st.secrets)
    except Exception:
        pass
    return secrets


def show_plan(plan: DatePlan) -> None:
    st.subheader(f"💙 {plan.area} 데이트 코스")
    mode = "실시간 API 모드" if plan.live_mode else "데모/대체 데이터 모드"
    st.caption(f"{mode} · 날씨: {plan.weather.message}")

    st.info(make_plain_summary(plan))

    cols = st.columns(3)
    cols[0].metric("총 도보 거리", f"{plan.total_walk_m/1000:.1f} km")
    cols[1].metric("예상 소요 시간", f"{plan.total_time_min//60}시간 {plan.total_time_min%60}분")
    cols[2].metric("추천 장소", f"{len(plan.steps)}곳")

    for step in plan.steps:
        place = step.place
        status = "✅ 영업 중" if place.open_now is True else "ℹ️ 영업 정보 확인 필요" if place.open_now is None else "⚠️ 영업 종료 가능"
        walk = "시작 지점" if step.order == 1 else f"이전 장소에서 도보 약 {estimate_walk_minutes(step.walk_from_previous_m)}분 / {step.walk_from_previous_m}m"
        maps = f"[Google Maps 열기]({place.maps_url})" if place.maps_url else ""
        st.markdown(
            f"""
            <div class="step-card">
              <b>{step.order}. {step.time_label} · {place.name}</b><br>
              <span class="small-muted">{place.address}</span><br>
              {status} · 평점 {place.rating or '정보 없음'} · 가격대 {place.price_label}<br>
              🚶 {walk}<br>
              <span class="small-muted">추천 이유: {step.reason}</span><br>
              {maps}
            </div>
            """,
            unsafe_allow_html=True,
        )

    map_rows = [
        {"lat": s.place.lat, "lon": s.place.lng, "name": f"{s.order}. {s.place.name}"}
        for s in plan.steps
    ]
    if map_rows:
        st.map(pd.DataFrame(map_rows), latitude="lat", longitude="lon", size=80)

    with st.expander("에이전트 판단 로그"):
        st.write("- " + "\n- ".join(plan.notes))
        st.json(plan.to_dict())


secrets = read_secrets()
google_key = get_secret("GOOGLE_MAPS_API_KEY", secrets)
kma_key = get_secret("KMA_SERVICE_KEY", secrets)

st.title("💙 DateMate AI Agent")
st.write("날씨, 위치, 영업 여부, 이동 거리를 함께 보고 데이트 코스를 추천합니다.")

with st.sidebar:
    st.header("설정")
    st.caption("API 키는 GitHub에 올리지 말고 Streamlit secrets에 넣어 주세요.")
    st.code(
        "GOOGLE_MAPS_API_KEY = '...'\nKMA_SERVICE_KEY = '...'",
        language="toml",
    )
    if google_key and kma_key:
        st.success("API 키가 연결되었습니다.")
    else:
        st.warning("API 키가 없으면 데모 데이터로 실행됩니다.")

    st.divider()
    st.subheader("방문 기록")
    history = load_history()
    history_names = flatten_history_names(history)
    if history_names:
        st.write(", ".join(history_names[-8:]))
    else:
        st.caption("아직 저장된 방문 기록이 없습니다.")

with st.form("plan_form"):
    col1, col2 = st.columns([2, 1])
    with col1:
        request_text = st.text_input("원하는 코스를 말해 주세요", value="잠실 데이트코스 추천좀")
        area = st.text_input("지역", value="잠실")
        preference = st.selectbox("선호 분위기", ["균형", "실내 위주", "카페 먼저", "산책 포함"])
    with col2:
        start_time = st.time_input("시작 시간").strftime("%H:%M")
        max_walk_m = st.slider("장소 간 최대 도보 거리", 300, 2000, 900, 100)
        only_open = st.checkbox("현재 영업 중인 곳 우선", value=True)
        exclude_history = st.checkbox("저번에 간 곳 제외", value=True)

    manual_exclude = st.multiselect("추가로 제외할 장소", options=history_names)
    use_gps = st.checkbox("GPS 현재 위치 기준으로 추천", value=False)
    submitted = st.form_submit_button("데이트 코스 만들기", type="primary")

if submitted:
    gps_lat = gps_lng = None
    if use_gps and get_geolocation is not None:
        loc = get_geolocation()
        if loc and loc.get("coords"):
            gps_lat = loc["coords"].get("latitude")
            gps_lng = loc["coords"].get("longitude")
    with st.spinner("날씨·영업 여부·동선을 확인하고 있어요..."):
        plan = plan_date_course(
            requested_text=request_text,
            area=area,
            start_time=start_time,
            preference=preference,
            max_walk_m=max_walk_m,
            only_open=only_open,
            exclude_history=exclude_history,
            manual_exclude_names=manual_exclude,
            google_api_key=google_key,
            kma_service_key=kma_key,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
        )
        st.session_state["last_plan"] = plan

if "last_plan" in st.session_state:
    show_plan(st.session_state["last_plan"])
    if st.button("이 코스를 방문 기록에 저장"):
        plan = st.session_state["last_plan"]
        save_history_entry(f"{plan.area} 데이트 코스", [s.place for s in plan.steps])
        st.success("방문 기록에 저장했습니다. 다음 추천부터 제외할 수 있어요.")

st.markdown("---")
st.caption("DateMate AI Agent · 개인 일상과 성장을 돕는 데이트 코스 추천 에이전트")
