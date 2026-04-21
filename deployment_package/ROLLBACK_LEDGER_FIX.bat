@echo off
echo ===============================================
echo ROLLING BACK DUPLICATE LEDGER ENTRIES FIX
echo ===============================================
echo.
echo This script will rollback the ledger fix and restore
echo the original files to their previous state.
echo.

set /p confirm="Are you sure you want to rollback? This will undo the fix. (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Rollback cancelled.
    pause
    exit /b 1
)

echo.
echo Step 1: Removing new files...
if exist "accounting_pdf_reports\views\ledger_fix.xml" del "accounting_pdf_reports\views\ledger_fix.xml"
echo ✓ Removed ledger_fix.xml

echo.
echo Step 2: Restoring original files...
copy "ledger_menu_original.xml" "accounting_pdf_reports\views\ledger_menu.xml" >nul
copy "__manifest___original.py" "accounting_pdf_reports\__manifest__.py" >nul
echo ✓ Original files restored

echo.
echo Step 3: Rollback complete!
echo.
echo NEXT STEPS:
echo 1. Restart Odoo server
echo 2. Update the accounting_pdf_reports module in Odoo
echo 3. The system will return to the original state with duplicate entries
echo.
echo NOTE: The duplicate entries issue will return after rollback
echo.

pause
