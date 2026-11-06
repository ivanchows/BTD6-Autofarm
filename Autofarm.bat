@echo off
cd /d "%~dp0"
set "UV="
for %%P in (uv.exe) do if not "%%~$PATH:P"=="" set "UV=%%~$PATH:P"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV=%USERPROFILE%\.cargo\bin\uv.exe"
if not defined UV if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
if not defined UV for /f "delims=" %%F in ('dir /b /s "%APPDATA%\Python\uv.exe" 2^>nul') do set "UV=%%F"
if not defined UV (
  echo uv is not installed yet. Double-click Install.bat first.
  pause
  exit /b
)
rem uvw = uv without a console window
set "UVW=%UV:uv.exe=uvw.exe%"
if exist "%UVW%" (start "" "%UVW%" run gui.py) else (start "" "%UV%" run --gui-script gui.py)
