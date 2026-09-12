@echo off
rem Build dist\S2Tweaker\ with the signed pythonw.exe launcher and readable code.
rem Requires: pip install -r requirements.txt
rem Use a full python.org installation as "python" (pythonw.exe, DLLs, Lib, tcl).
rem tools\build_exe.py owns the build steps and verifies the resulting directory.
rem GitHub CI refreshes a hash-pinned runtime with tools\refresh_portable.py.
rem The local build performs a brief launch check that opens an application window.
python tools\build_exe.py || goto :error
echo.
echo Done: dist\S2Tweaker\S2Tweaker.exe
pause
exit /b 0

:error
echo.
echo BUILD FAILED.
pause
exit /b 1
