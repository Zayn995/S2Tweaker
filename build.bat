@echo off
rem Builds dist\S2Tweaker.exe (needs: pip install -r requirements.txt)
rem
rem --exclude-module PIL: Pillow is an optional customtkinter dependency that
rem this app never uses (we have no CTkImage anywhere; it is only needed by
rem tools\make_screenshots.py). Without this flag the exe is ~3 MB bigger on
rem machines that happen to have Pillow installed, so builds would differ
rem from PC to PC. Verified: the app runs fine without it.
python -m PyInstaller --noconfirm --onefile --windowed --name S2Tweaker ^
  --icon "assets\icon.ico" --add-binary "assets\icon.ico;." ^
  --add-binary "tools\repak.exe;." --collect-all customtkinter ^
  --exclude-module PIL main.py
pause
