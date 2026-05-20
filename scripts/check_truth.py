import json

with open("cache/screenings.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for s in data:
    if "truth" in s.get("movie_title", "").lower():
        print(f"Title: {s.get('movie_title')}")
        print(f"Year: {s.get('year')}")
        print(f"TMDB: {s.get('tmdb_url')}")
