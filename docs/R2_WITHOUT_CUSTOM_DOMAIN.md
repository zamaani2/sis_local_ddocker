# Using Cloudflare R2 Without a Custom Domain

**Short Answer: YES! You can use R2 without a custom domain!** ✅

## 🎯 For Railway Free Tier Users

If you're using Railway's free tier with a domain like:
- `schoolapp-web-production.up.railway.app`

You **don't need** a custom domain for R2. Here's how it works:

## ✅ How It Works Without Custom Domain

### What Happens:

1. **Files are stored in R2** (Cloudflare's storage)
2. **Files are accessed via R2's default endpoint:**
   ```
   https://<your-account-id>.r2.cloudflarestorage.com/<bucket-name>/media/...
   ```

3. **Your Django app serves the URLs** - users see the images on your Railway site
4. **Everything works perfectly!** No custom domain needed

### Example:

When a student profile picture is uploaded:
- **Stored at**: `https://abc123.r2.cloudflarestorage.com/schoolapp-media/media/profile_pictures/student_123.jpg`
- **Displayed on**: `https://schoolapp-web-production.up.railway.app` (your Railway site)
- **User sees**: The image loads perfectly on your site!

## 🔧 Configuration (No Custom Domain)

### Step 1: Set Up R2 (Same as Normal)

1. Create Cloudflare account
2. Create R2 bucket
3. Get API credentials

### Step 2: Configure CORS

In your R2 bucket CORS settings, add your Railway domain:

```json
[
  {
    "AllowedOrigins": [
      "https://schoolapp-web-production.up.railway.app",
      "https://*.up.railway.app"
    ],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

**Important**: Include `https://*.up.railway.app` to allow all Railway subdomains.

### Step 3: Railway Environment Variables

Set these in Railway (NO custom domain needed):

```bash
USE_R2=True
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret-key
R2_BUCKET_NAME=schoolapp-media
R2_ENDPOINT_URL=https://<your-account-id>.r2.cloudflarestorage.com

# DON'T set R2_CUSTOM_DOMAIN - leave it empty!
```

**That's it!** No custom domain needed.

## 📝 What the URLs Look Like

### With Custom Domain (Not Needed):
```
https://media.yourdomain.com/media/profile_pictures/student_123.jpg
```

### Without Custom Domain (What You'll Use):
```
https://abc123def456.r2.cloudflarestorage.com/schoolapp-media/media/profile_pictures/student_123.jpg
```

**Both work exactly the same!** The R2 URL is just longer, but:
- ✅ Works perfectly
- ✅ Fast (Cloudflare CDN)
- ✅ Free
- ✅ No setup needed

## 🎨 How It Appears to Users

Users won't see the R2 URL directly. Here's what happens:

1. **User visits**: `https://schoolapp-web-production.up.railway.app/student/123/`
2. **Django serves HTML** with image tag: `<img src="https://abc123.r2.../student_123.jpg">`
3. **Browser loads image** from R2 (fast, via Cloudflare CDN)
4. **User sees**: Image displayed on your site

**The R2 URL is in the HTML, but users just see the image on your site!**

## ✅ Advantages of No Custom Domain

1. **No Domain Needed**: Works immediately, no domain purchase
2. **No DNS Setup**: No configuration needed
3. **Still Fast**: Cloudflare CDN still works
4. **Still Free**: Same cost ($0.01/month)
5. **Less Complexity**: Fewer things to configure

## 🔒 Security Note

Even without a custom domain:
- ✅ Files are secure
- ✅ CORS protects your site
- ✅ Files are private (only accessible via your app)
- ✅ Same security as with custom domain

## 🆚 Custom Domain vs No Custom Domain

| Feature | With Custom Domain | Without Custom Domain |
|---------|-------------------|----------------------|
| Setup Time | 10-15 minutes | 5 minutes |
| Cost | Domain cost ($10-15/year) | Free |
| URL Length | Shorter | Longer (but hidden in HTML) |
| Performance | Same | Same (Cloudflare CDN) |
| Security | Same | Same |
| **Recommendation** | Only if you own a domain | **Perfect for free tier!** |

## 🎯 Recommendation

**For Railway Free Tier Users:**
- ✅ **Use R2 without custom domain** - it's simpler and works perfectly
- ✅ Save money (no domain purchase needed)
- ✅ Get started faster

**Only get a custom domain if:**
- You want shorter URLs (for sharing direct links)
- You already own a domain
- You want branding consistency

## 📖 Quick Setup Checklist

- [ ] Create Cloudflare account
- [ ] Create R2 bucket
- [ ] Get API credentials
- [ ] Configure CORS with Railway domain
- [ ] Set Railway environment variables (NO R2_CUSTOM_DOMAIN)
- [ ] Deploy and test!

## 🆘 Common Questions

**Q: Will images load slowly without custom domain?**
A: No! Cloudflare CDN works the same. Images load fast globally.

**Q: Can I add custom domain later?**
A: Yes! Just set `R2_CUSTOM_DOMAIN` and configure it in Cloudflare.

**Q: Do users see the R2 URL?**
A: Only in browser dev tools. The image appears normally on your site.

**Q: Is it less secure?**
A: No! Same security. CORS protects your files.

---

**Bottom Line**: You don't need a custom domain! R2 works perfectly with Railway's free domain. 🎉

