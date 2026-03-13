@echo off
echo.
echo  ai.play Build Script v0.2
echo  ==========================
echo.

python --version >nul 2>&1
if errorlevel 1 (echo [ERROR] Python not found & pause & exit /b 1)

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (pip install pyinstaller)

where makensis >nul 2>&1
if errorlevel 1 (
    echo [ERROR] NSIS not found. Download: https://nsis.sourceforge.io/Download
    pause & exit /b 1
)

echo [1/3] Building aip.exe...
python -m PyInstaller ^
    --onedir ^
    --name aip ^
    --console ^
    --add-data "lexer.py;." ^
    --add-data "parser.py;." ^
    --add-data "ast_nodes.py;." ^
    --add-data "interpreter.py;." ^
    --add-data "runtime.py;." ^
    --add-data "format_detector.py;." ^
    --add-data "memory_engine.py;." ^
    --add-data "server.py;." ^
    --add-data "ui_server.py;." ^
    --add-data "voice_engine.py;." ^
    --add-data "video_engine.py;." ^
    --add-data "skills_engine.py;." ^
    --add-data "user_memory.py;." ^
    --icon=aip.ico ^
    aiplay.py

if errorlevel 1 (echo [ERROR] PyInstaller failed & pause & exit /b 1)

echo [2/3] Copying source files...
for %%f in (aiplay.py lexer.py parser.py ast_nodes.py interpreter.py runtime.py format_detector.py memory_engine.py server.py ui_server.py) do copy %%f dist\aip\

echo [3/3] Building installer...
makensis installer.nsi
if errorlevel 1 (echo [ERROR] NSIS failed & pause & exit /b 1)

echo.
echo  Done. aiplay-setup.exe is ready.
pause
