from ddgs import DDGS
import googlemaps
import os 
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

geolocator = Nominatim(user_agent="peercopilot_app")
google_maps_api = os.getenv("GOOGLE_API_KEY")
gmaps = googlemaps.Client(key=google_maps_api)

_GEOCODE_CACHE = {}

def geocode_location(location: str):
    """
    Geocode a location using free Nominatim service.
    
    Args:
        location: City, zip code, or address
        
    Returns:
        (latitude, longitude) or (None, None)
    """
    if not location:
        return None, None
    
    cache_key = location.lower().strip()
    if cache_key in _GEOCODE_CACHE:
        cached = _GEOCODE_CACHE[cache_key]
        return cached['lat'], cached['lng']
    
    try:
        # Add NJ context if just a city/zip
        search_term = location
        if not any(state in location.lower() for state in ['nj', 'new jersey']):
            search_term = f"{location}, New Jersey, USA"
        
        # Respect Nominatim's 1 req/sec limit
        time.sleep(1)
        
        result = geolocator.geocode(search_term, timeout=10)
        
        if result:
            _GEOCODE_CACHE[cache_key] = {'lat': result.latitude, 'lng': result.longitude}
            return result.latitude, result.longitude
        
    except GeocoderTimedOut:
        print(f"[Geocoding Timeout] {location}")
    except Exception as e:
        print(f"[Geocoding Error] {location}: {e}")
    
    return None, None

def calculate_geographic_score(user_lat, user_lon, resource_lat, resource_lon, 
                               is_virtual=False, max_distance_km=50):
    """
    Calculate geographic proximity score (0-1, higher is closer).
    
    Args:
        user_lat, user_lon: User's location
        resource_lat, resource_lon: Resource location
        is_virtual: If True, resource is available anywhere
        max_distance_km: Maximum distance to consider
        
    Returns:
        Score from 0-1
    """
    # Virtual resources are "everywhere"
    if is_virtual:
        return 1.0
    
    # No location data - neutral score
    if resource_lat is None or resource_lon is None:
        return 0.5
    
    try:
        distance = geodesic(
            (user_lat, user_lon),
            (resource_lat, resource_lon)
        ).kilometers
        
        # Normalize to 0-1 (closer = higher score)
        score = max(0, 1 - (distance / max_distance_km))
        return score
    except:
        return 0.5

def query_resources_geo_aware(
    query: str,
    org_key: str,
    location: str = None,
    k: int = 5,
    saved_indices={},
    documents={},
    metadata={},
    embedding_model=None,
    semantic_weight=0.85,
    geographic_weight=0.15
):
    """
    Geographic-aware resource search combining semantic + location similarity.
    
    Args:
        query: What to search for (e.g., "food banks")
        org_key: Organization ID
        location: Where to search (city, zip, address) - optional
        k: Number of results
        semantic_weight: Weight for semantic similarity (default 0.85)
        geographic_weight: Weight for geographic proximity (default 0.15)
    """
    doc_key = f'resource_{org_key}'
    
    if doc_key not in saved_indices:
        print(f"[Warning] No resources loaded for {org_key}")
        return []
    
    # 1. Get semantic scores from FAISS
    query_emb = embedding_model.encode(query, convert_to_numpy=True).reshape(1, -1)
    D, I = saved_indices[doc_key].search(query_emb, k=k*3)  # Get extra candidates
    
    # 2. Geocode location if provided
    user_lat, user_lon = None, None
    if location:
        user_lat, user_lon = geocode_location(location)
        if user_lat is None:
            print(f"[Warning] Could not geocode location: {location}")
    
    # 3. Combine scores
    results = []
    for semantic_distance, idx in zip(D[0], I[0]):
        if idx >= len(documents[doc_key]):
            continue
        
        # Convert FAISS distance to similarity score
        semantic_score = 1 / (1 + semantic_distance)
        
        meta = metadata[doc_key][idx]
        
        # Calculate geographic score
        if user_lat and user_lon:
            geo_score = calculate_geographic_score(
                user_lat, user_lon,
                meta.get('latitude'),
                meta.get('longitude'),
                is_virtual=meta.get('is_virtual', False)
            )
        else:
            # No location in query - virtual resources get slight boost
            geo_score = 1.0 if meta.get('is_virtual') else 0.5
        
        # Hybrid final score
        final_score = (semantic_weight * semantic_score) + (geographic_weight * geo_score)
        
        # Calculate distance (None for virtual resources)
        distance_km = None
        if user_lat and not meta.get('is_virtual'):
            if meta.get('latitude') and meta.get('longitude'):
                try:
                    distance_km = geodesic(
                        (user_lat, user_lon),
                        (meta.get('latitude'), meta.get('longitude'))
                    ).kilometers
                except:
                    pass
        
        results.append({
            "resource_text": documents[doc_key][idx],
            "metadata": meta,
            "semantic_score": float(semantic_score),
            "geographic_score": float(geo_score),
            "final_score": float(final_score),
            "distance_km": distance_km,
            "is_virtual": meta.get('is_virtual', False)
        })
    
    # Sort by final score
    results.sort(key=lambda x: x['final_score'], reverse=True)
    return results[:k]

