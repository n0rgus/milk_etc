from __future__ import annotations

import os
import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import joinedload

from fastapi import FastAPI, Request, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import SessionLocal, init_db
from .models import (
    Item,
    Store,
    StoreLink,
    PriceHistory,
    ShopSession,
    ShopPurchase,
    CaptureRun,
    CaptureRunItem,
)
from .scrape import scrape_item_prices
from .services import (
    get_latest_prices_for_items,
    compute_best_store_map,
    compute_cycle_insights,
    build_buylist_groups,
    seed_from_json_if_empty,
)

APP_TITLE = "Grocery PriceWatch"

app = FastAPI(title=APP_TITLE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def _startup():
    init_db()
    # Seed from JSON if DB is empty
    seed_path = os.path.join(os.path.dirname(__file__), "..", "seed_items.json")
    db = SessionLocal()
    try:
        seed_from_json_if_empty(db, seed_path)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    db = SessionLocal()
    try:
        items = db.query(Item).order_by(Item.category.asc().nullslast(), Item.name.asc()).all()
        latest = get_latest_prices_for_items(db, [i.id for i in items])
        best = compute_best_store_map(items, latest)
        cycles = compute_cycle_insights(db, [i.id for i in items])
        stores = db.query(Store).order_by(Store.name.asc()).all()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": APP_TITLE,
                "items": items,
                "stores": stores,
                "latest": latest,
                "best": best,
                "cycles": cycles,
            },
        )
    finally:
        db.close()


@app.get("/items/new", response_class=HTMLResponse)
def item_new_form(request: Request):
    db = SessionLocal()
    try:
        stores = db.query(Store).order_by(Store.name.asc()).all()
        return templates.TemplateResponse(
            "item_form.html",
            {"request": request, "title": "Add Item", "item": None, "stores": stores, "links": {}},
        )
    finally:
        db.close()


@app.post("/items/new")
def item_new(
    name: str = Form(...),
    category: str = Form(""),
    brand: str = Form(""),
    buy_freq: str = Form(""),
    buy_qty: Optional[float] = Form(None),
    preferred_store: str = Form(""),
    aldi_label: str = Form(""),
    aldi_url: str = Form(""),
    coles_label: str = Form(""),
    coles_url: str = Form(""),
    woolies_label: str = Form(""),
    woolies_url: str = Form(""),
):
    db = SessionLocal()
    try:
        item = Item(
            name=name.strip(),
            category=(category or "").strip() or None,
            brand=(brand or "").strip() or None,
            buy_freq=(buy_freq or "").strip() or None,
            buy_qty=buy_qty,
            preferred_store=(preferred_store or "").strip() or None,
        )
        db.add(item)
        db.flush()

        def upsert_link(store_name: str, label: str, url: str):
            label = (label or "").strip()
            url = (url or "").strip()
            if not label and not url:
                return
            store = db.query(Store).filter(Store.name == store_name).one()
            db.add(StoreLink(item_id=item.id, store_id=store.id, store_label=label or None, url=url or None))

        upsert_link("ALDI", aldi_label, aldi_url)
        upsert_link("COLES", coles_label, coles_url)
        upsert_link("WOOLWORTHS", woolies_label, woolies_url)

        db.commit()
        return RedirectResponse(url="/", status_code=303)
    finally:
        db.close()


@app.get("/items/{item_id}", response_class=HTMLResponse)
def item_edit_form(request: Request, item_id: int):
    db = SessionLocal()
    try:
        item = db.query(Item).filter(Item.id == item_id).one()
        stores = db.query(Store).order_by(Store.name.asc()).all()
        links = {sl.store.name: sl for sl in db.query(StoreLink).join(Store).filter(StoreLink.item_id == item_id).all()}
        return templates.TemplateResponse(
            "item_form.html",
            {"request": request, "title": f"Edit Item • {item.name}", "item": item, "stores": stores, "links": links},
        )
    finally:
        db.close()


