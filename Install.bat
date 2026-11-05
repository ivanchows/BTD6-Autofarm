@echo off
title BTD6-Autofarm setup
where uv >nul 2>nul && (echo uv is already installed. You are ready.) || (
  echo Installing uv...
  powershell -NoProfile -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  echo.
  echo Done. Close this window and open a new one before you play.
)
echo.
pause
