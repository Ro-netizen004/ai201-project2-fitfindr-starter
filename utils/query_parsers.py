import re
from typing import Optional

KNOWN_STYLE_TAGS = sorted(
    [
        "dark academia",
        "earth tones",
        "color block",
        "graphic tee",
        "band tee",
        "streetwear",
        "cottagecore",
        "knitwear",
        "layering",
        "minimal",
        "oversized",
        "athletic",
        "basics",
        "classic",
        "crochet",
        "denim",
        "feminine",
        "flannel",
        "floral",
        "graphic",
        "grunge",
        "leather",
        "linen",
        "platform",
        "preppy",
        "summer",
        "vintage",
        "western",
        "y2k",
        "90s",
        "70s",
        "2000s",
        "boho",
        "cargo",
        "cozy",
        "goth",
    ],
    key=len,
    reverse=True,
)

KNOWN_OCCASIONS = sorted(
    [
        "date night",
        "night out",
        "going out",
        "everyday",
        "workout",
        "wedding",
        "festival",
        "concert",
        "interview",
        "vacation",
        "brunch",
        "office",
        "casual",
        "formal",
        "party",
        "school",
        "work",
        "gym",
    ],
    key=len,
    reverse=True,
)

KNOWN_FIT_PREFERENCES = sorted(
    [
        "oversized",
        "tailored",
        "relaxed",
        "cropped",
        "fitted",
        "baggy",
        "slim",
        "loose",
    ],
    key=len,
    reverse=True,
)

_MAX_PRICE_PATTERNS = [
    re.compile(
        r"(?:under|below|less than|max(?:imum)?|up to|within)\s*\$?\s*(\d+(?:\.\d{1,2})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\$\s*(\d+(?:\.\d{1,2})?)\s*(?:or less|max(?:imum)?)",
        re.IGNORECASE,
    ),
]

_MIN_PRICE_PATTERN = re.compile(
    r"(?:over|above|more than|at least|min(?:imum)?)\s*\$?\s*(\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

_SIZE_PATTERN = re.compile(
    r"\bsize\s*[:\-]?\s*([A-Za-z0-9/.]+(?:\s*\([^)]+\))?)",
    re.IGNORECASE,
)

_FILLER_PREFIX = re.compile(
    r"^(?:i(?:'m| am)?\s+)?(?:looking for|searching for|want(?:ing)?|need(?:ing)?|trying to find)\s+(?:a|an|some)?\s*",
    re.IGNORECASE,
)

_TRAILING_QUESTION = re.compile(
    r"\s*(?:what(?:'s| is)? out there|how (?:would|should|could) i style (?:it|this|them)|any suggestions?)\??\s*$",
    re.IGNORECASE,
)

_OCCASION_PATTERN = re.compile(
    r"\bfor\s+(?:a|an)?\s*([a-z][a-z\s]+?)(?:\s*,|\s+under|\s+below|\s+size\b|$)",
    re.IGNORECASE,
)


def extract_price(query: str) -> Optional[float]:
    """Return max price from phrases like 'under $30' or 'below 50'."""
    for pattern in _MAX_PRICE_PATTERNS:
        match = pattern.search(query)
        if match:
            return float(match.group(1))
    return None


def extract_min_price(query: str) -> Optional[float]:
    """Return min price from phrases like 'over $20' or 'at least 15'."""
    match = _MIN_PRICE_PATTERN.search(query)
    if match:
        return float(match.group(1))
    return None


def extract_size(query: str) -> Optional[str]:
    """Return size from phrases like 'size M' or 'size S/M'."""
    match = _SIZE_PATTERN.search(query)
    if not match:
        return None
    return match.group(1).strip()


def extract_style_tags(query: str) -> list[str]:
    """Return style tags mentioned in the query that match the listings dataset."""
    lowered = query.lower()
    found: list[str] = []
    for tag in KNOWN_STYLE_TAGS:
        if tag in lowered and not any(tag in existing for existing in found):
            found.append(tag)
    return found


def extract_occasion(query: str) -> Optional[str]:
    """Return occasion from known keywords or 'for <occasion>' phrases."""
    lowered = query.lower()
    for occasion in KNOWN_OCCASIONS:
        if occasion in lowered:
            return occasion

    match = _OCCASION_PATTERN.search(query)
    if match:
        return match.group(1).strip()
    return None


def extract_fit_preference(query: str) -> Optional[str]:
    """Return fit preference like baggy, oversized, or fitted."""
    lowered = query.lower()
    for fit in KNOWN_FIT_PREFERENCES:
        if fit in lowered:
            return fit
    return None


def extract_item(query: str) -> str:
    """
    Return the core item description after removing price, size, and filler text.
    Style keywords are kept so search_listings can score them.
    """
    text = query.strip()

    for pattern in _MAX_PRICE_PATTERNS:
        text = pattern.sub("", text)
    text = _MIN_PRICE_PATTERN.sub("", text)
    text = _SIZE_PATTERN.sub("", text)
    text = _FILLER_PREFIX.sub("", text)
    text = _TRAILING_QUESTION.sub("", text)

    for occasion in KNOWN_OCCASIONS:
        text = re.sub(rf"\bfor\s+{re.escape(occasion)}\b", "", text, flags=re.IGNORECASE)
    for fit in KNOWN_FIT_PREFERENCES:
        text = re.sub(rf"\b{re.escape(fit)}\b", "", text, flags=re.IGNORECASE)

    text = re.sub(
        r"\b(?:under|below|less than|max(?:imum)?|up to|within|over|above|more than|at least)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*,\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.-")

    return text or query.strip()
