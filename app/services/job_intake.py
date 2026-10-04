import json

from app.schemas import JobMetadata, JobCreateRequest
from app.services.gemini import AgentError, generate_json
from app.services.pricing import get_price_lookup, find_service_key, service_price_bounds


def classify_job(request: JobCreateRequest) -> JobMetadata:
    price_lookup = get_price_lookup()
    allowed_trades = list(price_lookup)
    system_prompt = (
        "Classify home-service requests in Pune. Use only the supplied trade "
        "and service keys. Set urgency to low, medium, or high based on risk "
        "and time sensitivity. Write a concise neutral summary and 3 to 6 "
        "keywords. Return valid JSON only."
    )
    user_prompt = f"""
Customer description: {request.description_raw}
Location: {request.location.model_dump()}
Time: {request.timestamp or "not provided"}

Known trades, services, and INR bounds:
{json.dumps(price_lookup, ensure_ascii=False)}

Return keys: trade_inferred, service_key, urgency_score, summary, keywords.
trade_inferred must exactly match a trade key. service_key must be a key under
that trade. Do not return prices.
"""
    result = generate_json(system_prompt, user_prompt)
    try:
        trade = result["trade_inferred"]
        if trade not in allowed_trades:
            raise ValueError("trade_inferred is not in the configured price data")
        service_key = find_service_key(trade, result.get("service_key"))
        bounds = service_price_bounds(trade, service_key)
        return JobMetadata.model_validate(
            {
                "trade_inferred": trade,
                "service_key": service_key,
                "urgency_score": result["urgency_score"],
                **bounds,
                "summary": result["summary"],
                "keywords": result["keywords"],
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AgentError(f"Gemini returned invalid job metadata: {exc}") from exc
