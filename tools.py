"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client() -> Groq:
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _call_groq(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except ValueError:
        raise
    except Exception as exc:
        error_text = str(exc).lower()
        if "invalid_api_key" in error_text or "invalid api key" in error_text:
            raise ValueError(
                "Invalid GROQ_API_KEY. Update your .env file with a valid key from console.groq.com."
            ) from exc
        raise


def _format_listing(item: dict) -> str:
    brand = item.get("brand") or "unbranded"
    return (
        f"Title: {item.get('title', 'Unknown')}\n"
        f"Category: {item.get('category', '')}\n"
        f"Price: ${item.get('price', '')}\n"
        f"Size: {item.get('size', '')}\n"
        f"Condition: {item.get('condition', '')}\n"
        f"Colors: {', '.join(item.get('colors', []))}\n"
        f"Style tags: {', '.join(item.get('style_tags', []))}\n"
        f"Brand: {brand}\n"
        f"Platform: {item.get('platform', '')}\n"
        f"Description: {item.get('description', '')}"
    )


def _format_wardrobe(wardrobe: dict) -> str:
    items = wardrobe.get("items", [])
    if not items:
        return "(empty wardrobe)"

    lines = []
    for item in items:
        lines.append(
            f"- {item['name']} [{item['category']}]: "
            f"colors={', '.join(item.get('colors', []))}, "
            f"styles={', '.join(item.get('style_tags', []))}"
            + (f", notes={item['notes']}" if item.get("notes") else "")
        )
    return "\n".join(lines)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

_STOP_WORDS = {
    "a", "an", "the", "for", "and", "or", "i", "my", "some", "with", "in", "on",
    "to", "of", "is", "it", "that", "this", "looking", "want", "need",
}


def _extract_keywords(description: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", description.lower())
    return [word for word in words if len(word) > 1 and word not in _STOP_WORDS]


def _matches_size(listing_size: str, filter_size: str) -> bool:
    listing_size_lower = listing_size.lower()
    filter_size_lower = filter_size.lower()
    return (
        filter_size_lower in listing_size_lower
        or listing_size_lower in filter_size_lower
    )


def _score_listing(listing: dict, keywords: list[str]) -> int:
    searchable = " ".join(
        [
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            " ".join(listing.get("style_tags", [])),
        ]
    ).lower()

    return sum(1 for keyword in keywords if keyword in searchable)


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    """
    keywords = _extract_keywords(description)
    if not keywords:
        return []

    scored: list[tuple[int, dict]] = []

    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue

        if size is not None and not _matches_size(listing["size"], size):
            continue

        score = _score_listing(listing, keywords)
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [listing for _, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    """
    item_text = _format_listing(new_item)
    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        system_prompt = (
            "You are a fashion stylist. The user has no saved wardrobe items yet. "
            "Give general styling advice for the thrift find: what categories pair well, "
            "what vibe it suits, and 1–2 example outfit directions. "
            "Do not invent specific named pieces from a wardrobe. Keep it concise and practical."
        )
        user_prompt = f"Thrift find:\n{item_text}"
    else:
        system_prompt = (
            "You are a fashion stylist. Suggest 1–2 complete outfits using the thrift find "
            "plus ONLY items from the user's wardrobe list. Do not invent clothing. "
            "Name wardrobe pieces explicitly, explain why the combo works, and keep colors/styles cohesive."
        )
        user_prompt = (
            f"Thrift find:\n{item_text}\n\n"
            f"Wardrobe:\n{_format_wardrobe(wardrobe)}"
        )

    suggestion = _call_groq(system_prompt, user_prompt, temperature=0.7)
    if not suggestion.strip():
        return (
            "Couldn't generate outfit ideas right now. Try again, or search for a "
            "different item with clearer style keywords."
        )
    return suggestion.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    """
    if not outfit or not outfit.strip():
        return (
            "Can't create a fit card without an outfit suggestion. "
            "Style the find first, then try generating the fit card again."
        )

    item_text = _format_listing(new_item)
    system_prompt = (
        "Write a casual Instagram/TikTok outfit caption (2–4 sentences). "
        "Sound like a real OOTD post, not a product listing. "
        "Mention the item title, price, and platform once each in a natural way. "
        "Capture the outfit vibe with specific details. Use lowercase, relaxed tone."
    )
    user_prompt = (
        f"Thrift find:\n{item_text}\n\n"
        f"Outfit suggestion:\n{outfit.strip()}"
    )

    caption = _call_groq(system_prompt, user_prompt, temperature=0.95)
    if not caption.strip():
        return (
            "Fit card generation failed. The outfit suggestion is saved — "
            "try generating the fit card again."
        )
    return caption.strip()
