# FitFindr

FitFindr is a multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. Given a natural language query, the agent searches mock listings, suggests outfits using the user's wardrobe, and generates a shareable fit card caption.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

## Run

```bash
python app.py          # Gradio UI
python agent.py        # CLI test (happy path + no-results path)
pytest tests/ -v       # All tool and agent tests
```

---

## Tool Inventory

### 1. `search_listings(description, size, max_price)` — `tools.py`

**Purpose:** Find matching secondhand listings from the mock dataset.

| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | `str` | Keywords for what the user wants (e.g., `"vintage graphic tee"`) |
| `size` | `str \| None` | Optional size filter; case-insensitive substring match |
| `max_price` | `float \| None` | Optional max price (inclusive) |

**Returns:** `list[dict]` — matching listings sorted by relevance. Each dict has:
`id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`.

Empty list if nothing matches. Never raises.

---

### 2. `suggest_outfit(new_item, wardrobe)` — `tools.py`

**Purpose:** Suggest 1–2 outfits combining the thrift find with the user's wardrobe.

| Parameter | Type | Description |
|-----------|------|-------------|
| `new_item` | `dict` | Listing dict from `search_listings` |
| `wardrobe` | `dict` | Wardrobe with `items` list (see `data/wardrobe_schema.json`) |

**Returns:** `str` — outfit suggestion or general styling advice if wardrobe is empty.

Uses Groq `llama-3.3-70b-versatile`.

---

### 3. `create_fit_card(outfit, new_item)` — `tools.py`

**Purpose:** Generate a casual, shareable outfit caption (Instagram/TikTok style).

| Parameter | Type | Description |
|-----------|------|-------------|
| `outfit` | `str` | Outfit suggestion from `suggest_outfit` |
| `new_item` | `dict` | Same listing dict used in outfit styling |

**Returns:** `str` — 2–4 sentence caption mentioning title, price, and platform once each. Uses temperature 0.95 for variety.

---

## Planning Loop

`run_agent(query, wardrobe)` in `agent.py` runs a **conditional sequential loop**:

```
parse query
    ↓
search_listings
    ↓
results empty? ──yes──► set error, STOP (no outfit, no fit card)
    ↓ no
selected_item = results[0]
    ↓
suggest_outfit(selected_item, wardrobe)
    ↓
create_fit_card(outfit_suggestion, selected_item)
    ↓
return session
```

**What triggers each decision:**

| Check | If true | Action |
|-------|---------|--------|
| Parsed `item_type` is empty | Can't search | Set error, return — **no tools called** |
| `search_results` is empty | Nothing to style | Set error with filter details, return — **`suggest_outfit` and `create_fit_card` skipped** |
| Search succeeded | Have an item | Continue to outfit + fit card tools |
| Groq API fails | Can't generate text | Set error, return — downstream tool skipped |

This is **not** a fixed pipeline. A no-results query behaves differently from a happy-path query: only one tool runs (search), then the agent stops.

---

## State Management

All state is stored in a **session dict** for each interaction:

```python
{
    "query": str,              # original user input
    "parsed": dict,            # extracted item_type, size, max_price, etc.
    "search_results": list,    # all matches from search_listings
    "selected_item": dict,     # top result → passed to suggest_outfit & create_fit_card
    "wardrobe": dict,          # user's wardrobe → passed to suggest_outfit
    "outfit_suggestion": str,  # LLM output → passed to create_fit_card
    "fit_card": str,           # final caption
    "error": str | None,       # set on early exit
}
```

**Flow without re-entry:**
1. `search_listings` → `session["selected_item"]`
2. `suggest_outfit(session["selected_item"], wardrobe)` → `session["outfit_suggestion"]`
3. `create_fit_card(session["outfit_suggestion"], session["selected_item"])` → `session["fit_card"]`

The same listing dict object flows through all three tools. The user types once; the agent carries data forward automatically.

---

## Error Handling

| Tool | Failure mode | What the agent does |
|------|-------------|---------------------|
| `search_listings` | No matches | Sets `session["error"]` naming the search terms and active filters. Suggests broadening keywords or raising price. **Does not call outfit or fit card tools.** |
| `suggest_outfit` | Empty wardrobe | **Not treated as failure** — returns general styling advice and continues. |
| `suggest_outfit` | Invalid/missing API key | Sets error: *"Outfit styling failed… Add GROQ_API_KEY to your .env file."* Returns early. |
| `create_fit_card` | Empty outfit string | Returns error message string: *"Can't create a fit card without an outfit suggestion."* |
| `create_fit_card` | API failure | Sets session error; outfit suggestion may still be visible in the UI. |

### Concrete example (tested)

Query: `"designer ballgown size XXS under $5"`

```
session["error"] = "No listings matched your search for 'designer ballgown'.
  Active filters: size XXS, under $5.
  Try broadening your search — use fewer filters, raise your price limit,
  or try different keywords (e.g., 'vintage tee' instead of a specific brand)."
session["selected_item"] = None
session["outfit_suggestion"] = None
session["fit_card"] = None
```

Verified by `tests/test_agent.py::test_agent_no_results_path` and the second test case in `agent.py`.

---

## Spec Reflection

**How the spec helped:** The milestone structure (test each tool in isolation before wiring the loop) prevented debugging three broken tools at once. The explicit requirement that empty search results must **stop** the pipeline — not call `suggest_outfit` with empty input — shaped the most important branch in `run_agent()`.

**Where implementation diverged:** The spec suggests the agent could use an LLM to decide which tools to call. I used a **deterministic conditional loop** instead because the tool sequence is always the same when search succeeds (search → outfit → fit card), and the only meaningful branch is whether search returned results. Regex query parsing replaced LLM parsing for reliability and speed — price/size extraction from `"under $30, size M"` is predictable without an API call.

---

## AI Usage

### Instance 1 — Implementing `search_listings`

**Directed:** Gave Cursor the Tool 1 spec from `planning.md` (inputs, return fields, failure mode) and asked it to implement keyword scoring with `load_listings()`, price filtering, and size matching.

**Reviewed/overrode:** Verified the function returns `[]` not an exception for impossible queries. Confirmed size matching uses substring logic so `"M"` matches `"S/M"`. Added pytest tests before moving to the next tool.

### Instance 2 — Wiring the planning loop

**Directed:** Shared the architecture diagram and Planning Loop + State Management sections from `planning.md` and asked Cursor to implement `run_agent()` with early return on empty search results.

**Reviewed/overrode:** Removed an incorrect `return None` on error — the spec requires returning the session dict so the UI can read `session["error"]`. Fixed imports so query parsing lives in `utils/query_parsers.py` rather than duplicating regex in `agent.py`. Added `tests/test_agent.py` to lock in the no-results branch behavior.

---

## Project Structure

```
├── agent.py              # Planning loop + run_agent()
├── app.py                # Gradio UI
├── tools.py              # search_listings, suggest_outfit, create_fit_card
├── utils/
│   ├── data_loader.py    # Load listings and wardrobes
│   └── query_parsers.py  # Regex query parsing
├── schemas/models.py     # ParsedQuery Pydantic model
├── data/
│   ├── listings.json
│   └── wardrobe_schema.json
├── tests/
│   ├── test_tools.py
│   └── test_agent.py
└── planning.md
```
