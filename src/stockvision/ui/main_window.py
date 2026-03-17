from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QToolBar, QStatusBar, QDockWidget, QListWidget, QTextEdit, QFrame
)
from PySide6.QtCore import Qt, QSize
import qtawesome as qta


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("StockVision")
        self.setMinimumSize(1200, 720)

        self._build_toolbar()
        self._build_statusbar()
        self._build_docks()
        self._build_central()

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        # Brand icon
        brand_icon = QLabel()
        pix = qta.icon("fa5s.chart-line", color="#2b72ff").pixmap(18, 18)
        brand_icon.setPixmap(pix)

        brand_title = QLabel("StockVision")
        brand_title.setObjectName("BrandTitle")

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search ticker (AAPL, MSFT, TSLA) or crypto (BTC-USD, ETH-USD)")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(520)
        self.search.returnPressed.connect(self._add_from_search)

        btn_add = QPushButton("Add")
        btn_add.setIcon(qta.icon("fa5s.plus", color="#e6e6e6"))
        btn_add.clicked.connect(self._add_from_search)

        btn_theme = QPushButton("Theme")
        btn_theme.setIcon(qta.icon("fa5s.adjust", color="#e6e6e6"))
        btn_theme.clicked.connect(self._theme_info)

        tb.addWidget(brand_icon)
        tb.addWidget(QLabel("  "))
        tb.addWidget(brand_title)
        tb.addSeparator()
        tb.addWidget(self.search)
        tb.addWidget(btn_add)
        tb.addSeparator()
        tb.addWidget(btn_theme)

    def _build_statusbar(self):
        sb = QStatusBar()
        sb.showMessage("Ready. Step 2: Pro layout + custom dark theme loaded.")
        self.setStatusBar(sb)

    def _build_docks(self):
        self.watchlist = QListWidget()
        self.watchlist.addItems(["AAPL", "MSFT", "TSLA", "NVDA", "BTC-USD", "ETH-USD"])
        self.watchlist.currentTextChanged.connect(self._select_symbol)

        dock_left = QDockWidget("Watchlist", self)
        dock_left.setWidget(self.watchlist)
        dock_left.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock_left)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setText(
            "Asset Details Panel\n\n"
            "- Profile/Metadata (later)\n"
            "- Price + change (later)\n"
            "- Risk metrics (later)\n"
            "- Indicators (later)\n\n"
            "Education-only guidance will be shown here (not financial advice)."
        )

        dock_right = QDockWidget("Details", self)
        dock_right.setWidget(self.details)
        dock_right.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_right)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self._log("App started. UI loaded successfully.")

        dock_bottom = QDockWidget("Event Log", self)
        dock_bottom.setWidget(self.log)
        dock_bottom.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock_bottom)

    def _build_central(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Chart Workspace")
        title.setStyleSheet("font-size: 18px; font-weight: 800;")

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("ChartFrame")
        chart_layout = QVBoxLayout(self.chart_frame)
        chart_layout.setContentsMargins(18, 18, 18, 18)

        self.chart_label = QLabel("Step 3 will add real candlesticks + live graphs here.")
        self.chart_label.setAlignment(Qt.AlignCenter)
        self.chart_label.setStyleSheet("font-size: 14px; color: rgba(230,230,230,0.75);")

        chart_layout.addStretch()
        chart_layout.addWidget(self.chart_label)
        chart_layout.addStretch()

        layout.addWidget(title)
        layout.addWidget(self.chart_frame, stretch=1)
        self.setCentralWidget(root)

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

    def _select_symbol(self, symbol: str):
        if not symbol:
            return
        self._log(f"Selected symbol: {symbol}")
        self.statusBar().showMessage(f"Selected {symbol}", 1500)
        self.chart_label.setText(f"Selected: {symbol}\n\nStep 3 will render candlesticks and live price here.")

        self.details.setText(
            f"Asset Details: {symbol}\n\n"
            "Next Steps (coming soon):\n"
            "- Live price feed\n"
            "- Historical candles\n"
            "- Technical indicators\n"
            "- Comparison view\n"
            "- Education-only risk info\n"
        )

    def _theme_info(self):
        self._log("Theme button clicked. (We can add light/dark toggle in a later step.)")
        self.statusBar().showMessage("Custom dark theme active.", 2500)

    def _log(self, message: str):
        self.log.append(message)
