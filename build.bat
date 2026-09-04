@echo off
rem Builds dist\S2Tweaker\ (S2Tweaker.exe + _internal), needs:
rem     pip install -r requirements.txt
rem
rem Die eigentliche Bau-Anweisung steht in tools\build_exe.py — GENAU EINE
rem Stelle, weil der GitHub-Actions-Workflow (.github\workflows\build.yml)
rem dasselbe Skript aufruft. Zwei Kopien der PyInstaller-Zeile waeren
rem irgendwann auseinandergelaufen, und darauf beruht die Zusage, dass die
rem veroeffentlichte EXE aus genau diesem Quellcode stammt.
rem
rem Warum --onedir und --version-file (kurz; ausfuehrlich in build_exe.py
rem und docs/ROADMAP.md "Virenscanner-Fehlalarm"): die fruehere
rem --onefile-EXE war ein selbstentpackendes 15-MB-Archiv, das sich beim
rem Start nach %TEMP% auspackt — fuer ML-Heuristiken das Profil eines
rem Droppers. Der Nexus-Support konnte die Datei deshalb nicht freigeben,
rem und Windows Defender hat eine frisch gebaute EXE einmal geloescht.
rem Ausserdem hatte die EXE ueberhaupt keine Versions-Angaben.
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
