def main():
    import sys
    from PySide6.QtWidgets import QApplication
    from stockvision.ui.theme import dark_qss
    from stockvision.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyleSheet(dark_qss())

    win = MainWindow()
    win.show()

    sys.exit(app.exec())
