"""Weather and air quality from Open-Meteo (free, no API key)."""

from datetime import datetime

import httpx

from ..config import get_settings
from ..timeutil import clock

CODES = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Cloudy", 45: "Foggy", 48: "Foggy",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Rain showers", 81: "Rain showers", 82: "Heavy showers", 95: "Thunderstorm", 96: "Thunderstorm",
    99: "Thunderstorm",
}


def aqi_label(aqi: float | None) -> str:
    if aqi is None:
        return ""
    if aqi <= 50:
        return "good"
    if aqi <= 100:
        return "moderate"
    if aqi <= 150:
        return "unhealthy for sensitive people"
    if aqi <= 200:
        return "unhealthy"
    if aqi <= 300:
        return "very unhealthy"
    return "hazardous"


def current() -> dict:
    s = get_settings()
    with httpx.Client(timeout=15) as http:
        w = http.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": s.latitude,
                "longitude": s.longitude,
                "current": "temperature_2m,weather_code,relative_humidity_2m",
                "hourly": "precipitation_probability",
                "forecast_days": 1,
                "timezone": s.timezone,
            },
        ).json()
        try:
            a = http.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={"latitude": s.latitude, "longitude": s.longitude, "current": "us_aqi", "timezone": s.timezone},
            ).json()
            aqi = a.get("current", {}).get("us_aqi")
        except httpx.HTTPError:
            aqi = None

    cur = w.get("current", {})
    now = datetime.fromisoformat(cur.get("time")) if cur.get("time") else None
    rain_at = None
    hours = w.get("hourly", {})
    for t, p in zip(hours.get("time", []), hours.get("precipitation_probability", [])):
        when = datetime.fromisoformat(t)
        if now and when > now and (p or 0) >= 50:
            rain_at = clock(when, convert=False)  # Open-Meteo already gives local time
            break

    return {
        "city": s.city,
        "temp_c": round(cur.get("temperature_2m", 0)),
        "condition": CODES.get(cur.get("weather_code"), "—"),
        "humidity": cur.get("relative_humidity_2m"),
        "aqi": round(aqi) if aqi is not None else None,
        "aqi_label": aqi_label(aqi),
        "rain_at": rain_at,
    }
