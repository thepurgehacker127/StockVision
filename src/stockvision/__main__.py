from stockvision.ui.main_window import MainWindow

def main():
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
