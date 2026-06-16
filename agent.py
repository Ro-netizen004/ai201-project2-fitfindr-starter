"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from schemas.models import ParsedQuery
from tools import search_listings, suggest_outfit, create_fit_card
from utils.query_parsers import (
    extract_fit_preference,
    extract_item,
    extract_min_price,
    extract_occasion,
    extract_price,
    extract_size,
    extract_style_tags,
)


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one user interaction."""
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── query parsing ─────────────────────────────────────────────────────────────

def parse_query(query: str) -> ParsedQuery:
    return ParsedQuery(
        item_type=extract_item(query),
        max_price=extract_price(query),
        min_price=extract_min_price(query),
        size=extract_size(query),
        style_tags=extract_style_tags(query),
        occasion=extract_occasion(query),
        fit_preference=extract_fit_preference(query),
    )


def _no_results_message(parsed: ParsedQuery) -> str:
    message = f"No listings matched your search for '{parsed.item_type}'."
    filters: list[str] = []
    if parsed.size:
        filters.append(f"size {parsed.size}")
    if parsed.max_price is not None:
        filters.append(f"under ${parsed.max_price:g}")
    if filters:
        message += f" Active filters: {', '.join(filters)}."
    message += (
        " Try broadening your search — use fewer filters, raise your price limit, "
        "or try different keywords (e.g., 'vintage tee' instead of a specific brand)."
    )
    return message


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    session = _new_session(query, wardrobe)
    parsed = parse_query(query)
    session["parsed"] = parsed.model_dump()

    if not parsed.item_type.strip():
        session["error"] = (
            "I couldn't figure out what you're looking for. "
            "Try something like 'vintage graphic tee under $30, size M'."
        )
        return session

    search_results = search_listings(
        parsed.item_type,
        size=parsed.size,
        max_price=parsed.max_price,
    )
    session["search_results"] = search_results

    if not search_results:
        session["error"] = _no_results_message(parsed)
        return session

    session["selected_item"] = search_results[0]

    try:
        outfit_suggestion = suggest_outfit(session["selected_item"], wardrobe)
    except ValueError as exc:
        session["error"] = (
            f"Outfit styling failed: {exc} "
            "Add GROQ_API_KEY to your .env file and try again."
        )
        return session
    except Exception as exc:
        session["error"] = (
            f"Outfit styling hit an unexpected error: {exc}. "
            "Try again in a moment."
        )
        return session

    session["outfit_suggestion"] = outfit_suggestion

    try:
        session["fit_card"] = create_fit_card(outfit_suggestion, session["selected_item"])
    except ValueError as exc:
        session["error"] = (
            f"Fit card generation failed: {exc} "
            "Add GROQ_API_KEY to your .env file and try again."
        )
        return session
    except Exception as exc:
        session["error"] = (
            f"Fit card generation hit an unexpected error: {exc}. "
            "Your outfit suggestion is still available above."
        )
        return session

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"Fit card (should be None): {session2['fit_card']}")
