# Railway Storage Guide - Handling Media Files

## ⚠️ Critical Storage Issue

**Railway's filesystem is EPHEMERAL** - this means:
- Files stored locally are **LOST** when you redeploy
- Files stored locally are **LOST** when the container restarts
- Files stored locally are **LOST** when Railway scales your service

### What Happens When Storage Fills Up?

1. **Upload Failures**: New file uploads will fail with "No space left on device" errors
2. **Application Errors**: Your Django app may crash or become unstable
3. **Database Issues**: PostgreSQL may fail to write temporary files
4. **Service Restart**: Railway may restart your service, causing downtime

## 📊 Storage Requirements Analysis

### Your Current Usage:

**Profile Pictures:**
- 700+ students
- Average profile picture size: ~200KB (optimized) to 2MB (unoptimized)
- **Estimated storage: 140MB - 1.4GB** (if all students have pictures)

**Terminal Reports:**
- ✅ **Good News**: Terminal reports are generated **on-demand** and NOT saved to disk
- PDFs are generated in memory and sent directly to the browser
- **Storage impact: ZERO** (unless you're saving them, which you're not)

**Other Media Files:**
- School logos/images
- Signatures
- Backup files (if stored locally)
- **Estimated additional: 50-200MB**

### Total Estimated Storage Needs:
- **Minimum**: ~200MB
- **Realistic**: ~500MB - 1GB
- **With growth**: 2-5GB over time

## 🚨 Why Local Storage Won't Work on Railway

Railway containers are stateless. Even if you have enough space initially:
- Every redeploy = **ALL FILES LOST**
- Container restart = **ALL FILES LOST**
- Scaling = **NEW CONTAINERS HAVE NO FILES**

## ✅ Solution: External Storage

You **MUST** use external storage for media files. Three options:

### Option 1: AWS S3 (Recommended for Production)

**Pros:**
- Highly reliable and scalable
- Industry standard
- Good performance worldwide
- Pay-as-you-go pricing

**Cons:**
- Costs money (but very affordable)
- Requires AWS account

**Setup:**
1. Create AWS account
2. Create S3 bucket
3. Create IAM user with S3 permissions
4. Configure environment variables in Railway

**Cost Estimate:**
- Storage: $0.023/GB/month
- Requests: $0.005 per 1,000 requests
- **For 1GB storage + 10,000 requests/month: ~$0.03/month**

### Option 2: Cloudflare R2 (⭐ RECOMMENDED - Essentially FREE!)

**Pros:**
- **FREE** egress (no bandwidth charges - unlimited!)
- **FREE** requests (no per-request fees)
- Very cheap storage ($0.015/GB/month)
- S3-compatible API
- Excellent performance with global CDN
- **For 700 students: ~$0.01/month** (practically free!)

**Cons:**
- Requires Cloudflare account (free account works!)
- Small storage fee (but negligible)

**Setup:**
📖 **See detailed guide: [CLOUDFLARE_R2_SETUP.md](./CLOUDFLARE_R2_SETUP.md)**

Quick steps:
1. Create free Cloudflare account
2. Enable R2 in dashboard
3. Create R2 bucket
4. Create API token
5. Configure environment variables in Railway

**Cost Estimate for Your Use Case:**
- 200MB-1GB storage: **$0.003-$0.015/month**
- Bandwidth: **FREE** (unlimited)
- Requests: **FREE**
- **Total: ~$0.01/month** 🎉

### Option 3: Railway Volumes (Limited Use)

**Pros:**
- Integrated with Railway
- Persistent storage

**Cons:**
- **NOT recommended for media files**
- Limited to single region
- More expensive than S3/R2
- Not ideal for serving files directly

**Best Use:** Database backups, temporary files

## 🔧 Configuration Steps

### Step 1: Install Required Package

Already installed: `django-storages>=1.14.2` ✅

### Step 2: Choose Your Storage Provider

#### For AWS S3:

Add these environment variables in Railway:

```bash
USE_S3=True
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
AWS_S3_CUSTOM_DOMAIN=your-cdn-domain.com  # Optional: CloudFront CDN
```

