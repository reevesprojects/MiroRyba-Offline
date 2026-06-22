@echo off
echo ===================================================
echo Starting Bulk Ollama Model Download...
echo Depending on your internet speed, this may take a while.
echo ===================================================

echo.
echo Pulling qwen3:8b...
ollama pull qwen3:8b

echo.
echo Pulling qwen3:14b...
ollama pull qwen3:14b

echo.
echo Pulling ministral-3:8b...
ollama pull ministral-3:8b

echo.
echo Pulling ministral-3:14b...
ollama pull ministral-3:14b

echo.
echo Pulling gemma4:12b...
ollama pull gemma4:12b

echo.
echo Pulling deepseek-r1:8b...
ollama pull deepseek-r1:8b

echo.
echo Pulling deepseek-r1:14b...
ollama pull deepseek-r1:14b

echo.
echo ===================================================
echo All downloads finished!
echo ===================================================
pause
