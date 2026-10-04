import json
from functools import lru_cache

from app.config import BASE_DIR


@lru_cache(maxsize=1)
def get_price_lookup() -> dict:
    path = BASE_DIR / "price_lookup.json"
    with path.open(encoding="utf-8") as price_file:
        return json.load(price_file)


def find_service_key(trade: str, requested_key: str | None) -> str:
    prices = get_price_lookup().get(trade)
    if not prices:
        raise ValueError(f"No price data is configured for trade '{trade}'")
    if requested_key is not None and requested_key in prices:
        return requested_key
    raise ValueError(
        f"Gemini returned service key '{requested_key}' that is not configured for '{trade}'"
    )


def service_price_bounds(trade: str, service_key: str) -> dict[str, int]:
    prices = get_price_lookup().get(trade, {})
    bounds = prices.get(service_key)
    if not bounds:
        raise ValueError(f"No price data is configured for '{trade}/{service_key}'")
    return {
        "price_min_inr": int(bounds["price_min_inr"]),
        "price_max_inr": int(bounds["price_max_inr"]),
    }


def trade_price_bounds(trade: str) -> tuple[int, int]:
    services = get_price_lookup().get(trade)
    if not services:
        raise ValueError(f"No price data is configured for trade '{trade}'")
    return (
        min(int(service["price_min_inr"]) for service in services.values()),
        max(int(service["price_max_inr"]) for service in services.values()),
    )
