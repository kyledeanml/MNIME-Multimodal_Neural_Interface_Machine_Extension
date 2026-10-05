import sys
import os
import cProfile
from PyQt6.QtCore import QTimer

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import MNIME

def run():
    # We need to quit after 10 seconds to get the profile.
    # MNIME.main() creates the QApplication and runs app.exec().
    # Let's inject a QTimer before app.exec()
    original_exec = MNIME.QApplication.exec
    def hook():
        QTimer.singleShot(10000, MNIME.QApplication.quit)
        return original_exec()
    MNIME.QApplication.exec = hook
    
    MNIME.main()

if __name__ == '__main__':
    cProfile.run('run()', 'idle_mnime.prof')
