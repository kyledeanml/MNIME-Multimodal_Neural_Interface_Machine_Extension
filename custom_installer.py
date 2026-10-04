import os
import sys
import shutil
import math
import random
import time
import subprocess
import argparse

# Parse arguments
parser = argparse.ArgumentParser(description="MNIME Installer")
parser.add_argument("--dry-run", action="store_true", help="Run the installer UI sequence without modifying any files or registry")
args, unknown = parser.parse_known_args()
DRY_RUN = args.dry_run

# Ensure PyQt6 path during development (skip if compiled)
if not getattr(sys, 'frozen', False):
    venv_base = os.path.dirname(os.path.dirname(sys.executable))
    plugin_base = os.path.join(venv_base, "Lib", "site-packages", "PyQt6", "Qt6", "plugins")
    os.environ["QT_PLUGIN_PATH"] = plugin_base
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(plugin_base, "platforms")

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import (QFont, QPainter, QLinearGradient, QColor,
                         QFontMetrics, QPen, QBrush, QPixmap, QPolygonF, QPainterPath)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF

class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()
    
    def run(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            source_dir = os.path.join(base_path, 'app_files')
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            source_dir = os.path.join(base_path, 'dist', 'MNIME')
            
        install_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'MNIME')
        
        self.progress.emit(2, "Initializing installer UI...")
        time.sleep(1.0)
        
        if not DRY_RUN:
            if os.path.exists(source_dir):
                if os.path.exists(install_dir):
                    self.progress.emit(5, "Removing old version...")
                    try:
                        shutil.rmtree(install_dir)
                    except Exception:
                        pass
                
                os.makedirs(install_dir, exist_ok=True)
                
                all_files = []
                total_size_bytes = 0
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        full_p = os.path.join(root, file)
                        all_files.append(full_p)
                        try:
                            total_size_bytes += os.path.getsize(full_p)
                        except Exception:
                            pass
                        
                total_files = len(all_files)
                if total_files > 0:
                    for i, file_path in enumerate(all_files):
                        rel_path = os.path.relpath(file_path, source_dir)
                        dest_path = os.path.join(install_dir, rel_path)
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        try:
                            shutil.copy2(file_path, dest_path)
                        except Exception:
                            pass
                        
                        if i % max(1, (total_files // 100)) == 0:
                            pct = 5 + int((i / total_files) * 80)
                            self.progress.emit(pct, f"Installing: {os.path.basename(file_path)}")
                            time.sleep(0.01)
                
                # Create icon explicitly if it didn't copy
                if not os.path.exists(os.path.join(install_dir, "MN.ico")):
                    try:
                        shutil.copy2("MN.ico", os.path.join(install_dir, "MN.ico"))
                    except Exception: pass
            else:
                self.progress.emit(0, "Error: Application build files not found (dist/MNIME). Please build before running installer.")
                time.sleep(2.0)
                self.finished.emit()
                return
        else:
            # Simulate installation progress
            self.progress.emit(5, "Simulating installation (Dry Run)...")
            time.sleep(1)
            for i in range(5, 86):
                self.progress.emit(i, f"Simulating file copy: fake_file_{i}.dll")
                time.sleep(0.02)
                
        self.progress.emit(88, "Registering uninstaller in Windows...")
        
        if not DRY_RUN:
            # Uninstaller and Registry Registration
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                    desktop_dir = winreg.QueryValueEx(key, "Desktop")[0]
                    desktop_dir = os.path.expandvars(desktop_dir)
            except Exception:
                desktop_dir = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
            desktop = os.path.join(desktop_dir, 'MNIME.lnk')
            start_menu = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'MNIME.lnk')
            target = os.path.join(install_dir, 'MNIME.exe')
            icon = os.path.join(install_dir, 'MN.ico')
            display_icon = icon if os.path.exists(icon) else f"{target},0"
            uninst_bat = os.path.join(install_dir, 'uninstall.bat')
            uninst_vbs = os.path.join(install_dir, 'uninstall.vbs')
            
            # Write uninstaller script into install directory
            localapp = os.environ.get('LOCALAPPDATA', '')
            uninstaller_content = (
                "@echo off\r\n"
                "title Uninstall MNIME\r\n"
                "echo ========================================================\r\n"
                "echo Uninstalling MNIME...\r\n"
                "echo ========================================================\r\n"
                "\r\n"
                ":: Terminate running MNIME instances\r\n"
                "taskkill /F /IM MNIME.exe /T >nul 2>&1\r\n"
                "\r\n"
                ":: Remove Add/Remove Programs registry entry\r\n"
                "reg delete \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\MNIME\" /f >nul 2>&1\r\n"
                "\r\n"
                ":: Remove application settings\r\n"
                "reg delete \"HKCU\\Software\\MNIME\" /f >nul 2>&1\r\n"
                "\r\n"
                ":: Remove application class registrations\r\n"
                "reg delete \"HKCU\\Software\\Classes\\Applications\\MNIME.exe\" /f >nul 2>&1\r\n"
                "reg delete \"HKCU\\Software\\Classes\\MNIME.Document\" /f >nul 2>&1\r\n"
                "\r\n"
                ":: Remove startup autorun entry\r\n"
                "reg delete \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\" /v \"MNIME\" /f >nul 2>&1\r\n"
                "\r\n"
                ":: Clean Explorer PDF file association entries\r\n"
                "reg delete \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.pdf\\OpenWithProgids\" /v \"Applications\\MNIME.exe\" /f >nul 2>&1\r\n"
                "reg delete \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.pdf\\OpenWithProgids\" /v \"MNIME.Document\" /f >nul 2>&1\r\n"
                "powershell -NoProfile -ExecutionPolicy Bypass -Command \"$owl='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.pdf\\OpenWithList'; if(Test-Path $owl){$p=Get-ItemProperty $owl;$mru=$p.MRUList;foreach($prop in ($p.psobject.Properties|Where-Object{$_.Value -eq 'MNIME.exe'})){Remove-ItemProperty -Path $owl -Name $prop.Name -ErrorAction SilentlyContinue;if($mru){$mru=$mru.Replace($prop.Name,'')}};if($mru){Set-ItemProperty -Path $owl -Name 'MRUList' -Value $mru -ErrorAction SilentlyContinue}}; $uc='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.pdf\\UserChoice'; if(Test-Path $uc){$prog=(Get-ItemProperty $uc -ErrorAction SilentlyContinue).ProgId;if($prog -like '*MNIME*'){Remove-Item -Path $uc -Recurse -Force -ErrorAction SilentlyContinue}}\" >nul 2>&1\r\n"
                "\r\n"
                ":: Remove shortcuts\r\n"
                f"if exist \"{desktop}\" del /f /q \"{desktop}\" >nul 2>&1\r\n"
                f"if exist \"%USERPROFILE%\\Desktop\\MNIME.lnk\" del /f /q \"%USERPROFILE%\\Desktop\\MNIME.lnk\" >nul 2>&1\r\n"
                f"if exist \"%USERPROFILE%\\OneDrive\\Desktop\\MNIME.lnk\" del /f /q \"%USERPROFILE%\\OneDrive\\Desktop\\MNIME.lnk\" >nul 2>&1\r\n"
                f"if exist \"%PUBLIC%\\Desktop\\MNIME.lnk\" del /f /q \"%PUBLIC%\\Desktop\\MNIME.lnk\" >nul 2>&1\r\n"
                f"if exist \"{start_menu}\" del /f /q \"{start_menu}\" >nul 2>&1\r\n"
                "\r\n"
                ":: Remove application logs\r\n"
                f"if exist \"{localapp}\\MNIME\" rmdir /s /q \"{localapp}\\MNIME\" >nul 2>&1\r\n"
                "\r\n"
                ":: Refresh Windows Explorer icon cache and shell notifications\r\n"
                "ie4uinit.exe -show >nul 2>&1\r\n"
                "powershell -NoProfile -ExecutionPolicy Bypass -Command \"$code = '[DllImport(\\\"shell32.dll\\\")] public static extern void SHChangeNotify(int eventId, int flags, IntPtr item1, IntPtr item2);'; $type = Add-Type -MemberDefinition $code -Name ShellNotifier -Namespace Win32 -PassThru -ErrorAction SilentlyContinue; if($type){$type::SHChangeNotify(0x08000000, 0x1000, [IntPtr]::Zero, [IntPtr]::Zero)}\" >nul 2>&1\r\n"
                "\r\n"
                ":: Clean up application files via detached background cleanup\r\n"
                f"set \"TARGET_DIR={install_dir}\"\r\n"
                "start \"\" /b powershell -NoProfile -WindowStyle Hidden -Command \"Start-Sleep -Seconds 1; Remove-Item -LiteralPath '%TARGET_DIR%' -Recurse -Force -ErrorAction SilentlyContinue\"\r\n"
                "echo MNIME has been successfully uninstalled.\r\n"
                "timeout /t 2 /nobreak >nul\r\n"
            )
            try:
                with open(uninst_bat, "w", encoding="utf-8") as f:
                    f.write(uninstaller_content)
                with open(uninst_vbs, "w", encoding="utf-8") as f:
                    f.write('Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run chr(34) & "' + uninst_bat + '" & chr(34), 0\nSet WshShell = Nothing\n')
            except Exception:
                pass
                
            # Register in Windows Add or Remove Programs (HKCU)
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\MNIME"
            try:
                import winreg
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "MNIME")
                    winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "MNIME")
                    winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
                    winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{display_icon},0" if display_icon.endswith('.ico') else display_icon)
                    winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'wscript.exe "{uninst_vbs}"')
                    winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'wscript.exe "{uninst_vbs}"')
                    winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, max(1, total_size_bytes // 1024))
                    winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, time.strftime("%Y%m%d"))
                    winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, "https://MNIME.app")
                    winreg.SetValueEx(key, "HelpLink", 0, winreg.REG_SZ, "https://MNIME.app")
    
                # Register PDF document page preview presentation so Explorer displays document previews
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\MNIME.exe") as app_key:
                    winreg.SetValueEx(app_key, "FriendlyAppName", 0, winreg.REG_SZ, "MNIME")
                    winreg.SetValueEx(app_key, "Treatment", 0, winreg.REG_DWORD, 2)
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\MNIME.exe\DefaultIcon") as icon_key:
                    winreg.SetValueEx(icon_key, "", 0, winreg.REG_EXPAND_SZ, r"%SystemRoot%\System32\imageres.dll,-102")
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\MNIME.exe\SupportedTypes") as types_key:
                    winreg.SetValueEx(types_key, ".pdf", 0, winreg.REG_SZ, "")
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\MNIME.exe\shell\open\command") as cmd_key:
                    winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, f'"{target}" "%1"')
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\MNIME.exe\ShellEx\{8895b1c6-b41f-4c1c-a562-0d564250836f}") as sx_key:
                    winreg.SetValueEx(sx_key, "", 0, winreg.REG_SZ, "{3A84F9C2-6164-485C-A7D9-4B27F8AC009E}")
            except Exception:
                try:
                    cmd = (
                        f'reg add "HKCU\\{key_path}" /v "DisplayName" /t REG_SZ /d "MNIME" /f & '
                        f'reg add "HKCU\\{key_path}" /v "Publisher" /t REG_SZ /d "MNIME" /f & '
                        f'reg add "HKCU\\{key_path}" /v "InstallLocation" /t REG_SZ /d "{install_dir}" /f & '
                        f'reg add "HKCU\\{key_path}" /v "DisplayIcon" /t REG_SZ /d "{display_icon}" /f & '
                        f'reg add "HKCU\\{key_path}" /v "UninstallString" /t REG_SZ /d "wscript.exe \\"{uninst_vbs}\\"" /f & '
                        f'reg add "HKCU\\{key_path}" /v "EstimatedSize" /t REG_DWORD /d {max(1, total_size_bytes // 1024)} /f & '
                        f'reg add "HKCU\\{key_path}" /v "NoModify" /t REG_DWORD /d 1 /f & '
                        f'reg add "HKCU\\{key_path}" /v "NoRepair" /t REG_DWORD /d 1 /f & '
                        f'reg add "HKCU\\Software\\Classes\\Applications\\MNIME.exe" /v "FriendlyAppName" /t REG_SZ /d "MNIME" /f & '
                        f'reg add "HKCU\\Software\\Classes\\Applications\\MNIME.exe" /v "Treatment" /t REG_DWORD /d 2 /f & '
                        f'reg add "HKCU\\Software\\Classes\\Applications\\MNIME.exe\\DefaultIcon" /ve /t REG_EXPAND_SZ /d "%%SystemRoot%%\\System32\\imageres.dll,-102" /f & '
                        f'reg add "HKCU\\Software\\Classes\\Applications\\MNIME.exe\\SupportedTypes" /v ".pdf" /t REG_SZ /d "" /f & '
                        f'reg add "HKCU\\Software\\Classes\\Applications\\MNIME.exe\\shell\\open\\command" /ve /t REG_SZ /d "\"{target}\" \"%%1\"" /f & '
                        f'reg add "HKCU\\Software\\Classes\\Applications\\MNIME.exe\\ShellEx\\{{8895b1c6-b41f-4c1c-a562-0d564250836f}}" /ve /t REG_SZ /d "{{3A84F9C2-6164-485C-A7D9-4B27F8AC009E}}" /f'
                    )
                    subprocess.run(cmd, shell=True, capture_output=True)
                except Exception:
                    pass
        else:
            time.sleep(1)
            
        self.progress.emit(94, "Creating shortcuts...")
        
        if not DRY_RUN:
            # Shortcut Creation
            shortcuts_created = False
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                for lnk in [desktop, start_menu]:
                    shortcut = shell.CreateShortCut(lnk)
                    shortcut.Targetpath = target
                    shortcut.WorkingDirectory = install_dir
                    shortcut.IconLocation = f"{icon},0"
                    shortcut.save()
                shortcuts_created = True
            except Exception:
                pass
    
            if not shortcuts_created:
                try:
                    ps_script = (
                        f"$ws = New-Object -ComObject WScript.Shell; "
                        f"foreach ($p in @('{desktop}', '{start_menu}')) {{ "
                        f"$s = $ws.CreateShortcut($p); "
                        f"$s.TargetPath = '{target}'; "
                        f"$s.WorkingDirectory = '{install_dir}'; "
                        f"$s.IconLocation = '{icon},0'; "
                        f"$s.Save(); "
                        f"}}"
                    )
                    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                    subprocess.run(
                        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                        creationflags=flags,
                        timeout=10
                    )
                except Exception:
                    pass
        else:
            time.sleep(1)
            
        self.progress.emit(100, "Installation Complete! Launching MNIME..." if not DRY_RUN else "Dry Run Complete!")
        time.sleep(1.0)
        
        if not DRY_RUN:
            if os.path.exists(target):
                try:
                    flags = getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
                    subprocess.Popen([target], cwd=install_dir, creationflags=flags)
                except Exception:
                    pass
                
        self.finished.emit()


