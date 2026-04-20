@echo off
REM Lokální spuštění aggregatoru — pro Windows Task Scheduler.
REM Spouští se z adresáře projektu, aby fungoval relativní import `aggregator.*`.

cd /d "%~dp0.."
python -m aggregator.main
