from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QSize, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QToolBar, QStatusBar, QDockWidget, QListWidget, QTextEdit, QFrame,
    QTabWidget, QComboBox, QCheckBox
)
import qtawesome as qta

from stockvision.ui.chart_widget import ChartWidget
from stockvision.core.market_data import (
    normalize_symbol, fetch_stooq_daily, fetch_binance_klines, MarketDataError, Candle
)
from stockvision.core.settings import load_settings, save_settings, AppSettings


class FetchWorker(QObject):
    finished = Signal(str, object)
    failed = Signal(str)

    def __init__(self, symbols: List[str], interval: str, compare: bool):
        super().__init__()
        self.symbols = symbols
        self.interval = interval
        self.compare = compare

    def run(self):
        try:
            if not self.symbols:
                self.failed.emit("No symbols selected.")
                return

            if self.compare:
                data: Dict[str, List[Candle]] = {}
                for s in self.symbols:
                    kind, norm = normalize_symbol(s)
                    if kind == "crypto":
                        data[s] = fetch_binance_klines(norm, interval=self.interval, limit=500)
                    else:
                        data[s] = fetch_stooq_daily(norm, limit=400)
                self.finished.emit("compare", data)
                return

            s = self.symbols[0]
            kind, norm = normalize_symbol(s)
            if kind == "crypto":
                candles = fetch_binance_klines(norm, interval=self.interval, limit=500)
            else:
                candles = fetch_stooq_daily(norm, limit=400)
            self.finished.emit("single", (s, candles))

        except MarketDataError as e:
            self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(f"Unexpected error: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("StockVision")
        self.setMinimumSize(1200, 720)

        self._thread: Optional[QThread] = None
        self._worker: Optional[FetchWorker] = None

        self._default_watchlist = ["AAPL", "MSFT", "TSLA", "NVDA", "BTC-USD", "ETH-USD"]
        self._settings: AppSettings = load_settings(self._default_watchlist)

        self._build_toolbar()
        self._build_statusbar()
        self._build_docks()
        self._build_central()

        # update OHLC bar from crosshair
        self.chart.crosshair_info.connect(self._on_crosshair_info)

        if self.watchlist.count() > 0:
            self.watchlist.setCurrentRow(0)

    # ---------- Toolbar ----------
    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        brand_icon = QLabel()
        brand_icon.setPixmap(qta.icon("fa5s.chart-line", color="#2b72ff").pixmap(18, 18))

        brand_title = QLabel("StockVision")
        brand_title.setObjectName("BrandTitle")

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search ticker (AAPL) or crypto (BTC-USD)")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(360)
        self.search.returnPressed.connect(self._add_from_search)

        btn_add = QPushButton("Add")
        btn_add.setIcon(qta.icon("fa5s.plus", color="#e6e6e6"))
        btn_add.clicked.connect(self._add_from_search)

        self.interval = QComboBox()
        self.interval.addItems(["1m", "5m", "15m", "1h", "4h", "1d"])
        self.interval.setCurrentText("1h")
        self.interval.currentTextChanged.connect(lambda _x: self._refresh())

        self.compare = QCheckBox("Compare")
        self.compare.stateChanged.connect(self._on_compare_toggle)

        self.normalize = QCheckBox("Normalize")
        self.normalize.setChecked(True)
        self.normalize.setToolTip("Compare mode: show % change from start (on) vs raw price (off)")
        self.normalize.stateChanged.connect(lambda _s: self._refresh())
        self.normalize.setEnabled(False)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(qta.icon("fa5s.sync", color="#e6e6e6"))
        btn_refresh.clicked.connect(self._refresh)

        tb.addWidget(brand_icon)
        tb.addWidget(QLabel("  "))
        tb.addWidget(brand_title)
        tb.addSeparator()
        tb.addWidget(self.search)
        tb.addWidget(btn_add)
        tb.addSeparator()
        tb.addWidget(QLabel("Interval: "))
        tb.addWidget(self.interval)
        tb.addWidget(self.compare)
        tb.addWidget(self.normalize)
        tb.addWidget(btn_refresh)

    def _on_compare_toggle(self, _state):
        self.normalize.setEnabled(self.compare.isChecked())
        self._refresh()

    # ---------- Status ----------
    def _build_statusbar(self):
        sb = QStatusBar()
        sb.showMessage("Ready. Step 5: OHLC info bar + axis zoom + watchlist persistence.")
        self.setStatusBar(sb)

    # ---------- Docks ----------
    def _build_docks(self):
        self.watchlist = QListWidget()
        self.watchlist.addItems(self._settings.watchlist)
        self.watchlist.setSelectionMode(QListWidget.ExtendedSelection)
        self.watchlist.itemSelectionChanged.connect(self._refresh)

        dock_left = QDockWidget("Watchlist (multi-select for compare)", self)
        dock_left.setWidget(self.watchlist)
        dock_left.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock_left)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setText(
            "Step 5 added:\n"
            "- OHLC info bar updates with crosshair\n"
            "- Ctrl+wheel zoom X only, Shift+wheel zoom Y only\n"
            "- Compare normalize toggle\n"
            "- Watchlist auto-saves\n"
        )

        dock_right = QDockWidget("Details", self)
        dock_right.setWidget(self.details)
        dock_right.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_right)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self._log("App started. Step 5 UX enhancements active.")

        dock_bottom = QDockWidget("Event Log", self)
        dock_bottom.setWidget(self.log)
        dock_bottom.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock_bottom)

    # ---------- Central ----------
    def _build_central(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        header = QLabel("Chart Workspace")
        header.setStyleSheet("font-size: 18px; font-weight: 800;")

        # Info bar (TradingView-like)
        self.ohlc_bar = QLabel("Move mouse over chart → OHLC will appear here.")
        self.ohlc_bar.setStyleSheet(
            "padding: 6px 10px; border-radius: 10px; "
            "background: rgba(27,34,50,0.75); "
            "border: 1px solid rgba(255,255,255,0.10); "
            "color: rgba(230,230,230,0.95); font-weight: 600;"
        )

        top_row = QHBoxLayout()
        top_row.addWidget(header)
        top_row.addStretch(1)
        top_row.addWidget(self.ohlc_bar)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.chart = ChartWidget()
        frame = QFrame()
        frame.setObjectName("ChartFrame")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 8, 8, 8)
        fl.addWidget(self.chart)
        self.tabs.addTab(frame, "Chart")

        outer.addLayout(top_row)
        outer.addWidget(self.tabs, stretch=1)

        self.setCentralWidget(root)

    # ---------- Helpers ----------
    def _selected_symbols(self) -> List[str]:
        items = self.watchlist.selectedItems()
        if not items and self.watchlist.currentItem():
            return [self.watchlist.currentItem().text()]
        return [i.text() for i in items]

    def _log(self, msg: str):
        self.log.append(msg)

    def _save_watchlist(self):
        wl = [self.watchlist.item(i).text().strip().upper() for i in range(self.watchlist.count())]
        wl = [x for x in wl if x]
        self._settings.watchlist = wl
        save_settings(self._settings)

    # ---------- Actions ----------
    def _add_from_search(self):
        text = (self.search.text() or "").strip().upper()
        if not text:
            self.statusBar().showMessage("Type a symbol first.", 2500)
            return
        existing = [self.watchlist.item(i).text() for i in range(self.watchlist.count())]
        if text in existing:
            self.statusBar().showMessage(f"{text} is already in your watchlist.", 2500)
            return
        self.watchlist.addItem(text)
        self._save_watchlist()
        self._log(f"Added {text} to watchlist.")
        self.statusBar().showMessage(f"Added {text}.", 2500)
        self.search.clear()

    # ---------- Fetch threading ----------
    def _safe_stop_previous_thread(self):
        if not self._thread:
            return
        try:
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(1200)
        except RuntimeError:
            pass
        self._thread = None
        self._worker = None

    def _cleanup_after_thread(self):
        self._thread = None
        self._worker = None

    def _refresh(self):
        symbols = self._selected_symbols()
        if not symbols:
            return

        compare_mode = self.compare.isChecked()
        interval = self.interval.currentText()

        self.statusBar().showMessage("Fetching market data…", 2000)
        self._log(f"Fetching: symbols={symbols} compare={compare_mode} interval={interval}")

        self._start_fetch(symbols, interval, compare_mode)

    def _start_fetch(self, symbols: List[str], interval: str, compare: bool):
        self._safe_stop_previous_thread()

        thread = QThread(self)
        worker = FetchWorker(symbols=symbols, interval=interval, compare=compare)
        worker.moveToThread(thread)

        self._thread = thread
        self._worker = worker

        thread.started.connect(worker.run)
        worker.finished.connect(lambda mode, payload: self._on_data(mode, payload))
        worker.failed.connect(self._on_error)

        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)

        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._cleanup_after_thread)

        thread.start()

    def _on_data(self, mode: str, payload: object):
        if mode == "single":
            symbol, candles = payload  # type: ignore
            self.chart.plot_candles(symbol, candles)
            self.tabs.setTabText(0, symbol)
            self.statusBar().showMessage(f"Loaded {symbol} candles.", 2500)
            self._log(f"Rendered candles for {symbol} ({len(candles)} points).")
            return

        if mode == "compare":
            data = payload  # type: ignore
            norm = self.normalize.isChecked()
            self.chart.plot_compare(data, normalize=norm)
            self.tabs.setTabText(0, "Comparison")
            self.statusBar().showMessage("Loaded comparison view.", 2500)
            self._log(f"Rendered comparison series: {list(data.keys())} normalize={norm}")
            return

    def _on_error(self, message: str):
        self.statusBar().showMessage("Data fetch failed.", 3000)
        self._log(f"❌ {message}")

    def closeEvent(self, event):
        self._save_watchlist()
        super().closeEvent(event)
    # ---------- Crosshair info bar ----------
    def _on_crosshair_info(self, payload_obj: object):
        try:
            p = payload_obj  # dict
            if p.get("has_candle"):
                self.ohlc_bar.setText(
                    f"{p.get('symbol','')}  {p.get('candle_time_str','')}   "
                    f"O {p.get('o',0):.4f}  H {p.get('h',0):.4f}  "
                    f"L {p.get('l',0):.4f}  C {p.get('c',0):.4f}"
                )
            else:
                self.ohlc_bar.setText(
                    f"{p.get('symbol','')}  {p.get('time_str','')}   "
                    f"Y {p.get('y',0):.4f}"
                )
        except Exception:
            pass
    # ---------- Crosshair info bar ----------
    def _on_crosshair_info(self, payload_obj: object):
        try:
            p = payload_obj  # dict
            if p.get("has_candle"):
                self.ohlc_bar.setText(
                    f"{p.get('symbol','')}  {p.get('candle_time_str','')}   "
                    f"O {p.get('o',0):.4f}  H {p.get('h',0):.4f}  "
                    f"L {p.get('l',0):.4f}  C {p.get('c',0):.4f}"
                )
            else:
                self.ohlc_bar.setText(
                    f"{p.get('symbol','')}  {p.get('time_str','')}   "
                    f"Y {p.get('y',0):.4f}"
                )
        except Exception:
            pass
