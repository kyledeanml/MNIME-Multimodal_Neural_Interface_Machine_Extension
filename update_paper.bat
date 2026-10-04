@echo off
title Update MNIME Research Paper PDF and Cover Preview
cd /d "%~dp0"

echo ========================================================
echo Updating MNIME Research Paper PDF and Preview Cover...
echo ========================================================

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "C:\Users\kyled\AppData\Local\Programs\Python\Python312\python.exe" set "PYTHON_EXE=C:\Users\kyled\AppData\Local\Programs\Python\Python312\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

"%PYTHON_EXE%" scripts\generate_paper_preview.py --compile

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo SUCCESS: MNIME_paper.pdf and docs\paper_cover_v5.png
    echo have been successfully generated and synchronized.
    echo ========================================================
) else (
    echo.
    echo ERROR: Failed to generate research paper preview cover.
)
pause
