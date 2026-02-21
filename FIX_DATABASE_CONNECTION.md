# Fix Database Connection - Quick Checklist

## 🚨 Problem: Still connecting to localhost:5432

Even though you added `DATABASE_URL`, the app is still trying to connect to localhost.

## ✅ Solution: Check These 3 Things

### 1. Is `DJANGO_SETTINGS_MODULE` set? (MOST IMPORTANT!)

**In Railway Dashboard:**
1. Go to your **Django service** (not PostgreSQL)
2. Click **"Variables"** tab
3. Look for: `DJANGO_SETTINGS_MODULE`
4. **Value MUST be:** `SchoolApp.settings_railway`

**If it's missing or wrong:**
- Click **"+ New Variable"**
- Name: `DJANGO_SETTINGS_MODULE`
- Value: `SchoolApp.settings_railway`
- Click **"Add"**
- **Redeploy** your service

### 2. Is `DATABASE_URL` set correctly?

**In Railway Dashboard:**
1. Go to your **Django service** → **"Variables"** tab
2. Look for: `DATABASE_URL`
3. Should start with: `postgresql://` or `postgres://`

**If it's missing:**
- Make sure PostgreSQL service is added
- Make sure services are linked
- Railway should auto-set this when services are linked

**To manually add:**
1. Go to **PostgreSQL service** → **"Settings"** tab
2. Under **"Connect"**, copy the connection string
3. Go to **Django service** → **"Variables"**
4. Add: `DATABASE_URL` = (paste connection string)

### 3. Are services linked?

**Check:**
- Both Django and PostgreSQL services are in **same Railway project**
- PostgreSQL service shows **"Connected"** status
- Django service shows PostgreSQL in connected services

## 🔍 How to Verify It's Working

After setting `DJANGO_SETTINGS_MODULE` and redeploying, check the logs:

**You should see:**
```
==========================================
Starting SchoolApp...
==========================================
DJANGO_SETTINGS_MODULE: SchoolApp.settings_railway

✅ DATABASE_URL is configured

============================================================
RAILWAY SETTINGS LOADED
============================================================
DATABASE_URL present: True
✅ Database configured from DATABASE_URL
   Host: <some-host> (NOT localhost!)
```

**If you see:**
```
❌ WARNING: No DATABASE_URL or DB_* variables found!
```
Then `DATABASE_URL` is not set.

**If you see:**
```
DJANGO_SETTINGS_MODULE: NOT SET
```
Then `DJANGO_SETTINGS_MODULE` is not set.

## 📝 Step-by-Step Fix

1. **Set `DJANGO_SETTINGS_MODULE`:**
   - Django service → Variables → Add
   - Name: `DJANGO_SETTINGS_MODULE`
   - Value: `SchoolApp.settings_railway`
   - Save

2. **Verify `DATABASE_URL`:**
   - Django service → Variables
   - Should see `DATABASE_URL` (Railway auto-sets this)
   - If missing, add it manually from PostgreSQL service

3. **Redeploy:**
   - Click "Deploy" → "Redeploy"
   - Or wait for auto-redeploy

4. **Check logs:**
   - Look for "RAILWAY SETTINGS LOADED"
   - Look for database host (should NOT be localhost)

## ⚠️ Most Common Issue

**90% of the time, the problem is:**
- `DJANGO_SETTINGS_MODULE` is NOT set to `SchoolApp.settings_railway`
- Or it's set to `SchoolApp.settings` (wrong!)

**Fix:** Set it to `SchoolApp.settings_railway` in Railway variables.

---

**The code is already fixed with better debugging!** Just set the environment variables correctly. 🚀

