@echo off
rem Tin Can Chronicles launcher (Windows)
cd /d "%~dp0"

set PY=python

if exist ".venv\Scripts\python.exe" (
    set PY=.venv\Scripts\python.exe
    goto run
)

%PY% -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo * creating virtual environment...
    %PY% -m venv .venv
    .venv\Scripts\pip install --quiet pygame
    set PY=.venv\Scripts\python.exe
)

:run
%PY% main.py %*
