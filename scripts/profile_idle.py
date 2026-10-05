import sys
import os
import cProfile

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    from ui.main_window import MainWindow
    
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    win.hide()  # Simulate it going to tray immediately
    
    QTimer.singleShot(10000, app.quit) # Exit gracefully after 10 seconds
    
    app.exec()

if __name__ == '__main__':
    cProfile.run('run()', 'idle.prof')
