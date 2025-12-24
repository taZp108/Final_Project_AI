import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.app_window import MainWindow

if __name__ == '__main__':
    if not hasattr(Qt.AlignmentFlag, 'AlignCenter') and hasattr(Qt, 'AlignCenter'):
        Qt.AlignmentFlag.AlignCenter = Qt.AlignCenter
        
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())