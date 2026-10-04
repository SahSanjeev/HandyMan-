from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Artisan
from app.services.pricing import get_price_lookup


SEED_ARTISANS = [
    ("Demo Plumber 1", "plumber", "Kothrud", "9000000001"),
    ("Demo Plumber 2", "plumber", "Baner", "9000000002"),
    ("Demo Electrician 1", "electrician", "Viman Nagar", "9000000003"),
    ("Demo Electrician 2", "electrician", "Aundh", "9000000004"),
    ("Demo AC Technician", "ac_appliance_repair", "Baner", "9000000005"),
    ("Demo AC Technician 2", "ac_appliance_repair", "Kothrud", "9000000006"),
    ("Demo Cleaner 1", "cleaner", "Kothrud", "9000000007"),
    ("Demo Cleaner 2", "cleaner", "Baner", "9000000008"),
    ("Demo Mechanic 1", "mechanic", "Viman Nagar", "9000000009"),
    ("Demo Mechanic 2", "mechanic", "Aundh", "9000000010"),
]


def seed_demo_artisans(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Artisan)):
        return

    price_lookup = get_price_lookup()
    for name, trade, area, phone in SEED_ARTISANS:
        services = []
        for service_key, price in list(price_lookup.get(trade, {}).items())[:5]:
            services.append(
                {
                    "service_key": service_key,
                    "name": service_key.replace("_", " ").title(),
                    **price,
                }
            )
        db.add(
            Artisan(
                phone=f"+91{phone}",
                name=name,
                trade=trade,
                location={"area": area, "city": "Pune"},
                language_preference="mr",
                profile={
                    "trade": trade,
                    "services": services,
                    "description_en": f"Verified local {trade.replace('_', ' ')} serving {area}.",
                    "description_local": f"{area} परिसरात सेवा देणारे स्थानिक कारागीर.",
                },
                verification_status="verified",
                rating=4.5 + (len(name) % 5) / 10,
                rating_count=12 + len(name),
            )
        )
    db.commit()
