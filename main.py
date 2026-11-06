"""
Punto de entrada para el Desktop Buddy de Hackmon.
"""
import sys
from PyQt6.QtWidgets import QApplication
from src.buddy import DesktopBuddy

def main():
    app = QApplication(sys.argv)
    buddy = DesktopBuddy()
    buddy.show()
    buddy.raise_()
    buddy.activateWindow()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
