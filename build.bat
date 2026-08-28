@echo off
rem Builds dist\S2Tweaker.exe (needs: pip install -r requirements.txt)
python -m PyInstaller --noconfirm --onefile --windowed --name S2Tweaker ^
  --add-binary "tools\repak.exe;." --collect-all customtkinter main.py
pause
