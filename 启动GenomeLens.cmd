@echo off
setlocal

chcp 65001 >nul
set "ROOT=%~dp0"
set "CONDA_ENV=genomelens"
set "PYTHONPATH=%ROOT%platform\src;%ROOT%engines\jcvi\src"
set "PYTHONIOENCODING=utf-8"
set "GENOMELENS_FORCE_COLOR=1"
set "CONDA_NO_PLUGINS=true"

set "PYTHON_EXE="
if defined CONDA_PREFIX (
  if exist "%CONDA_PREFIX%\python.exe" set "PYTHON_EXE=%CONDA_PREFIX%\python.exe"
)
if not defined PYTHON_EXE if exist "%USERPROFILE%\.conda\envs\%CONDA_ENV%\python.exe" set "PYTHON_EXE=%USERPROFILE%\.conda\envs\%CONDA_ENV%\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\conda\conda\envs\%CONDA_ENV%\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\conda\conda\envs\%CONDA_ENV%\python.exe"
if not defined PYTHON_EXE if exist "C:\ProgramData\miniconda3\envs\%CONDA_ENV%\python.exe" set "PYTHON_EXE=C:\ProgramData\miniconda3\envs\%CONDA_ENV%\python.exe"
if not defined PYTHON_EXE if exist "C:\ProgramData\anaconda3\envs\%CONDA_ENV%\python.exe" set "PYTHON_EXE=C:\ProgramData\anaconda3\envs\%CONDA_ENV%\python.exe"

set "RUN_ARGS=%*"
if "%~1"=="" set "RUN_ARGS=workbench"
if /I "%~1"=="-Check" set "RUN_ARGS=check"
if /I "%~1"=="/Check" set "RUN_ARGS=check"

echo.
echo GenomeLens launcher
echo Project root: %ROOT%
echo Conda env:    %CONDA_ENV%
echo Arguments:    %RUN_ARGS%

if defined PYTHON_EXE (
  echo Python:       %PYTHON_EXE%
  "%PYTHON_EXE%" -m genomelens.cli.main %RUN_ARGS%
  set "EXIT_CODE=%ERRORLEVEL%"
  goto :done
)

where conda >nul 2>nul
if errorlevel 1 (
  echo.
  echo 没有找到 conda，也没有找到 %CONDA_ENV% 环境里的 python.exe。
  echo 请先创建 genomelens conda 环境，或在脚本中补充你的 Python 路径。
  set "EXIT_CODE=3"
  goto :done
)

echo Python:       conda run fallback
conda run --no-capture-output -n %CONDA_ENV% python -m genomelens.cli.main %RUN_ARGS%
set "EXIT_CODE=%ERRORLEVEL%"

:done
if not "%EXIT_CODE%"=="0" (
  echo.
  echo GenomeLens 已退出，退出码：%EXIT_CODE%
)

endlocal & exit /b %EXIT_CODE%
