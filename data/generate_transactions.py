"""
Payment Transaction Analytics — synthetic data generator
=========================================================

Generates ~1.2M realistic payment transactions across five African markets
(Nigeria, Kenya, Ghana, South Africa, Egypt) over a 12-month period with
daily + hourly granularity.

Design goals
------------
* Realistic TPV, success-rate, and failure-mix differences across:
    - merchants (SMB vs Enterprise)
    - payment methods (Cards vs Bank Transfer vs Mobile Money)
    - countries (infra reliability differs)
    - hour-of-day / day-of-week (peak vs off-peak)
* Believable failure-reason distribution (insufficient funds, fraud, timeout, ...)
* Deterministic when seeded — reproducible for portfolio reviewers.

Run:
    python data/generate_transactions.py --rows 1200000 --out data/transactions.parquet
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

# --------------------------------------------------------------------------- #
# Reference data — African fintech context                                    #
# --------------------------------------------------------------------------- #

COUNTRIES = {
    "NG": {"name": "Nigeria",  "currency": "NGN", "fx_to_usd": 0.00065, "weight": 0.34, "infra_score": 0.86},
    "KE": {"name": "Kenya",    "currency": "KES", "fx_to_usd": 0.0072, "weight": 0.22, "infra_score": 0.91},
    "GH": {"name": "Ghana",    "currency": "GHS", "fx_to_usd": 0.072,  "weight": 0.12, "infra_score": 0.88},
    "ZA": {"name": "South Africa", "currency": "ZAR", "fx_to_usd": 0.054, "weight": 0.22, "infra_score": 0.95},
    "EG": {"name": "Egypt",    "currency": "EGP", "fx_to_usd": 0.021,  "weight": 0.10, "infra_score": 0.89},
}

# Payment methods with realistic African fintech mix
PAYMENT_METHODS = {
    "card": {
        "label": "Card",
        "weight": 0.32,
        "providers": ["Visa", "Mastercard", "Verve"],
        "base_success": 0.925,
    },
    "bank_transfer": {
        "label": "Bank Transfer",
        "weight": 0.28,
        "providers": ["NIBSS", "PesaLink", "GHIPSS", "EAC", "EgyPTS"],
        "base_success": 0.952,
    },
    "mobile_money": {
        "label": "Mobile Money",
        "weight": 0.36,
        "providers": ["MTN MoMo", "Airtel Money", "M-Pesa", "Vodafone Cash", "Orange Money", "Fawry"],
        "base_success": 0.941,
    },
    "ussd": {
        "label": "USSD",
        "weight": 0.04,
        "providers": ["USSD"],
        "base_success": 0.918,
    },
}

# Merchant segments — ticket_mu / ticket_sigma are log-normal params for USD amount.
# Medians (e^mu) reflect realistic African fintech ticket sizes.
MERCHANT_SEGMENTS = {
    "ecommerce":     {"weight": 0.26, "ticket_mu": 3.4, "ticket_sigma": 0.9, "success_boost": 0.0},   # ~$30
    "bill_pay":      {"weight": 0.18, "ticket_mu": 3.0, "ticket_sigma": 0.7, "success_boost": 0.015}, # ~$20
    "ride_hailing":  {"weight": 0.12, "ticket_mu": 2.0, "ticket_sigma": 0.5, "success_boost": 0.008}, # ~$7
    "food_delivery": {"weight": 0.11, "ticket_mu": 2.5, "ticket_sigma": 0.6, "success_boost": 0.005}, # ~$12
    "streaming":     {"weight": 0.09, "ticket_mu": 2.4, "ticket_sigma": 0.4, "success_boost": 0.020}, # ~$11
    "betting":       {"weight": 0.08, "ticket_mu": 2.3, "ticket_sigma": 0.8, "success_boost": -0.030},# ~$10
    "travel":        {"weight": 0.06, "ticket_mu": 4.8, "ticket_sigma": 1.0, "success_boost": -0.010},# ~$120
    "savings":       {"weight": 0.06, "ticket_mu": 3.2, "ticket_sigma": 1.0, "success_boost": 0.025}, # ~$25
    "insurance":     {"weight": 0.04, "ticket_mu": 3.7, "ticket_sigma": 0.7, "success_boost": 0.010}, # ~$40
}

# Generate ~200 merchants distributed across segments + countries
def _build_merchants(n: int = 220, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    seg_names = list(MERCHANT_SEGMENTS.keys())
    seg_weights = np.array([MERCHANT_SEGMENTS[s]["weight"] for s in seg_names])
    seg_weights /= seg_weights.sum()
    country_codes = list(COUNTRIES.keys())
    country_weights = np.array([COUNTRIES[c]["weight"] for c in country_codes])
    country_weights /= country_weights.sum()

    for i in range(n):
        seg = rng.choice(seg_names, p=seg_weights)
        cc = rng.choice(country_codes, p=country_weights)
        tier = rng.choice(["enterprise", "mid_market", "smb"], p=[0.12, 0.38, 0.50])
        name = f"{COUNTRIES[cc]['name'].split()[0]} {seg.replace('_',' ').title()} {i:03d}"
        rows.append({
            "merchant_id": f"M{i+1:04d}",
            "merchant_name": name,
            "segment": seg,
            "tier": tier,
            "country": cc,
            "onboarded_at": datetime(2024, 1, 1) + timedelta(days=int(rng.integers(0, 365))),
        })
    return pd.DataFrame(rows)

# Failure reasons with realistic probabilities per failure event
FAILURE_REASONS = {
    "insufficient_funds": 0.34,
    "card_declined":      0.18,
    "network_timeout":    0.16,
    "fraud_suspected":    0.09,
    "limit_exceeded":     0.08,
    "invalid_account":    0.07,
    "bank_downtime":      0.05,
    "expired_card":       0.03,
}

# Channels
CHANNELS = {"web": 0.42, "mobile_app": 0.38, "ussd": 0.10, "pos": 0.07, "api": 0.03}

# Customer types
CUSTOMER_TYPES = {"new": 0.18, "returning": 0.62, "repeat_high_value": 0.20}

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _weighted_keys(d: dict, key: str = "weight") -> tuple[list, np.ndarray]:
    """Extract keys + normalised weights from a dict whose values are either
    plain floats (weight) or sub-dicts containing `key`."""
    keys = list(d.keys())
    raw = []
    for k in keys:
        v = d[k]
        raw.append(v if isinstance(v, (int, float)) else v[key])
    w = np.array(raw, dtype=float)
    w /= w.sum()
    return keys, w

def _hour_weight(h: int) -> float:
    """Higher activity during business + evening hours (Africa time, UTC+1 to UTC+2)."""
    if 9 <= h <= 11:   return 1.20   # Morning rush
    if 12 <= h <= 14:  return 1.05   # Lunch
    if 15 <= h <= 17:  return 1.15   # Afternoon
    if 18 <= h <= 21:  return 1.35   # Evening peak (mobile money, betting, food)
    if 22 <= h <= 23:  return 0.85   # Late night
    if 0 <= h <= 5:    return 0.35   # Dead hours
    return 0.95                # 6-8

def _dow_weight(d: int) -> float:
    """Mon–Sun (0=Mon). Friday + Saturday peak in Africa."""
    return [1.0, 1.0, 1.0, 1.05, 1.20, 1.25, 0.85][d]

# --------------------------------------------------------------------------- #
# Main generator                                                              #
# --------------------------------------------------------------------------- #

def generate(rows: int = 1_200_000,
             start: str = "2025-01-01",
             end: str = "2025-12-31",
             seed: int = 42) -> pd.DataFrame:
    """Generate `rows` synthetic transactions as a pandas DataFrame."""
    rng = np.random.default_rng(seed)
    random.seed(seed)

    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    span_days = (end_dt - start_dt).days + 1
    if span_days <= 0:
        raise ValueError("end date must be after start date")

    merchants = _build_merchants(seed=seed)
    merchant_ids = merchants["merchant_id"].tolist()
    m_by_id = merchants.set_index("merchant_id").to_dict("index")

    country_keys, country_w = _weighted_keys(COUNTRIES)
    method_keys,   method_w  = _weighted_keys(PAYMENT_METHODS)
    channel_keys,  channel_w = _weighted_keys(CHANNELS)
    cust_keys,     cust_w    = _weighted_keys(CUSTOMER_TYPES)
    fail_reasons   = list(FAILURE_REASONS.keys())
    fail_probs     = np.array(list(FAILURE_REASONS.values()))
    fail_probs    /= fail_probs.sum()

    # Pre-compute hour + dow weights (vectorizable)
    hours = np.arange(24)
    hour_w = np.array([_hour_weight(h) for h in hours])
    hour_w /= hour_w.sum()
    dows = np.arange(7)
    dow_w = np.array([_dow_weight(d) for d in dows])
    dow_w /= dow_w.sum()

    # Pick transaction day: first pick dow distribution, then a date with that dow
    chosen_dows = rng.choice(dows, size=rows, p=dow_w)
    offsets = np.empty(rows, dtype=np.int64)
    for d in dows:
        mask = chosen_dows == d
        n_d = int(mask.sum())
        # All dates in span with this day-of-week
        valid_offsets = [i for i in range(span_days) if (start_dt + timedelta(days=i)).weekday() == d]
        offsets[mask] = rng.choice(valid_offsets, size=n_d, replace=True)

    tx_dates = start_dt + pd.to_timedelta(offsets, unit="D")
    tx_hours = rng.choice(hours, size=rows, p=hour_w)
    tx_minutes = rng.integers(0, 60, size=rows)
    timestamps = pd.to_datetime(tx_dates) + pd.to_timedelta(tx_hours, unit="h") + pd.to_timedelta(tx_minutes, unit="m")

    # Merchant assignment (weighted by tier — enterprise merchants have higher volume)
    tier_mult = {"enterprise": 4.0, "mid_market": 1.6, "smb": 0.6}
    m_weights = np.array([tier_mult[m_by_id[m]["tier"]] for m in merchant_ids], dtype=float)
    m_weights /= m_weights.sum()
    chosen_merchants = rng.choice(merchant_ids, size=rows, p=m_weights)

    # Vectorised enrichment: pandas merge with the merchants frame
    tx_m = pd.DataFrame({"merchant_id": chosen_merchants})
    tx_m = tx_m.merge(merchants[["merchant_id", "country", "segment", "tier"]], on="merchant_id", how="left")
    countries = tx_m["country"].to_numpy()
    segments  = tx_m["segment"].to_numpy()
    tiers     = tx_m["tier"].to_numpy()

    # Payment method — vectorised per-country using a small lookup table
    # Pre-compute per-country method probability vectors
    method_idx = {m: i for i, m in enumerate(method_keys)}
    country_method_probs = {}
    for cc in COUNTRIES:
        w = method_w.copy()
        if cc in ("NG", "KE", "GH"):
            w[method_idx["mobile_money"]]   *= 1.25
            w[method_idx["bank_transfer"]]  *= 1.10
        elif cc == "ZA":
            w[method_idx["card"]]           *= 1.30
        elif cc == "EG":
            w[method_idx["mobile_money"]]   *= 1.10
        w = w / w.sum()
        country_method_probs[cc] = w

    # Assign method per row, grouped by country for speed
    methods = np.empty(rows, dtype=object)
    method_arr = np.empty(rows, dtype=object)
    provider_arr = np.empty(rows, dtype=object)
    unique_cc = np.unique(countries)
    for cc in unique_cc:
        mask = countries == cc
        n_cc = int(mask.sum())
        chosen = rng.choice(method_keys, size=n_cc, p=country_method_probs[cc])
        methods[mask] = chosen
        method_arr[mask] = [PAYMENT_METHODS[m]["label"] for m in chosen]
        # Provider assignment — write through boolean mask into the master array
        # (avoid chained indexing: use the indices that map back to global rows)
        global_idx = np.where(mask)[0]
        for m in method_keys:
            sub_local = chosen == m
            if sub_local.any():
                picks = rng.choice(PAYMENT_METHODS[m]["providers"], size=int(sub_local.sum()))
                provider_arr[global_idx[sub_local]] = picks

    # Channels + customer types (vectorized)
    channels_arr = rng.choice(channel_keys, size=rows, p=channel_w)
    cust_arr = rng.choice(cust_keys, size=rows, p=cust_w)

    # Amounts — log-normal in USD using segment ticket size, then convert to local currency
    seg_of_row = np.array([MERCHANT_SEGMENTS[s]["ticket_mu"] for s in segments])
    seg_sigma = np.array([MERCHANT_SEGMENTS[s]["ticket_sigma"] for s in segments])
    amounts_usd = np.round(np.exp(rng.normal(seg_of_row, seg_sigma)), 2)
    # Floor at $0.50 (min realistic payment) and cap at $5,000 (rare large purchase)
    amounts_usd = np.clip(amounts_usd, 0.50, 5000.0)

    # Convert to local currency
    fx_arr = np.array([COUNTRIES[c]["fx_to_usd"] for c in countries])
    amounts_local = np.round(amounts_usd / fx_arr, 2)

    # Currency
    currency_arr = np.array([COUNTRIES[c]["currency"] for c in countries])

    # ---- Success probability per transaction ----
    base = np.array([PAYMENT_METHODS[m]["base_success"] for m in methods])
    seg_boost = np.array([MERCHANT_SEGMENTS[s]["success_boost"] for s in segments])
    infra_boost = np.array([(COUNTRIES[c]["infra_score"] - 0.90) * 0.5 for c in countries])

    # Off-hours slightly worse; peak hours slightly worse (congestion)
    hour_penalty = np.where((tx_hours < 6) | (tx_hours >= 22), -0.008,
                            np.where((tx_hours >= 18) & (tx_hours <= 21), -0.004, 0.0))
    # High-value transactions slightly riskier
    high_val_penalty = np.where(amounts_usd > 200, -0.015,
                                np.where(amounts_usd > 50, -0.005, 0.0))
    # New customers slightly riskier
    new_pen = np.where(cust_arr == "new", -0.010, 0.0)
    # USSD channel slightly worse
    ussd_pen = np.where(channels_arr == "ussd", -0.006, 0.0)

    p_success = np.clip(base + seg_boost + infra_boost + hour_penalty + high_val_penalty + new_pen + ussd_pen, 0.70, 0.995)
    rand_draw = rng.random(size=rows)
    is_success = rand_draw < p_success

    # Status + failure reasons
    status_arr = np.where(is_success, "success", "failed")
    fail_mask = ~is_success
    reason_arr = np.empty(rows, dtype=object)
    if fail_mask.any():
        n_fail = int(fail_mask.sum())
        reason_arr[fail_mask] = rng.choice(fail_reasons, size=n_fail, p=fail_probs)
    reason_arr[~fail_mask] = None

    # Response time (ms) — successful transactions tend to be faster
    response_ms = np.where(
        is_success,
        rng.integers(180, 1800, size=rows),
        rng.integers(900, 4500, size=rows),
    )

    # Build transaction IDs
    tx_ids = np.array([f"TX{2025}{i:09d}" for i in range(rows)])

    df = pd.DataFrame({
        "transaction_id":    tx_ids,
        "timestamp":         timestamps,
        "merchant_id":       chosen_merchants,
        "country":           countries,
        "currency":          currency_arr,
        "payment_method":    methods,
        "payment_method_label": method_arr,
        "provider":          provider_arr,
        "channel":           channels_arr,
        "customer_type":     cust_arr,
        "amount_local":      amounts_local,
        "amount_usd":        amounts_usd,
        "status":            status_arr,
        "failure_reason":    reason_arr,
        "response_ms":       response_ms,
        "segment":           segments,
        "merchant_tier":     tiers,
    })

    # Sort by timestamp for cleaner storage
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df, merchants


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic payment transactions.")
    parser.add_argument("--rows", type=int, default=1_200_000, help="Number of transactions (default: 1.2M)")
    parser.add_argument("--out",  type=str, default="data/transactions.parquet")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=str, default="2025-01-01")
    parser.add_argument("--end",   type=str, default="2025-12-31")
    args = parser.parse_args()

    print(f"Generating {args.rows:,} transactions (seed={args.seed})...")
    df, merchants = generate(rows=args.rows, start=args.start, end=args.end, seed=args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    merchants.to_parquet(out_path.parent / "merchants.parquet", index=False)
    # Also write a small CSV slice for quick inspection / GitHub preview
    df.head(1000).to_csv(out_path.parent / "transactions_sample.csv", index=False)
    merchants.to_csv(out_path.parent / "merchants.csv", index=False)

    print(f"\n  Wrote {len(df):,} transactions -> {out_path}")
    print(f"  Wrote {len(merchants)} merchants     -> {out_path.parent / 'merchants.parquet'}")
    print(f"  Sample CSV (1k rows)         -> {out_path.parent / 'transactions_sample.csv'}")
    print("\nKPIs (sanity check):")
    print(f"  TPV (USD):         ${df['amount_usd'].sum():,.2f}")
    print(f"  Volume:            {len(df):,}")
    print(f"  Avg ticket (USD):  ${df['amount_usd'].mean():,.2f}")
    print(f"  Success rate:      {(df['status']=='success').mean()*100:.2f}%")
    print(f"  Date range:        {df['timestamp'].min().date()} -> {df['timestamp'].max().date()}")
    print(f"  Countries:         {sorted(df['country'].unique())}")
    print(f"  Methods:           {sorted(df['payment_method'].unique())}")


if __name__ == "__main__":
    main()
