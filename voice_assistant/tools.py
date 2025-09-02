import os, requests
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

@dataclass
class ToolResult:
    ok: bool
    content: str

def calculate(expression: str) -> ToolResult:
    """
    Calculate expression:
    - If result is integer => output like "5"
    - Otherwise => round to 2 decimal places, like "14.38", "0.33"
    """
    try:
        from sympy import sympify, N
        val = N(sympify(expression))          # Calculate with Sympy
        f = float(val)                        # Convert to Python float

        # First check if it's "almost integer" (eliminate floating point tiny errors)
        if abs(f - round(f)) < 1e-12:
            s = str(int(round(f)))            # Pure integer output
            return ToolResult(True, s)

        # Otherwise round to 2 decimal places (HALF_UP)
        d = Decimal(str(f)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        s = f"{d:.2f}"
        if s == "-0.00":                      # Avoid -0.00
            s = "0.00"
        return ToolResult(True, s)
    except Exception as e:
        return ToolResult(False, f"Math calculation error: {e}")

# Simple WMO code descriptions (can be expanded as needed)
_WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "light rain", 63: "moderate rain", 65: "heavy rain",
    71: "light snow", 73: "moderate snow", 75: "heavy snow",
    80: "rain showers", 81: "heavy rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm w/ light hail", 99: "thunderstorm w/ heavy hail",
}

DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Toronto, ON")

def _geocode_city(name: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": name, "count": 1, "language": "en", "format": "json"}, timeout=8)
    r.raise_for_status()
    j = r.json()
    if not j.get("results"):
        return None
    it = j["results"][0]
    return {
        "name": it.get("name"),
        "country": it.get("country"),
        "lat": it["latitude"],
        "lon": it["longitude"],
    }

def get_weather(location: str = "") -> ToolResult:
    try:
        city = (location or DEFAULT_CITY).strip()
        geo = _geocode_city(city)
        if not geo:
            return ToolResult(False, f"Could not find location '{city}'. Please specify a city (e.g., 'weather in Toronto').")

        lat, lon = geo["lat"], geo["lon"]
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "temperature_unit": "celsius",
            "windspeed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",
        }
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        cur = r.json().get("current", {})
        t = cur.get("temperature_2m")
        feels = cur.get("apparent_temperature")
        wcode = cur.get("weather_code")
        wind = cur.get("wind_speed_10m")
        prcp = cur.get("precipitation")
        desc = _WMO.get(int(wcode) if wcode is not None else -1, "unknown")

        place = f"{geo['name']}, {geo.get('country','')}".strip().strip(",")
        text = f"{place}: {t}°C, feels like {feels}°C, {desc}, wind {wind} km/h, precip {prcp} mm (current)."
        return ToolResult(True, text)
    except Exception as e:
        return ToolResult(False, f"Weather error: {e}")

def search_arxiv(query: str) -> ToolResult:
    """
    Search arXiv papers:
    - Use arXiv API to search papers
    - Return titles, authors and summaries of top 5 relevant papers
    """
    try:
        import requests
        from urllib.parse import quote
        
        # Clean query terms
        query = query.strip()
        if not query:
            return ToolResult(False, "Please provide a search query for arXiv papers.")
        
        # arXiv API endpoint
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{quote(query)}",
            "start": 0,
            "max_results": 5,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse XML response
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # Extract paper information
        papers = []
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            title = entry.find(".//{http://www.w3.org/2005/Atom}title").text.strip()
            authors = [author.find(".//{http://www.w3.org/2005/Atom}name").text for author in entry.findall(".//{http://www.w3.org/2005/Atom}author")]
            summary = entry.find(".//{http://www.w3.org/2005/Atom}summary").text.strip()
            published = entry.find(".//{http://www.w3.org/2005/Atom}published").text[:10]  # Only take date part
            
            papers.append({
                "title": title,
                "authors": ", ".join(authors),
                "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                "published": published
            })
        
        if not papers:
            return ToolResult(False, f"No papers found for query: '{query}'")
        
        # Format output
        result = f"Found {len(papers)} papers for '{query}':\n\n"
        for i, paper in enumerate(papers, 1):
            result += f"{i}. {paper['title']}\n"
            result += f"   Authors: {paper['authors']}\n"
            result += f"   Published: {paper['published']}\n"
            result += f"   Summary: {paper['summary']}\n\n"
        
        return ToolResult(True, result.strip())
        
    except Exception as e:
        return ToolResult(False, f"arXiv search error: {e}")