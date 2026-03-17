from __future__ import annotations

import json
import csv
import io
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Candle:
    # time in milliseconds since epoch (UTC)
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float = 0.0


class MarketDataError(Exception):
    pass


def _http_get_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "StockVision/0.1 (+https://github.com/thepurgehacker127/StockVision)"
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except Exception as e:
        raise MarketDataError(f"HTTP GET failed: {url} -> {e}") from e


def _epoch_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def normalize_symbol(user_symbol: str) -> Tuple[str, str]:
    """
    Returns (kind, normalized_symbol)
    kind: 'crypto' or 'stock'
    normalized_symbol:
      - crypto: Binance symbol (e.g., BTCUSDT)
      - stock: Stooq symbol (e.g., aapl.us)
    """
    s = (user_symbol or "").strip().upper()

    # common crypto forms: BTC-USD, ETH-USD, BTCUSD
    if "-USD" in s or s.endswith("USD") or s in {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"}:
        base = s.replace("-", "")
        if base.endswith("USD"):
            base = base[:-3]
        base = base.replace("USD", "")
        if not base:
            raise MarketDataError(f"Invalid crypto symbol: {user_symbol}")
        # Binance uses USDT pairs commonly
        return "crypto", f"{base}USDT"

    # otherwise treat as stock/ETF
    # stooq uses lowercase and markets like .us
    st = s.lower()
    if "." not in st:
        st = f"{st}.us"
    return "stock", st


def fetch_stooq_daily(stooq_symbol: str, limit: int = 400) -> List[Candle]:
    """
    Free daily OHLCV from Stooq:
      https://stooq.com/q/d/l/?s=aapl.us&i=d
    """
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    text = _http_get_text(url)

    # Stooq CSV columns: Date,Open,High,Low,Close,Volume
    reader = csv.DictReader(io.StringIO(text))
    out: List[Candle] = []
    for row in reader:
        try:
            # Date format: YYYY-MM-DD
            dt = datetime.strptime(row["Date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            t = _epoch_ms(dt)
            o = float(row["Open"])
            h = float(row["High"])
            l = float(row["Low"])
            c = float(row["Close"])
            v = float(row.get("Volume", "0") or 0)
            out.append(Candle(t=t, o=o, h=h, l=l, c=c, v=v))
        except Exception:
            # skip malformed rows
            continue

    if not out:
        raise MarketDataError(f"No data returned from Stooq for {stooq_symbol}")

    # keep most recent 'limit'
    return out[-limit:]


def fetch_binance_klines(binance_symbol: str, interval: str = "1h", limit: int = 500) -> List[Candle]:
    """
    Free candles from Binance (no key):
      https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=500
    intervals: 1m,5m,15m,1h,4h,1d,...
    """
    url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={interval}&limit={limit}"
    text = _http_get_text(url)
    try:
        data = json.loads(text)
    except Exception as e:
        raise MarketDataError(f"Binance JSON parse failed: {e}") from e

    if not isinstance(data, list) or not data:
        raise MarketDataError(f"No data returned from Binance for {binance_symbol}")

    out: List[Candle] = []
    for k in data:
        # kline format:
        # [ openTime, open, high, low, close, volume, closeTime, ... ]
        try:
            t = int(k[0])  # already ms
            o = float(k[1])
            h = float(k[2])
            l = float(k[3])
            c = float(k[4])
            v = float(k[5])
            out.append(Candle(t=t, o=o, h=h, l=l, c=c, v=v))
        except Exception:
            continue

    if not out:
        raise MarketDataError(f"Binance returned malformed klines for {binance_symbol}")

    return out
