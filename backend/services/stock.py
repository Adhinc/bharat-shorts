"""
AI Stock Integration Service for Bharat Shorts

India-focused stock footage search across multiple providers.

Features:
- Pexels + Pixabay dual-provider search with fallback
- India-specific keyword enhancement (auto-adds "India" context)
- Curated Indian stock categories (cities, food, festivals, culture, nature)
- Smart keyword→Indian-context mapping
- Category-based browsing for quick B-Roll selection
- Portrait/landscape/square orientation support
"""

import os
import re
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ─── API Keys ─────────────────────────────────────────────────────────────

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "YOUR_PEXELS_API_KEY_HERE")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "YOUR_PIXABAY_API_KEY_HERE")

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"
PIXABAY_VIDEO_URL = "https://pixabay.com/api/videos/"
PIXABAY_PHOTO_URL = "https://pixabay.com/api/"

# ─── India-Specific Keyword Mapping ──────────────────────────────────────
# Maps generic keywords to India-specific search queries for better results

INDIA_KEYWORD_MAP = {
    # Cities & Landmarks
    "city": "India city skyline Mumbai Delhi",
    "building": "Indian architecture building",
    "skyline": "Mumbai skyline night",
    "street": "Indian street market bazaar",
    "traffic": "India traffic auto rickshaw",
    "road": "Indian highway road",
    "bridge": "India bridge infrastructure",
    "airport": "India airport terminal",
    "train": "Indian railway train station",
    "station": "India railway station crowd",

    # Food & Cuisine
    "food": "Indian street food thali",
    "cooking": "Indian cooking kitchen masala",
    "restaurant": "Indian restaurant dhaba",
    "eat": "Indian food eating",
    "meal": "Indian thali meal",
    "spice": "Indian spices market colorful",
    "tea": "Indian chai tea stall",
    "coffee": "Indian filter coffee",
    "sweet": "Indian mithai sweets",
    "fruit": "Indian fruit market vendor",

    # Culture & Festivals
    "festival": "Indian festival celebration Diwali",
    "dance": "Indian classical dance Bharatanatyam",
    "music": "Indian music instrument sitar tabla",
    "temple": "Indian temple Hindu",
    "prayer": "Indian prayer puja worship",
    "wedding": "Indian wedding ceremony",
    "celebration": "Indian celebration festival colors",
    "tradition": "Indian tradition culture",
    "art": "Indian art rangoli painting",
    "craft": "Indian handicraft artisan",

    # Nature & Geography
    "nature": "India nature landscape",
    "mountain": "Himalayas mountain India",
    "river": "Ganges river India holy",
    "beach": "Goa beach India sunset",
    "forest": "Indian forest jungle wildlife",
    "farm": "Indian agriculture farm field",
    "garden": "Indian garden Mughal",
    "sunset": "India sunset landscape",
    "rain": "India monsoon rain",
    "flower": "Indian marigold flower garland",

    # People & Lifestyle
    "people": "Indian people diverse",
    "crowd": "India crowd gathering",
    "woman": "Indian woman traditional",
    "man": "Indian man portrait",
    "child": "Indian children playing",
    "family": "Indian family together",
    "work": "Indian office workplace",
    "school": "Indian school students",
    "shop": "Indian shop market vendor",
    "yoga": "yoga India sunrise meditation",

    # Technology & Business
    "technology": "India technology startup",
    "phone": "Indian person smartphone",
    "computer": "Indian office computer work",
    "business": "Indian business meeting",
    "startup": "India startup office Bangalore",
    "money": "Indian rupee currency",
    "market": "Indian stock market trading",

    # Sports & Entertainment
    "sport": "cricket India stadium",
    "cricket": "Indian cricket match",
    "game": "Indian children game kabaddi",
    "movie": "Bollywood Indian cinema",
    "bollywood": "Bollywood Indian film dance",

    # Generic enhancers (Hinglish keywords)
    "desh": "India patriotic flag",
    "bharat": "India bharat culture",
    "ghar": "Indian home house traditional",
    "paani": "India water river sacred",
    "gaadi": "India car auto rickshaw traffic",
    "bazaar": "Indian bazaar market colorful",
    "chai": "Indian chai tea stall morning",
    "namaste": "India namaste greeting culture",
}

# ─── Curated Indian Stock Categories ─────────────────────────────────────

