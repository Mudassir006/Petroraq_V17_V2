@echo off
echo ===============================================
echo DEPLOYING DUPLICATE LEDGER ENTRIES FIX
echo ===============================================
echo.
echo This script will deploy the fix for duplicate ledger entries
echo by updating the accounting_pdf_reports module.
echo.
echo BACKUP: Original files will be backed up automatically
echo ROLLBACK: Use ROLLBACK_LEDGER_FIX.bat if issues occur
echo.

set /p confirm="Do you want to proceed with deployment? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Deployment cancelled.
    pause
    exit /b 1
)

echo.
echo Step 1: Creating backup of original files...
if not exist "backup" mkdir backup
copy "accounting_pdf_reports\views\ledger_menu.xml" "backup\ledger_menu_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.xml" >nul
copy "accounting_pdf_reports\__manifest__.py" "backup\__manifest___backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.py" >nul
echo ✓ Backup created in backup\ folder

echo.
echo Step 2: Deploying new files...
copy "ledger_fix.xml" "accounting_pdf_reports\views\" >nul
copy "ledger_menu_modified.xml" "accounting_pdf_reports\views\ledger_menu.xml" >nul
copy "__manifest___modified.py" "accounting_pdf_reports\__manifest__.py" >nul
echo ✓ New files deployed

echo.
echo Step 3: Deployment complete!
echo.
echo NEXT STEPS:
echo 1. Restart Odoo server
echo 2. Update the accounting_pdf_reports module in Odoo
echo 3. Test the General Ledger and Partner Ledger views
echo.
echo ROLLBACK: If issues occur, run ROLLBACK_LEDGER_FIX.bat
echo.

pause
