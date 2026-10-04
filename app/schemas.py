from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Location(BaseModel):
    area: str = Field(min_length=1, max_length=100)
    city: str = Field(default="Pune", min_length=1, max_length=100)
    pincode: str | None = Field(default=None, max_length=12)
    lat: float | None = None
    long: float | None = None


class ArtisanDraftRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    trade_hint: str = Field(min_length=1, max_length=100)
    one_liner: str = Field(min_length=5, max_length=1000)
    location: Location
    language_preference: str = Field(default="mr", max_length=12)


class ProfileService(BaseModel):
    service_key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=120)
    price_min_inr: int = Field(gt=0)
    price_max_inr: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_price_order(self):
        if self.price_min_inr > self.price_max_inr:
            raise ValueError("price_min_inr must not exceed price_max_inr")
        return self


class ArtisanProfile(BaseModel):
    trade: str = Field(min_length=1, max_length=64)
    services: list[ProfileService] = Field(min_length=5, max_length=10)
    description_en: str = Field(min_length=1, max_length=2000)
    description_local: str = Field(min_length=1, max_length=2000)


class ArtisanSubmitRequest(BaseModel):
    artisan_id: str
    profile: ArtisanProfile


class ArtisanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    trade: str
    location: dict
    profile: dict | None
    verification_status: str
    rating: float
    rating_count: int


class JobCreateRequest(BaseModel):
    description_raw: str = Field(min_length=5, max_length=3000)
    location: Location
    timestamp: str | None = None


class JobMetadata(BaseModel):
    trade_inferred: str
    service_key: str
    urgency_score: Literal["low", "medium", "high"]
    price_band_min_inr: int = Field(gt=0)
    price_band_max_inr: int = Field(gt=0)
    summary: str
    keywords: list[str] = Field(min_length=3, max_length=6)


class JobResponse(JobMetadata):
    id: str
    status: str
    location: dict


class BookingCreateRequest(BaseModel):
    job_id: str
    artisan_id: str
    agreed_price_inr: int | None = Field(default=None, gt=0)


class BookingActionRequest(BaseModel):
    artisan_id: str


class CompleteBookingRequest(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)


class BookingResponse(BaseModel):
    id: str
    job_id: str
    artisan_id: str
    artisan_name: str
    artisan_trade: str
    customer_name: str | None = None
    job_summary: str
    description_raw: str
    location: dict
    price_band_min_inr: int
    price_band_max_inr: int
    agreed_price_inr: int
    booking_status: str
    payment_status: str
    rating: float
    created_at: str


class EarningsSummary(BaseModel):
    total_held_inr: int
    total_released_inr: int
    total_pending_inr: int
