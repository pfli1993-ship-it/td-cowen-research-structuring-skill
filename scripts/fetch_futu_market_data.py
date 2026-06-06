#!/usr/bin/env python3
"""Fetch current Futu quote snapshot plus YTD change for public companies."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from futu import AuType, KLType, OpenQuoteContext, RET_OK


def market_currency(code: str) -> str:
    prefix = code.split(".", 1)[0].upper()
    return {"US": "USD", "HK": "HKD", "SH": "CNY", "SZ": "CNY"}.get(prefix, "")


def display_market_cap(value: float | None, currency: str) -> str:
    if not value or value <= 0:
        return "暂无有效数据"
    if currency == "USD":
        if value >= 1e12:
            return f"{value / 1e12:.2f}T USD"
        return f"{value / 1e9:.2f}B USD"
    if currency == "HKD":
        return f"{value / 1e9:.2f}B HKD"
    if currency == "CNY":
        return f"{value / 1e8:.2f}亿元"
    return f"{value:,.0f}"


def fetch_one(ctx: OpenQuoteContext, company: str, code: str, today: str) -> dict:
    currency = market_currency(code)
    base = {
        "company": company,
        "code": code,
        "quote_source": "Futu OpenAPI",
        "currency": currency,
    }
    ret, snap = ctx.get_market_snapshot([code])
    if ret != RET_OK:
        return {**base, "error": str(snap)}
    if len(snap) == 0:
        return {**base, "error": "Futu returned no snapshot data"}
    row = snap.iloc[0]
    last_price = float(row.get("last_price") or 0)
    market_cap = float(row.get("total_market_val") or 0)
    quote_time = str(row.get("update_time") or "")
    ytd_change = None
    ytd_error = ""
    ret, kline, _ = ctx.request_history_kline(
        code,
        start=f"{dt.date.today().year}-01-01",
        end=today,
        ktype=KLType.K_DAY,
        autype=AuType.QFQ,
        max_count=1000,
    )
    if ret == RET_OK and len(kline) > 0:
        first_close = float(kline.iloc[0].get("close") or 0)
        latest_close = float(kline.iloc[-1].get("close") or last_price or 0)
        if first_close > 0:
            ytd_change = (latest_close / first_close - 1) * 100
    else:
        ytd_error = str(kline)
    return {
        **base,
        "quote_time": quote_time,
        "last_price": last_price,
        "last_price_display": f"{last_price:.2f} {currency}" if last_price > 0 else "暂无有效数据",
        "market_cap": market_cap,
        "market_cap_display": display_market_cap(market_cap, currency),
        "ytd_change_pct": ytd_change,
        "ytd_change_display": f"{ytd_change:+.1f}%" if ytd_change is not None else "暂无有效数据",
        "error": ytd_error,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", nargs="+", help="Company=CODE, e.g. Biogen=US.BIIB")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()
    today = dt.date.today().isoformat()
    mappings = []
    for pair in args.pairs:
        if "=" not in pair:
            raise SystemExit(f"Invalid pair: {pair}. Use Company=CODE")
        company, code = pair.split("=", 1)
        mappings.append((company, code))
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        records = [fetch_one(ctx, company, code, today) for company, code in mappings]
    finally:
        ctx.close()
    payload = {"as_of": dt.datetime.now().isoformat(timespec="seconds"), "data": records}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
