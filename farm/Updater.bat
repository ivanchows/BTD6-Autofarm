@echo off
title BTD6-Autofarm updater
cd /d "%~dp0"
rem One line on purpose: the update can replace this file while it runs
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0updater.ps1" & echo. & pause & exit /b
