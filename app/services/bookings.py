from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Artisan, Booking, Job, JobDecline


ACTIVE_BOOKING_STATUSES = ("pending_acceptance", "in_progress")


def get_job_or_404(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def get_booking_or_404(db: Session, booking_id: str) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


def create_booking(
    db: Session,
    job: Job,
    artisan: Artisan,
    agreed_price_inr: int | None,
) -> Booking:
    if job.status not in ("open", "booked"):
        raise HTTPException(status_code=409, detail="This job is no longer available")
    if artisan.verification_status != "verified" or artisan.trade != job.trade_inferred:
        raise HTTPException(status_code=409, detail="This artisan cannot take this job")
    if db.get(JobDecline, (job.id, artisan.id)) is not None:
        raise HTTPException(status_code=409, detail="This artisan has declined the job")

    if job.status == "booked":
        active = db.scalar(
            select(Booking).where(
                Booking.job_id == job.id,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        if active:
            raise HTTPException(status_code=409, detail="This job already has an active booking")

    price = agreed_price_inr or (job.price_band_min_inr + job.price_band_max_inr) // 2
    if not job.price_band_min_inr <= price <= job.price_band_max_inr:
        raise HTTPException(
            status_code=422,
            detail="agreed_price_inr must be within the job's estimated price band",
        )

    booking = Booking(
        job_id=job.id,
        artisan_id=artisan.id,
        agreed_price_inr=price,
        status="pending_acceptance",
        payment_status="held",
    )
    job.status = "booked"
    job.assigned_artisan_id = artisan.id
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def update_job_and_booking(
    db: Session, booking: Booking, status: str, payment_status: str
) -> Job:
    job = get_job_or_404(db, booking.job_id)
    booking.status = status
    booking.payment_status = payment_status
    if status == "completed":
        booking.completed_at = datetime.now(timezone.utc)
        job.status = "completed"
    elif status == "disputed":
        job.status = "disputed"
    elif status == "declined":
        job.status = "open"
        job.assigned_artisan_id = None
    elif status == "in_progress":
        job.status = "in_progress"
    db.commit()
    return job


def serialize_booking(db: Session, booking: Booking) -> dict:
    job = get_job_or_404(db, booking.job_id)
    artisan = db.get(Artisan, booking.artisan_id)
    if artisan is None:
        raise HTTPException(status_code=500, detail="Booking artisan record is missing")
    return {
        "id": booking.id,
        "job_id": booking.job_id,
        "artisan_id": booking.artisan_id,
        "artisan_name": artisan.name,
        "artisan_trade": artisan.trade,
        "job_summary": job.summary,
        "description_raw": job.description_raw,
        "location": job.location,
        "price_band_min_inr": job.price_band_min_inr,
        "price_band_max_inr": job.price_band_max_inr,
        "agreed_price_inr": booking.agreed_price_inr,
        "booking_status": booking.status,
        "payment_status": booking.payment_status,
        "rating": artisan.rating,
        "created_at": booking.created_at.isoformat() if booking.created_at else "",
    }
