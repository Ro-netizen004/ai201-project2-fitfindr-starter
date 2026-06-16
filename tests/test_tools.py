# tests/test_tools.py
from unittest.mock import patch

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_create_fit_card_empty_outfit():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    message = create_fit_card("", results[0])
    assert isinstance(message, str)
    assert message.strip()
    assert "fit card" in message.lower() or "outfit" in message.lower()


@patch("tools._call_groq", return_value="Pair with wide-leg jeans and chunky sneakers.")
def test_suggest_outfit_empty_wardrobe(mock_call_groq):
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    suggestion = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(suggestion, str)
    assert suggestion.strip()
    mock_call_groq.assert_called_once()
