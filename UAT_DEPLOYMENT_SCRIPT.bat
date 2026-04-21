@echo off
echo ===============================================
echo UAT DEPLOYMENT - Duplicate Ledger Entries Fix
echo ===============================================
echo.
echo This script will deploy the fix to your UAT server
echo by pulling the latest changes from GitHub.
echo.
echo CHANGES TO BE DEPLOYED:
echo - Fix duplicate ledger entries (group by journal entry)
echo - Consolidate accounting menus (rename to "Petroraq Accounting")
echo - Add deployment package with rollback capability
echo.

set /p confirm="Do you want to proceed with UAT deployment? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo UAT deployment cancelled.
    pause
    exit /b 1
)

echo.
echo Step 1: Checking current Git status...
git status
echo.

echo Step 2: Pulling latest changes from GitHub...
git pull origin test
if %errorlevel% neq 0 (
    echo ERROR: Failed to pull changes from GitHub
    echo Please check your internet connection and GitHub access
    pause
    exit /b 1
)
echo ✓ Successfully pulled changes from GitHub

echo.
echo Step 3: Verifying deployed files...
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
echo Step 4: UAT deployment complete!
echo.
echo NEXT STEPS:
echo 1. Restart your UAT Odoo server
echo 2. Update the accounting_pdf_reports module in UAT Odoo
echo 3. Test the General Ledger and Partner Ledger views
echo 4. Verify menu consolidation (Petroraq Accounting)
echo.
echo ROLLBACK: If issues occur, run UAT_ROLLBACK_SCRIPT.bat
echo.

pause
