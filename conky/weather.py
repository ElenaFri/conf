#!/usr/bin/env python3
"""
Script météo pour Conky — source : wttr.in (géolocalisation IP auto)
Mise en cache 30 minutes pour éviter les requêtes excessives.
Pour forcer une ville : modifier CITY ci-dessous (ex. "Paris", "Lyon").
"""

import json
import os
import time
import urllib.request

CITY       = "Strasbourg"  # vide = détection automatique par IP
CACHE_FILE = "/tmp/conky_weather_cache"
CACHE_TTL  = 1800        # secondes (30 min)

DIR_FR = {
    "N":   "Nord",
    "NNE": "Nord-Nord-Est",
    "NE":  "Nord-Est",
    "ENE": "Est-Nord-Est",
    "E":   "Est",
    "ESE": "Est-Sud-Est",
    "SE":  "Sud-Est",
    "SSE": "Sud-Sud-Est",
    "S":   "Sud",
    "SSW": "Sud-Sud-Ouest",
    "SW":  "Sud-Ouest",
    "WSW": "Ouest-Sud-Ouest",
    "W":   "Ouest",
    "WNW": "Ouest-Nord-Ouest",
    "NW":  "Nord-Ouest",
    "NNW": "Nord-Nord-Ouest",
}

DAY_FR = {
    "Monday": "Lundi",  "Tuesday": "Mardi",  "Wednesday": "Mercredi",
    "Thursday": "Jeudi","Friday": "Vendredi","Saturday": "Samedi",
    "Sunday": "Dimanche",
}

def cache_fresh():
    if not os.path.exists(CACHE_FILE):
        return False
    return (time.time() - os.path.getmtime(CACHE_FILE)) < CACHE_TTL

def fetch():
    loc = CITY if CITY else ""
    url = f"https://wttr.in/{loc}?lang=fr&format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.81.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def day_name(date_str):
    """Retourne le nom du jour en français à partir de 'YYYY-MM-DD'."""
    import datetime
    d = datetime.date.fromisoformat(date_str)
    en = d.strftime("%A")
    return DAY_FR.get(en, en)

def format_data(data):
    cc   = data["current_condition"][0]
    desc = cc.get("lang_fr", [{"value": "N/A"}])[0]["value"]
    temp = cc["temp_C"]
    feels= cc["FeelsLikeC"]
    hum  = cc["humidity"]
    wind = cc["windspeedKmph"]
    wdir = DIR_FR.get(cc.get("winddir16Point", ""), cc.get("winddir16Point", ""))
    pres_hpa = int(cc.get("pressure", 0))
    pres_mmhg = round(pres_hpa * 0.750062)

    try:
        area    = data["nearest_area"][0]
        city    = area.get("areaName", [{"value": ""}])[0]["value"]
        country = area.get("country", [{"value": ""}])[0]["value"]
        loc_str = f"{city}, {country}" if city else "Position auto"
    except Exception:
        loc_str = "Position auto"

    lines = [
        f"  {loc_str}",
        f"  {desc}",
        f"  Temp      {temp}°C  (ressenti {feels}°C)",
        f"  Humidite  {hum}%    Pression {pres_mmhg} mmHg",
        f"  Vent      {wind} km/h  {wdir}",
        "",
        "  Previsions",
    ]

    today = None
    for i, day in enumerate(data.get("weather", [])[:3]):
        date_str = day.get("date", "")
        if i == 0:
            label = "Auj.  "
            today = date_str
        elif i == 1:
            label = "Dem.  "
        else:
            dname = day_name(date_str)[:4] + "."
            label = f"{dname:<6}"

        max_t = day.get("maxtempC", "?")
        min_t = day.get("mintempC", "?")
        # description du midi (index 4 = heure 12h)
        hourly = day.get("hourly", [])
        noon   = hourly[4] if len(hourly) > 4 else (hourly[-1] if hourly else {})
        d_fr   = noon.get("lang_fr", [{"value": "?"}])[0]["value"]
        lines.append(f"  {label}  {min_t}/{max_t}°C  {d_fr}")

    return "\n".join(lines)

def main():
    if cache_fresh():
        with open(CACHE_FILE) as f:
            print(f.read(), end="")
        return

    data = fetch()
    if data is None:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                print(f.read(), end="")
        else:
            print("  Météo indisponible\n  (pas de connexion)")
        return

    out = format_data(data)
    with open(CACHE_FILE, "w") as f:
        f.write(out)
    print(out, end="")

if __name__ == "__main__":
    main()
