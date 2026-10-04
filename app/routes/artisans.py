from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Artisan, Booking
from app.schemas import (
    ArtisanDraftRequest,
    ArtisanSubmitRequest,
    ArtisanSummary,
    EarningsSummary,
)
from app.services.gemini import AgentError
from app.services.pricing import service_price_bounds
from app.services.profile_generation import generate_artisan_profile


router = APIRouter(prefix="/artisans", tags=["artisans"])


@router.post("/create-profile-draft")
def create_profile_draft(request: ArtisanDraftRequest, db: Session = Depends(get_db)):
    try:
        profile = generate_artisan_profile(request)
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    artisan = db.scalar(select(Artisan).where(Artisan.phone == request.phone))
    if artisan and artisan.verification_status != "draft":
        raise HTTPException(status_code=409, detail="A profile already exists for this phone")
    if artisan is None:
        artisan = Artisan(
            phone=request.phone,
            name=request.name,
            trade=profile.trade,
            location=request.location.model_dump(),
            language_preference=request.language_preference,
        )
        db.add(artisan)
    else:
        artisan.name = request.name
        artisan.trade = profile.trade
        artisan.location = request.location.model_dump()
        artisan.language_preference = request.language_preference
    artisan.profile_draft = profile.model_dump()
    db.commit()
    db.refresh(artisan)
    return {"artisan_id": artisan.id, "profile_draft": artisan.profile_draft}


@router.post("/submit-profile")
def submit_profile(request: ArtisanSubmitRequest, db: Session = Depends(get_db)):
    artisan = db.get(Artisan, request.artisan_id)
    if artisan is None:
        raise HTTPException(status_code=404, detail="Artisan profile draft not found")
    if artisan.verification_status != "draft":
        raise HTTPException(status_code=409, detail="This profile has already been submitted")
    if request.profile.trade != artisan.trade:
        raise HTTPException(status_code=422, detail="Profile trade must match the generated trade")

    profile_data = request.profile.model_dump()
    for service in profile_data["services"]:
        try:
            bounds = service_price_bounds(artisan.trade, service["service_key"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if (
            service["price_min_inr"] < bounds["price_min_inr"]
            or service["price_max_inr"] > bounds["price_max_inr"]
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Prices for {service['service_key']} must stay within the listed Pune price band",
            )

    artisan.profile = profile_data
    artisan.profile_draft = None
    artisan.verification_status = "pending_verification"
    db.commit()
    db.refresh(artisan)
    return {
        "artisan_id": artisan.id,
        "verification_status": artisan.verification_status,
        "message": "Profile submitted for verification.",
    }


@router.get("", response_model=list[ArtisanSummary])
def list_artisans(db: Session = Depends(get_db)):
    return list(db.scalars(select(Artisan).order_by(Artisan.name)))


@router.get("/{artisan_id}/earnings", response_model=EarningsSummary)
def artisan_earnings(artisan_id: str, db: Session = Depends(get_db)):
    artisan = db.get(Artisan, artisan_id)
    if artisan is None:
        raise HTTPException(status_code=404, detail="Artisan not found")
    bookings = list(db.scalars(select(Booking).where(Booking.artisan_id == artisan_id)))
    return {
        "total_held_inr": sum(
            b.agreed_price_inr for b in bookings if b.payment_status in ("held", "frozen")
        ),
        "total_released_inr": sum(
            b.agreed_price_inr for b in bookings if b.payment_status == "released"
        ),
        "total_pending_inr": sum(
            b.agreed_price_inr
            for b in bookings
            if b.status == "pending_acceptance" and b.payment_status == "held"
        ),
    }
