import os
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
AREAS = [
    "Kothrud",
    "Baner",
    "Viman Nagar",
    "Aundh",
    "Hinjawadi",
    "Hadapsar",
    "Wakad",
    "Koregaon Park",
    "Shivajinagar",
]
TRADES = [
    "plumber",
    "electrician",
    "ac_appliance_repair",
    "cleaner",
    "mechanic",
]

st.set_page_config(page_title="FixPune", page_icon="🛠️", layout="wide")


def api_request(method: str, path: str, **kwargs: Any) -> Any:
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=30,
            **kwargs,
        )
    except requests.RequestException as exc:
        st.error(f"Could not reach the API at {API_BASE_URL}: {exc}")
        return None
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        st.error(f"API error ({response.status_code}): {detail}")
        return None
    if not response.content:
        return {}
    return response.json()


def load_artisans() -> list[dict]:
    result = api_request("GET", "/artisans")
    return result if isinstance(result, list) else []


def location_form(area: str, pincode: str = "") -> dict:
    return {"area": area, "city": "Pune", "pincode": pincode or None}


def onboarding_page() -> None:
    st.header("Artisan onboarding")
    st.caption("Phone verification is mocked for this MVP. Uploaded photos are not stored.")
    photos = st.file_uploader(
        "Work photos (optional; 3–6 recommended)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )
    if photos and len(photos) not in range(3, 7):
        st.info("For the demo, upload either 3–6 photos or leave this optional field empty.")

    with st.form("artisan_onboarding"):
        phone = st.text_input("Phone number", placeholder="+91 98XXXXXXXX")
        name = st.text_input("Name")
        col1, col2 = st.columns(2)
        with col1:
            area = st.selectbox("Area", AREAS)
            pincode = st.text_input("Pincode")
        with col2:
            trade = st.selectbox("Trade", TRADES)
            language = st.selectbox("Language", ["mr", "hi", "en"], format_func=lambda x: {
                "mr": "Marathi", "hi": "Hindi", "en": "English"
            }[x])
        one_liner = st.text_area(
            "Describe your experience and work",
            placeholder="I repair taps, pipes, and water leaks in homes...",
        )
        generate = st.form_submit_button("Generate profile")

    if generate:
        result = api_request(
            "POST",
            "/artisans/create-profile-draft",
            json={
                "phone": phone.strip(),
                "name": name.strip(),
                "trade_hint": trade,
                "one_liner": one_liner.strip(),
                "location": location_form(area, pincode.strip()),
                "language_preference": language,
            },
        )
        if result:
            st.session_state["profile_draft"] = result
            st.session_state["profile_name"] = name.strip()
            st.success("Draft generated. Review and edit the details below.")

    result = st.session_state.get("profile_draft")
    if not result:
        return
    draft = result["profile_draft"]
    st.subheader("Review your profile")
    with st.form("profile_review"):
        st.selectbox(
            "Trade",
            TRADES,
            index=TRADES.index(draft["trade"]),
            key="draft_trade",
            disabled=True,
        )
        services = []
        for index, service in enumerate(draft["services"]):
            st.markdown(f"**Service {index + 1}**")
            name_col, min_col, max_col = st.columns([3, 1, 1])
            with name_col:
                service_name = st.text_input("Service", service["name"], key=f"service_name_{index}")
            with min_col:
                minimum = st.number_input(
                    "Min ₹", min_value=1, value=int(service["price_min_inr"]), key=f"service_min_{index}"
                )
            with max_col:
                maximum = st.number_input(
                    "Max ₹", min_value=1, value=int(service["price_max_inr"]), key=f"service_max_{index}"
                )
            services.append(
                {
                    "service_key": service["service_key"],
                    "name": service_name,
                    "price_min_inr": minimum,
                    "price_max_inr": maximum,
                }
            )
        description_en = st.text_area("Description (English)", draft["description_en"])
        description_local = st.text_area("Description (local language)", draft["description_local"])
        submit_profile = st.form_submit_button("Submit profile")

    if submit_profile:
        submitted = api_request(
            "POST",
            "/artisans/submit-profile",
            json={
                "artisan_id": result["artisan_id"],
                "profile": {
                    "trade": draft["trade"],
                    "services": services,
                    "description_en": description_en,
                    "description_local": description_local,
                },
            },
        )
        if submitted:
            st.session_state.pop("profile_draft", None)
            st.success(f"Profile submitted — {submitted['verification_status']}.")
            st.info("Verification is pending; the profile is not yet eligible for matching.")


def customer_page() -> None:
    st.header("Find an artisan")
    with st.form("job_search"):
        description = st.text_area("Describe your problem", placeholder="My kitchen tap is leaking...")
        area = st.selectbox("Service area", AREAS, key="customer_area")
        submitted = st.form_submit_button("Find artisans")
    if submitted:
        created = api_request(
            "POST",
            "/jobs/create",
            json={"description_raw": description.strip(), "location": location_form(area)},
        )
        if created:
            matches = api_request("GET", f"/jobs/{created['job_id']}/artisans")
            st.session_state["customer_job"] = created
            st.session_state["customer_matches"] = matches or []
            st.session_state.pop("latest_booking", None)

    created = st.session_state.get("customer_job")
    if not created:
        return
    meta = created["job_meta"]
    st.subheader(meta["summary"])
    st.write(
        f"**Trade:** {meta['trade_inferred'].replace('_', ' ').title()}  ·  "
        f"**Urgency:** {meta['urgency_score']}  ·  "
        f"**Estimate:** ₹{meta['price_band_min_inr']}–₹{meta['price_band_max_inr']}"
    )
    artisans = st.session_state.get("customer_matches", [])
    latest_booking = st.session_state.get("latest_booking")
    already_booked = bool(latest_booking and latest_booking["job_id"] == created["job_id"])
    if not artisans:
        st.warning("No verified artisans are available for this trade yet.")
    for artisan in artisans:
        with st.container(border=True):
            st.subheader(artisan["name"])
            st.write(
                f"{artisan['trade'].replace('_', ' ').title()} · "
                f"{artisan['location'].get('area', 'Pune')} · "
                f"⭐ {artisan['rating']:.1f} ({artisan['rating_count']} reviews)"
            )
            st.write(
                "Services: " + ", ".join(service["name"] for service in artisan["services"])
            )
            if st.button(
                "Book artisan",
                key=f"book_{artisan['id']}",
                disabled=already_booked,
            ):
                booking = api_request(
                    "POST",
                    "/bookings/create",
                    json={
                        "job_id": created["job_id"],
                        "artisan_id": artisan["id"],
                    },
                )
                if booking:
                    st.session_state["latest_booking"] = booking
                    st.success(
                        f"Booking created. Payment held — awaiting artisan acceptance "
                        f"(booking {booking['id'][:8]})."
                    )


def execution_page() -> None:
    st.header("Job execution & completion")
    bookings = api_request("GET", "/bookings")
    if not bookings:
        st.info("No bookings yet.")
        return
    for booking in bookings:
        with st.container(border=True):
            st.subheader(booking["job_summary"])
            st.write(
                f"{booking['artisan_name']} · {booking['location'].get('area', 'Pune')} · "
                f"₹{booking['agreed_price_inr']} · "
                f"Booking: **{booking['booking_status']}** · "
                f"Payment: **{booking['payment_status']}**"
            )
            if booking["booking_status"] != "in_progress":
                continue
            rating = st.slider(
                "Rate the artisan",
                min_value=1,
                max_value=5,
                value=5,
                key=f"rating_{booking['id']}",
            )
            complete_col, dispute_col = st.columns(2)
            with complete_col:
                if st.button("Mark as completed", key=f"complete_{booking['id']}"):
                    result = api_request(
                        "POST",
                        f"/bookings/{booking['id']}/complete",
                        json={"rating": rating},
                    )
                    if result:
                        st.success("Job completed — payment released.")
                        st.rerun()
            with dispute_col:
                if st.button("Raise dispute", key=f"dispute_{booking['id']}"):
                    result = api_request("POST", f"/bookings/{booking['id']}/dispute")
                    if result:
                        st.warning("Dispute opened — payout frozen for review.")
                        st.rerun()


def artisan_feed_page() -> None:
    st.header("Artisan job feed")
    artisans = load_artisans()
    eligible = [a for a in artisans if a["verification_status"] == "verified"]
    if not eligible:
        st.info("No verified artisan profiles are available.")
        return
    selected = st.selectbox(
        "Mock artisan login",
        eligible,
        format_func=lambda a: f"{a['name']} · {a['trade'].replace('_', ' ').title()}",
    )
    artisan_id = selected["id"]

    st.subheader("Available jobs")
    jobs = api_request("GET", "/jobs/open", params={"artisan_id": artisan_id}) or []
    if not jobs:
        st.info("No open jobs match this artisan's trade.")
    for job in jobs:
        with st.container(border=True):
            st.write(
                f"**{job['summary']}** · {job['location'].get('area', 'Pune')} · "
                f"₹{job['price_band_min_inr']}–₹{job['price_band_max_inr']}"
            )
            if st.button("Accept", key=f"accept_job_{job['id']}"):
                accepted = api_request(
                    "POST",
                    f"/jobs/{job['id']}/accept",
                    json={"artisan_id": artisan_id},
                )
                if accepted:
                    st.success("Job accepted — payment is held.")
                    st.rerun()
            if st.button("Decline", key=f"decline_job_{job['id']}"):
                declined = api_request(
                    "POST",
                    f"/jobs/{job['id']}/decline",
                    json={"artisan_id": artisan_id},
                )
                if declined:
                    st.info("Job declined.")
                    st.rerun()

    st.subheader("My jobs")
    bookings = api_request("GET", "/bookings", params={"artisan_id": artisan_id}) or []
    if bookings:
        st.dataframe(
            [
                {
                    "Job": booking["job_summary"],
                    "Area": booking["location"].get("area", "Pune"),
                    "Agreed price (₹)": booking["agreed_price_inr"],
                    "Booking": booking["booking_status"],
                    "Payment": booking["payment_status"],
                }
                for booking in bookings
            ],
            use_container_width=True,
            hide_index=True,
        )
        for booking in bookings:
            if booking["booking_status"] != "pending_acceptance":
                continue
            accept_col, decline_col = st.columns(2)
            with accept_col:
                if st.button("Accept booking", key=f"accept_booking_{booking['id']}"):
                    accepted = api_request(
                        "POST",
                        f"/bookings/{booking['id']}/accept",
                        json={"artisan_id": artisan_id},
                    )
                    if accepted:
                        st.success("Booking accepted — job in progress.")
                        st.rerun()
            with decline_col:
                if st.button("Decline booking", key=f"decline_booking_{booking['id']}"):
                    declined = api_request(
                        "POST",
                        f"/bookings/{booking['id']}/decline",
                        json={"artisan_id": artisan_id},
                    )
                    if declined:
                        st.info("Booking declined; the payment hold was voided.")
                        st.rerun()
    earnings = api_request("GET", f"/artisans/{artisan_id}/earnings")
    if earnings:
        st.subheader("Earnings")
        held, released, pending = st.columns(3)
        held.metric("Held", f"₹{earnings['total_held_inr']}")
        released.metric("Released", f"₹{earnings['total_released_inr']}")
        pending.metric("Awaiting acceptance", f"₹{earnings['total_pending_inr']}")


st.title("FixPune · Local services marketplace")
page = st.sidebar.radio(
    "Prototype views",
    [
        "Artisan onboarding",
        "Customer job booking",
        "Job execution & completion",
        "Artisan job feed",
    ],
)

if page == "Artisan onboarding":
    onboarding_page()
elif page == "Customer job booking":
    customer_page()
elif page == "Job execution & completion":
    execution_page()
else:
    artisan_feed_page()