@app.post("/items/{item_id}")
def item_edit(
    item_id: int,
    name: str = Form(...),
    category: str = Form(""),
    brand: str = Form(""),
    buy_freq: str = Form(""),
    buy_qty: Optional[float] = Form(None),
    preferred_store: str = Form(""),
    aldi_label: str = Form(""),
    aldi_url: str = Form(""),
    coles_label: str = Form(""),
    coles_url: str = Form(""),
    woolies_label: str = Form(""),
    woolies_url: str = Form(""),
):
    db = SessionLocal()
    try:
        item = db.query(Item).filter(Item.id == item_id).one()
        item.name = name.strip()
        item.category = (category or "").strip() or None
        item.brand = (brand or "").strip() or None
        item.buy_freq = (buy_freq or "").strip() or None
        item.buy_qty = buy_qty
        item.preferred_store = (preferred_store or "").strip() or None

        store_by_name = {s.name: s for s in db.query(Store).all()}
        links = {sl.store_id: sl for sl in db.query(StoreLink).filter(StoreLink.item_id == item_id).all()}

        def set_link(store_name: str, label: str, url: str):
            store = store_by_name[store_name]
            label = (label or "").strip() or None
            url = (url or "").strip() or None
            if not label and not url:
                # delete if exists
                if store.id in links:
                    db.delete(links[store.id])
                return
            if store.id in links:
                links[store.id].store_label = label
                links[store.id].url = url
            else:
                db.add(StoreLink(item_id=item_id, store_id=store.id, store_label=label, url=url))

        set_link("ALDI", aldi_label, aldi_url)
        set_link("COLES", coles_label, coles_url)
        set_link("WOOLWORTHS", woolies_label, woolies_url)

        db.commit()
        return RedirectResponse(url="/", status_code=303)
    finally:
        db.close()


@app.post("/scrape")
def scrape_now(store: str = Form("ALL")):
    """
    Scrape prices for all items that have URLs for the selected store (or ALL).
    This runs synchronously; for big lists, consider running per-store.
    """
    db = SessionLocal()
    try:
        items = db.query(Item).order_by(Item.id.asc()).all()
        store_filter = store.strip().upper()
        count = 0
        for item in items:
            links = db.query(StoreLink).join(Store).filter(StoreLink.item_id == item.id).all()
            # Only scrape links with URLs
            eligible = []
            for sl in links:
                if sl.url:
                    if store_filter == "ALL" or sl.store.name == store_filter:
                        eligible.append(sl)
            if not eligible:
                continue

            results = scrape_item_prices(eligible)
            # Persist results
            for store_name, data in results.items():
                st = db.query(Store).filter(Store.name == store_name).one()
                ph = PriceHistory(
                    item_id=item.id,
                    store_id=st.id,
                    captured_at=datetime.utcnow(),
                    price=data.get("price"),
                    was_price=data.get("was_price"),
                    unit_price=data.get("unit_price"),
                    promo_text=data.get("promo_text"),
                    discount_percent=data.get("discount_percent"),
                )
                db.add(ph)
                count += 1
            db.commit()

        return RedirectResponse(url="/", status_code=303)
    finally:
        db.close()




def _get_store(db, store_name: str) -> Store:
    return db.query(Store).filter(Store.name == store_name).one()


