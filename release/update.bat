@echo off
rem ===================================================================
rem  S2Tweaker auto-updater
rem
rem  Downloads the latest release from GitHub and replaces the program
rem  files in this folder: S2Tweaker.exe and the _internal folder next
rem  to it. Settings, presets, cache and output are NOT touched.
rem  The old ones are kept as S2Tweaker.exe.bak and _internal.bak
rem
rem  This file is plain text on purpose - read it, it has no secrets.
rem  It talks to exactly one place:
rem      https://github.com/Zayn995/S2Tweaker/releases
rem  and it never runs by itself: you started it (double-click or the
rem  "update now" choice inside the tool).
rem ===================================================================
setlocal EnableExtensions

rem Run a copy of this script from %TEMP%, so the update may safely
rem replace update.bat itself in the tool folder.
if not "%~2"=="RELAUNCHED" (
    copy /y "%~f0" "%TEMP%\s2tweaker_update.bat" >nul
    start "S2Tweaker update" "%TEMP%\s2tweaker_update.bat" "%~dp0" RELAUNCHED
    exit /b 0
)

set "APPDIR=%~1"
if "%APPDIR%"=="" set "APPDIR=%CD%"
cd /d "%APPDIR%" || (echo Could not open "%APPDIR%". & pause & exit /b 1)

echo.
echo  S2Tweaker auto-updater
echo  Folder: %CD%
echo.

rem ---- wait until the tool is closed --------------------------------
:waitloop
tasklist /fi "imagename eq S2Tweaker.exe" 2>nul | find /i "S2Tweaker.exe" >nul
if not errorlevel 1 (
    echo Waiting for S2Tweaker.exe to close ...
    timeout /t 2 /nobreak >nul
    goto waitloop
)

rem ---- look up the latest release (one HTTPS request to GitHub) -----
echo Looking up the latest version on GitHub ...
set "PS=powershell -NoProfile -ExecutionPolicy Bypass -Command"
set "INFO="
for /f "usebackq delims=" %%A in (`%PS% "[Net.ServicePointManager]::SecurityProtocol = 'Tls12'; $r = Invoke-RestMethod -UseBasicParsing 'https://api.github.com/repos/Zayn995/S2Tweaker/releases/latest' -Headers @{ 'User-Agent' = 'S2Tweaker-updater' }; $a = $null; foreach ($x in $r.assets) { if ($x.name -like 'S2Tweaker_v*.zip' -and $x.name -notlike '*source*') { $a = $x; break } }; if ($a) { Write-Output ($r.tag_name + ';' + $a.browser_download_url) }"`) do set "INFO=%%A"
if not defined INFO goto fail_net
for /f "tokens=1,2 delims=;" %%A in ("%INFO%") do (set "TAG=%%A" & set "URL=%%B")
if not defined URL goto fail_net
echo Latest version: %TAG%
echo.

rem ---- download and unpack into a temporary folder ------------------
set "WORK=%TEMP%\s2tweaker_update_work"
rmdir /s /q "%WORK%" 2>nul
mkdir "%WORK%" 2>nul
echo Downloading %URL% ...
%PS% "[Net.ServicePointManager]::SecurityProtocol = 'Tls12'; Invoke-WebRequest -UseBasicParsing '%URL%' -OutFile '%WORK%\release.zip'"
if errorlevel 1 goto fail_dl
if not exist "%WORK%\release.zip" goto fail_dl
echo Unpacking ...
%PS% "Expand-Archive -Force '%WORK%\release.zip' '%WORK%\unpacked'"
if errorlevel 1 goto fail_dl
set "NEWEXE="
for /f "usebackq delims=" %%A in (`dir /b /s "%WORK%\unpacked\S2Tweaker.exe" 2^>nul`) do set "NEWEXE=%%A"
if not defined NEWEXE goto fail_dl

rem ---- swap exe AND _internal (backup first), refresh README+updater -
rem The tool ships as a folder: the exe next to an _internal folder
rem holding the Python runtime. Both have to be replaced together -
rem an old _internal with a new exe would not start.
for %%A in ("%NEWEXE%") do set "NEWDIR=%%~dpA"
echo Installing (the old files are kept as S2Tweaker.exe.bak / _internal.bak) ...
if exist "S2Tweaker.exe" copy /y "S2Tweaker.exe" "S2Tweaker.exe.bak" >nul
copy /y "%NEWEXE%" "S2Tweaker.exe" >nul
if errorlevel 1 goto fail_swap
if exist "%NEWDIR%_internal" (
    if exist "_internal.bak" rmdir /s /q "_internal.bak" 2>nul
    if exist "_internal" move /y "_internal" "_internal.bak" >nul
    xcopy /e /i /q /y "%NEWDIR%_internal" "_internal" >nul
    if errorlevel 1 goto fail_internal
)
for /f "usebackq delims=" %%A in (`dir /b /s "%WORK%\unpacked\README.txt" 2^>nul`) do copy /y "%%A" "README.txt" >nul
for /f "usebackq delims=" %%A in (`dir /b /s "%WORK%\unpacked\update.bat" 2^>nul`) do copy /y "%%A" "update.bat" >nul
rmdir /s /q "%WORK%" 2>nul

echo.
echo Done - S2Tweaker %TAG% is installed.
echo Settings, presets, cache and output were not touched.
echo.
choice /c YN /m "Start S2Tweaker now"
if not errorlevel 2 start "" "S2Tweaker.exe"
exit /b 0

:fail_net
echo.
echo Could not reach github.com - offline, or blocked by a firewall,
echo proxy or antivirus HTTPS inspection. Nothing was changed.
echo Manual download: https://github.com/Zayn995/S2Tweaker/releases
echo.
pause
exit /b 1

:fail_dl
echo.
echo Download or unpacking failed. Nothing was changed.
echo Manual download: https://github.com/Zayn995/S2Tweaker/releases
echo.
pause
exit /b 1

:fail_swap
echo.
echo Could not replace S2Tweaker.exe - is it still running?
echo Your previous exe is unchanged (or available as S2Tweaker.exe.bak).
echo.
pause
exit /b 1

:fail_internal
echo.
echo Could not replace the _internal folder. Your previous one is still
echo there as _internal.bak - rename it back to _internal and the old
echo S2Tweaker.exe.bak back to S2Tweaker.exe to undo this update.
echo Manual download: https://github.com/Zayn995/S2Tweaker/releases
echo.
pause
exit /b 1
