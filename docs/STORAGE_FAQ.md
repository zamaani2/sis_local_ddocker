# Storage FAQ - Answers to Common Questions

## Q: What happens when media storage is full on Railway?

**A:** When storage fills up on Railway:

1. **File Upload Failures**: New uploads will fail with errors like:
   - "No space left on device"
   - "Disk quota exceeded"
   - HTTP 500 errors

2. **Application Instability**: 
   - Django may crash when trying to write files
   - Database operations may fail (PostgreSQL needs temp space)
   - Application may become unresponsive

3. **Service Restarts**: Railway may restart your service, causing downtime

4. **Data Loss Risk**: If using local storage, files may be corrupted or lost

**However**, with Railway's ephemeral filesystem, **files stored locally are lost anyway** on redeploy, so this is why external storage is mandatory.

## Q: How much storage do I need for 700 students?

**A:** Storage breakdown:

**Profile Pictures:**
- 700 students × ~200KB (optimized) = **~140MB**
- 700 students × ~2MB (unoptimized) = **~1.4GB**

**Recommendation:** Optimize images to max 200KB each = **~140MB**

**Terminal Reports:**
- ✅ **ZERO storage** - Reports are generated on-demand, not saved

**Other Media:**
- School logos, signatures, etc.: **~50-100MB**

**Total Estimated:**
- **Minimum**: ~200MB
- **Realistic**: ~500MB
- **With growth**: 1-2GB over time

## Q: Can I use Railway's local storage for media files?

**A:** **NO - Not recommended!** Here's why:

1. **Ephemeral Filesystem**: Files are lost on:
   - Every redeploy
   - Container restart
   - Service scaling
   - Railway maintenance

2. **Limited Space**: Railway containers have limited disk space
3. **No Persistence**: Files don't survive deployments
4. **Scaling Issues**: New containers won't have existing files

**You MUST use external storage (S3/R2) for media files.**

## Q: What's the cheapest storage option?

**A:** **Cloudflare R2** is the cheapest:

| Provider | Storage Cost | Bandwidth Cost | Total (1GB, 100GB/month) |
|----------|-------------|----------------|--------------------------|
| Cloudflare R2 | $0.015/GB | **FREE** | **$0.015/month** |
| AWS S3 | $0.023/GB | $0.09/GB | ~$9.02/month |
| Railway Volumes | N/A | N/A | ~$5-10/month |

**Recommendation:** Use Cloudflare R2 - it's 600x cheaper than S3 for bandwidth-heavy use cases.

## Q: Do terminal reports consume storage?

**A:** **NO!** Terminal reports are generated on-demand:

- PDFs are created in memory
- Sent directly to browser
- **Not saved to disk**
- Zero storage impact

Your code already does this correctly - reports are generated using `generate_pdf_from_html()` and returned as HTTP responses, not saved files.

## Q: What if I already have files stored locally?

**A:** You need to migrate them:

1. **Backup existing files** from current deployment
2. **Upload to S3/R2** using:
   - AWS CLI (for S3)
   - Cloudflare R2 CLI (for R2)
   - Or use the migration script in the storage guide
3. **Update database** (if file paths changed)

See [RAILWAY_STORAGE_GUIDE.md](./RAILWAY_STORAGE_GUIDE.md) for migration instructions.

## Q: How do I optimize image storage?

**A:** Reduce storage needs:

1. **Compress Images**: Use tools like Pillow to compress on upload
2. **Resize Images**: Limit profile pictures to max 800x800px
3. **Use WebP Format**: Better compression than JPEG/PNG
4. **Set Max File Size**: Limit uploads to 500KB-1MB

**Example code:**
```python
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

def compress_image(image_file, max_size=(800, 800), quality=85):
    img = Image.open(image_file)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    output = BytesIO()
    img.save(output, format='WEBP', quality=quality, optimize=True)
    output.seek(0)
    
    return InMemoryUploadedFile(
        output, 'ImageField', image_file.name,
        'image/webp', output.tell(), None
    )
```

## Q: Can I use Railway Volumes for media files?

**A:** **Not recommended** because:

1. **Single Region**: Limited to one region
2. **Not Ideal for Serving**: Volumes are for persistent storage, not file serving
3. **More Expensive**: Costs more than S3/R2
4. **Scaling Issues**: Doesn't work well with multiple replicas

**Better Use Cases for Volumes:**
- Database backups
- Temporary files
- Log files

**For media files, use S3/R2.**

## Q: What happens if I don't configure external storage?

**A:** You'll experience:

1. **Immediate Issues:**
   - Files uploaded will be lost on next redeploy
   - No way to persist user uploads
   - Broken image links after deployment

2. **Long-term Issues:**
   - Can't scale horizontally (files won't sync across replicas)
   - Data loss on every deployment
   - Poor user experience

3. **Storage Warnings:**
   - Railway will show warnings in logs
   - Application may become unstable

**Bottom Line:** External storage is **REQUIRED**, not optional.

## Q: How do I monitor storage usage?

**A:** Monitoring options:

**Cloudflare R2:**
- Dashboard shows storage usage
- Set up alerts for storage thresholds
- Monitor bandwidth usage

**AWS S3:**
- CloudWatch metrics
- S3 Storage Lens
- Set up billing alerts

**Railway:**
- Check service metrics
- Monitor disk usage (if using local storage)
- Set up alerts for resource limits

## Q: What's the setup process?

**A:** Quick checklist:

1. ✅ Choose storage provider (R2 recommended)
2. ✅ Create bucket/account
3. ✅ Get API credentials
4. ✅ Set environment variables in Railway
5. ✅ Update `DJANGO_SETTINGS_MODULE` to `SchoolApp.settings_railway`
6. ✅ Test file upload
7. ✅ Migrate existing files (if any)

See [RAILWAY_DEPLOYMENT_GUIDE.md](./RAILWAY_DEPLOYMENT_GUIDE.md) for detailed steps.

## Q: Will this work with my current code?

**A:** **Yes!** Your code already uses Django's default storage:

- `default_storage.save()` - works with any storage backend
- `student.profile_picture` - Django FileField handles storage automatically
- No code changes needed - just configuration!

The `settings_railway.py` file handles all the storage backend switching automatically based on environment variables.

---

**Still have questions?** Check the detailed guides:
- [RAILWAY_STORAGE_GUIDE.md](./RAILWAY_STORAGE_GUIDE.md) - Complete storage setup
- [RAILWAY_DEPLOYMENT_GUIDE.md](./RAILWAY_DEPLOYMENT_GUIDE.md) - Full deployment guide

