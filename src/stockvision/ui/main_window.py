from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("StockVision")
        self.setMinimumSize(1100, 700)   # resizable by default in Qt
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        title = QLabel("StockVision — Market Monitor")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 700; padding: 18px;")

        subtitle = QLabel("Step 1: GUI shell is running. Next we add a professional theme + chart panel.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #555; padding-bottom: 8px;")

        btn = QPushButton("OK — Window Works ✅")
        btn.setFixedHeight(44)
        btn.setStyleSheet("font-size: 14px;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        layout.addStretch()

        self.setCentralWidget(root)
