@echo off
echo ===============================================
echo UAT ROLLBACK - Duplicate Ledger Entries Fix
echo ===============================================
echo.
echo This script will rollback the UAT deployment and restore
echo the original files to their previous state.
echo.

set /p confirm="Are you sure you want to rollback UAT? This will undo the fix. (Y/N): "
if /i not "%confirm%"=="Y" (
    echo UAT rollback cancelled.
    pause
    exit /b 1
)

echo.
echo Step 1: Rolling back to previous commit...
git checkout HEAD~1
if %errorlevel% neq 0 (
    echo ERROR: Failed to rollback to previous commit
    echo Please check your Git status
    pause
    exit /b 1
)
echo ✓ Successfully rolled back to previous commit

echo.
echo Step 2: Verifying rollback...
git log --oneline -1
echo.

echo Step 3: UAT rollback complete!
echo.
echo NEXT STEPS:
echo 1. Restart your UAT Odoo server
echo 2. Update the accounting_pdf_reports module in UAT Odoo
echo 3. The system will return to the original state with duplicate entries
echo.
echo NOTE: The duplicate entries issue will return after rollback
echo.

pause