INDIAN_CATEGORIES = {
    "mumbai": {
        "name": "Mumbai",
        "queries": ["Mumbai skyline", "Mumbai street market", "Gateway of India", "Mumbai local train", "Marine Drive night"],
        "icon": "🏙️",
    },
    "delhi": {
        "name": "Delhi",
        "queries": ["Delhi India Gate", "Red Fort Delhi", "Delhi street food", "Chandni Chowk market", "Lotus Temple Delhi"],
        "icon": "🕌",
    },
    "bangalore": {
        "name": "Bangalore",
        "queries": ["Bangalore tech park", "Bangalore garden city", "Bangalore traffic", "Cubbon Park Bangalore"],
        "icon": "💻",
    },
    "jaipur": {
        "name": "Jaipur",
        "queries": ["Jaipur pink city", "Hawa Mahal Jaipur", "Jaipur palace", "Rajasthan desert"],
        "icon": "🏰",
    },
    "varanasi": {
        "name": "Varanasi",
        "queries": ["Varanasi Ganges ghats", "Varanasi aarti ceremony", "Varanasi boat river", "Varanasi temple"],
        "icon": "🛕",
    },
    "kerala": {
        "name": "Kerala",
        "queries": ["Kerala backwaters", "Kerala houseboat", "Kerala tea plantation", "Kerala beach sunset"],
        "icon": "🌴",
    },
    "street_food": {
        "name": "Street Food",
        "queries": ["Indian street food vendor", "pani puri chaat", "Indian chai stall", "samosa frying", "Indian thali plate"],
        "icon": "🍛",
    },
    "festivals": {
        "name": "Festivals",
        "queries": ["Diwali festival lights", "Holi colors celebration", "Durga Puja pandal", "Ganesh Chaturthi procession", "Indian wedding ceremony"],
        "icon": "🎉",
    },
    "nature_india": {
        "name": "Indian Nature",
        "queries": ["Himalayas sunrise", "Goa beach sunset", "Indian monsoon rain", "tea garden Darjeeling", "Indian tiger wildlife"],
        "icon": "🏔️",
    },
    "daily_life": {
        "name": "Daily Life",
        "queries": ["Indian morning routine", "Indian market shopping", "auto rickshaw ride", "Indian office workers", "Indian school children"],
        "icon": "🚶",
    },
    "business_india": {
        "name": "Business & Tech",
        "queries": ["India tech startup office", "Indian business meeting", "Indian coding developer", "Bangalore IT park", "Indian rupee money"],
        "icon": "📈",
    },
    "spirituality": {
        "name": "Spirituality",
        "queries": ["yoga meditation India", "temple bells morning", "incense prayer India", "Ganges holy river", "Buddhist monastery India"],
        "icon": "🧘",
    },
}


# ─── Provider: Pexels ────────────────────────────────────────────────────

def search_pexels(
    query: str,
    media_type: str = "video",
    per_page: int = 6,
    orientation: str = "portrait",
) -> list[dict]:
    """Search Pexels for videos or photos."""
    url = PEXELS_VIDEO_URL if media_type == "video" else PEXELS_PHOTO_URL
    headers = {"Authorization": PEXELS_API_KEY}
    params: dict[str, Any] = {
        "query": query,
        "per_page": min(per_page, 80),
        "orientation": orientation,
    }

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=15.0)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning(f"Pexels search failed: {e}")
        return []

    data = resp.json()
    results = []

    if media_type == "video":
        for video in data.get("videos", []):
            video_files = [
                {
                    "link": vf.get("link"),
                    "width": vf.get("width"),
                    "height": vf.get("height"),
                    "quality": vf.get("quality"),
                }
                for vf in video.get("video_files", [])
                if vf.get("link")
            ]
            results.append({
                "id": f"pexels_{video.get('id')}",
                "provider": "pexels",
                "url": video.get("url"),
                "thumbnail": video.get("image"),
                "duration": video.get("duration"),
                "video_files": video_files,
            })
    else:
        for photo in data.get("photos", []):
            results.append({
                "id": f"pexels_{photo.get('id')}",
                "provider": "pexels",
                "url": photo.get("url"),
                "thumbnail": photo.get("src", {}).get("medium"),
                "original": photo.get("src", {}).get("original"),
                "width": photo.get("width"),
                "height": photo.get("height"),
            })

    return results


# ─── Provider: Pixabay ───────────────────────────────────────────────────

def search_pixabay(
    query: str,
    media_type: str = "video",
    per_page: int = 6,
    orientation: str = "vertical",
) -> list[dict]:
    """Search Pixabay for videos or photos."""
    # Map orientation names
    pixabay_orientation = {
        "portrait": "vertical",
        "landscape": "horizontal",
        "square": "all",
    }.get(orientation, orientation)

    url = PIXABAY_VIDEO_URL if media_type == "video" else PIXABAY_PHOTO_URL
    params: dict[str, Any] = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "per_page": min(per_page, 200),
        "orientation": pixabay_orientation,
        "safesearch": "true",
    }

    try:
        resp = httpx.get(url, params=params, timeout=15.0)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning(f"Pixabay search failed: {e}")
        return []

    data = resp.json()
    results = []

    if media_type == "video":
        for hit in data.get("hits", []):
            videos = hit.get("videos", {})
            video_files = []
            for quality_key in ("large", "medium", "small", "tiny"):
                vf = videos.get(quality_key, {})
                if vf.get("url"):
                    video_files.append({
                        "link": vf["url"],
                        "width": vf.get("width", 0),
                        "height": vf.get("height", 0),
                        "quality": quality_key,
                    })
            results.append({
                "id": f"pixabay_{hit.get('id')}",
                "provider": "pixabay",
                "url": hit.get("pageURL"),
                "thumbnail": f"https://i.vimeocdn.com/video/{hit.get('picture_id')}_295x166.jpg" if hit.get("picture_id") else None,
                "duration": hit.get("duration"),
                "video_files": video_files,
            })
    else:
        for hit in data.get("hits", []):
            results.append({
                "id": f"pixabay_{hit.get('id')}",
                "provider": "pixabay",
                "url": hit.get("pageURL"),
                "thumbnail": hit.get("webformatURL"),
                "original": hit.get("largeImageURL"),
                "width": hit.get("imageWidth"),
                "height": hit.get("imageHeight"),
            })

    return results


