from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Artisan, Booking, Job, JobDecline
from app.schemas import BookingActionRequest, BookingResponse, JobCreateRequest, JobResponse
from app.services.bookings import create_booking, get_job_or_404, serialize_booking
from app.services.gemini import AgentError
from app.services.job_intake import classify_job
from app.services.matching import find_matching_artisans


router = APIRouter(prefix="/jobs", tags=["jobs"])


def serialize_job(job: Job) -> dict:
    return {
        "id": job.id,
        "trade_inferred": job.trade_inferred,
        "service_key": job.service_key,
        "urgency_score": job.urgency_score,
        "price_band_min_inr": job.price_band_min_inr,
        "price_band_max_inr": job.price_band_max_inr,
        "summary": job.summary,
        "keywords": job.keywords,
        "status": job.status,
        "location": job.location,
    }


@router.post("/create")
def create_job(request: JobCreateRequest, db: Session = Depends(get_db)):
    try:
        metadata = classify_job(request)
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    job = Job(
        description_raw=request.description_raw,
        location=request.location.model_dump(),
        trade_inferred=metadata.trade_inferred,
        service_key=metadata.service_key,
        urgency_score=metadata.urgency_score,
        price_band_min_inr=metadata.price_band_min_inr,
        price_band_max_inr=metadata.price_band_max_inr,
        summary=metadata.summary,
        keywords=metadata.keywords,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": job.id, "job_meta": serialize_job(job)}


@router.get("/open", response_model=list[JobResponse])
def open_jobs(artisan_id: str | None = None, db: Session = Depends(get_db)):
    statement = select(Job).where(Job.status == "open").order_by(Job.created_at.desc())
    if artisan_id:
        artisan = db.get(Artisan, artisan_id)
        if artisan is None:
            raise HTTPException(status_code=404, detail="Artisan not found")
        if artisan.verification_status != "verified":
            raise HTTPException(status_code=403, detail="Artisan is not verified")
        declined_job_ids = select(JobDecline.job_id).where(JobDecline.artisan_id == artisan_id)
        statement = statement.where(
            Job.trade_inferred == artisan.trade,
            Job.id.not_in(declined_job_ids),
        )
    return [serialize_job(job) for job in db.scalars(statement)]


@router.get("/{job_id}/artisans", response_model=list[dict])
def matched_artisans(job_id: str, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    matches = find_matching_artisans(db, job)
    return [
        {
            "id": artisan.id,
            "name": artisan.name,
            "trade": artisan.trade,
            "services": artisan.profile["services"],
            "location": artisan.location,
            "price_band_min_inr": job.price_band_min_inr,
            "price_band_max_inr": job.price_band_max_inr,
            "rating": artisan.rating,
            "rating_count": artisan.rating_count,
        }
        for artisan in matches
    ]


@router.post("/{job_id}/accept", response_model=BookingResponse)
def accept_job(job_id: str, request: BookingActionRequest, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    artisan = db.get(Artisan, request.artisan_id)
    if artisan is None:
        raise HTTPException(status_code=404, detail="Artisan not found")
    booking = create_booking(db, job, artisan, None)
    return serialize_booking(db, booking)


@router.post("/{job_id}/decline")
def decline_job(job_id: str, request: BookingActionRequest, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    artisan = db.get(Artisan, request.artisan_id)
    if artisan is None:
        raise HTTPException(status_code=404, detail="Artisan not found")
    if artisan.trade != job.trade_inferred or artisan.verification_status != "verified":
        raise HTTPException(status_code=409, detail="This artisan cannot decline this job")

    if job.status == "open":
        already_declined = db.get(JobDecline, (job.id, artisan.id))
        if already_declined is None:
            db.add(JobDecline(job_id=job.id, artisan_id=artisan.id))
        db.commit()
        return {"job_id": job.id, "status": "declined"}
    if job.status != "booked" or job.assigned_artisan_id != artisan.id:
        raise HTTPException(status_code=409, detail="No pending booking for this artisan")

    booking = db.scalar(
        select(Booking).where(
            Booking.job_id == job.id,
            Booking.artisan_id == artisan.id,
            Booking.status == "pending_acceptance",
        )
    )
    if booking is None:
        raise HTTPException(status_code=409, detail="Only pending bookings can be declined")
    booking.status = "declined"
    booking.payment_status = "voided"
    job.status = "open"
    job.assigned_artisan_id = None
    if db.get(JobDecline, (job.id, artisan.id)) is None:
        db.add(JobDecline(job_id=job.id, artisan_id=artisan.id))
    db.commit()
    return {"job_id": job.id, "status": job.status, "payment_status": booking.payment_status}
