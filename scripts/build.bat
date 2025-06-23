@echo off

REM Build script for Windows

echo Setting up Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Running tests...
python -m pytest tests\ -v

echo Building executable...
python build_spec.py

echo Build completed! Executable can be found in dist\
pause