def main():
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont
    from stockvision.ui.theme import dark_qss
    from stockvision.ui.main_window import MainWindow

    app = QApplication(sys.argv)

    # Avoid Qt font warnings by setting an explicit font size
    font = QFont(app.font())
    font.setPointSize(10)
    app.setFont(font)

    app.setStyleSheet(dark_qss())

    win = MainWindow()
    win.show()

    sys.exit(app.exec())
