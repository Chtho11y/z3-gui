import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow


def load_stylesheet(app, path="styles.qss"):
    with open(path, "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_stylesheet(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