def _ensure_capture_run(db, store_name: str) -> CaptureRun:
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(hours=6)
    run = (
        db.query(CaptureRun)
        .filter(CaptureRun.store == store_name)
        .filter(CaptureRun.started_at >= cutoff)
        .order_by(CaptureRun.id.desc())
        .first()
    )
    if run:
        return run
    run = CaptureRun(store=store_name, started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@app.get("/api/next")
def api_next(store: str):
    store = store.strip().upper()
    db = SessionLocal()
    try:
        st = _get_store(db, store)
        run = _ensure_capture_run(db, store)

        subq = (
            db.query(CaptureRunItem.item_id)
            .filter(CaptureRunItem.capture_run_id == run.id)
            .filter(CaptureRunItem.store_id == st.id)
            .subquery()
        )

        link = (
            db.query(StoreLink)
            .options(joinedload(StoreLink.item))
            .filter(StoreLink.store_id == st.id)
            .filter(StoreLink.url.isnot(None))
            .filter(StoreLink.url != "")
            .filter(~StoreLink.item_id.in_(subq))
            .order_by(StoreLink.item_id.asc())
            .first()
        )

        if not link:
            return JSONResponse({"done": True})

        return {
            "done": False,
            "capture_run_id": run.id,
            "store": store,
            "item_id": link.item_id,
            "item_name": link.item.name if link.item else None,
            "url": link.url,
        }
    finally:
        db.close()


@app.post("/api/capture")
def api_capture(payload: dict = Body(...)):
    db = SessionLocal()
    try:
        store = str(payload.get("store", "")).strip().upper()
        capture_run_id = int(payload.get("capture_run_id"))
        item_id = int(payload.get("item_id"))

        st = _get_store(db, store)

        ph = PriceHistory(
            item_id=item_id,
            store_id=st.id,
            captured_at=datetime.utcnow(),
            price=float(payload["price"]) if payload.get("price") is not None else None,
            was_price=float(payload["was_price"]) if payload.get("was_price") is not None else None,
            unit_price=float(payload["unit_price"]) if payload.get("unit_price") is not None else None,
            promo_text=(payload.get("promo_text") or None),
            discount_percent=None,
        )
        if ph.price is not None and ph.was_price is not None and ph.was_price > 0 and ph.was_price > ph.price:
            ph.discount_percent = round((ph.was_price - ph.price) / ph.was_price * 100.0, 1)

        db.add(ph)
        db.add(
            CaptureRunItem(
                capture_run_id=capture_run_id,
                item_id=item_id,
                store_id=st.id,
                captured_at=datetime.utcnow(),
            )
        )

        db.commit()
        return {"ok": True}
    finally:
        db.close()

@app.get("/buylist", response_class=HTMLResponse)
def buylist(request: Request):
    db = SessionLocal()
    try:
        items = db.query(Item).order_by(Item.category.asc().nullslast(), Item.name.asc()).all()
        latest = get_latest_prices_for_items(db, [i.id for i in items])
        cycles = compute_cycle_insights(db, [i.id for i in items])
        groups = build_buylist_groups(items, latest, cycles)
        return templates.TemplateResponse(
            "buylist.html",
            {"request": request, "title": "Buy List", "groups": groups},
        )
    finally:
        db.close()


@app.post("/shop/start")
def shop_start():
    db = SessionLocal()
    try:
        session = ShopSession(started_at=datetime.utcnow())
        db.add(session)
        db.commit()
        return RedirectResponse(url=f"/shop/{session.id}", status_code=303)
    finally:
        db.close()


@app.get("/shop/{session_id}", response_class=HTMLResponse)
def shop_view(request: Request, session_id: int):
    db = SessionLocal()
    try:
        session = db.query(ShopSession).filter(ShopSession.id == session_id).one()
        items = db.query(Item).order_by(Item.category.asc().nullslast(), Item.name.asc()).all()
        latest = get_latest_prices_for_items(db, [i.id for i in items])
        cycles = compute_cycle_insights(db, [i.id for i in items])
        groups = build_buylist_groups(items, latest, cycles)

        # existing purchases
        purchased = {
            p.item_id: p for p in db.query(ShopPurchase).filter(ShopPurchase.shop_session_id == session_id).all()
        }

        return templates.TemplateResponse(
            "shop.html",
            {"request": request, "title": f"Shop Session #{session_id}", "session": session, "groups": groups, "purchased": purchased},
        )
    finally:
        db.close()


@app.post("/shop/{session_id}")
def shop_save(session_id: int, purchased_ids: Optional[str] = Form(None)):
    """
    purchased_ids is a comma-separated list of item IDs checked in the UI.
    """
    db = SessionLocal()
    try:
        session = db.query(ShopSession).filter(ShopSession.id == session_id).one()
        keep = set()
        if purchased_ids:
            for part in purchased_ids.split(","):
                part = part.strip()
                if part.isdigit():
                    keep.add(int(part))

        existing = db.query(ShopPurchase).filter(ShopPurchase.shop_session_id == session_id).all()
        existing_by_item = {p.item_id: p for p in existing}

        # Add missing
        for item_id in keep:
            if item_id not in existing_by_item:
                db.add(ShopPurchase(shop_session_id=session_id, item_id=item_id, purchased_at=datetime.utcnow()))

        # Remove unchecked
        for item_id, row in existing_by_item.items():
            if item_id not in keep:
                db.delete(row)

        db.commit()
        return RedirectResponse(url=f"/shop/{session_id}", status_code=303)
    finally:
        db.close()
