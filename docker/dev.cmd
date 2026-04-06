@echo off
REM Обход ExecutionPolicy для dev.ps1 (скрипты .ps1 иначе могут быть заблокированы).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
