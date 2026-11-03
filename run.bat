@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Tworze srodowisko Python w folderze .venv ...
    python -m venv .venv
    if errorlevel 1 goto :error
)

rem Samo istnienie .venv nie znaczy, ze zaleznosci sa zainstalowane -
rem poprzednie uruchomienie moglo zostac przerwane w trakcie instalacji.
".venv\Scripts\python.exe" -c "import PySide6, PIL" >nul 2>&1
if errorlevel 1 (
    echo Instaluje zaleznosci ^(PySide6, Pillow^). To moze potrwac kilka minut ...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :runerror
exit /b 0

:error
echo.
echo Nie udalo sie przygotowac srodowiska Python.
echo Sprawdz, czy Python 3.11+ jest zainstalowany i czy jest polaczenie z internetem.
echo Mozesz tez usunac folder .venv i uruchomic run.bat ponownie.
pause
exit /b 1

:runerror
echo.
echo Program zakonczyl sie bledem - skopiuj powyzszy komunikat.
pause
exit /b 1
