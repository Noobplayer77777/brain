@echo off
echo Starting Exam Brain...
echo.
echo Make sure Ollama is running in the background!
echo (You can run 'ollama serve' in another terminal if it's not).
echo.
echo Launching Streamlit interface...
call .\venv\Scripts\activate
streamlit run app.py
pause