def resources_tool(query: str, organization: str, location: str = None, k: int = 5,
                   saved_indices={}, documents={}, metadata={}, embedding_model=None):
    """
    Search for community resources with optional geographic filtering.
    
    Args:
        query: What to search for (e.g., "food banks", "legal aid")
        organization: Organization ID (e.g., "cspnj")
        location: Where to search near (city, zip code, address) - optional
        k: Number of results to return
    
    Returns:
        Formatted string with top resources
    """
    top_resources = query_resources_geo_aware(
        query=query,
        org_key=organization.lower(),
        location=location,
        k=k,
        saved_indices=saved_indices,
        documents=documents,
        metadata=metadata,
        embedding_model=embedding_model
    )
    
    if not top_resources:
        return "No relevant resources found."
    
    lines = []
    for r in top_resources:
        # Different display for virtual vs physical resources
        if r['is_virtual']:
            availability = " [Available Statewide/Online]"
        elif r['distance_km'] is not None:
            availability = f" [{r['distance_km']:.1f}km away]"
        else:
            availability = ""
        
        lines.append(f"- {r['resource_text']}{availability}")
    
    return "\n".join(lines)

def library_tool(query: str, category: str, k: int = 3,saved_indices_peer={},documents_peer={},embedding_model=None):
    """
    Searches specialized document libraries (e.g., 'trans', 'crisis', 'legal').
    """
    doc_key = f"cat_{category.lower()}"
    
    if doc_key not in saved_indices_peer:
        return f"Error: The category '{category}' does not exist. Available: trans, crisis, housing."
    
    # Standard FAISS search (same logic as your query_resources)
    query_emb = embedding_model.encode(query, convert_to_numpy=True).reshape(1, -1)
    D, I = saved_indices_peer[doc_key].search(query_emb, k=k)
    
    results = [documents_peer[doc_key][idx] for idx in I[0] if idx < len(documents_peer[doc_key])]
    
    if not results:
        return "No specific documents found for that query."
        
    return "\n---\n".join(results)

def directions_tool(origin: str, destination: str, mode: str = "driving"):
    """
    Get detailed, step-by-step navigation instructions.
    """
    try:
        result = gmaps.directions(origin, destination, mode=mode, departure_time="now")
        if not result:
            return "No routes found."
        leg = result[0]['legs'][0]
        full_instructions = [f"Total Trip: {leg['duration']['text']} ({leg['distance']['text']})\n"]
        for i, step in enumerate(leg['steps'], 1):
            # Clean up HTML tags (like <b>) that Google returns
            import re
            instruction = re.sub('<[^<]+?>', '', step['html_instructions'])
            duration = step['duration']['text']
            # Add specific transit details if they exist
            if step.get('travel_mode') == 'TRANSIT':
                details = step.get('transit_details', {})
                line = details.get('line', {}).get('short_name', 'Transit')
                stop = details.get('arrival_stop', {}).get('name', 'destination')
                instruction += f" (Take {line} to {stop})"
            full_instructions.append(f"{i}. {instruction} [{duration}]")
        return "\n".join(full_instructions)
    except Exception as e:
        return f"Error: {str(e)}"

def check_eligibility(program: str, household_size: int, monthly_income: float):
    """
    Checks eligibility based on official 2026 NJ income limits.
    """
    program = program.lower()
    
    # 2026 NJ SNAP Gross Income Limits (185% Federal Poverty Level)
    # Source: NJ Dept of Human Services / USDA
    snap_limits = {
        1: 2413,
        2: 3261,
        3: 4109,
        4: 4957,
        5: 5805,
        6: 6653,
        7: 7501,
        8: 8349
    }
    
    if "snap" in program or "food stamp" in program:
        # Get limit (add $848 for each person beyond 8)
        if household_size <= 8:
            limit = snap_limits.get(household_size)
        else:
            limit = 8349 + (848 * (household_size - 8))
            
        if monthly_income <= limit:
            return f"✅ LIKELY ELIGIBLE. Household income (${monthly_income}) is BELOW the NJ SNAP gross limit (${limit}) for {household_size} people."
        else:
            return f"❌ LIKELY INELIGIBLE. Household income (${monthly_income}) is ABOVE the NJ SNAP gross limit (${limit})."

    return "Error: Unknown benefit program. Currently supporting: SNAP."


def web_search_tool(query: str, max_results: int = 4):
    """
    Performs a live web search using Brave Search API.
    """

    try:
        # Get API key from environment variable
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return "Error: BRAVE_API_KEY environment variable not set"
        
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
        
        params = {
            "q": query,
            "count": max_results,
            "safesearch": "moderate"  # Options: off, moderate, strict
        }
        
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we got results
        results = data.get("web", {}).get("results", [])
        if not results:
            return "No results found."
        
        # Format results nicely for the LLM
        formatted = f"Search results for: {query}\n\n"
        for i, r in enumerate(results[:max_results], 1):
            formatted += f"{i}. {r['title']}\n"
            formatted += f"   URL: {r['url']}\n"
            formatted += f"   {r.get('description', '')}\n"
        
        return formatted
        
    except requests.exceptions.RequestException as e:
        return f"Search failed: {str(e)}"
    except Exception as e:
        return f"Search failed: {str(e)}"

def calculator_tool(expression: str):
    """
    A safe calculator for basic arithmetic. 
    Supports +, -, *, /, and round().
    """
    allowed_chars = "0123456789+-*/(). "
    if any(char not in allowed_chars for char in expression):
        return "Error: Invalid characters. Only numbers and basic math (+-*/) allowed."
    
    try:
        # Evaluate using a restricted scope to prevent code injection
        # (For production, consider libraries like 'simpleeval')
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"
