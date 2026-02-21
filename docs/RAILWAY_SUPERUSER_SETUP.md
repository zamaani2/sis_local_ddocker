# Railway Superuser Auto-Creation

## What this does

On each deployment, the app will:

1. Run database migrations (if `DATABASE_URL` is set)
2. **Automatically create a superuser** if none exists
   - Uses environment variables for credentials
   - Skips creation if a superuser already exists

This logic runs from `start.sh` so it's non-interactive and safe for Railway.

## Required environment variables (Railway → Django service → Variables)

Set these to control the initial superuser:

- **`SUPERUSER_EMAIL`** (recommended)
  - Example: `admin@yourdomain.com`
- **`SUPERUSER_PASSWORD`** (recommended)
  - Example: `your-strong-password`
- **`SUPERUSER_USERNAME`** (optional)
  - If not set, it will use `SUPERUSER_EMAIL` or `admin`

If you **don't** set these:

- Username: `admin`
- Email: `admin@example.com`
- Password: `admin123` (you should change this ASAP)

## How it works (summary of code in `start.sh`)

After migrations succeed, the script runs:

```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os

User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    username = os.environ.get('SUPERUSER_USERNAME') or os.environ.get('SUPERUSER_EMAIL') or 'admin'
    email = os.environ.get('SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('SUPERUSER_PASSWORD', 'admin123')

    print(f'No superuser found. Creating initial superuser: {username} ({email})')
    User.objects.create_superuser(username=username, email=email, password=password)
    print('✅ Initial superuser created successfully.')
else:
    print('ℹ️ Superuser already exists. Skipping creation.')
"
```

## One-time setup steps

1. In Railway, open your **Django service**
2. Go to **Variables** tab
3. Add:

```text
SUPERUSER_EMAIL=your-email@example.com
SUPERUSER_PASSWORD=your-strong-password
SUPERUSER_USERNAME=your-admin-username   # optional
```

4. Redeploy the service
5. Check logs to confirm:

```text
No superuser found. Creating initial superuser: your-admin-username (your-email@example.com)
✅ Initial superuser created successfully.
```

If a superuser already exists, you'll see:

```text
ℹ️ Superuser already exists. Skipping creation.
```

## Security notes

- Use a **strong password** for `SUPERUSER_PASSWORD`
- Treat these variables as secrets in Railway
- After first login, you can:
  - Change the password from Django admin
  - Optionally remove the `SUPERUSER_PASSWORD` env var

---

This makes deployments fully automatic: no need to run `createsuperuser` manually on Railway. 🎉


