"""
MNIME Windows Shell Integration & Clean Lifecycle Management.
Ensures document preview presentation (preventing application logo branding
from replacing document page previews) and handles complete system cleanup.
"""

import os
import sys
import ctypes
from typing import Optional


SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_IDLIST = 0x0000
PDF_PREVIEW_HANDLER_CLSID = "{3A84F9C2-6164-485C-A7D9-4B27F8AC009E}"
DOCUMENT_PAGE_ICON = r"%SystemRoot%\System32\imageres.dll,-102"


def notify_shell_refresh() -> None:
    """Broadcasts a shell association change notification to refresh Explorer icons."""
    try:
        if sys.platform == "win32":
            ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        pass


def ensure_pdf_page_preview() -> bool:
    """
    Ensures that when MNIME is associated with or default for PDFs,
    Windows Explorer displays the standard clean document page preview icon
    (Treatment=2, imageres.dll,-102, and native PreviewHandler) rather than
    plastering the MNIME application branding logo onto user documents.
    """
    if sys.platform != "win32":
        return False

    import winreg

    try:
        app_key_path = r"Software\Classes\Applications\MNIME.exe"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key_path) as key:
            winreg.SetValueEx(key, "FriendlyAppName", 0, winreg.REG_SZ, "MNIME")
            winreg.SetValueEx(key, "Treatment", 0, winreg.REG_DWORD, 2)

        icon_key_path = rf"{app_key_path}\DefaultIcon"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, icon_key_path) as icon_key:
            winreg.SetValueEx(icon_key, "", 0, winreg.REG_EXPAND_SZ, DOCUMENT_PAGE_ICON)

        types_key_path = rf"{app_key_path}\SupportedTypes"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, types_key_path) as key:
            winreg.SetValueEx(key, ".pdf", 0, winreg.REG_SZ, "")

        # Attach preview handler so Explorer Preview Pane continues to render documents
        shellex_key_path = rf"{app_key_path}\ShellEx\{{8895b1c6-b41f-4c1c-a562-0d564250836f}}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, shellex_key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, PDF_PREVIEW_HANDLER_CLSID)

        notify_shell_refresh()
        return True
    except Exception:
        return False


def clean_uninstallation(install_dir: Optional[str] = None) -> bool:
    """
    Performs complete uninstallation cleanup across Windows:
    1. Removes Add/Remove Programs registry key
    2. Removes MNIME application settings (QSettings)
    3. Removes Applications/MNIME.exe and MNIME.Document class associations
    4. Removes startup autorun entry
    5. Cleans FileExts .pdf registrations (UserChoice, OpenWithProgids, OpenWithList)
    6. Removes Desktop and Start Menu shortcuts
    7. Cleans %LOCALAPPDATA%\\MNIME logs and temporary files
    8. Broadcasts SHChangeNotify to refresh Explorer
    """
    if sys.platform != "win32":
        return False

    import winreg

    # 1. Add/Remove Programs key
    _delete_reg_tree(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\MNIME")

    # 2. MNIME application QSettings
    _delete_reg_tree(winreg.HKEY_CURRENT_USER, r"Software\MNIME")

    # 3. Application registry classes
    _delete_reg_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\MNIME.exe")
    _delete_reg_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\MNIME.Document")

    # 4. Startup entry
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            try:
                winreg.DeleteValue(key, "MNIME")
            except OSError:
                pass
    except OSError:
        pass

    # 5. Clean FileExts .pdf associations
    _clean_pdf_file_exts()

    # 6. Remove shortcuts
    desktop_lnk = os.path.join(os.path.expanduser("~"), "Desktop", "MNIME.lnk")
    if os.path.exists(desktop_lnk):
        try:
            os.remove(desktop_lnk)
        except OSError:
            pass

    appdata = os.environ.get("APPDATA", "")
    startmenu_lnk = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "MNIME.lnk")
    if os.path.exists(startmenu_lnk):
        try:
            os.remove(startmenu_lnk)
        except OSError:
            pass

    # 7. Clean LocalAppData logs
    localappdata = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        mnime_local = os.path.join(localappdata, "MNIME")
        if os.path.isdir(mnime_local):
            import shutil
            try:
                shutil.rmtree(mnime_local, ignore_errors=True)
            except Exception:
                pass

    # 8. Notify shell
    notify_shell_refresh()
    return True


def _delete_reg_tree(root, subkey: str) -> None:
    """Recursively deletes a Windows registry key and all its subkeys."""
    import winreg

    try:
        subkeys = []
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                i = 0
                while True:
                    subkeys.append(winreg.EnumKey(key, i))
                    i += 1
            except OSError:
                pass
        
        for child in subkeys:
            _delete_reg_tree(root, f"{subkey}\\{child}")
            
        winreg.DeleteKey(root, subkey)
    except OSError:
        pass


def _clean_pdf_file_exts() -> None:
    """Cleans MNIME associations out of HKCU\\...\\Explorer\\FileExts\\.pdf."""
    import winreg

    base_ext = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf"

    # Remove OpenWithProgids
    try:
        progids_path = f"{base_ext}\\OpenWithProgids"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, progids_path, 0, winreg.KEY_SET_VALUE) as key:
            for prog in ["Applications\\MNIME.exe", "MNIME.Document"]:
                try:
                    winreg.DeleteValue(key, prog)
                except OSError:
                    pass
    except OSError:
        pass

    # Clean OpenWithList
    try:
        owl_path = f"{base_ext}\\OpenWithList"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, owl_path, 0, winreg.KEY_ALL_ACCESS) as key:
            mru = ""
            try:
                mru, _ = winreg.QueryValueEx(key, "MRUList")
            except OSError:
                pass

            to_remove = []
            idx = 0
            while True:
                try:
                    val_name, val_data, _ = winreg.EnumValue(key, idx)
                    if val_name != "MRUList" and isinstance(val_data, str) and "mnime" in val_data.lower():
                        to_remove.append(val_name)
                    idx += 1
                except OSError:
                    break

            for name in to_remove:
                try:
                    winreg.DeleteValue(key, name)
                except OSError:
                    pass
                if mru and name in mru:
                    mru = mru.replace(name, "")

            if mru:
                try:
                    winreg.SetValueEx(key, "MRUList", 0, winreg.REG_SZ, mru)
                except OSError:
                    pass
    except OSError:
        pass

    # Clean UserChoice if it references MNIME
    try:
        uc_path = f"{base_ext}\\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, uc_path, 0, winreg.KEY_READ) as key:
            try:
                prog_id, _ = winreg.QueryValueEx(key, "ProgId")
                is_mnime = isinstance(prog_id, str) and "mnime" in prog_id.lower()
            except OSError:
                is_mnime = False

        if is_mnime:
            _delete_reg_tree(winreg.HKEY_CURRENT_USER, uc_path)
    except OSError:
        pass
