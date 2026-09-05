@echo off
rem Baut dist\S2Tweaker\ (S2Tweaker.exe + DLLs + _internal), braucht:
rem     pip install -r requirements.txt
rem und eine python.org-Installation als "python" (pythonw.exe, DLLs\,
rem Lib\, tcl\ nebeneinander) - deren signierte pythonw.exe WIRD der Starter.
rem
rem Die eigentliche Bau-Anweisung steht in tools\build_exe.py - GENAU EINE
rem Stelle, weil der GitHub-Actions-Workflow (.github\workflows\build.yml)
rem dasselbe Skript aufruft. Zwei Kopien waeren irgendwann
rem auseinandergelaufen, und darauf beruht die Zusage, dass die
rem veroeffentlichte Datei aus genau diesem Quellcode stammt.
rem
rem Seit 1.21.0 OHNE PyInstaller (Begruendung im Kopf von build_exe.py,
rem kurz: die Virenscanner-Treffer galten PyInstallers eigener Kennung).
rem Das Skript prueft seinen Ordner selbst und startet ihn einmal
rem probeweise - dabei geht kurz ein Fenster auf und wieder zu.
python tools\build_exe.py || goto :error
echo.
echo Fertig: dist\S2Tweaker\S2Tweaker.exe
pause
exit /b 0

:error
echo.
echo BUILD FEHLGESCHLAGEN.
pause
exit /b 1
