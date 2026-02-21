# Railway Deployment Guide

Complete guide for deploying SchoolApp on Railway platform.

## 🚀 Quick Start

### Prerequisites

1. Railway account ([railway.app](https://railway.app))
2. GitHub repository with your code
3. External storage account (AWS S3 or Cloudflare R2) - **REQUIRED**

### Step 1: Prepare Your Repository

1. Ensure all files are committed to Git
2. Push to GitHub
3. Verify `railway.json` and `Dockerfile` are in root directory

### Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will detect your Dockerfile automatically

### Step 3: Add PostgreSQL Database

1. In your Railway project, click "+ New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create and configure the database
4. The `DATABASE_URL` environment variable will be set automatically

### Step 4: Configure Environment Variables

Go to your service → Variables tab and add:

**Required Variables:**

```bash
DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway
DJANGO_SECRET_KEY=<generate-a-secret-key>
DJANGO_DEBUG=False
```

**Generate Secret Key:**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Storage Configuration (Choose ONE):**

**Option A: Cloudflare R2 (Recommended)**
```bash
USE_R2=True
R2_ACCESS_KEY_ID=<your-r2-access-key>
R2_SECRET_ACCESS_KEY=<your-r2-secret-key>
R2_BUCKET_NAME=<your-bucket-name>
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
```

**Option B: AWS S3**
```bash
USE_S3=True
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
AWS_STORAGE_BUCKET_NAME=<your-bucket-name>
AWS_S3_REGION_NAME=us-east-1
```

**Additional Variables:**
```bash
ALLOWED_HOSTS=your-app.railway.app,your-custom-domain.com
SITE_URL=https://your-app.railway.app
CSRF_TRUSTED_ORIGINS=https://your-app.railway.app
```

See `railway.env.example` for complete list.

### Step 5: Set Up External Storage

**⚠️ CRITICAL: You MUST set up external storage before deploying!**

See [RAILWAY_STORAGE_GUIDE.md](./RAILWAY_STORAGE_GUIDE.md) for detailed instructions.

**Quick Setup - Cloudflare R2:**

1. Create Cloudflare account
2. Go to R2 → Create bucket
3. Create API token with R2 permissions
4. Add environment variables to Railway

### Step 6: Deploy

1. Railway will automatically build and deploy
2. Monitor the build logs
3. Wait for deployment to complete
4. Your app will be available at `https://your-app.railway.app`

### Step 7: Run Migrations

After first deployment:

1. Go to your service → Deployments
2. Click on the latest deployment
3. Open the "Shell" tab
4. Run:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 📊 Resource Configuration

### Recommended Settings for Your Use Case (700+ students)

**Hobby Plan ($5/month):**
- Memory: 1GB RAM
- CPU: 1 vCPU
- Should handle 50-100 concurrent users

**Pro Plan ($20/month):**
- Memory: 2GB RAM
- CPU: 2 vCPU
- Better for 100-300 concurrent users

### Monitoring Resource Usage

1. Go to your service → Metrics
2. Monitor:
   - CPU usage
   - Memory usage
   - Network traffic
   - Request count

## 🔧 Configuration Details

### Port Configuration

Railway automatically sets the `PORT` environment variable. The start command uses this:

```bash
gunicorn --bind 0.0.0.0:$PORT ...
```

### Static Files

Static files are served using WhiteNoise middleware. They're collected during build and served directly by Django.

### Media Files

Media files MUST be stored externally (S3/R2). See storage guide for details.

## 🐛 Troubleshooting

### Build Failures

**Issue:** Build fails with dependency errors
**Solution:** Check `requirements.txt` and ensure all packages are compatible

**Issue:** Build fails with collectstatic error
**Solution:** This is expected during build. Static files will be collected at runtime.

### Runtime Errors

**Issue:** Application crashes on startup
**Solution:** 
- Check environment variables are set correctly
- Verify `DJANGO_SETTINGS_MODULE` is set to `SchoolApp.settings_railway`
- Check logs in Railway dashboard

**Issue:** Database connection errors
**Solution:**
- Verify PostgreSQL service is running
- Check `DATABASE_URL` is set (Railway sets this automatically)
- Ensure database migrations have run

**Issue:** Media files not uploading
**Solution:**
- Verify external storage is configured (S3/R2)
- Check storage credentials are correct
- Verify bucket exists and has correct permissions

**Issue:** Static files not loading
**Solution:**
- Run `python manage.py collectstatic --noinput` in Railway shell
- Check `STATIC_ROOT` is configured correctly
- Verify WhiteNoise middleware is enabled

### Storage Issues

**Issue:** "No space left on device" errors
**Solution:**
- You're using local storage! Configure external storage immediately
- Files stored locally are lost on redeploy anyway

**Issue:** Files disappear after redeploy
**Solution:**
- This is expected with local storage
- Configure external storage (S3/R2) to persist files

## 📈 Scaling

### Horizontal Scaling

Railway supports horizontal scaling:
1. Go to service → Settings
2. Enable "Replicas"
3. Set number of instances

**Note:** With multiple replicas, external storage (S3/R2) is essential!

### Vertical Scaling

Upgrade your plan for more resources:
- Hobby: Up to 48GB RAM, 48 vCPU
- Pro: Up to 1TB RAM, 1000 vCPU

## 🔒 Security Checklist

- [ ] `DJANGO_DEBUG=False` in production
- [ ] Strong `DJANGO_SECRET_KEY` set
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] `CSRF_TRUSTED_ORIGINS` set
- [ ] SSL/HTTPS enabled (automatic on Railway)
- [ ] Database credentials secure (Railway handles this)
- [ ] Storage credentials secure (use Railway secrets)
- [ ] Email credentials secure

## 💰 Cost Estimation

**Monthly Costs:**

- Railway Hobby Plan: $5/month
- PostgreSQL Database: Included in plan
- Cloudflare R2 Storage: ~$0.02/month (for 1GB)
- **Total: ~$5.02/month**

**For Higher Traffic:**

- Railway Pro Plan: $20/month
- Additional resources as needed
- Cloudflare R2: Scales with usage
- **Total: ~$20-30/month**

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Storage Guide](./RAILWAY_STORAGE_GUIDE.md)

## 🆘 Support

If you encounter issues:

1. Check Railway logs: Service → Deployments → Logs
2. Check Django logs: Service → Deployments → Shell → `tail -f logs/debug.log`
3. Review [RAILWAY_STORAGE_GUIDE.md](./RAILWAY_STORAGE_GUIDE.md) for storage issues
4. Check Railway status: [status.railway.app](https://status.railway.app)

---

**Remember:** External storage (S3/R2) is NOT optional - it's REQUIRED for Railway deployment!

