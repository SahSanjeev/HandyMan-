import json

from app.schemas import ArtisanDraftRequest, ArtisanProfile
from app.services.gemini import AgentError, generate_json
from app.services.pricing import get_price_lookup, service_price_bounds


def generate_artisan_profile(request: ArtisanDraftRequest) -> ArtisanProfile:
    price_lookup = get_price_lookup()
    allowed_trades = list(price_lookup)
    if not allowed_trades:
        raise AgentError("No trade price data is configured.")

    system_prompt = (
        "You create concise, accurate service profiles for artisans in Pune. "
        "Use only the allowed trades and service keys. Do not invent prices or "
        "include contact details, guarantees, or off-platform invitations. "
        "Return valid JSON only."
    )
    user_prompt = f"""
Create a draft profile for:
Name: {request.name}
Trade hint: {request.trade_hint}
One-liner: {request.one_liner}
Location: {request.location.model_dump()}
Description language: {request.language_preference}

Allowed trade and service price data (INR):
{json.dumps(price_lookup, ensure_ascii=False)}

Return keys: trade, services, description_en, description_local.
The trade must exactly match an allowed trade key.
Return 5 to 10 services. Each service must contain service_key, name,
price_min_inr, price_max_inr. Use exact service keys and bounds from the data.
"""
    result = generate_json(system_prompt, user_prompt)
    try:
        trade = result["trade"]
        if trade not in allowed_trades:
            raise ValueError("trade is not in the configured price data")
        raw_services = result["services"]
        if not isinstance(raw_services, list):
            raise ValueError("services must be a list")
        services = []
        for item in raw_services:
            key = item["service_key"]
            bounds = service_price_bounds(trade, key)
            services.append(
                {
                    "service_key": key,
                    "name": item["name"],
                    **bounds,
                }
            )
        return ArtisanProfile.model_validate(
            {
                "trade": trade,
                "services": services,
                "description_en": result["description_en"],
                "description_local": result["description_local"],
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AgentError(f"Gemini returned an invalid artisan profile: {exc}") from exc
