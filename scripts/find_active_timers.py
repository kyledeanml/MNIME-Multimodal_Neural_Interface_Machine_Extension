import sys
import os

# Set required environment variables so imports work
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.main_window import MainWindow

app = QApplication(sys.argv)
win = MainWindow()
win.show()
app.processEvents()
win.hide()
app.processEvents()

active = []
for w in QApplication.allWidgets():
    for t in w.findChildren(QTimer):
        if t.isActive():
            parent_name = type(t.parent()).__name__ if t.parent() else "None"
            active.append((parent_name, t.interval()))

print("Active timers:", active)
