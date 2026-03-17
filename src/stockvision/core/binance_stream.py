from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import websocket  # websocket-client

from stockvision.core.market_data import Candle


@dataclass(frozen=True)
class StreamConfig:
    symbol: str         # e.g., BTCUSDT
    interval: str       # e.g., 1m, 5m, 15m, 1h, 4h, 1d


class BinanceKlineStream:
    """
    Threaded Binance websocket stream for klines.

    Calls:
      on_candle(Candle) whenever a kline update arrives (includes in-progress updates)
      on_status(str) to report connection status
    """

    def __init__(
        self,
        cfg: StreamConfig,
        on_candle: Callable[[Candle], None],
        on_status: Callable[[str], None],
    ):
        self.cfg = cfg
        self.on_candle = on_candle
        self.on_status = on_status

        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def _stream_url(self) -> str:
        stream = f"{self.cfg.symbol.lower()}@kline_{self.cfg.interval}"
        return f"wss://stream.binance.com:9443/ws/{stream}"

    def start(self):
        self.stop()  # prevent duplicate streams
        self._stop.clear()

        url = self._stream_url()
        self.on_status(f"Connecting: {url}")

        def on_open(ws):
            self.on_status("✅ Live connected")

        def on_close(ws, code, msg):
            self.on_status(f"⛔ Live disconnected ({code})")

        def on_error(ws, err):
            self.on_status(f"❌ Live error: {err}")

        def on_message(ws, message: str):
            try:
                data = json.loads(message)
                k = data.get("k", {})
                t = int(k["t"])
                o = float(k["o"])
                h = float(k["h"])
                l = float(k["l"])
                c = float(k["c"])
                v = float(k["v"])
                self.on_candle(Candle(t=t, o=o, h=h, l=l, c=c, v=v))
            except Exception:
                return

        self._ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
            on_message=on_message,
        )

        def run():
            while not self._stop.is_set():
                try:
                    self._ws.run_forever(ping_interval=20, ping_timeout=10)
                except Exception as e:
                    self.on_status(f"❌ Live run exception: {e}")

                if self._stop.is_set():
                    break

                self.on_status("Reconnecting in 2s…")
                time.sleep(2)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        self._ws = None
        self._thread = None
        self.on_status("Live stopped.")
