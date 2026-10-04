from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import Artisan, Job, JobDecline


def find_matching_artisans(db: Session, job: Job, limit: int = 3) -> list[Artisan]:
    statement = (
        select(Artisan)
        .where(
            Artisan.trade == job.trade_inferred,
            Artisan.verification_status == "verified",
            Artisan.profile.is_not(None),
            ~exists().where(
                JobDecline.job_id == job.id,
                JobDecline.artisan_id == Artisan.id,
            ),
        )
        .order_by(Artisan.rating.desc(), Artisan.rating_count.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))
