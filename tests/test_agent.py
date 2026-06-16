from agent import run_agent
from utils.data_loader import get_example_wardrobe


def test_agent_no_results_path():
    session = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    assert session["error"]
    assert session["search_results"] == []
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None


def test_agent_parses_query_into_session():
    session = run_agent(
        query="vintage graphic tee under 30, size M",
        wardrobe=get_example_wardrobe(),
    )
    assert session["parsed"]["item_type"]
    assert session["parsed"]["max_price"] == 30.0
    assert session["parsed"]["size"] == "M"
