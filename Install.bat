@echo off
title BTD6-Autofarm setup
cd /d "%~dp0"

rem Unzipped? (run from inside the zip, Windows uses a temp folder without the other files)
if not exist "%~dp0watchdog.py" (
  echo Unzip the folder first: right-click the zip, Extract All, then run Install.bat from there.
  goto end
)

call :finduv
if defined UV (
  echo uv is already installed. Opening the app...
  goto launch
)

echo Installing uv (1 of 3: official installer)...
powershell -NoProfile -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
call :finduv
if defined UV goto ok

echo Trying again (2 of 3: winget)...
winget install --id=astral-sh.uv -e --accept-source-agreements --accept-package-agreements
call :finduv
if defined UV goto ok

echo Trying again (3 of 3: pip)...
python -m pip install --user uv
call :finduv
if defined UV goto ok

echo.
echo Could not install uv. Check your internet, or ask whoever runs this PC
echo (antivirus or school/work PCs can block it). Then run Install.bat again.
goto end

:ok
echo.
"%UV%" --version
echo uv is installed. Opening the app...
goto launch

rem Finds uv even when this window can't see it yet (PATH only updates in new windows)
:finduv
set "UV="
for %%P in (uv.exe) do if not "%%~$PATH:P"=="" set "UV=%%~$PATH:P"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV=%USERPROFILE%\.cargo\bin\uv.exe"
if not defined UV if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
if not defined UV for /f "delims=" %%F in ('dir /b /s "%APPDATA%\Python\uv.exe" 2^>nul') do set "UV=%%F"
exit /b

:launch
rem The app (gui.py), without a console window: uvw = uv's no-window twin
set "UVW=%UV:uv.exe=uvw.exe%"
if exist "%UVW%" (start "" "%UVW%" run gui.py) else (start "" "%UV%" run --gui-script gui.py)
echo The first start takes up to a minute. Next time, double-click Autofarm.bat.
timeout /t 5 >nul
exit /b

:end
echo.
pause