# ─── Unified Multi-Provider Search ───────────────────────────────────────

def enhance_query_for_india(query: str) -> str:
    """Enhance a generic query with India-specific context."""
    lower = query.lower().strip()

    # Check if already India-specific
    india_terms = {"india", "indian", "mumbai", "delhi", "bangalore", "hindu", "bollywood",
                   "himalaya", "ganges", "rajasthan", "kerala", "goa", "tamil", "punjab"}
    words = set(lower.split())
    if words & india_terms:
        return query  # Already India-specific

    # Check keyword map
    for key, mapped in INDIA_KEYWORD_MAP.items():
        if key in lower:
            return mapped

    # Default: append "India" for context
    return f"{query} India"


def search_stock(
    query: str,
    media_type: str = "video",
    per_page: int = 8,
    orientation: str = "portrait",
    india_focus: bool = True,
    providers: list[str] | None = None,
) -> dict:
    """
    Search multiple stock providers with optional India-focus.

    Args:
        query: Search term
        media_type: "video" or "photo"
        per_page: Results per provider
        orientation: "portrait", "landscape", "square"
        india_focus: Auto-enhance query for Indian content
        providers: List of providers to use (default: ["pexels", "pixabay"])

    Returns:
        {
            "query": "enhanced query",
            "original_query": "original query",
            "results": [...],
            "total": 12,
            "providers_used": ["pexels", "pixabay"],
        }
    """
    providers = providers or ["pexels", "pixabay"]
    enhanced_query = enhance_query_for_india(query) if india_focus else query

    all_results = []
    providers_used = []

    if "pexels" in providers:
        pexels_results = search_pexels(enhanced_query, media_type, per_page, orientation)
        if pexels_results:
            all_results.extend(pexels_results)
            providers_used.append("pexels")

    if "pixabay" in providers:
        pixabay_results = search_pixabay(enhanced_query, media_type, per_page, orientation)
        if pixabay_results:
            all_results.extend(pixabay_results)
            providers_used.append("pixabay")

    # If India-focused search returned nothing, try original query
    if not all_results and india_focus and enhanced_query != query:
        logger.info(f"India-enhanced search empty, trying original: {query}")
        if "pexels" in providers:
            pexels_results = search_pexels(query, media_type, per_page, orientation)
            all_results.extend(pexels_results)
        if "pixabay" in providers:
            pixabay_results = search_pixabay(query, media_type, per_page, orientation)
            all_results.extend(pixabay_results)

    return {
        "query": enhanced_query,
        "original_query": query,
        "results": all_results,
        "total": len(all_results),
        "providers_used": providers_used,
    }


def browse_category(
    category_id: str,
    media_type: str = "video",
    per_page: int = 6,
    orientation: str = "portrait",
) -> dict:
    """
    Browse a curated Indian stock category.

    Returns results from multiple queries within the category.
    """
    if category_id not in INDIAN_CATEGORIES:
        return {"error": f"Unknown category: {category_id}", "results": [], "total": 0}

    category = INDIAN_CATEGORIES[category_id]
    all_results = []

    for q in category["queries"]:
        result = search_stock(q, media_type, per_page=per_page, orientation=orientation, india_focus=False)
        all_results.extend(result["results"])

    return {
        "category_id": category_id,
        "category_name": category["name"],
        "icon": category["icon"],
        "results": all_results,
        "total": len(all_results),
    }


def list_categories() -> list[dict]:
    """List all available Indian stock categories."""
    return [
        {
            "id": cat_id,
            "name": cat["name"],
            "icon": cat["icon"],
            "query_count": len(cat["queries"]),
        }
        for cat_id, cat in INDIAN_CATEGORIES.items()
    ]


def match_segments_to_indian_stock(
    segments: list[dict],
    keywords_per_segment: int = 2,
    per_keyword: int = 3,
    orientation: str = "portrait",
) -> list[dict]:
    """
    Enhanced B-Roll matching with India-focused stock search.

    Like broll.match_broll_to_segments but uses multi-provider search
    with India keyword enhancement.
    """
    from services.broll import extract_keywords

    suggestions = []
    seen_keywords: set[str] = set()

    for seg in segments:
        text = seg.get("text", "")
        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)

        keywords = extract_keywords(text, max_keywords=keywords_per_segment)

        for kw in keywords:
            if kw in seen_keywords:
                continue
            seen_keywords.add(kw)

            result = search_stock(
                kw,
                media_type="video",
                per_page=per_keyword,
                orientation=orientation,
                india_focus=True,
            )

            suggestions.append({
                "keyword": kw,
                "enhanced_query": result["query"],
                "start_time": round(start, 3),
                "end_time": round(end, 3),
                "videos": result["results"],
                "providers": result["providers_used"],
            })

    return suggestions
