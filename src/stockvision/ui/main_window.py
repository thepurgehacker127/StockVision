from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import Qt, QSize, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QToolBar, QStatusBar, QDockWidget, QListWidget, QTextEdit, QFrame,
    QTabWidget, QComboBox, QCheckBox
)
import qtawesome as qta

from stockvision.ui.chart_widget import ChartWidget
from stockvision.core.market_data import (
    normalize_symbol, fetch_stooq_daily, fetch_binance_klines, MarketDataError, Candle
)


class FetchWorker(QObject):
    finished = Signal(str, object)  # (mode, payload)
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

        self._thread: QThread | None = None
        self._worker: FetchWorker | None = None

        self._build_toolbar()
        self._build_statusbar()
        self._build_docks()
        self._build_central()

        if self.watchlist.count() > 0:
            self.watchlist.setCurrentRow(0)

    # ---------- Top toolbar ----------
    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        brand_icon = QLabel()
        pix = qta.icon("fa5s.chart-line", color="#2b72ff").pixmap(18, 18)
        brand_icon.setPixmap(pix)

        brand_title = QLabel("StockVision")
        brand_title.setObjectName("BrandTitle")

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search ticker (AAPL, MSFT) or crypto (BTC-USD, ETH-USD)")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(420)
        self.search.returnPressed.connect(self._add_from_search)

        btn_add = QPushButton("Add")
        btn_add.setIcon(qta.icon("fa5s.plus", color="#e6e6e6"))
        btn_add.clicked.connect(self._add_from_search)

        self.interval = QComboBox()
        self.interval.addItems(["1m", "5m", "15m", "1h", "4h", "1d"])
        self.interval.setCurrentText("1h")
        self.interval.currentTextChanged.connect(lambda _x: self._refresh())

        self.compare = QCheckBox("Compare")
        self.compare.stateChanged.connect(lambda _s: self._refresh())

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
        tb.addWidget(btn_refresh)

    # ---------- Status bar ----------
    def _build_statusbar(self):
        sb = QStatusBar()
        sb.showMessage("Ready. Step 3: Candles + comparison charts + data providers.")
        self.setStatusBar(sb)

    # ---------- Dock panels ----------
    def _build_docks(self):
        self.watchlist = QListWidget()
        self.watchlist.addItems(["AAPL", "MSFT", "TSLA", "NVDA", "BTC-USD", "ETH-USD"])
        self.watchlist.setSelectionMode(QListWidget.ExtendedSelection)
        self.watchlist.itemSelectionChanged.connect(self._refresh)

        dock_left = QDockWidget("Watchlist (multi-select for compare)", self)
        dock_left.setWidget(self.watchlist)
        dock_left.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock_left)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setText(
            "Asset Details Panel\n\n"
            "Step 3:\n"
            "- Candlesticks (stocks + crypto)\n"
            "- Compare mode (multi-select)\n"
            "- Free sources: Stooq (stocks daily), Binance (crypto)\n\n"
            "Education-only guidance will appear here later (not financial advice)."
        )

        dock_right = QDockWidget("Details", self)
        dock_right.setWidget(self.details)
        dock_right.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_right)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self._log("App started. Step 3 chart engine ready.")

        dock_bottom = QDockWidget("Event Log", self)
        dock_bottom.setWidget(self.log)
        dock_bottom.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock_bottom)

    # ---------- Central workspace ----------
    def _build_central(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QLabel("Chart Workspace")
        header.setStyleSheet("font-size: 18px; font-weight: 800;")

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.chart = ChartWidget()
        frame = QFrame()
        frame.setObjectName("ChartFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.addWidget(self.chart)
        self.tabs.addTab(frame, "Chart")

        layout.addWidget(header)
        layout.addWidget(self.tabs, stretch=1)
        self.setCentralWidget(root)

    # ---------- Utilities ----------
    def _selected_symbols(self) -> List[str]:
        items = self.watchlist.selectedItems()
        if not items and self.watchlist.currentItem():
            return [self.watchlist.currentItem().text()]
        return [i.text() for i in items]

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
        self._log(f"Added {text} to watchlist.")
        self.statusBar().showMessage(f"Added {text}.", 2500)
        self.search.clear()

    def _refresh(self):
        symbols = self._selected_symbols()
        if not symbols:
            return

        compare_mode = self.compare.isChecked()
        interval = self.interval.currentText()

        self.statusBar().showMessage("Fetching market data…", 2000)
        self._log(f"Fetching: symbols={symbols} compare={compare_mode} interval={interval}")

        self._start_fetch(symbols, interval, compare_mode)

    def _safe_stop_previous_thread(self):
        if not self._thread:
            return

        # The thread may already be deleted; touching it raises RuntimeError.
        try:
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(1200)
        except RuntimeError:
            pass

        self._thread = None
        self._worker = None

    def _cleanup_after_thread(self):
        # Called when thread finishes (safe to reset references)
        self._thread = None
        self._worker = None

    def _start_fetch(self, symbols: List[str], interval: str, compare: bool):
        self._safe_stop_previous_thread()

        thread = QThread(self)  # parented so Qt manages lifetime safely
        worker = FetchWorker(symbols=symbols, interval=interval, compare=compare)
        worker.moveToThread(thread)

        # Save references so they don't get GC'd
        self._thread = thread
        self._worker = worker

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_data)
        worker.failed.connect(self._on_error)

        # Ensure thread stops
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)

        # Cleanup objects safely
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._cleanup_after_thread)

        thread.start()

    def _on_data(self, mode: str, payload: object):
        if mode == "single":
            symbol, candles = payload  # type: ignore
            self.chart.plot_candles(symbol, candles)
            self.tabs.setTabText(0, symbol)
            self.details.setText(
                f"Asset Details: {symbol}\n\n"
                f"Candles loaded: {len(candles)}\n"
                "Source:\n"
                "- Stocks: Stooq (daily)\n"
                "- Crypto: Binance (interval)\n\n"
                "Next:\n"
                "- Live streaming\n"
                "- Indicators\n"
                "- Alerts\n"
            )
            self.statusBar().showMessage(f"Loaded {symbol} candles.", 2500)
            self._log(f"Rendered candles for {symbol} ({len(candles)} points).")
            return

        if mode == "compare":
            data = payload  # type: ignore
            self.chart.plot_compare(data, normalize=True)
            self.tabs.setTabText(0, "Comparison")
            self.details.setText(
                "Comparison Mode\n\n"
                f"Symbols: {', '.join(data.keys())}\n"
                "Display: % change from start (normalized)\n\n"
                "Tip: Multi-select in Watchlist to compare.\n"
                "Source:\n"
                "- Stocks: Stooq (daily)\n"
                "- Crypto: Binance\n"
            )
            self.statusBar().showMessage("Loaded comparison view.", 2500)
            self._log(f"Rendered comparison series: {list(data.keys())}")
            return

    def _on_error(self, message: str):
        self.statusBar().showMessage("Data fetch failed.", 3000)
        self._log(f"❌ {message}")
        self.details.setText(
            "Data Fetch Error\n\n"
            f"{message}\n\n"
            "Troubleshooting:\n"
            "- Check internet connection\n"
            "- Try another symbol\n"
            "- Crypto uses Binance (try BTC-USD)\n"
            "- Stocks use Stooq (try AAPL)\n"
        )

    def _log(self, message: str):
        self.log.append(message)
