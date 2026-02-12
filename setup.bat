@echo off
cd /d "%~dp0"
py -m venv env
env\Scripts\python -m pip install -r requirements.txt