#### For Cloudflare R2:

Add these environment variables in Railway:

```bash
USE_R2=True
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=your-bucket-name
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_CUSTOM_DOMAIN=your-custom-domain.com  # Optional: Custom domain
```

### Step 3: Update Railway Settings

The `settings_railway.py` file is already configured to use external storage when these environment variables are set.

### Step 4: Set Django Settings Module

In Railway, set:
```bash
DJANGO_SETTINGS_MODULE=SchoolApp.settings_railway
```

## 📝 Migration Guide

### Moving Existing Files to External Storage

If you have existing media files, you'll need to migrate them:

1. **Backup existing files** from your current deployment
2. **Upload to S3/R2** using AWS CLI or Cloudflare R2 CLI
3. **Update database** to point to new URLs (if needed)

### Example Migration Script

```python
# migrate_to_s3.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SchoolApp.settings_railway')
django.setup()

from django.core.files.storage import default_storage
from shs_system.models import Student
from django.core.files.base import ContentFile

# Migrate student profile pictures
for student in Student.objects.exclude(profile_picture=''):
    if student.profile_picture:
        try:
            # Read existing file
            with open(student.profile_picture.path, 'rb') as f:
                file_content = f.read()
            
            # Save to S3/R2
            file_name = student.profile_picture.name
            default_storage.save(file_name, ContentFile(file_content))
            
            print(f"Migrated: {student.full_name}")
        except Exception as e:
            print(f"Error migrating {student.full_name}: {e}")
```

## 🎯 Recommended Setup for Your Use Case

**For 700+ students with profile pictures:**

1. **⭐ Use Cloudflare R2** (essentially FREE - $0.01/month!)
   - Create bucket: `schoolapp-media`
   - Set up custom domain: `media.yourschool.com` (optional)
   - Configure CORS for image access
   - **📖 Full setup guide: [CLOUDFLARE_R2_SETUP.md](./CLOUDFLARE_R2_SETUP.md)**

2. **Optimize Images** (reduce storage needs)
   - Compress profile pictures to max 200KB
   - Use WebP format for better compression
   - Implement image resizing on upload

3. **Monitor Storage Usage**
   - Set up alerts in Cloudflare dashboard
   - Track storage growth over time
   - With R2, you'll likely never exceed $0.50/month even with growth

## 💰 Cost Comparison

| Storage Provider | Storage (1GB) | Bandwidth (100GB) | Total/Month |
|-----------------|---------------|-------------------|-------------|
| AWS S3          | $0.023        | $9.00             | ~$9.02      |
| **Cloudflare R2** | **$0.015**   | **FREE**          | **~$0.015** |
| Railway Volumes | N/A           | N/A               | ~$5-10      |

**For Your 700 Students:**
- Cloudflare R2: **~$0.01/month** (200MB-1GB storage)
- AWS S3: **~$9/month** (with bandwidth)
- Railway Volumes: **~$5-10/month**

**⭐ Recommendation: Use Cloudflare R2** - It's essentially FREE and perfect for your use case!

## 🔒 Security Considerations

1. **Bucket Policies**: Set up proper bucket policies to allow public read for media files
2. **CORS Configuration**: Configure CORS for your domain
3. **Access Control**: Use signed URLs for sensitive files (if needed)
4. **Backup Strategy**: Consider backing up critical files

## 📚 Additional Resources

- [AWS S3 Setup Guide](https://docs.aws.amazon.com/s3/)
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [Django Storages Documentation](https://django-storages.readthedocs.io/)

## ⚡ Quick Start Checklist

- [ ] Choose storage provider (S3 or R2)
- [ ] Create bucket/account
- [ ] Set environment variables in Railway
- [ ] Update `DJANGO_SETTINGS_MODULE` to `SchoolApp.settings_railway`
- [ ] Test file upload
- [ ] Migrate existing files (if any)
- [ ] Set up monitoring/alerts
- [ ] Configure custom domain (optional)

---

**Remember**: Terminal reports are generated on-demand and don't consume storage. Your main concern is profile pictures and other media files. With external storage configured, you'll have unlimited scalability!

