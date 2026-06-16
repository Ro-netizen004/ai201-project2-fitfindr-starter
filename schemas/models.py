from pydantic import BaseModel
from typing import Optional, List


class ParsedQuery(BaseModel):
    item_type: str
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    size: Optional[str] = None
    style_tags: List[str] = []
    occasion: Optional[str] = None
    fit_preference: Optional[str] = None


class WardrobeItem(BaseModel):
    id: str
    name: str
    category: str  # tops, bottoms, outerwear, shoes, accessories
    colors: List[str]
    style_tags: List[str]
    notes: Optional[str] = None


class Wardrobe(BaseModel):
    items: List[WardrobeItem]