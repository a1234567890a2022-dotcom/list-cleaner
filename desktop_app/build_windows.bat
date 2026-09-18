@echo off
setlocal
cd /d "%~dp0"

python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name ListCleaner list_cleaner_app.py

echo.
echo Finished. Your application is in the dist\ListCleaner.exe file.
pause
