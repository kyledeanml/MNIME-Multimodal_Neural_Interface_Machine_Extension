@echo off
title Install MNIME
cd /d "%~dp0"

echo ========================================================
echo Installing MNIME Application
echo ========================================================
echo.

:: -------------------------------------------------------
:: Stale-build check: compare dist exe timestamp against
:: the most recently modified source file in core\ and ui\
:: If source is newer than the exe, force a rebuild first.
:: -------------------------------------------------------
set "EXE=dist\MNIME\MNIME.exe"
set "NEED_BUILD=0"

if not exist "%EXE%" (
    echo No compiled application found. Will build first.
    set "NEED_BUILD=1"
    goto :maybe_build
)

:: Use PowerShell to compare timestamps
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$exe = Get-Item '%EXE%'; " ^
    "$src = Get-ChildItem -Recurse -Include *.py 'core','ui' | Sort-Object LastWriteTime -Descending | Select-Object -First 1; " ^
    "if ($src -and $src.LastWriteTime -gt $exe.LastWriteTime) { exit 1 } else { exit 0 }"

if %errorlevel% equ 1 (
    echo Source files are newer than the compiled exe. Rebuilding...
    set "NEED_BUILD=1"
)

:maybe_build
if "%NEED_BUILD%"=="1" (
    echo.
    echo ========================================================
    echo Running build_app.bat to compile latest changes...
    echo ========================================================
    call build_app.bat
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Build failed. Installation aborted.
        pause
        exit /b %errorlevel%
    )
)

if not exist "%EXE%" (
    echo ERROR: Could not find compiled application after build!
    pause
    exit /b 1
)

set "INSTALL_DIR=%LOCALAPPDATA%\Programs\MNIME"

if exist "%INSTALL_DIR%" (
    echo Removing old installation...
    rmdir /S /Q "%INSTALL_DIR%"
)

echo Copying application files to %INSTALL_DIR% ...
mkdir "%INSTALL_DIR%"
xcopy /E /I /Q /Y "dist\MNIME\*" "%INSTALL_DIR%\"
if exist "MN.ico" copy /Y "MN.ico" "%INSTALL_DIR%\" >nul

echo.
echo Creating Desktop and Start Menu shortcuts...

set "DESKTOP_LNK=%USERPROFILE%\Desktop\MNIME.lnk"
set "STARTMENU_LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\MNIME.lnk"
set "EXE_PATH=%INSTALL_DIR%\MNIME.exe"
set "ICON_PATH=%INSTALL_DIR%\MN.ico"

:: We write a temporary powershell script and execute it
echo $WshShell = New-Object -ComObject WScript.Shell > create_links.ps1
echo $Shortcut = $WshShell.CreateShortcut('%DESKTOP_LNK%') >> create_links.ps1
echo $Shortcut.TargetPath = '%EXE_PATH%' >> create_links.ps1
echo $Shortcut.WorkingDirectory = '%INSTALL_DIR%' >> create_links.ps1
echo $Shortcut.IconLocation = '%ICON_PATH%,0' >> create_links.ps1
echo $Shortcut.Save() >> create_links.ps1
echo $Shortcut2 = $WshShell.CreateShortcut('%STARTMENU_LNK%') >> create_links.ps1
echo $Shortcut2.TargetPath = '%EXE_PATH%' >> create_links.ps1
echo $Shortcut2.WorkingDirectory = '%INSTALL_DIR%' >> create_links.ps1
echo $Shortcut2.IconLocation = '%ICON_PATH%,0' >> create_links.ps1
echo $Shortcut2.Save() >> create_links.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File create_links.ps1
del create_links.ps1

echo.
echo Registering application and PDF document presentation in Windows...
set "APP_KEY=HKCU\Software\Classes\Applications\MNIME.exe"
reg add "%APP_KEY%" /v "FriendlyAppName" /t REG_SZ /d "MNIME" /f >nul
reg add "%APP_KEY%" /v "Treatment" /t REG_DWORD /d 2 /f >nul
reg add "%APP_KEY%\DefaultIcon" /ve /t REG_EXPAND_SZ /d "%%SystemRoot%%\System32\imageres.dll,-102" /f >nul
reg add "%APP_KEY%\SupportedTypes" /v ".pdf" /t REG_SZ /d "" /f >nul
reg add "%APP_KEY%\shell\open\command" /ve /t REG_SZ /d "\"%EXE_PATH%\" \"%%1\"" /f >nul
reg add "%APP_KEY%\ShellEx\{8895b1c6-b41f-4c1c-a562-0d564250836f}" /ve /t REG_SZ /d "{3A84F9C2-6164-485C-A7D9-4B27F8AC009E}" /f >nul

echo Registering uninstall entry in Add/Remove Programs...

set "UNINST_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\MNIME"
set "UNINST_BAT=%INSTALL_DIR%\uninstall.bat"

