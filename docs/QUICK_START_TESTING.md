# Quick Start Testing Guide

## Run All Tests in One Command

### Method 1: Comprehensive Test Script (Recommended)

```bash
python run_comprehensive_tests.py
```

This single command will:

- ✓ Check your environment
- ✓ Run all tests (unit, integration, views, security, deployment)
- ✓ Generate coverage report
- ✓ Create deployment readiness report
- ✓ Tell you if the system is ready for deployment

**Expected Time:** 10-15 minutes

---

### Method 2: Django Test Suite

```bash
# Run all tests
python manage.py test shs_system --verbosity=2

# With coverage
coverage run --source='shs_system' manage.py test shs_system
coverage report
```

**Expected Time:** 5-10 minutes

---

## Interpret Results

### ✓ SUCCESS - Ready for Deployment

```
Ran 150 tests in 120.5s
OK

VERDICT: System is READY for deployment!
```

### ⚠ WARNING - Review Before Deployment

```
Ran 150 tests in 120.5s
OK (skipped=2)

⚠ Code coverage: 75% (Target: >= 80%)
⚠ Deployment check found warnings

VERDICT: System is READY with warnings
```

### ✗ FAILURE - Fix Before Deployment

```
Ran 150 tests in 60.2s
FAILED (failures=5, errors=2)

✗ Unit tests failed
✗ Security tests failed

VERDICT: System is NOT READY for deployment!
```

---

## Quick Checks

### 1. System Check (30 seconds)

```bash
python manage.py check
```

### 2. Deployment Check (30 seconds)

```bash
python manage.py check --deploy
```

### 3. Database Check (30 seconds)

```bash
python manage.py showmigrations
```

---

## If Tests Fail

1. **Check the error message**

   - Read what test failed
   - Look for specific error details

2. **Check your configuration**

   ```bash
   # Verify .env file exists
   dir .env  # Windows
   ls .env   # Mac/Linux
   ```

3. **Verify database is running**

   ```bash
   python manage.py dbshell
   ```

4. **Reinstall dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

---

## Next Steps

### If All Tests Pass:

1. Review `deployment_checklist.md`
2. Review `deployment_report_*.txt` file
3. Perform manual testing
4. Deploy to production

### If Tests Fail:

1. Fix the failing tests
2. Re-run tests
3. Review documentation
4. Consult development team

---

## Quick Reference

| Command                             | Purpose                  | Time      |
| ----------------------------------- | ------------------------ | --------- |
| `python run_comprehensive_tests.py` | Full test suite + report | 10-15 min |
| `python manage.py test shs_system`  | Django tests only        | 5-10 min  |
| `python manage.py check --deploy`   | Deployment check         | 30 sec    |
| `coverage report`                   | View coverage            | 30 sec    |

---

## Get Detailed Help

For detailed testing instructions, see:

- `COMPREHENSIVE_TESTING_GUIDE.md` - Complete testing guide
- `deployment_checklist.md` - Deployment checklist
- `docs/DEPLOYMENT_GUIDE.md` - Deployment instructions

---

**Ready to Test?**

```bash
python run_comprehensive_tests.py
```

**That's it!** 🚀
