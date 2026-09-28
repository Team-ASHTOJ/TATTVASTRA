@echo off
rem One-action JOCKY Windows endpoint setup.
rem
rem Put this bundle in a folder together with the jocky-bootstrap.json
rem downloaded from JOCKY (Endpoints -> Connect Endpoint -> Windows ->
rem Advanced Setup -> Prepare), then run this file. It elevates itself and
rem installs the bounded JOCKY supervisor service. No other command is needed.
setlocal
set "BUNDLE=%~dp0"
set "CONFIG=%BUNDLE%jocky-bootstrap.json"
set "INSTALLER=%BUNDLE%install-jocky-bootstrap.ps1"

if not exist "%INSTALLER%" goto missinginstaller
if not exist "%CONFIG%" goto missingconfig

net session >nul 2>&1
if not errorlevel 1 goto elevated

echo Requesting administrator rights for the one-time JOCKY install...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b 0

:elevated
powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALLER%" -Configuration "%CONFIG%" -SourceDirectory "%BUNDLE%"
set "RESULT=%errorlevel%"
echo.
if not "%RESULT%"=="0" goto failed
echo JOCKY endpoint setup completed.
pause
exit /b 0

:failed
echo JOCKY endpoint setup FAILED with exit code %RESULT%. Read the message above.
pause
exit /b %RESULT%

:missinginstaller
echo ERROR: install-jocky-bootstrap.ps1 is missing from "%BUNDLE%".
echo Extract the whole jocky-windows-endpoint bundle before running this.
pause
exit /b 1

:missingconfig
echo ERROR: jocky-bootstrap.json was not found next to this file.
echo In JOCKY open Endpoints -^> Connect Endpoint -^> Windows -^> Advanced Setup,
echo choose Prepare, and save the downloaded jocky-bootstrap.json into:
echo   %BUNDLE%
pause
exit /b 1
