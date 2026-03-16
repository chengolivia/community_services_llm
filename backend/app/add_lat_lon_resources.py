import os
import time
import json
import psycopg
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import openai

openai.api_key = os.environ.get("SECRET_KEY")
geolocator = Nominatim(user_agent="resource_populator")

EXTRACTION_PROMPT = """Extract location info from this resource description.
Return JSON only:
{{
  "address": "full street address or null",
  "city": "city name or null", 
  "zip": "zip code or null",
  "is_virtual": true/false  // true if online/statewide/hotline/no physical location
}}
Description: {}"""

def extract_location_with_gpt(description: str) -> dict:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(description)}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)

def geocode_address(address: str, city: str, zip_code: str,org: str) -> tuple[float, float]:
    attempts = []

    if org == 'cspnj':
        default_loc = 'NJ'
    elif org == 'georgia':
        default_loc = 'GA'
    elif org == 'clhs':
        default_loc = 'PA'
    else:
        default_loc = ''

    if address and city:
        attempts.append(f"{address}, {city}, {default_loc}, USA")
    if zip_code:
        attempts.append(f"{zip_code}, {default_loc}, USA")
    if city:
        attempts.append(f"{city}, {default_loc}, USA")
    
    for attempt in attempts:
        try:
            time.sleep(1.1)
            result = geolocator.geocode(attempt, timeout=10)
            if result:
                return result.latitude, result.longitude
        except GeocoderTimedOut:
            continue
    
    return None, None

def populate_coordinates():
    conn = psycopg.connect(os.getenv("RESOURCE_DB_URL"))
    cur = conn.cursor()

    cur.execute("""
        SELECT id, description, organization
        FROM resources 
        WHERE ID >= 6371
        ORDER BY ID
    """)
    resources = cur.fetchall()
    print(f"Processing {len(resources)} resources...\n")

    success, marked_virtual, failed_gpt = 0, 0, 0

    for i, (resource_id, description,org) in enumerate(resources):
        print(f"[{i+1}/{len(resources)}] ID: {resource_id}")
        print(f"  Description: {description[:120]}...")

        # GPT extraction — if this fails, mark virtual
        try:
            extracted = extract_location_with_gpt(description)
        except Exception as e:
            print(f"  GPT FAILED: {e} -> marking virtual")
            cur.execute("UPDATE resources SET is_virtual = TRUE WHERE id = %s", (resource_id,))
            failed_gpt += 1
            continue

        is_virtual = extracted.get("is_virtual", False)

        if is_virtual:
            print(f"  -> GPT says virtual, updating flag")
            cur.execute("UPDATE resources SET is_virtual = TRUE WHERE id = %s", (resource_id,))
            marked_virtual += 1
            continue

        # Geocode — if this fails, mark virtual
        lat, lon = geocode_address(
            extracted.get("address"),
            extracted.get("city"),
            extracted.get("zip"),
            org, 
        )

        if lat and lon:
            print(f"  -> GEOCODED: ({lat:.5f}, {lon:.5f})")
            cur.execute(
                "UPDATE resources SET latitude = %s, longitude = %s WHERE id = %s",
                (lat, lon, resource_id)
            )
            success += 1
        else:
            print(f"  -> GEOCODING FAILED -> marking virtual")
            cur.execute("UPDATE resources SET is_virtual = TRUE WHERE id = %s", (resource_id,))
            marked_virtual += 1

        # Commit every 50 records
        if (i + 1) % 50 == 0:
            conn.commit()
            print(f"  [Committed at {i+1}]")

        print()

    conn.commit()
    cur.close()
    conn.close()

    print("=== SUMMARY ===")
    print(f"  Geocoded successfully : {success}")
    print(f"  Marked virtual        : {marked_virtual}")
    print(f"  GPT failures          : {failed_gpt}")
    print(f"  Total                 : {len(resources)}")

if __name__ == "__main__":
    populate_coordinates()