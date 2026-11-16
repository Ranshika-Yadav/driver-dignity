# Driver Dignity — Final Website

Run in this folder:

```bash
export ADMIN_PASSWORD="replace-with-a-strong-private-password"
python3 server.py
```

Website: http://localhost:8000
Admin: http://localhost:8000/admin.html

This build uses external Unsplash image URLs. Internet access is required and the specific image content has not been independently verified in this environment. The photographs are not testimonials. Check photo suitability and licensing before publication.

If the browser still shows an old version, stop the old server, start this folder's server and hard-refresh with Cmd+Shift+R.

## Fixes in this build
- Prevented missing footer year element from stopping the main JavaScript (which had hidden quiz answers).
- Quiz options, feedback and next-step controls now initialize normally when JavaScript runs.
- Adjusted quiz layout and sticky-header anchor spacing.
- Retained original homepage, portraits, Respect Wall design, and backend.

**Important:** Open `http://localhost:8000`, not `file:///.../index.html`. Forms, moderation, and admin requests need the Python server. If port 8000 is already in use, stop the previous Python server before starting this one.
