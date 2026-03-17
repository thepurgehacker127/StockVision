def dark_qss() -> str:
    # Pro fintech-style dark theme (no external dependencies)
    return r'''
QWidget {
    background: #0f1218;
    color: #e6e6e6;
    font-size: 12px;
}

QMainWindow::separator {
    background: rgba(255,255,255,0.08);
    width: 1px;
    height: 1px;
}

QToolBar {
    background: #121724;
    border: none;
    spacing: 8px;
    padding: 8px;
}

QStatusBar {
    background: #121724;
    border-top: 1px solid rgba(255,255,255,0.08);
}

QDockWidget {
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    border: 1px solid rgba(255,255,255,0.08);
}

QDockWidget::title {
    background: #121724;
    padding: 8px;
    font-weight: 700;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}

QLineEdit {
    background: #0c0f14;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #2b72ff;
}
QLineEdit:focus {
    border: 1px solid rgba(43,114,255,0.85);
}

QPushButton {
    background: #1b2232;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background: #222b40;
    border: 1px solid rgba(255,255,255,0.18);
}
QPushButton:pressed {
    background: #151b28;
}

QListWidget, QTextEdit {
    background: #0c0f14;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 8px;
}
QListWidget::item:selected {
    background: rgba(43,114,255,0.25);
    border: 1px solid rgba(43,114,255,0.45);
}

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 6px 2px 6px 2px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.18);
    border-radius: 6px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255,255,255,0.28);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QLabel#BrandTitle {
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QFrame#ChartFrame {
    background: #0c0f14;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.10);
}
'''
