@echo off
REM venv-samurai仮想環境をアクティベート
call venv-samurai\Scripts\activate.bat
REM MASAAnnotationAppを起動
python AutoAnnotationTool\src\MASAAnnotationApp\MASAAnnotationApp.py
