# Quick Fix: Database Connection Error

## 🚨 Error You're Seeing

```
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
```

## ✅ Solution (2 Minutes)

### Step 1: Add PostgreSQL in Railway

1. Go to your Railway project dashboard
2. Click **"+ New"** (top right)
3. Select **"Database"** → **"Add PostgreSQL"**
4. Wait for it to provision (30 seconds)

### Step 2: Verify DATABASE_URL

1. Go to your **Django service** (not the database)
2. Click **"Variables"** tab
3. Look for `DATABASE_URL` - it should appear automatically
4. If not there, Railway will add it when services are linked

### Step 3: Redeploy

1. Railway will auto-redeploy, OR
2. Click **"Deploy"** → **"Redeploy"** on your Django service

### Step 4: Check Logs

You should now see:
```
Database configured from DATABASE_URL
Running migrations...
Operations to perform:
  Apply all migrations: ...
```

## ✅ That's It!

The database connection error should be gone. Your app will now:
- ✅ Connect to Railway's PostgreSQL
- ✅ Run migrations automatically
- ✅ Work correctly

## 🔍 If Still Not Working

1. **Check Variables:**
   - Django service → Variables tab
   - Look for `DATABASE_URL`
   - Should start with `postgresql://`

2. **Check Service Link:**
   - Both services (Django + PostgreSQL) should be in same project
   - Railway auto-links them

3. **Check Settings:**
   - Ensure `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway` is set

4. **Redeploy:**
   - Sometimes a fresh deploy fixes connection issues

---

**The code is already fixed!** Just add PostgreSQL service in Railway. 🚀

