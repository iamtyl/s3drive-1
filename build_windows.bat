@echo off
echo =======================================================
echo    S3Drive Replica - Windows Portable Builder
echo =======================================================
echo.

:: Create virtual environment
echo [1/4] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

:: Install dependencies
echo [2/4] Installing requirements...
pip install -r requirements.txt

:: Build EXE
echo [3/4] Packaging into a portable EXE...
pyinstaller --onefile --windowed --name "S3DriveReplica" main.py

:: Cleanup
echo [4/4] Cleaning up...
rmdir /s /q build
del S3DriveReplica.spec

echo.
echo =======================================================
echo    SUCCESS! Your portable EXE is in the 'dist' folder.
echo =======================================================
pause
