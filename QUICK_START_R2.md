# Quick Start: Free Storage with Cloudflare R2

Get free storage set up in 5 minutes! 🚀

## ⚡ 5-Minute Setup

### 1. Create Cloudflare Account (1 min)
- Go to [cloudflare.com](https://www.cloudflare.com) → Sign Up (free!)

### 2. Create R2 Bucket (1 min)
- Dashboard → R2 → Create bucket
- Name: `schoolapp-media`
- Location: Choose closest to you

### 3. Get API Credentials (2 min)
- R2 → Manage R2 API Tokens → Create API Token
- Permissions: Object Read & Write
- **Copy both keys immediately!**

### 4. Configure Railway (1 min)
Add these environment variables in Railway:

```bash
USE_R2=True
R2_ACCESS_KEY_ID=<paste-your-access-key>
R2_SECRET_ACCESS_KEY=<paste-your-secret-key>
R2_BUCKET_NAME=schoolapp-media
R2_ENDPOINT_URL=https://<your-account-id>.r2.cloudflarestorage.com

# NO CUSTOM DOMAIN NEEDED! Leave R2_CUSTOM_DOMAIN empty or don't set it.
```

**To find your Account ID:**
- Look at Cloudflare dashboard URL or sidebar
- Format: `https://<account-id>.r2.cloudflarestorage.com`

### 5. Set CORS (1 min)
- R2 bucket → Settings → CORS Policy
- Add your Railway domain: `https://schoolapp-web-production.up.railway.app`
- Also add: `https://*.up.railway.app` (for all Railway subdomains)
- Save

## ✅ Done!

Your storage is now configured. Cost: **~$0.01/month** for 700 students!

## 📖 Need More Details?

See full guide: [docs/CLOUDFLARE_R2_SETUP.md](docs/CLOUDFLARE_R2_SETUP.md)

## 🆘 Quick Troubleshooting

**Images not uploading?**
- Check API token permissions
- Verify bucket name matches exactly

**CORS errors?**
- Make sure CORS policy includes your Railway domain
- Clear browser cache

**"Invalid endpoint" error?**
- Check `R2_ENDPOINT_URL` format
- Ensure account ID is correct

---

**That's it!** You now have essentially free storage. 🎉