class LittleFile:
    def __init__(self, start_x, start_y, target_x, target_y):
        self.start_x = start_x
        self.start_y = start_y
        self.target_x = target_x
        self.target_y = target_y
        
        # Control point for arc trajectory
        self.ctrl_x = (start_x + target_x) / 2 + random.uniform(-100, 100)
        self.ctrl_y = (start_y + target_y) / 2 - random.uniform(50, 200)
        
        self.t = 0.0
        self.speed = random.uniform(0.015, 0.03)
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-15, 15)
        self.size = random.uniform(0.7, 1.2)
        
        self.cx = start_x
        self.cy = start_y
        
    def update(self):
        self.t += self.speed
        if self.t > 1.0:
            self.t = 1.0
        u = 1 - self.t
        self.cx = u*u*self.start_x + 2*u*self.t*self.ctrl_x + self.t*self.t*self.target_x
        self.cy = u*u*self.start_y + 2*u*self.t*self.ctrl_y + self.t*self.t*self.target_y
        self.rotation += self.rot_speed


class InstallerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(650, 450)
        
        self.progress_val = 0
        self.status_text = "Initializing installer..."
        
        self.swirl_angle = 0.0
        self.little_files = []
        
        # The tiny files
        self.tiny_file_pixmap = self.create_file_pixmap(QColor(140, 230, 255), 16)
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_anim)
        self.anim_timer.start(16)
        
        self.worker = InstallWorker()
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        
        QTimer.singleShot(1000, self.worker.start)

    def create_file_pixmap(self, color, size=48):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        scale = size / 24.0
        poly = QPolygonF([
            QPointF(4*scale, 2*scale), QPointF(14*scale, 2*scale), 
            QPointF(20*scale, 8*scale), QPointF(20*scale, 22*scale), 
            QPointF(4*scale, 22*scale)
        ])
        
        # File body
        p.setPen(QPen(color, max(1.5, 2 * scale)))
        brush_color = QColor(color.red(), color.green(), color.blue(), 50)
        p.setBrush(brush_color)
        p.drawPolygon(poly)
        
        # Folded corner
        p.drawLine(QPointF(14*scale, 2*scale), QPointF(14*scale, 8*scale))
        p.drawLine(QPointF(14*scale, 8*scale), QPointF(20*scale, 8*scale))
        
        
        p.end()
        return pix

    def on_progress(self, val, text):
        old_val = self.progress_val
        self.progress_val = val
        self.status_text = text
        
        if val > old_val and val < 100:
            # Spawn little files from left off-screen flying to the progress bar
            num_spawn = min((val - old_val) * 2, 10)
            for _ in range(num_spawn):
                sx = -30
                sy = random.uniform(50, self.height() - 50)
                tx = 50 + (val / 100.0) * 550
                ty = 350 # Progress bar Y position
                self.little_files.append(LittleFile(sx, sy, tx, ty))

    def on_finished(self):
        sys.exit(0)

    def update_anim(self):
        self.swirl_angle += 1.25
        for lf in self.little_files:
            lf.update()
        self.little_files = [lf for lf in self.little_files if lf.t < 1.0]
        self.update()

    def mousePressEvent(self, event):
        # Consume the event to prevent frameless window drag/lag behavior
        from PyQt6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Main Background
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 20, 20)
        p.fillPath(path, QColor(13, 17, 23, 245))
        p.setPen(QPen(QColor(48, 54, 61), 2))
        p.drawPath(path)
        
        cx, cy = self.width() // 2, self.height() // 2 - 30
        
        # 2. Tasteful MNIME Text
        font = QFont("Segoe UI Black", 48, QFont.Weight.Black)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6.0)
        p.setFont(font)
        
        fm = QFontMetrics(font)
        text = "MNIME"
        tr = fm.boundingRect(text)
        x = cx - tr.width() // 2
        y = cy + tr.height() // 2
        
        glow = QColor(0, 210, 255, 30)
        p.setPen(glow)
        for offset in [3, 6]:
            p.drawText(x-offset, y-offset, text)
            p.drawText(x+offset, y+offset, text)
            p.drawText(x-offset, y+offset, text)
            p.drawText(x+offset, y-offset, text)
            
        p.setPen(QColor(0, 0, 0, 150))
        p.drawText(x+4, y+4, text)
        
        grad = QLinearGradient(x, y-tr.height(), x, y)
        grad.setColorAt(0.0, QColor("#ffffff"))
        grad.setColorAt(0.5, QColor("#8b949e"))
        grad.setColorAt(1.0, QColor("#161b22"))
        pen = QPen()
        pen.setBrush(QBrush(grad))
        p.setPen(pen)
        p.drawText(x, y, text)
        
        # 3. Logo Placement (Above Title)
        fx = cx
        fy = cy - 80
        
        from core.app_icon import get_logo_pixmap
        animated_logo = get_logo_pixmap(80, math.radians(self.swirl_angle * 2.0))
        
        p.save()
        p.translate(fx, fy)
        # Gentle bobbing
        p.translate(0, math.sin(math.radians(self.swirl_angle * 3)) * 5)
        p.drawPixmap(-40, -40, 80, 80, animated_logo)
        p.restore()
        
        # 4. Progress Bar Background
        bar_x = 50
        bar_y = 350
        bar_w = 550
        bar_h = 12
        p.setPen(QPen(QColor(48, 54, 61), 1))
        p.setBrush(QColor(1, 4, 9))
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 6, 6)
        
        # Progress Bar Fill
        fill_w = (self.progress_val / 100.0) * bar_w
        if fill_w > 0:
            fill_grad = QLinearGradient(bar_x, bar_y, bar_x + fill_w, bar_y)
            fill_grad.setColorAt(0, QColor(0, 150, 255))
            fill_grad.setColorAt(1, QColor(0, 255, 200))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(fill_grad))
            p.drawRoundedRect(bar_x, bar_y, int(fill_w), bar_h, 6, 6)
            
            # Draw a bright glowing head at the end of the progress bar
            p.setBrush(QColor(255, 255, 255, 200))
            p.drawEllipse(QPointF(bar_x + fill_w, bar_y + bar_h/2), 6, 6)
            
        # 5. Little Files Piling In
        for lf in self.little_files:
            p.save()
            p.translate(lf.cx, lf.cy)
            p.rotate(lf.rotation)
            p.scale(lf.size, lf.size)
            p.drawPixmap(-8, -8, 16, 16, self.tiny_file_pixmap)
            p.restore()
            
        # 6. Status Text
        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(139, 148, 158))
        p.drawText(bar_x, bar_y - 10, self.status_text)
        p.drawText(bar_x + bar_w - 35, bar_y - 10, f"{self.progress_val}%")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass
        
    win = InstallerUI()
    win.show()
    sys.exit(app.exec())
