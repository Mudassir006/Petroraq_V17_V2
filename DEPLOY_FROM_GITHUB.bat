@echo off
echo ===============================================
echo DEPLOY FROM GITHUB - Duplicate Ledger Entries Fix
echo ===============================================
echo.
echo This script will deploy the fix directly from GitHub
echo to your current Odoo installation.
echo.

set /p server_type="Which server are you deploying to? (UAT/PRODUCTION): "
if /i "%server_type%"=="UAT" (
    echo Deploying to UAT server...
    set server_name=UAT
) else if /i "%server_type%"=="PRODUCTION" (
    echo Deploying to PRODUCTION server...
    set server_name=PRODUCTION
) else (
    echo Invalid server type. Please enter UAT or PRODUCTION.
    pause
    exit /b 1
)

echo.
echo Step 1: Pulling latest changes from GitHub...
git pull origin test
if %errorlevel% neq 0 (
    echo ERROR: Failed to pull changes from GitHub
    echo Please check your internet connection and GitHub access
    pause
    exit /b 1
)
echo ✓ Successfully pulled changes from GitHub

echo.
echo Step 2: Verifying deployed files...
if exist "accounting_pdf_reports\views\ledger_fix.xml" (
    echo ✓ ledger_fix.xml deployed
) else (
    echo ✗ ledger_fix.xml missing
)

if exist "deployment_package\" (
    echo ✓ deployment_package deployed
) else (
    echo ✗ deployment_package missing
)

echo.
echo Step 3: %server_name% deployment complete!
echo.
echo NEXT STEPS:
echo 1. Restart your %server_name% Odoo server
echo 2. Update the accounting_pdf_reports module in %server_name% Odoo
echo 3. Test the General Ledger and Partner Ledger views
echo 4. Verify menu consolidation (Petroraq Accounting)
echo.
echo ROLLBACK: If issues occur, run ROLLBACK_FROM_GITHUB.bat
echo.

pause
