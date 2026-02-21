# Railway Database Connection Troubleshooting

## Error: Still connecting to localhost:5432

If you've added `DATABASE_URL` but still see localhost errors, check these:

## ✅ Checklist

### 1. Is `DJANGO_SETTINGS_MODULE` set?

**Check in Railway:**
- Go to your Django service
- Click "Variables" tab
- Look for: `DJANGO_SETTINGS_MODULE`
- Value should be: `SchoolApp.settings_railway`

**If not set:**
- Add it: `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway`
- Redeploy

### 2. Is `DATABASE_URL` actually set?

**Check in Railway:**
- Go to your Django service
- Click "Variables" tab
- Look for: `DATABASE_URL`
- Should start with: `postgresql://` or `postgres://`

**If not there:**
- Make sure PostgreSQL service is added
- Make sure services are linked
- Check PostgreSQL service → Settings → Connect

### 3. Are services linked?

**Check in Railway:**
- Both Django and PostgreSQL services should be in same project
- Railway auto-links them, but verify:
  - PostgreSQL service shows "Connected" status
  - Django service shows PostgreSQL in "Connected Services"

### 4. Check the logs

After redeploy, check logs for:

**Good signs:**
```
RAILWAY SETTINGS LOADED
DATABASE_URL present: True
✅ Database configured from DATABASE_URL
   Host: <some-host> (NOT localhost!)
```

**Bad signs:**
```
❌ WARNING: No DATABASE_URL or DB_* variables found!
❌ WARNING: Database connection will fail!
```

## 🔧 Step-by-Step Fix

### Step 1: Verify Settings Module

1. Railway dashboard → Django service → Variables
2. Add/verify: `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway`
3. Save

### Step 2: Verify Database Service

1. Railway dashboard → Check if PostgreSQL service exists
2. If not, add it: "+ New" → "Database" → "Add PostgreSQL"
3. Wait for it to provision

### Step 3: Verify DATABASE_URL

1. Railway dashboard → Django service → Variables
2. Look for `DATABASE_URL`
3. If missing:
   - Go to PostgreSQL service
   - Click "Settings" tab
   - Copy connection string
   - Add to Django service variables as `DATABASE_URL`

### Step 4: Redeploy

1. Trigger a redeploy
2. Check logs
3. Look for the debug messages

## 🐛 Common Issues

### Issue: DATABASE_URL is set but still using localhost

**Possible causes:**
1. `DJANGO_SETTINGS_MODULE` not set to `settings_railway`
2. Settings file not being loaded
3. Environment variable not being read

**Solution:**
- Verify `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway`
- Check logs for "RAILWAY SETTINGS LOADED" message
- If not present, settings_railway.py is not being used

### Issue: DATABASE_URL format is wrong

**Correct format:**
```
postgresql://user:password@host:port/dbname
```

**Check:**
- Starts with `postgresql://` or `postgres://`
- Contains `@` (separates credentials from host)
- Contains `/` (separates host from database name)

### Issue: Services not linked

**Solution:**
- Both services must be in same Railway project
- Railway auto-links, but you can manually link:
  - Django service → Settings → Connected Services
  - Add PostgreSQL service

## 📊 Debug Output

After the fix, you should see in logs:

```
==========================================
Starting SchoolApp...
==========================================
PORT is set to: 8080
DJANGO_SETTINGS_MODULE: SchoolApp.settings_railway

✅ DATABASE_URL is configured
   DATABASE_URL starts with: postgresql://postgres:...

============================================================
RAILWAY SETTINGS LOADED
============================================================
DATABASE_URL present: True
DATABASE_URL starts with: postgresql://postgres:...
============================================================
✅ Database configured from DATABASE_URL
   Host: <railway-postgres-host>
   Port: 5432
   Name: <database-name>
   User: postgres
```

## 🆘 Still Not Working?

1. **Check all environment variables:**
   - `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway` ✅
   - `DATABASE_URL=postgresql://...` ✅

2. **Verify PostgreSQL service:**
   - Service is running (green status)
   - Connection string is available

3. **Check service linking:**
   - Services are in same project
   - Services are linked

4. **Try manual DATABASE_URL:**
   - Get connection string from PostgreSQL service
   - Manually add to Django service variables
   - Format: `postgresql://user:password@host:port/dbname`

5. **Check logs for errors:**
   - Look for any error messages
   - Check if settings_railway.py is being loaded

---

**Most common issue:** `DJANGO_SETTINGS_MODULE` not set to `SchoolApp.settings_railway`!

