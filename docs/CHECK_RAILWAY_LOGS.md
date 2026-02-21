# How to Check Railway Logs for Database Issues

## Step 1: View Logs in Railway

1. Go to Railway dashboard
2. Click on your **Django service** (not PostgreSQL)
3. Click **"Deployments"** tab
4. Click on the **latest deployment**
5. Click **"View Logs"** or **"Logs"** tab

## Step 2: Look for These Messages

After the app starts, you should see:

### ✅ Good Output (Settings Loading):
```
==========================================
Starting SchoolApp...
==========================================
PORT is set to: 8080
DJANGO_SETTINGS_MODULE: SchoolApp.settings_railway

✅ DATABASE_URL is configured
   DATABASE_URL starts with: postgresql://...

============================================================
RAILWAY SETTINGS LOADED
============================================================
DJANGO_SETTINGS_MODULE: SchoolApp.settings_railway
DATABASE_URL present: True
DATABASE_PUBLIC_URL present: True/False
Using DATABASE_URL: True
DATABASE_URL starts with: postgresql://...
============================================================
✅ Database configured from DATABASE_URL
   Host: <railway-host> (NOT localhost!)
   Port: 5432
   Name: <database-name>
   User: postgres
```

### ❌ Bad Output (Settings Not Loading):
```
DJANGO_SETTINGS_MODULE: NOT SET
```
OR
```
DJANGO_SETTINGS_MODULE: SchoolApp.settings
```
(Should be `SchoolApp.settings_railway`!)

### ❌ Bad Output (No DATABASE_URL):
```
❌ WARNING: DATABASE_URL is not set!
```
OR
```
DATABASE_URL present: False
❌ ERROR: No DATABASE_URL or DATABASE_PUBLIC_URL found!
```

### ❌ Bad Output (Wrong Host):
```
✅ Database configured from DATABASE_URL
   Host: localhost  ← THIS IS WRONG!
```

## Step 3: What Each Message Means

| Message | Meaning | Action |
|---------|---------|--------|
| `DJANGO_SETTINGS_MODULE: NOT SET` | Settings module not configured | Set `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway` |
| `DJANGO_SETTINGS_MODULE: SchoolApp.settings` | Wrong settings file | Change to `SchoolApp.settings_railway` |
| `DATABASE_URL present: False` | DATABASE_URL not set | Add PostgreSQL service or check variables |
| `Host: localhost` | Wrong database config | Settings file not loading correctly |
| `❌ ERROR parsing DATABASE_URL` | Invalid format | Check DATABASE_URL format |

## Step 4: Common Issues and Fixes

### Issue: "DJANGO_SETTINGS_MODULE: NOT SET"

**Fix:**
1. Railway → Django service → Variables
2. Add: `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway`
3. Redeploy

### Issue: "DATABASE_URL present: False"

**Fix:**
1. Check if PostgreSQL service exists
2. Check if services are linked
3. Check Variables tab for DATABASE_URL
4. If missing, get from PostgreSQL service → Settings → Connect

### Issue: "Host: localhost"

**Fix:**
- This means `settings_railway.py` is not being used
- Verify `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway`
- Check exact spelling (case-sensitive!)

## Step 5: Share Logs

If still having issues, copy the relevant log lines:
- The "Starting SchoolApp..." section
- The "RAILWAY SETTINGS LOADED" section
- Any error messages
- The database configuration output

---

**Check your logs now!** They'll tell you exactly what's wrong. 🔍

