"""DateMate AI Agent core logic.

This module is designed to run both with real APIs and in demo mode.
Real mode uses:
- Google Places API (New) for POI search, ratings, open-now status, map URL
- KMA VilageFcstInfoService getUltraSrtFcst for short-term weather

No API keys are stored in source code. Provide keys through Streamlit secrets or env vars.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

KST = timezone(timedelta(hours=9))

GOOGLE_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
KMA_ULTRA_FCST_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"

HISTORY_PATH = Path("data/visited_places.json")

CATEGORY_QUERIES = {
    "meal": ["{area} 데이트 맛집", "{area} 분위기 좋은 식당", "{area} 파스타", "{area} 한식 맛집"],
    "cafe": ["{area} 카페", "{area} 디저트 카페", "{area} 뷰 좋은 카페"],
    "activity_indoor": ["{area} 실내 데이트", "{area} 전시", "{area} 영화관", "{area} 실내 체험"],
    "activity_outdoor": ["{area} 산책", "{area} 공원", "{area} 야경", "{area} 전망대"],
    "dessert": ["{area} 디저트", "{area} 아이스크림", "{area} 베이커리"],
}

DEMO_PLACES = [
    {
        "id": "demo-seoul-sky",
        "name": "서울스카이",
        "address": "서울 송파구 올림픽로 300",
        "lat": 37.5126,
        "lng": 127.1025,
        "category": "activity_indoor",
        "rating": 4.4,
        "review_count": 3100,
        "open_now": True,
        "price_level": "PRICE_LEVEL_EXPENSIVE",
        "maps_url": "https://maps.google.com/?q=서울스카이",
        "why": "날씨가 흐리거나 더워도 실내 중심으로 즐길 수 있는 대표 전망 코스",
    },
    {
        "id": "demo-lotte-mall",
        "name": "롯데월드몰",
        "address": "서울 송파구 올림픽로 300",
        "lat": 37.5130,
        "lng": 127.1035,
        "category": "activity_indoor",
        "rating": 4.3,
        "review_count": 15000,
        "open_now": True,
        "price_level": "PRICE_LEVEL_MODERATE",
        "maps_url": "https://maps.google.com/?q=롯데월드몰",
        "why": "식사, 카페, 쇼핑, 실내 이동을 한 번에 묶기 쉬움",
    },
    {
        "id": "demo-seokchon",
        "name": "석촌호수 산책로",
        "address": "서울 송파구 잠실동",
        "lat": 37.5082,
        "lng": 127.1036,
        "category": "activity_outdoor",
        "rating": 4.5,
        "review_count": 9000,
        "open_now": True,
        "price_level": "PRICE_LEVEL_FREE",
        "maps_url": "https://maps.google.com/?q=석촌호수",
        "why": "카페와 식당 사이에 넣기 좋은 짧은 산책 동선",
    },
    {
        "id": "demo-bills",
        "name": "빌즈 잠실",
        "address": "서울 송파구 올림픽로 300 롯데월드몰",
        "lat": 37.5132,
        "lng": 127.1033,
        "category": "meal",
        "rating": 4.2,
        "review_count": 1800,
        "open_now": True,
        "price_level": "PRICE_LEVEL_EXPENSIVE",
        "maps_url": "https://maps.google.com/?q=빌즈 잠실",
        "why": "데이트 첫 식사로 무난한 분위기와 접근성",
    },
    {
        "id": "demo-cafe-knotted",
        "name": "카페 노티드 잠실",
        "address": "서울 송파구 올림픽로 300",
        "lat": 37.5129,
        "lng": 127.1028,
        "category": "cafe",
        "rating": 4.1,
        "review_count": 2500,
        "open_now": True,
        "price_level": "PRICE_LEVEL_MODERATE",
        "maps_url": "https://maps.google.com/?q=노티드 잠실",
        "why": "짧게 들러 디저트와 커피를 해결하기 좋음",
    },
    {
        "id": "demo-aquarium",
        "name": "롯데월드 아쿠아리움",
        "address": "서울 송파구 올림픽로 300",
        "lat": 37.5136,
        "lng": 127.1029,
        "category": "activity_indoor",
        "rating": 4.3,
        "review_count": 7200,
        "open_now": True,
        "price_level": "PRICE_LEVEL_EXPENSIVE",
        "maps_url": "https://maps.google.com/?q=롯데월드 아쿠아리움",
        "why": "비 오는 날에도 안정적으로 즐길 수 있는 실내 활동",
    },
]

PRICE_LABELS = {
    "PRICE_LEVEL_FREE": "무료",
    "PRICE_LEVEL_INEXPENSIVE": "저렴",
    "PRICE_LEVEL_MODERATE": "보통",
    "PRICE_LEVEL_EXPENSIVE": "높음",
    "PRICE_LEVEL_VERY_EXPENSIVE": "매우 높음",
    "PRICE_LEVEL_UNSPECIFIED": "정보 없음",
    None: "정보 없음",
}

PTY_LABELS = {
    "0": "강수 없음",
    "1": "비",
    "2": "비/눈",
    "3": "눈",
    "4": "소나기",
    "5": "빗방울",
    "6": "빗방울/눈날림",
    "7": "눈날림",
}

SKY_LABELS = {"1": "맑음", "3": "구름 많음", "4": "흐림"}


@dataclass
class Place:
    id: str
    name: str
    address: str
    lat: float
    lng: float
    category: str
    rating: float = 0.0
    review_count: int = 0
    open_now: Optional[bool] = None
    price_level: Optional[str] = None
    maps_url: str = ""
    why: str = ""
    source: str = "google"

    @property
    def price_label(self) -> str:
        return PRICE_LABELS.get(self.price_level, "정보 없음")


@dataclass
class WeatherSummary:
    temp_c: Optional[float]
    sky: str
    precipitation: str
    rain_mm: Optional[float]
    source: str
    raw: Dict[str, Any]

    @property
    def is_bad_weather(self) -> bool:
        return self.precipitation not in ("강수 없음", "정보 없음") or self.sky == "흐림"

    @property
    def message(self) -> str:
        temp = f"{self.temp_c:.0f}℃" if self.temp_c is not None else "기온 정보 없음"
        rain = f", 강수 {self.rain_mm:g}mm" if self.rain_mm not in (None, 0) else ""
        return f"{temp}, {self.sky}, {self.precipitation}{rain}"


@dataclass
class ItineraryStep:
    order: int
    time_label: str
    place: Place
    stay_minutes: int
    walk_from_previous_m: int
    reason: str


@dataclass
class DatePlan:
    area: str
    requested_text: str
    weather: WeatherSummary
    steps: List[ItineraryStep]
    total_walk_m: int
    total_time_min: int
    excluded_names: List[str]
    live_mode: bool
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


def get_secret(name: str, secrets: Optional[Dict[str, Any]] = None, default: str = "") -> str:
    """Read a secret from Streamlit secrets-like object or environment."""
    if secrets and name in secrets:
        return str(secrets[name])
    return os.environ.get(name, default)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def estimate_walk_minutes(distance_m: int) -> int:
    # Comfortable walking speed for city dating course: about 70 m/min.
    return max(1, round(distance_m / 70))


def extract_area(text: str) -> str:
    m = re.search(r"([가-힣A-Za-z0-9]+)\s*(데이트|코스|근처|주변)", text)
    if m:
        return m.group(1)
    cleaned = re.sub(r"추천|데이트|코스|짜줘|좀|해줘|요|\. |\?", " ", text).strip()
    return cleaned.split()[0] if cleaned.split() else "잠실"


def geocode_area(area: str, google_api_key: str = "") -> Tuple[float, float, str, bool]:
    if not google_api_key:
        # Default demo center: Jamsil / Lotte World Tower area.
        return 37.5133, 127.1028, f"{area} 중심 좌표(데모: 잠실 기준)", False
    params = {"address": area, "language": "ko", "region": "kr", "key": google_api_key}
    r = requests.get(GOOGLE_GEOCODE_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK" or not data.get("results"):
        return 37.5133, 127.1028, f"{area} 좌표 검색 실패, 데모 좌표 사용", False
    result = data["results"][0]
    loc = result["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"]), result.get("formatted_address", area), True


def dfs_xy_conv(lat: float, lon: float) -> Tuple[int, int]:
    """Convert WGS84 lat/lon to KMA DFS grid x/y.

    Formula published in KMA sample code for the Lambert Conformal Conic grid.
    """
    import math

    RE = 6371.00877  # earth radius, km
    GRID = 5.0       # grid spacing, km
    SLAT1 = 30.0     # projection latitude 1, degree
    SLAT2 = 60.0     # projection latitude 2, degree
    OLON = 126.0     # reference longitude, degree
    OLAT = 38.0      # reference latitude, degree
    XO = 43          # reference x
    YO = 136         # reference y

    DEGRAD = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro ** sn)
    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / (ra ** sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn
    x = int(ra * math.sin(theta) + XO + 0.5)
    y = int(ro - ra * math.cos(theta) + YO + 0.5)
    return x, y


def kma_base_datetime(now: Optional[datetime] = None) -> Tuple[str, str]:
    now = now.astimezone(KST) if now else datetime.now(KST)
    # Ultra-short forecast is safest after about 45 minutes from release.
    base = now - timedelta(minutes=45)
    base = base.replace(minute=30, second=0, microsecond=0)
    return base.strftime("%Y%m%d"), base.strftime("%H%M")


def fetch_kma_weather(lat: float, lon: float, service_key: str = "") -> WeatherSummary:
    if not service_key:
        return WeatherSummary(
            temp_c=24,
            sky="구름 많음",
            precipitation="강수 없음",
            rain_mm=0,
            source="demo",
            raw={"notice": "KMA_SERVICE_KEY가 없어 데모 날씨를 사용했습니다."},
        )

    nx, ny = dfs_xy_conv(lat, lon)
    base_date, base_time = kma_base_datetime()
    params = {
        "serviceKey": service_key,
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }
    try:
        r = requests.get(KMA_ULTRA_FCST_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if not items:
            raise ValueError("KMA response has no forecast items")

        now_hhmm = datetime.now(KST).strftime("%H%M")
        by_time: Dict[str, Dict[str, str]] = {}
        for item in items:
            ft = item.get("fcstTime", "")
            by_time.setdefault(ft, {})[item.get("category", "")] = str(item.get("fcstValue", ""))
        selected_time = sorted(by_time.keys(), key=lambda t: (t < now_hhmm, t))[0]
        values = by_time[selected_time]
        temp = None
        if "T1H" in values:
            try:
                temp = float(values["T1H"])
            except ValueError:
                temp = None
        rain_mm = None
        if "RN1" in values:
            try:
                rain_mm = float(re.sub(r"[^0-9.]", "", values["RN1"]) or 0)
            except ValueError:
                rain_mm = None
        return WeatherSummary(
            temp_c=temp,
            sky=SKY_LABELS.get(values.get("SKY"), "정보 없음"),
            precipitation=PTY_LABELS.get(values.get("PTY"), "정보 없음"),
            rain_mm=rain_mm,
            source="kma",
            raw={"base_date": base_date, "base_time": base_time, "fcst_time": selected_time, "nx": nx, "ny": ny},
        )
    except Exception as exc:  # noqa: BLE001 - app should degrade gracefully
        return WeatherSummary(
            temp_c=None,
            sky="정보 없음",
            precipitation="정보 없음",
            rain_mm=None,
            source="fallback",
            raw={"error": str(exc)},
        )


def google_text_search(
    query: str,
    lat: float,
    lng: float,
    google_api_key: str,
    radius_m: int = 2500,
    max_results: int = 8,
) -> List[Dict[str, Any]]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": google_api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.rating,places.userRatingCount,places.businessStatus,"
            "places.currentOpeningHours,places.googleMapsUri,places.primaryType,"
            "places.types,places.priceLevel"
        ),
    }
    body = {
        "textQuery": query,
        "languageCode": "ko",
        "regionCode": "KR",
        "maxResultCount": max_results,
        "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": radius_m}},
    }
    r = requests.post(GOOGLE_TEXT_SEARCH_URL, headers=headers, json=body, timeout=12)
    r.raise_for_status()
    return r.json().get("places", [])


def normalize_google_place(raw: Dict[str, Any], category: str) -> Optional[Place]:
    loc = raw.get("location") or {}
    if "latitude" not in loc or "longitude" not in loc:
        return None
    name = raw.get("displayName", {}).get("text") or "이름 없음"
    open_now = None
    if isinstance(raw.get("currentOpeningHours"), dict):
        open_now = raw["currentOpeningHours"].get("openNow")
    return Place(
        id=raw.get("id", name),
        name=name,
        address=raw.get("formattedAddress", ""),
        lat=float(loc["latitude"]),
        lng=float(loc["longitude"]),
        category=category,
        rating=float(raw.get("rating") or 0),
        review_count=int(raw.get("userRatingCount") or 0),
        open_now=open_now,
        price_level=raw.get("priceLevel"),
        maps_url=raw.get("googleMapsUri", ""),
        why="평점, 현재 영업 여부, 동선 접근성을 기준으로 선별했습니다.",
        source="google",
    )


def search_places(
    area: str,
    lat: float,
    lng: float,
    google_api_key: str = "",
    radius_m: int = 2500,
) -> List[Place]:
    if not google_api_key:
        return [Place(**p, source="demo") for p in DEMO_PLACES]

    places: List[Place] = []
    seen: set[str] = set()
    for category, query_templates in CATEGORY_QUERIES.items():
        for template in query_templates[:2]:
            query = template.format(area=area)
            try:
                for raw in google_text_search(query, lat, lng, google_api_key, radius_m=radius_m):
                    place = normalize_google_place(raw, category)
                    if not place or place.id in seen:
                        continue
                    seen.add(place.id)
                    places.append(place)
            except Exception:
                # Keep going with other queries; final response tells user if demo/fallback was used.
                continue
    return places or [Place(**p, source="demo") for p in DEMO_PLACES]


def load_history(path: Path = HISTORY_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history_entry(course_name: str, places: Iterable[Place], path: Path = HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    history = load_history(path)
    history.append(
        {
            "saved_at": datetime.now(KST).isoformat(),
            "course_name": course_name,
            "places": [p.name for p in places],
        }
    )
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def flatten_history_names(history: Iterable[Dict[str, Any]]) -> List[str]:
    names: List[str] = []
    for h in history:
        names.extend(h.get("places", []))
    return sorted(set(names))


def filter_open_and_history(places: List[Place], exclude_names: Iterable[str], only_open: bool = True) -> List[Place]:
    exclude = {n.strip().lower() for n in exclude_names if n.strip()}
    result = []
    for p in places:
        if any(n in p.name.lower() for n in exclude):
            continue
        if only_open and p.open_now is False:
            continue
        result.append(p)
    return result


def score_place(place: Place, center_lat: float, center_lng: float, weather: WeatherSummary, prefer_indoor: bool) -> float:
    distance = haversine_m(center_lat, center_lng, place.lat, place.lng)
    rating_score = place.rating * 12
    review_score = min(place.review_count, 5000) / 5000 * 10
    proximity_score = max(0, 25 - distance / 100)
    open_bonus = 8 if place.open_now is True else 0
    weather_bonus = 0
    if prefer_indoor and place.category == "activity_indoor":
        weather_bonus += 12
    if not prefer_indoor and place.category == "activity_outdoor":
        weather_bonus += 10
    return rating_score + review_score + proximity_score + open_bonus + weather_bonus


def choose_course_pattern(weather: WeatherSummary, user_preference: str) -> List[str]:
    if "실내" in user_preference or weather.is_bad_weather:
        return ["meal", "activity_indoor", "cafe"]
    if "카페" in user_preference:
        return ["cafe", "activity_outdoor", "meal"]
    return ["meal", "activity_outdoor", "cafe"]


def pick_places_for_pattern(
    places: List[Place],
    pattern: List[str],
    center_lat: float,
    center_lng: float,
    weather: WeatherSummary,
    max_walk_m: int,
) -> List[Place]:
    chosen: List[Place] = []
    current_lat, current_lng = center_lat, center_lng
    prefer_indoor = weather.is_bad_weather
    for category in pattern:
        candidates = [p for p in places if p.category == category and p.id not in {c.id for c in chosen}]
        if not candidates and category == "activity_outdoor":
            candidates = [p for p in places if p.category == "activity_indoor" and p.id not in {c.id for c in chosen}]
        if not candidates and category == "activity_indoor":
            candidates = [p for p in places if p.category == "activity_outdoor" and p.id not in {c.id for c in chosen}]
        if not candidates:
            candidates = [p for p in places if p.id not in {c.id for c in chosen}]
        if not candidates:
            break
        ranked = sorted(
            candidates,
            key=lambda p: (
                score_place(p, center_lat, center_lng, weather, prefer_indoor)
                - haversine_m(current_lat, current_lng, p.lat, p.lng) / 80
            ),
            reverse=True,
        )
        chosen.append(ranked[0])
        current_lat, current_lng = ranked[0].lat, ranked[0].lng

    # If selected course exceeds walking limit too much, greedily reorder by nearest neighbor.
    return optimize_order(chosen, center_lat, center_lng, max_walk_m)


def optimize_order(places: List[Place], start_lat: float, start_lng: float, max_walk_m: int) -> List[Place]:
    if len(places) <= 2:
        return places
    remaining = places[:]
    ordered: List[Place] = []
    cur_lat, cur_lng = start_lat, start_lng
    while remaining:
        next_place = min(remaining, key=lambda p: haversine_m(cur_lat, cur_lng, p.lat, p.lng))
        ordered.append(next_place)
        remaining.remove(next_place)
        cur_lat, cur_lng = next_place.lat, next_place.lng
    return ordered


def build_steps(ordered_places: List[Place], start_lat: float, start_lng: float, start_time: str) -> Tuple[List[ItineraryStep], int, int]:
    steps: List[ItineraryStep] = []
    cur_lat, cur_lng = start_lat, start_lng
    total_walk = 0
    cursor = datetime.strptime(start_time, "%H:%M")
    stay_by_category = {
        "meal": 80,
        "cafe": 50,
        "dessert": 40,
        "activity_indoor": 90,
        "activity_outdoor": 45,
    }
    for idx, place in enumerate(ordered_places, start=1):
        walk_m = int(round(haversine_m(cur_lat, cur_lng, place.lat, place.lng)))
        walk_min = estimate_walk_minutes(walk_m)
        total_walk += walk_m
        if idx > 1:
            cursor += timedelta(minutes=walk_min)
        stay = stay_by_category.get(place.category, 60)
        time_label = cursor.strftime("%H:%M")
        reason = place.why or "영업 여부, 평점, 이동 거리 기준으로 추천했습니다."
        steps.append(ItineraryStep(idx, time_label, place, stay, walk_m if idx > 1 else 0, reason))
        cursor += timedelta(minutes=stay)
        cur_lat, cur_lng = place.lat, place.lng
    total_time = int((cursor - datetime.strptime(start_time, "%H:%M")).total_seconds() / 60)
    return steps, total_walk, total_time


def plan_date_course(
    requested_text: str,
    area: Optional[str] = None,
    start_time: str = "14:00",
    preference: str = "균형",
    max_walk_m: int = 900,
    only_open: bool = True,
    exclude_history: bool = True,
    manual_exclude_names: Optional[List[str]] = None,
    google_api_key: str = "",
    kma_service_key: str = "",
    gps_lat: Optional[float] = None,
    gps_lng: Optional[float] = None,
) -> DatePlan:
    area = area or extract_area(requested_text)
    center_lat, center_lng, geocode_label, geocode_live = geocode_area(area, google_api_key)
    if gps_lat is not None and gps_lng is not None:
        center_lat, center_lng = gps_lat, gps_lng
        geocode_label = "GPS 현재 위치 기준"

    weather = fetch_kma_weather(center_lat, center_lng, kma_service_key)
    places = search_places(area, center_lat, center_lng, google_api_key)

    history_names = flatten_history_names(load_history()) if exclude_history else []
    excludes = sorted(set(history_names + (manual_exclude_names or [])))
    candidates = filter_open_and_history(places, excludes, only_open=only_open)
    if len(candidates) < 3:
        # Relax open filter to avoid empty course, but keep history exclusion.
        candidates = filter_open_and_history(places, excludes, only_open=False)
    if not candidates:
        candidates = places

    pattern = choose_course_pattern(weather, preference)
    ordered = pick_places_for_pattern(candidates, pattern, center_lat, center_lng, weather, max_walk_m=max_walk_m)
    steps, total_walk, total_time = build_steps(ordered, center_lat, center_lng, start_time)

    live_mode = bool(google_api_key and kma_service_key and any(p.source == "google" for p in places))
    notes = [f"위치 기준: {geocode_label}"]
    if weather.source != "kma":
        notes.append("기상청 API 키가 없거나 응답 실패로 데모/대체 날씨를 사용했습니다.")
    if not google_api_key or all(p.source == "demo" for p in places):
        notes.append("Google Places API 키가 없거나 응답 실패로 데모 장소를 사용했습니다.")
    if only_open:
        notes.append("영업 중 여부가 확인되는 장소를 우선 필터링했습니다. 영업시간 정보가 없는 장소는 후보로 남길 수 있습니다.")
    if excludes:
        notes.append(f"방문 이력/수동 제외 장소 {len(excludes)}개를 제외했습니다.")

    return DatePlan(area, requested_text, weather, steps, total_walk, total_time, excludes, live_mode, notes)


def make_plain_summary(plan: DatePlan) -> str:
    if not plan.steps:
        return "추천 가능한 코스를 찾지 못했습니다. 반경을 넓히거나 제외 조건을 줄여 주세요."
    intro = "비/흐림 가능성이 있어 실내 중심으로 구성했습니다." if plan.weather.is_bad_weather else "날씨가 무난해 산책을 포함한 코스로 구성했습니다."
    lines = [f"{plan.area} 기준으로 {intro}"]
    for step in plan.steps:
        walk = f", 이전 장소에서 도보 약 {estimate_walk_minutes(step.walk_from_previous_m)}분" if step.order > 1 else ""
        open_status = "영업 중" if step.place.open_now is True else "영업 정보 확인 필요" if step.place.open_now is None else "영업 종료 가능"
        lines.append(f"{step.order}. {step.time_label} {step.place.name} ({open_status}{walk})")
    lines.append(f"총 도보 약 {plan.total_walk_m/1000:.1f}km, 예상 소요 {plan.total_time_min//60}시간 {plan.total_time_min%60}분")
    return "\n".join(lines)
