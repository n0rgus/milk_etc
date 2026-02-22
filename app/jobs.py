from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, Optional

from .db import SessionLocal
from .models import Item, PriceHistory, ScrapeJob, Store, StoreLink
from .scrape import scrape_item_prices
from .services import get_scrape_settings

_executor = ThreadPoolExecutor(max_workers=1)
_lock = threading.Lock()
_cancel_events: Dict[int, threading.Event] = {}


def enqueue_scrape_job(store: Optional[str] = None) -> int:
    db = SessionLocal()
    try:
        job = ScrapeJob(
            status="queued",
            created_at=datetime.utcnow(),
            store=(store.upper() if store and store.strip() else None),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = int(job.id)
    finally:
        db.close()

    ev = threading.Event()
    with _lock:
        _cancel_events[job_id] = ev

    _executor.submit(_run_scrape_job, job_id, store, ev)
    return job_id


def _run_scrape_job(job_id: int, store: Optional[str], cancel_event: threading.Event) -> None:
    del cancel_event  # reserved for future cancellation support
    db = SessionLocal()
    try:
        job = db.get(ScrapeJob, job_id)
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.message = None
        db.commit()

        store_filter = (store or "ALL").strip().upper()
        items = db.query(Item).order_by(Item.id.asc()).all()
        scrape_settings = get_scrape_settings(db)

        saved_count = 0
        error_count = 0

        for item in items:
            links = db.query(StoreLink).join(Store).filter(StoreLink.item_id == item.id).all()
            eligible = []
            for sl in links:
                if sl.url and (store_filter == "ALL" or sl.store.name == store_filter):
                    eligible.append(sl)
            if not eligible:
                continue

            try:
                results = scrape_item_prices(eligible, settings=scrape_settings)
            except Exception as exc:  # noqa: PERF203
                error_count += 1
                job.message = f"Partial failures so far. Last: item_id={item.id} {type(exc).__name__}"
                db.commit()
                continue

            for store_name, data in results.items():
                st = db.query(Store).filter(Store.name == store_name).first()
                if st is None:
                    continue
                db.add(
                    PriceHistory(
                        item_id=item.id,
                        store_id=st.id,
                        captured_at=datetime.utcnow(),
                        price=data.get("price"),
                        was_price=data.get("was_price"),
                        unit_price=data.get("unit_price"),
                        promo_text=data.get("promo_text"),
                        discount_percent=data.get("discount_percent"),
                    )
                )
                saved_count += 1
            db.commit()

        job.status = "done" if error_count == 0 else "error"
        job.finished_at = datetime.utcnow()
        if error_count == 0:
            job.message = f"OK ({saved_count} price rows saved)"
        else:
            job.message = f"Completed with failures ({saved_count} saved, {error_count} failed items)"
        db.commit()
    except Exception as exc:  # noqa: PERF203
        job = db.get(ScrapeJob, job_id)
        if job:
            job.status = "error"
            job.finished_at = datetime.utcnow()
            job.message = f"{type(exc).__name__}: {exc}"
            db.commit()
    finally:
        db.close()
        with _lock:
            _cancel_events.pop(job_id, None)


def get_job(job_id: int) -> Optional[ScrapeJob]:
    db = SessionLocal()
    try:
        return db.get(ScrapeJob, job_id)
    finally:
        db.close()
