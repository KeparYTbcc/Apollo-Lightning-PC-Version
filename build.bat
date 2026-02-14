@echo off
cd /d "%~dp0"
env\Scripts\pyinstaller --onefile --name led-controller --collect-all bleak --collect-all PyQt5 main.py
echo.
echo Build complete! Executable is in: dist\led-controller.exe
pause