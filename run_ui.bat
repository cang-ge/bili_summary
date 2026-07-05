@echo off
REM Launch bili_summary Streamlit UI
cd /d "%~dp0"
echo.
echo ============================================
echo   bili_summary · Streamlit UI
echo   http://localhost:8501
echo ============================================
echo.
streamlit run app.py
pause