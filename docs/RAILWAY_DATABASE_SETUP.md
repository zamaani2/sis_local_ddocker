# Railway Database Setup Guide

## Error: Connection to localhost:5432 failed

This error occurs when Django tries to connect to PostgreSQL at `localhost`, which doesn't exist on Railway.

## ✅ Solution: Add PostgreSQL Service

Railway requires you to **explicitly add a PostgreSQL service** to your project. Here's how:

### Step 1: Add PostgreSQL Service

1. Go to your Railway project dashboard
2. Click **"+ New"** button
3. Select **"Database"** → **"Add PostgreSQL"**
4. Railway will automatically:
   - Create a PostgreSQL database
   - Set the `DATABASE_URL` environment variable
   - Link it to your Django service

### Step 2: Verify DATABASE_URL

1. Go to your Django service
2. Click on **"Variables"** tab
3. Look for `DATABASE_URL` - it should be automatically set
4. It should look like: `postgresql://user:password@host:port/dbname`

### Step 3: Link Services (If Not Automatic)

If `DATABASE_URL` is not automatically set:

1. Go to your PostgreSQL service
2. Click **"Settings"** tab
3. Under **"Connect"**, copy the connection details
4. Go to your Django service → **"Variables"**
5. Add `DATABASE_URL` with the connection string

### Step 4: Redeploy

After adding the database:

1. Railway will automatically redeploy
2. Or trigger a manual redeploy
3. Check logs - you should see: `"Database configured from DATABASE_URL"`

## 🔍 Troubleshooting

### Issue: DATABASE_URL not set

**Solution:**
- Make sure PostgreSQL service is added to your project
- Ensure services are linked (Railway usually does this automatically)
- Check Variables tab for `DATABASE_URL`

### Issue: Still connecting to localhost

**Solution:**
- Verify `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway` is set
- Check that `DATABASE_URL` is in environment variables
- Restart/redeploy the service

### Issue: Connection timeout

**Solution:**
- Wait a few seconds for database to be ready
- Check PostgreSQL service is running
- Verify network connectivity between services

### Issue: Authentication failed

**Solution:**
- Railway automatically sets credentials
- Don't manually set `DB_USER`, `DB_PASSWORD`, etc.
- Use `DATABASE_URL` only

## 📋 Quick Checklist

- [ ] PostgreSQL service added to Railway project
- [ ] `DATABASE_URL` appears in Django service variables
- [ ] `DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway` is set
- [ ] Services are linked (automatic in Railway)
- [ ] Service redeployed after adding database
- [ ] Logs show "Database configured from DATABASE_URL"

## 🎯 Expected Behavior

After setup:

1. **Logs should show:**
   ```
   Database configured from DATABASE_URL
   Running migrations...
   Operations to perform:
     Apply all migrations: ...
   ```

2. **No more localhost errors:**
   - ✅ No "connection to localhost:5432 failed"
   - ✅ Migrations run successfully
   - ✅ App connects to database

3. **App works:**
   - ✅ Can access admin panel
   - ✅ Can create users
   - ✅ Database operations work

## 💡 Important Notes

1. **Railway automatically provides DATABASE_URL** when you add PostgreSQL
2. **Don't manually set DB_HOST, DB_USER, etc.** - use DATABASE_URL
3. **Services must be in the same project** to auto-link
4. **Free tier includes PostgreSQL** - no extra cost!

## 🆘 Still Having Issues?

1. Check Railway logs for detailed error messages
2. Verify PostgreSQL service is running (green status)
3. Check service networking (services should be linked)
4. Try removing and re-adding PostgreSQL service
5. Ensure `settings_railway.py` is being used (check `DJANGO_SETTINGS_MODULE`)

---

**The fix is in the code!** Just add PostgreSQL service in Railway and it will work. 🚀

