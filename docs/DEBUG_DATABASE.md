# Debug Database Connection Issue

## Check Railway Logs

After redeploying, check your Railway logs. You should see output like this:

```
============================================================
RAILWAY SETTINGS LOADED
============================================================
DJANGO_SETTINGS_MODULE: SchoolApp.settings_railway
DATABASE_URL present: True/False
DATABASE_PUBLIC_URL present: True/False
Using DATABASE_URL: True/False
DATABASE_URL starts with: postgresql://...
============================================================
✅ Database configured from DATABASE_URL
   Host: <should NOT be localhost>
   Port: 5432
   Name: <database-name>
   User: postgres
```

## What to Look For

### ✅ Good Signs:
- "RAILWAY SETTINGS LOADED" appears
- "DATABASE_URL present: True"
- "Host: <some-railway-host>" (NOT localhost)
- "✅ Database configured from DATABASE_URL"

### ❌ Bad Signs:
- No "RAILWAY SETTINGS LOADED" message = settings_railway.py not being used
- "DATABASE_URL present: False" = DATABASE_URL not set
- "Host: localhost" = Wrong database config
- "❌ ERROR parsing DATABASE_URL" = Invalid format

## Common Issues

### Issue 1: Settings file not loading

**Symptoms:**
- No "RAILWAY SETTINGS LOADED" in logs
- Still connecting to localhost

**Fix:**
- Verify `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway` is set
- Check exact spelling (case-sensitive!)
- Redeploy after setting

### Issue 2: DATABASE_URL not set

**Symptoms:**
- "DATABASE_URL present: False"
- "❌ ERROR: No DATABASE_URL or DATABASE_PUBLIC_URL found!"

**Fix:**
- Check Railway Variables tab
- Make sure PostgreSQL service is added
- Make sure services are linked
- Check if DATABASE_URL appears in variables

### Issue 3: DATABASE_URL format wrong

**Symptoms:**
- "⚠️ WARNING: DATABASE_URL doesn't start with postgresql://"
- "❌ ERROR parsing DATABASE_URL"

**Fix:**
- DATABASE_URL should start with `postgresql://` or `postgres://`
- Format: `postgresql://user:password@host:port/dbname`
- Get correct URL from PostgreSQL service → Settings → Connect

### Issue 4: Using DATABASE_PUBLIC_URL instead

**Symptoms:**
- DATABASE_URL is empty but DATABASE_PUBLIC_URL is set
- Connection still fails

**Fix:**
- Code now checks both DATABASE_URL and DATABASE_PUBLIC_URL
- But prefer DATABASE_URL (internal connection, faster)
- If only DATABASE_PUBLIC_URL works, use that

## Quick Test

1. **Check logs for "RAILWAY SETTINGS LOADED"**
   - If missing → `DJANGO_SETTINGS_MODULE` not set correctly

2. **Check "DATABASE_URL present"**
   - If False → DATABASE_URL not in environment variables

3. **Check "Host:" value**
   - If "localhost" → Wrong config being used
   - Should be Railway's database host

4. **Check for errors**
   - Look for "❌ ERROR" messages
   - They'll tell you what's wrong

## Next Steps

1. Redeploy your service
2. Check logs immediately after startup
3. Look for the debug output
4. Share the relevant log lines if still having issues

---

**The code now has extensive debugging!** Check your Railway logs to see what's happening.

