@echo off
setlocal enabledelayedexpansion

REM Prompt the user for the location of the .env file
set /p "env_file_location=Enter the location of the .env file: "

REM Read environment variables from the .env file
for /f "usebackq tokens=1,* delims==" %%a in ("%env_file_location%") do (
    set "env_var=%%a"
    set "env_val=%%b"
    set !env_var!=!env_val!
)

:menu
cls
echo Choose an option:
echo ===================================
echo 1. Upgrade head
echo 2. Add revision
echo 3. Downgrade base
echo 4. Downgrade to a specific revision
echo 5. Exit
echo ===================================

set choice=0
set /p "choice=Enter your choice number: "

if "%choice%"=="1" (
    echo # You selected Upgrade head #

    REM Run the alembic upgrade command
    alembic upgrade head

    pause
    goto menu

) else if "%choice%"=="2" (
    echo # You selected Add revision #

    @echo off
    setlocal enabledelayedexpansion

    REM Prompt the user for a message
    set /p "message=Enter a message: "

    REM Run the alembic command with the provided message
    alembic revision --autogenerate -m "!message!"

    pause
    goto menu

) else if "%choice%"=="3" (
    echo # You selected Downgrade base #

    REM Run the alembic downgrade command
    alembic downgrade base

    pause
    goto menu

) else if "%choice%"=="4" (
    echo # You selected Downgrade to a specific revision #

    @echo off
    setlocal enabledelayedexpansion

    REM Prompt the user for the revision of the downgraded version
    set /p "revision_id=Enter the revision ID: "
    alembic downgrade "!revision_id!"

    pause
    goto menu

)else if "%choice%"=="5" (
    echo Exiting the script
    endlocal
    exit /b 0
) else (
    echo Invalid choice. Please enter a valid number...
    pause
    goto menu
)
