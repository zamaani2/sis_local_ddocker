# Cloudflare R2 Setup Guide - Free Storage Solution

Cloudflare R2 is the **cheapest storage option** - essentially free for your use case!

## 💰 Cost Breakdown

For your 700 students:
- **Storage**: ~200MB-1GB = **$0.003-$0.015/month** (practically free!)
- **Bandwidth**: **FREE** (unlimited egress)
- **Requests**: **FREE** (no per-request charges)

**Total Cost: ~$0.01/month** (essentially free!)

## 🚀 Step-by-Step Setup

### Step 1: Create Cloudflare Account

1. Go to [cloudflare.com](https://www.cloudflare.com)
2. Click "Sign Up" (free account works!)
3. Verify your email

### Step 2: Enable R2

1. Log into Cloudflare dashboard
2. Click "R2" in the left sidebar
3. If you don't see R2:
   - Go to "Workers & Pages" → "R2"
   - Or visit: https://dash.cloudflare.com/r2
4. Click "Get Started" or "Create bucket"

### Step 3: Create R2 Bucket

1. Click "Create bucket"
2. Enter bucket name: `schoolapp-media` (or your preferred name)
3. Choose location: Select closest region to your users
   - Recommended: `us-east-1` or `eu-west-1`
4. Click "Create bucket"

### Step 4: Create API Token

1. In R2 dashboard, click "Manage R2 API Tokens"
2. Click "Create API Token"
3. Configure token:
   - **Token name**: `railway-schoolapp` (or any name)
   - **Permissions**: 
     - ✅ Object Read & Write
     - ✅ Object Admin (optional, for management)
   - **TTL**: Leave blank (no expiration) or set expiration date
   - **Bucket access**: 
     - Select "Allow access to specific buckets"
     - Choose your bucket: `schoolapp-media`
4. Click "Create API Token"
5. **IMPORTANT**: Copy both values immediately:
   - **Access Key ID** (starts with something like `abc123...`)
   - **Secret Access Key** (long string - you can only see this once!)

### Step 5: Get Your Account ID and Endpoint

1. In R2 dashboard, look at the URL or bucket settings
2. Your endpoint will be: `https://<account-id>.r2.cloudflarestorage.com`
3. To find your Account ID:
   - Go to any Cloudflare dashboard page
   - Look at the URL or sidebar - it shows your account ID
   - Or go to: https://dash.cloudflare.com → Your account name → Overview

### Step 6: Configure CORS (Important!)

Your Django app needs to access R2 files. Set up CORS:

1. In R2 dashboard, go to your bucket
2. Click "Settings" tab
3. Scroll to "CORS Policy"
4. Click "Edit CORS Policy"
5. Add this configuration:

```json
[
  {
    "AllowedOrigins": [
      "https://your-app.railway.app",
      "https://your-custom-domain.com"
    ],
    "AllowedMethods": [
      "GET",
      "PUT",
      "POST",
      "DELETE",
      "HEAD"
    ],
    "AllowedHeaders": [
      "*"
    ],
    "ExposeHeaders": [
      "ETag"
    ],
    "MaxAgeSeconds": 3600
  }
]
```

6. Replace `your-app.railway.app` with your actual Railway domain
7. Click "Save"

### Step 7: Set Up Custom Domain (Optional - Skip if You Don't Have One!)

**⚠️ IMPORTANT: Custom domain is OPTIONAL!** You can use R2 without owning a domain.

**Option A: Use R2 Directly (No Custom Domain Needed) ✅**

If you don't have a custom domain, R2 will work perfectly fine using the default endpoint:
- URLs will be: `https://<account-id>.r2.cloudflarestorage.com/<bucket>/media/...`
- This works great and is completely free!
- **Just skip this step and continue to Step 8**

**Option B: Use Custom Domain (If You Own One)**

For better performance and cleaner URLs (only if you own a domain):

1. In R2 bucket settings, go to "Custom Domains"
2. Click "Connect Domain"
3. Enter your domain: `media.yourdomain.com`
4. Follow Cloudflare's DNS setup instructions
5. This gives you URLs like: `https://media.yourdomain.com/media/profile_pictures/...`

**Note**: You need to own a domain and have it on Cloudflare for this to work.

**For Railway Free Tier Users:**
- You can use your Railway domain: `schoolapp-web-production.up.railway.app`
- However, R2 custom domains require the domain to be on Cloudflare
- **Recommendation**: Just use R2's default endpoint - it works perfectly!

### Step 8: Configure Railway Environment Variables

In your Railway project, add these environment variables:

**If You DON'T Have a Custom Domain (Most Common):**

```bash
# Enable R2
USE_R2=True

# R2 Credentials (from Step 4)
R2_ACCESS_KEY_ID=your-access-key-id-here
R2_SECRET_ACCESS_KEY=your-secret-access-key-here

# R2 Bucket Configuration
R2_BUCKET_NAME=schoolapp-media
R2_ENDPOINT_URL=https://<your-account-id>.r2.cloudflarestorage.com

# Leave R2_CUSTOM_DOMAIN empty or don't set it
```

**If You DO Have a Custom Domain:**

```bash
# Enable R2
USE_R2=True

# R2 Credentials (from Step 4)
R2_ACCESS_KEY_ID=your-access-key-id-here
R2_SECRET_ACCESS_KEY=your-secret-access-key-here

# R2 Bucket Configuration
R2_BUCKET_NAME=schoolapp-media
R2_ENDPOINT_URL=https://<your-account-id>.r2.cloudflarestorage.com

# Optional: Custom Domain (only if you set one up in Step 7)
R2_CUSTOM_DOMAIN=media.yourdomain.com
```

**For Railway Free Tier Users:**
- Your Railway domain: `schoolapp-web-production.up.railway.app`
- **You don't need R2_CUSTOM_DOMAIN** - just use the R2 endpoint directly
- Files will be accessible via: `https://<account-id>.r2.cloudflarestorage.com/<bucket>/media/...`

**Important Security Note**: 
- Never commit these to Git!
- Use Railway's environment variables (secrets)
- Mark them as "Secret" in Railway dashboard

### Step 9: Verify Configuration

1. Deploy your app to Railway
2. Try uploading a test image (student profile picture)
3. Check R2 dashboard - you should see the file appear
4. Verify the image loads correctly on your site

## 🔍 Troubleshooting

### Issue: "Access Denied" errors

**Solution:**
- Verify API token has correct permissions
- Check bucket name matches exactly
- Ensure token hasn't expired

### Issue: Images not loading (CORS errors)

**Solution:**
- Verify CORS policy is configured correctly
- Check allowed origins include your Railway domain
- Clear browser cache and try again

### Issue: "Invalid endpoint" errors

**Solution:**
- Verify `R2_ENDPOINT_URL` format: `https://<account-id>.r2.cloudflarestorage.com`
- Ensure account ID is correct (no extra characters)

### Issue: Files upload but URLs are wrong

**Solution:**
- Check `R2_CUSTOM_DOMAIN` is set if using custom domain
- Verify `MEDIA_URL` in settings matches your configuration
- Check bucket name in URL matches `R2_BUCKET_NAME`

## 📊 Monitoring Usage

### Check Storage Usage:

1. Go to R2 dashboard
2. Click on your bucket
3. View "Storage" tab for usage statistics

### Set Up Alerts (Optional):

1. Go to Cloudflare dashboard → Notifications
2. Create alert for R2 storage thresholds
3. Get notified if usage exceeds limits

## 💡 Pro Tips

1. **Image Optimization**: Compress images before upload to save storage
   - Target: 200KB per profile picture
   - Use WebP format for better compression

2. **Lifecycle Policies**: Set up automatic cleanup of old files
   - Go to bucket → Settings → Lifecycle Rules
   - Example: Delete files older than 5 years

3. **CDN Integration**: R2 automatically uses Cloudflare's CDN
   - Fast global delivery
   - No additional cost

4. **Backup Strategy**: Consider backing up critical files
   - Use R2's versioning feature
   - Or sync to another storage service

## 🎯 Quick Reference

**R2 Pricing (as of 2024):**
- Storage: $0.015/GB/month
- Egress: **FREE** (unlimited)
- Requests: **FREE**
- No minimum charges

**Your Estimated Costs:**
- 200MB storage: $0.003/month
- 1GB storage: $0.015/month
- Bandwidth: $0 (free!)
- **Total: ~$0.01/month** 🎉

## ✅ Setup Checklist

- [ ] Cloudflare account created
- [ ] R2 bucket created (`schoolapp-media`)
- [ ] API token created with correct permissions
- [ ] Account ID and endpoint URL noted
- [ ] CORS policy configured
- [ ] Custom domain set up (optional)
- [ ] Railway environment variables configured
- [ ] Test upload successful
- [ ] Images loading correctly on site

## 🔗 Useful Links

- [Cloudflare R2 Dashboard](https://dash.cloudflare.com/r2)
- [R2 Documentation](https://developers.cloudflare.com/r2/)
- [R2 Pricing](https://developers.cloudflare.com/r2/pricing/)
- [R2 API Reference](https://developers.cloudflare.com/r2/api/)

---

**That's it!** Your storage is now configured and essentially free. With 700 students, you'll pay less than $0.02/month for storage. 🎉

