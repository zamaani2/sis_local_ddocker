# Railway PORT Error Fix

## Error Message

```
Error: '$PORT' is not a valid port number.
```

## Cause

Railway automatically sets the `PORT` environment variable, but the Dockerfile was using a hardcoded port (8000) instead of reading the `PORT` variable.

## Solution

The configuration has been updated to:

1. **Use startup script** (`start.sh`) that properly reads the `PORT` environment variable
2. **Updated Dockerfile** to use the startup script as entrypoint
3. **Removed hardcoded port** from railway.json (Dockerfile handles it now)

## What Changed

### Before:
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", ...]
```

### After:
```dockerfile
ENTRYPOINT ["/app/start.sh"]
```

The `start.sh` script:
- Reads `PORT` from environment (Railway sets this automatically)
- Falls back to 8000 if PORT is not set (for local development)
- Runs migrations and collects static files
- Starts Gunicorn on the correct port

## Verification

After deployment, Railway will:
1. Set `PORT` environment variable automatically
2. Start script reads `PORT` and starts Gunicorn on that port
3. Your app will be accessible on Railway's domain

## If You Still Get Errors

1. **Check Railway Environment Variables:**
   - Railway should automatically set `PORT`
   - Don't manually set it unless needed

2. **Verify Dockerfile:**
   - Make sure `start.sh` is copied and executable
   - Check that ENTRYPOINT points to `/app/start.sh`

3. **Check Logs:**
   - Railway dashboard → Your service → Logs
   - Look for "PORT is set to: XXXX" message
   - Verify Gunicorn starts successfully

4. **Test Locally:**
   ```bash
   PORT=5000 docker run -p 5000:5000 your-image
   ```
   Should start on port 5000

## Alternative: Direct CMD (If Script Doesn't Work)

If the startup script approach doesn't work, you can use:

```dockerfile
CMD sh -c "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120 SchoolApp.wsgi:application"
```

But the startup script approach is recommended as it also handles migrations and static files.

---

**The fix is already applied!** Just redeploy on Railway and the error should be resolved.

