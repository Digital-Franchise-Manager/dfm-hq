"""Append-only market history port owned by draft."""
from typing import Protocol
from .models import PriceMovement
class MarketHistoryRepository(Protocol):
    def append_once(self,movement:PriceMovement)->bool: ...
    def list_market(self,market_id:str)->tuple[PriceMovement,...]: ...
class MarketHistory:
    def __init__(self,repository:MarketHistoryRepository):self._repository=repository
    def record(self,movements:tuple[PriceMovement,...])->int:return sum(1 for m in movements if self._repository.append_once(m))
    def list(self,market_id:str)->tuple[PriceMovement,...]:
        if not market_id.strip():raise ValueError("market ID required")
        return self._repository.list_market(market_id)