:: Write uninstaller script into the install dir
(
    echo @echo off
    echo title Uninstall MNIME
    echo echo ========================================================
    echo echo Uninstalling MNIME...
    echo echo ========================================================
    echo.
    echo :: Close running application
    echo taskkill /F /IM MNIME.exe /T ^>nul 2^>^&1
    echo.
    echo :: Remove Add/Remove Programs registry entry
    echo reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\MNIME" /f ^>nul 2^>^&1
    echo.
    echo :: Remove application settings
    echo reg delete "HKCU\Software\MNIME" /f ^>nul 2^>^&1
    echo.
    echo :: Remove application class registrations
    echo reg delete "HKCU\Software\Classes\Applications\MNIME.exe" /f ^>nul 2^>^&1
    echo reg delete "HKCU\Software\Classes\MNIME.Document" /f ^>nul 2^>^&1
    echo.
    echo :: Remove startup autorun entry
    echo reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "MNIME" /f ^>nul 2^>^&1
    echo.
    echo :: Clean Explorer PDF file association entries
    echo reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\OpenWithProgids" /v "Applications\MNIME.exe" /f ^>nul 2^>^&1
    echo reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\OpenWithProgids" /v "MNIME.Document" /f ^>nul 2^>^&1
    echo powershell -NoProfile -ExecutionPolicy Bypass -Command "$owl='HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\OpenWithList'; if(Test-Path $owl){$p=Get-ItemProperty $owl;$mru=$p.MRUList;foreach($prop in ($p.psobject.Properties|Where-Object{$_.Value -eq 'MNIME.exe'})){Remove-ItemProperty -Path $owl -Name $prop.Name -ErrorAction SilentlyContinue;if($mru){$mru=$mru.Replace($prop.Name,'')}};if($mru){Set-ItemProperty -Path $owl -Name 'MRUList' -Value $mru -ErrorAction SilentlyContinue}}; $uc='HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice'; if(Test-Path $uc){$prog=(Get-ItemProperty $uc -ErrorAction SilentlyContinue).ProgId;if($prog -like '*MNIME*'){Remove-Item -Path $uc -Recurse -Force -ErrorAction SilentlyContinue}}" ^>nul 2^>^&1
    echo.
    echo :: Remove shortcuts
    echo if exist "%DESKTOP_LNK%" del /f /q "%DESKTOP_LNK%" ^>nul 2^>^&1
    echo if exist "%USERPROFILE%\Desktop\MNIME.lnk" del /f /q "%USERPROFILE%\Desktop\MNIME.lnk" ^>nul 2^>^&1
    echo if exist "%USERPROFILE%\OneDrive\Desktop\MNIME.lnk" del /f /q "%USERPROFILE%\OneDrive\Desktop\MNIME.lnk" ^>nul 2^>^&1
    echo if exist "%PUBLIC%\Desktop\MNIME.lnk" del /f /q "%PUBLIC%\Desktop\MNIME.lnk" ^>nul 2^>^&1
    echo if exist "%STARTMENU_LNK%" del /f /q "%STARTMENU_LNK%" ^>nul 2^>^&1
    echo.
    echo :: Remove application logs
    echo if exist "%LOCALAPPDATA%\MNIME" rmdir /s /q "%LOCALAPPDATA%\MNIME" ^>nul 2^>^&1
    echo.
    echo :: Refresh Windows Explorer icon cache and shell notifications
    echo ie4uinit.exe -show ^>nul 2^>^&1
    echo powershell -NoProfile -ExecutionPolicy Bypass -Command "$code = '[DllImport(\"shell32.dll\")] public static extern void SHChangeNotify(int eventId, int flags, IntPtr item1, IntPtr item2);'; $type = Add-Type -MemberDefinition $code -Name ShellNotifier -Namespace Win32 -PassThru -ErrorAction SilentlyContinue; if($type){$type::SHChangeNotify(0x08000000, 0x1000, [IntPtr]::Zero, [IntPtr]::Zero)}" ^>nul 2^>^&1
    echo.
    echo :: Clean up application files via detached background cleanup
    echo set "TARGET_DIR=%INSTALL_DIR%"
    echo start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 1; Remove-Item -LiteralPath '%%TARGET_DIR%%' -Recurse -Force -ErrorAction SilentlyContinue"
    echo echo MNIME has been successfully uninstalled.
    echo timeout /t 2 /nobreak ^>nul
) > "%UNINST_BAT%"

reg add "%UNINST_KEY%" /v "DisplayName"          /t REG_SZ    /d "MNIME"                    /f >nul
reg add "%UNINST_KEY%" /v "DisplayVersion"       /t REG_SZ    /d "2.1"                      /f >nul
reg add "%UNINST_KEY%" /v "Publisher"            /t REG_SZ    /d "MNIME"                    /f >nul
reg add "%UNINST_KEY%" /v "InstallLocation"      /t REG_SZ    /d "%INSTALL_DIR%"            /f >nul
reg add "%UNINST_KEY%" /v "DisplayIcon"          /t REG_SZ    /d "%ICON_PATH%,0"            /f >nul
reg add "%UNINST_KEY%" /v "UninstallString"      /t REG_SZ    /d "\"%UNINST_BAT%\""         /f >nul
reg add "%UNINST_KEY%" /v "QuietUninstallString" /t REG_SZ    /d "\"%UNINST_BAT%\""         /f >nul
reg add "%UNINST_KEY%" /v "NoModify"             /t REG_DWORD /d 1                          /f >nul
reg add "%UNINST_KEY%" /v "NoRepair"             /t REG_DWORD /d 1                          /f >nul
reg add "%UNINST_KEY%" /v "URLInfoAbout"         /t REG_SZ    /d "https://MNIME.app"        /f >nul
reg add "%UNINST_KEY%" /v "HelpLink"             /t REG_SZ    /d "https://MNIME.app"        /f >nul

echo.
echo ========================================================
echo MNIME has been successfully installed!
echo It now appears in Add/Remove Programs for clean removal.
echo You can now launch it from your Desktop or Start Menu.
echo ========================================================
pause
