@echo off
rem Builds Autofarm.exe from Autofarm.cs with the C# compiler that ships with Windows (.NET Framework 4).
cd /d "%~dp0"
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /optimize ^
  /win32icon:..\assets\autofarm.ico /r:System.Windows.Forms.dll /out:..\Autofarm.exe Autofarm.cs
