
import streamlit as st
import datetime
import requests
import json
import difflib

st.set_page_config(page_title="MC1 Fishing Assistant", layout="centered")
st.title("🎣 MC1 AI Fishing Advisor")

username = st.text_input("👤 Your Username")

# Load district and location maps
with open("hk_districts.json", "r", encoding="utf-8") as f:
    HK_DISTRICTS = json.load(f)

with open("district_to_tide_station.json", "r", encoding="utf-8") as f:
    DISTRICT_TO_TIDE = json.load(f)

with open("district_to_temp_station.json", "r", encoding="utf-8") as f:
    DISTRICT_TO_TEMP = json.load(f)

district = st.selectbox("📍 請選擇你所在區域", sorted(HK_DISTRICTS.keys()))
spot = st.selectbox("🎣 請選擇具體釣魚地點", HK_DISTRICTS[district])

def recommend_score(rain_chance, tide_type, moon_phase):
    score = 50
    if rain_chance < 20:
        score += 20
    elif rain_chance > 50:
        score -= 30
    if tide_type == "High":
        score += 15
    if "滿月" in moon_phase or "上弦" in moon_phase:
        score += 10
    return max(0, min(score, 100))

def get_hko_weather():
    url = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

def get_tide_data(station_name):
    today = datetime.date.today()
    today_str = today.strftime("%Y%m%d")
    url = f"https://data.weather.gov.hk/weatherAPI/opendata/tideTimes.php?year={today.year}&lang=tc"
    try:
        r = requests.get(url)
        data = r.json().get("tide", [])
        def is_today(t):
            return t.get("year")+t.get("month").zfill(2)+t.get("day").zfill(2) == today_str
        tides = [t for t in data if station_name in t.get("place", "") and is_today(t)]
        return tides[:3] if tides else [t for t in data if station_name in t.get("place", "")][:3]
    except:
        return []

def get_moon_phase():
    today = datetime.date.today()
    diff = today - datetime.date(2001, 1, 1)
    lunations = 29.53058867
    index = (diff.days + 1) % lunations / lunations
    if index < 0.25:
        return "🌒 初月"
    elif index < 0.5:
        return "🌓 上弦"
    elif index < 0.75:
        return "🌔 盈凸月"
    else:
        return "🌕 滿月"

if username and spot:
    st.success(f"Welcome {username}! Checking info for {spot}...")

    weather = get_hko_weather()
    if not weather:
        st.error("Failed to fetch weather.")
    else:
        # 🌧️ Rainfall
        rainfall_data = weather.get("rainfall", [])
        rain_places = [r["place"]["tc"] for r in rainfall_data if isinstance(r, dict) and "place" in r and "tc" in r["place"]]
        rain = next((r["max"] for r in rainfall_data if r.get("place", {}).get("tc") == spot), 0)

        # 🌡️ Temperature
        temp_data = weather.get("temperature", {}).get("data", [])
        temp_spot = DISTRICT_TO_TEMP.get(district)
        temp_value = next(
            (t["value"] for t in temp_data
             if isinstance(t, dict)
             and "value" in t
             and isinstance(t.get("place"), dict)
             and t["place"].get("tc") == temp_spot),
            None
        )

        # 🌕 Moon phase
        moon = get_moon_phase()

        # 🌊 Tide info
        tide_station = DISTRICT_TO_TIDE.get(district, "尖沙咀")
        tides = get_tide_data(tide_station)

        st.markdown(f"### 🌤️ Weather Info ({spot})")
        st.write(f"🌡️ Temp in {temp_spot}: {temp_value}°C" if temp_value else "🌡️ Temperature data not found")
        st.write(f"🌧️ Rainfall: {rain} mm")

        st.markdown(f"### 🌕 Moon Phase")
        st.write(f"{moon}")

        st.markdown(f"### 🌊 Tide Info ({tide_station})")
        if tides:
            for t in tides:
                st.write(f"{t['eventType']} Tide at {t['eventTime']}")
        else:
            st.write("⚠️ No tide events found for today. Showing fallback to next available.")

        tide_type = tides[0]['eventType'] if tides else "Low"
        score = recommend_score(rain, tide_type, moon)
        advice = "🟢 Great time to fish!" if score > 75 else "🟡 Okay but watch conditions." if score > 50 else "🔴 Not recommended."

        st.markdown("### 🎣 AI Recommendation")
        st.metric("Score", score)
        st.write(advice)

        with st.expander("📓 Log your catch"):
            caught = st.text_input("Species caught (comma separated)")
            qty = st.number_input("Quantity", min_value=0, step=1)
            notes = st.text_area("Notes")
            if st.button("Save Log"):
                today = str(datetime.date.today())
                log = {
                    "spot": spot,
                    "species": caught.split(","),
                    "qty": qty,
                    "notes": notes
                }
                try:
                    with open("fishing_log.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                except:
                    data = {}
                if username not in data:
                    data[username] = {}
                data[username][today] = log
                with open("fishing_log.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                st.success("🎉 Log saved!")
