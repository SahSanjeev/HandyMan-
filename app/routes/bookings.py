from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Artisan, Booking, Job, JobDecline
from app.schemas import (
    BookingActionRequest,
    BookingCreateRequest,
    BookingResponse,
    CompleteBookingRequest,
)
from app.services.bookings import (
    create_booking,
    get_booking_or_404,
    get_job_or_404,
    serialize_booking,
    update_job_and_booking,
)


router = APIRouter(prefix="/bookings", tags=["bookings"])


def get_booking_for_action(db: Session, booking_id: str, artisan_id: str) -> Booking:
    booking = get_booking_or_404(db, booking_id)
    if booking.artisan_id != artisan_id:
        raise HTTPException(status_code=403, detail="This booking belongs to another artisan")
    return booking


@router.post("/create", response_model=BookingResponse)
def create_booking_endpoint(request: BookingCreateRequest, db: Session = Depends(get_db)):
    job = get_job_or_404(db, request.job_id)
    artisan = db.get(Artisan, request.artisan_id)
    if artisan is None:
        raise HTTPException(status_code=404, detail="Artisan not found")
    booking = create_booking(db, job, artisan, request.agreed_price_inr)
    return serialize_booking(db, booking)


@router.get("", response_model=list[BookingResponse])
def list_bookings(
    artisan_id: str | None = None,
    db: Session = Depends(get_db),
):
    statement = select(Booking).order_by(Booking.created_at.desc())
    if artisan_id:
        statement = statement.where(Booking.artisan_id == artisan_id)
    return [serialize_booking(db, booking) for booking in db.scalars(statement)]


@router.post("/{booking_id}/accept", response_model=BookingResponse)
def accept_booking(
    booking_id: str,
    request: BookingActionRequest,
    db: Session = Depends(get_db),
):
    booking = get_booking_for_action(db, booking_id, request.artisan_id)
    if booking.status != "pending_acceptance":
        raise HTTPException(status_code=409, detail="Only pending bookings can be accepted")
    update_job_and_booking(db, booking, "in_progress", "held")
    db.refresh(booking)
    return serialize_booking(db, booking)


@router.post("/{booking_id}/decline", response_model=BookingResponse)
def decline_booking(
    booking_id: str,
    request: BookingActionRequest,
    db: Session = Depends(get_db),
):
    booking = get_booking_for_action(db, booking_id, request.artisan_id)
    if booking.status != "pending_acceptance":
        raise HTTPException(status_code=409, detail="Only pending bookings can be declined")
    update_job_and_booking(db, booking, "declined", "voided")
    if db.get(JobDecline, (booking.job_id, booking.artisan_id)) is None:
        db.add(JobDecline(job_id=booking.job_id, artisan_id=booking.artisan_id))
        db.commit()
    db.refresh(booking)
    return serialize_booking(db, booking)


@router.post("/{booking_id}/complete", response_model=BookingResponse)
def complete_booking(
    booking_id: str,
    request: CompleteBookingRequest | None = None,
    db: Session = Depends(get_db),
):
    booking = get_booking_or_404(db, booking_id)
    if booking.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only in-progress bookings can be completed")
    if request and request.rating is not None:
        artisan = db.get(Artisan, booking.artisan_id)
        if artisan is None:
            raise HTTPException(status_code=500, detail="Booking artisan record is missing")
        artisan.rating = (
            (artisan.rating * artisan.rating_count + request.rating) / (artisan.rating_count + 1)
        )
        artisan.rating_count += 1
        booking.rating = request.rating
    update_job_and_booking(db, booking, "completed", "released")
    db.refresh(booking)
    return serialize_booking(db, booking)


@router.post("/{booking_id}/dispute", response_model=BookingResponse)
def dispute_booking(booking_id: str, db: Session = Depends(get_db)):
    booking = get_booking_or_404(db, booking_id)
    if booking.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only in-progress bookings can be disputed")
    update_job_and_booking(db, booking, "disputed", "frozen")
    db.refresh(booking)
    return serialize_booking(db, booking)
