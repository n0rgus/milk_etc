from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from .models import Item, Store, StoreLink, PriceHistory

def seed_from_json_if_empty(db: Session, seed_path: str) -> None:
    if db.query(Item).count() > 0:
        return

    # ensure stores exist
    for name in ["ALDI", "COLES", "WOOLWORTHS"]:
        if db.query(Store).filter(Store.name == name).count() == 0:
            db.add(Store(name=name))
    db.commit()

    with open(seed_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    stores = {s.name: s for s in db.query(Store).all()}

    for r in rows:
        item = Item(
            name=r.get("name"),
            category=r.get("category"),
            brand=r.get("brand"),
            buy_freq=r.get("buy_freq"),
            buy_qty=r.get("buy_qty"),
            preferred_store=r.get("preferred_store"),
        )
        db.add(item)
        db.flush()

        store_map = r.get("stores") or {}
        for store_name, payload in store_map.items():
            if not payload:
                continue
            db.add(StoreLink(
                item_id=item.id,
                store_id=stores[store_name].id,
                store_label=payload.get("label"),
                url=payload.get("url") or None,
            ))
    db.commit()


def get_latest_prices_for_items(db: Session, item_ids: List[int]) -> Dict[int, Dict[str, PriceHistory]]:
    """
    Returns: {item_id: {STORE_NAME: latest_price_row}}
    """
    if not item_ids:
        return {}
    subq = (
        db.query(
            PriceHistory.item_id.label("item_id"),
            PriceHistory.store_id.label("store_id"),
            func.max(PriceHistory.captured_at).label("max_ts"),
        )
        .filter(PriceHistory.item_id.in_(item_ids))
        .group_by(PriceHistory.item_id, PriceHistory.store_id)
        .subquery()
    )

    rows = (
        db.query(PriceHistory, Store)
        .join(Store, Store.id == PriceHistory.store_id)
        .join(subq, and_(
            subq.c.item_id == PriceHistory.item_id,
            subq.c.store_id == PriceHistory.store_id,
            subq.c.max_ts == PriceHistory.captured_at,
        ))
        .all()
    )

    out: Dict[int, Dict[str, PriceHistory]] = {i: {} for i in item_ids}
    for ph, store in rows:
        out.setdefault(ph.item_id, {})[store.name] = ph
    return out


def compute_best_store_map(items: List[Item], latest: Dict[int, Dict[str, PriceHistory]]) -> Dict[int, Tuple[str, float] | None]:
    """
    For each item, pick the cheapest current price among stores with a latest price.
    Returns {item_id: (store_name, price)} or None
    """
    best: Dict[int, Tuple[str, float] | None] = {}
    for item in items:
        candidates = []
        for store_name, ph in (latest.get(item.id) or {}).items():
            if ph.price is not None:
                candidates.append((store_name, ph.price))
        best[item.id] = min(candidates, key=lambda x: x[1]) if candidates else None
    return best


def compute_cycle_insights(db: Session, item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Basic cycle model per item (across all stores):
    - min historical price per store
    - last discount date per store
    - avg interval between discounts per store (days)
    - next expected discount (date) per store
    """
    insights: Dict[int, Dict[str, Any]] = {i: {} for i in item_ids}
    if not item_ids:
        return insights

    stores = db.query(Store).all()
    store_by_id = {s.id: s.name for s in stores}

    # Pull discount events: where discount_percent >= 10 OR was_price not null and was_price > price
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.item_id.in_(item_ids))
        .filter(
            (PriceHistory.discount_percent != None) | (PriceHistory.was_price != None)
        )
        .order_by(PriceHistory.item_id.asc(), PriceHistory.store_id.asc(), PriceHistory.captured_at.asc())
        .all()
    )

    # min price per store
    mins = (
        db.query(
            PriceHistory.item_id, PriceHistory.store_id, func.min(PriceHistory.price)
        )
        .filter(PriceHistory.item_id.in_(item_ids))
        .filter(PriceHistory.price != None)
        .group_by(PriceHistory.item_id, PriceHistory.store_id)
        .all()
    )
    min_map = {(i, s): p for i, s, p in mins}

    # build per item/store discount timestamps
    from collections import defaultdict
    ts_map = defaultdict(list)
    for ph in rows:
        # treat as discount if it really looks discounted
        is_disc = False
        if ph.discount_percent is not None and ph.discount_percent >= 10:
            is_disc = True
        elif ph.was_price is not None and ph.price is not None and ph.was_price > ph.price:
            is_disc = True
        if is_disc:
            ts_map[(ph.item_id, ph.store_id)].append(ph.captured_at)

    for item_id in item_ids:
        per_store: Dict[str, Any] = {}
        for s in stores:
            key = (item_id, s.id)
            dts = ts_map.get(key, [])
            avg_days = None
            last_disc = None
            next_expected = None
            if len(dts) >= 2:
                gaps = []
                for a, b in zip(dts[:-1], dts[1:]):
                    gaps.append((b - a).days)
                gaps = [g for g in gaps if g > 0]
                if gaps:
                    avg_days = round(sum(gaps) / len(gaps), 1)
            if dts:
                last_disc = dts[-1]
                if avg_days:
                    next_expected = last_disc + timedelta(days=float(avg_days))
            per_store[s.name] = {
                "min_price": min_map.get(key),
                "last_discount": last_disc,
                "avg_discount_interval_days": avg_days,
                "next_expected_discount": next_expected,
            }
        insights[item_id] = per_store
    return insights


def build_buylist_groups(items: List[Item], latest: Dict[int, Dict[str, PriceHistory]], cycles: Dict[int, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group items by which store to buy at (based on cheapest current price).
    Adds simple WAIT suggestion if next expected discount is soon.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {"ALDI": [], "COLES": [], "WOOLWORTHS": [], "UNPRICED": []}

    for item in items:
        lp = latest.get(item.id) or {}
        candidates = [(store, ph.price, ph) for store, ph in lp.items() if ph.price is not None]
        if not candidates:
            groups["UNPRICED"].append({"item": item, "best": None, "note": "No captured prices yet", "latest": lp, "wait": False})
            continue
        store_name, price, best_ph = min(candidates, key=lambda x: x[1])

        # simple WAIT rule
        wait = False
        note = ""
        cyc = (cycles.get(item.id) or {}).get(store_name) or {}
        next_expected = cyc.get("next_expected_discount")
        min_price = cyc.get("min_price")

        if next_expected and isinstance(next_expected, datetime):
            days_to = (next_expected.date() - datetime.utcnow().date()).days
            if 0 <= days_to <= 14 and min_price and price > min_price * 1.05:
                wait = True
                note = f"Likely discount in ~{days_to} days (based on history)"

        groups.setdefault(store_name, []).append({"item": item, "best": (store_name, price, best_ph), "note": note, "latest": lp, "wait": wait})

    # sort within each group
    for k in groups:
        groups[k].sort(key=lambda row: ((row["item"].category or "ZZZ"), row["item"].name))
    return groups
