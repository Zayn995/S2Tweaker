@echo off
rem ===================================================================
rem  S2Tweaker auto-updater
rem
rem  Downloads the latest release from GitHub and replaces the program
rem  files in this folder: S2Tweaker.exe, the Python runtime next to it
rem  (python3XX.dll, vcruntime140*.dll, python3XX._pth) and the
rem  _internal folder. Settings, presets, cache and output are NOT
rem  touched. The old program is kept as S2Tweaker.exe.bak and
rem  _internal.bak (the old runtime DLLs are moved into _internal.bak).
rem
rem  This file is plain text on purpose - read it, it has no secrets.
rem  It talks to exactly one place:
rem      https://github.com/Zayn995/S2Tweaker/releases
rem  and it never runs by itself: you started it (double-click).
rem  It is not part of the download and not needed: extracting the new
rem  ZIP over your S2Tweaker folder does exactly the same thing.
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
for %%A in ("%NEWEXE%") do set "NEWDIR=%%~dpA"
if not exist "%NEWDIR%_internal\" goto fail_dl

rem ---- replace the whole program (backup first) ---------------------
rem Since 1.21.0 the program is S2Tweaker.exe (the signed python.org
rem launcher) plus the runtime DLLs and python3XX._pth next to it, plus
rem the _internal folder. Everything the ZIP contains is copied over;
rem the previous program goes to S2Tweaker.exe.bak and _internal.bak.
echo Installing (the old files are kept as S2Tweaker.exe.bak / _internal.bak) ...
if exist "_internal.bak" rmdir /s /q "_internal.bak" 2>nul
if exist "_internal" move /y "_internal" "_internal.bak" >nul
if not exist "_internal.bak" mkdir "_internal.bak"
if exist "S2Tweaker.exe" copy /y "S2Tweaker.exe" "S2Tweaker.exe.bak" >nul
for %%A in (python3*.dll python3*._pth vcruntime140*.dll) do move /y "%%A" "_internal.bak\" >nul 2>&1
xcopy /e /i /q /y "%NEWDIR%." "." >nul
if errorlevel 1 goto fail_internal
if not exist "S2Tweaker.exe" goto fail_internal
if not exist "_internal\sitecustomize.py" goto fail_internal
dir /b "python3*._pth" >nul 2>&1 || goto fail_internal
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

:fail_internal
echo.
echo Could not install the new program files. Your previous program is
echo still there: S2Tweaker.exe.bak and the _internal.bak folder (which
echo also holds the old runtime DLLs). The simplest way to a working
echo folder is to download the ZIP and extract it over this folder:
echo https://github.com/Zayn995/S2Tweaker/releases
echo Settings, presets, cache and output are untouched either way.
echo.
pause
exit /b 1
