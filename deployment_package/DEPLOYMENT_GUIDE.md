# Duplicate Ledger Entries Fix - Deployment Guide

## 🚀 DEPLOYMENT PACKAGE CONTENTS

This deployment package contains everything needed to fix the duplicate ledger entries issue:

### Files Included:
- `ledger_fix.xml` - New custom views that group by journal entry
- `ledger_menu_modified.xml` - Updated menu configuration
- `__manifest___modified.py` - Updated module manifest
- `ledger_menu_original.xml` - Original menu file (for rollback)
- `__manifest___original.py` - Original manifest file (for rollback)
- `DEPLOY_LEDGER_FIX.bat` - Automated deployment script
- `ROLLBACK_LEDGER_FIX.bat` - Automated rollback script

## 📋 PRE-DEPLOYMENT CHECKLIST

### ✅ Prerequisites:
- [ ] Odoo server is running
- [ ] Database backup is completed
- [ ] All users are logged out of the system
- [ ] Maintenance window is scheduled
- [ ] Rollback plan is understood

### ✅ Verification:
- [ ] Current duplicate entries issue is documented
- [ ] Test environment has been validated
- [ ] Deployment team is ready

## 🔧 DEPLOYMENT STEPS

### Option 1: Automated Deployment (Recommended)

1. **Copy the deployment package** to your Odoo server
2. **Navigate to the deployment_package folder**
3. **Run the deployment script:**
   ```bash
   DEPLOY_LEDGER_FIX.bat
   ```
4. **Follow the prompts** and confirm deployment
5. **Restart Odoo server**
6. **Update the module** in Odoo (Apps → Update Apps → accounting_pdf_reports)

### Option 2: Manual Deployment

1. **Create backup** of original files:
   ```bash
   copy accounting_pdf_reports\views\ledger_menu.xml backup\
   copy accounting_pdf_reports\__manifest__.py backup\
   ```

2. **Deploy new files:**
   ```bash
   copy ledger_fix.xml accounting_pdf_reports\views\
   copy ledger_menu_modified.xml accounting_pdf_reports\views\ledger_menu.xml
   copy __manifest___modified.py accounting_pdf_reports\__manifest__.py
   ```

3. **Restart Odoo server**

4. **Update the module** in Odoo

## 🧪 POST-DEPLOYMENT TESTING

### Test Checklist:
- [ ] **General Ledger** - Navigate to Accounting → Petroraq Accounting → Reports → Ledgers → General Ledger
- [ ] **Partner Ledger** - Navigate to Accounting → Petroraq Accounting → Reports → Ledgers → Partner Ledger
- [ ] **Verify grouping** - Entries should be grouped by journal entry (CPV, BPV, etc.)
- [ ] **Verify expandability** - Click on grouped entries to see individual move lines
- [ ] **Verify totals** - Check that totals are correct for each journal entry
- [ ] **Verify no duplicates** - No more duplicate entries should appear

### Expected Results:
```
✅ BEFORE (Duplicate Entries):
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate

✅ AFTER (Grouped by Journal Entry):
📁 CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical...
   ├── Account A | 50.00
   ├── Account B | 30.00
   ├── Account C | 20.00
   └── Total: 100.00
```

## 🔄 ROLLBACK PROCEDURE

### If Issues Occur:

1. **Run the rollback script:**
   ```bash
   ROLLBACK_LEDGER_FIX.bat
   ```

2. **Follow the prompts** and confirm rollback

3. **Restart Odoo server**

4. **Update the module** in Odoo

5. **System returns to original state**

### Manual Rollback:
```bash
# Remove new files
del accounting_pdf_reports\views\ledger_fix.xml

# Restore original files
copy ledger_menu_original.xml accounting_pdf_reports\views\ledger_menu.xml
copy __manifest___original.py accounting_pdf_reports\__manifest__.py
```

## 📊 IMPACT ASSESSMENT

### ✅ Positive Impacts:
- **Eliminates duplicate entries display**
- **Improves user experience**
- **Maintains data integrity**
- **No business disruption**

### ⚠️ Considerations:
- **View change only** - No data modifications
- **Immediate effect** - Changes visible after module update
- **Reversible** - Can be rolled back if needed

## 🆘 TROUBLESHOOTING

### Common Issues:

**Issue**: Module update fails
**Solution**: Check file permissions and restart Odoo server

**Issue**: Views not loading
**Solution**: Clear browser cache and refresh

**Issue**: Still seeing duplicates
**Solution**: Verify module was updated and restart Odoo

### Support:
- Check Odoo logs for errors
- Verify file permissions
- Ensure all files were deployed correctly

## 📞 CONTACT INFORMATION

For deployment support or issues:
- **Technical Lead**: [Your Name]
- **Deployment Date**: [Date]
- **Rollback Available**: Yes (guaranteed)

## ✅ DEPLOYMENT SIGN-OFF

- [ ] **Deployment completed successfully**
- [ ] **Testing completed successfully**
- [ ] **No issues identified**
- [ ] **Users notified of changes**
- [ ] **Documentation updated**

**Deployment Date**: _______________
**Deployed By**: _______________
**Approved By**: _______________
