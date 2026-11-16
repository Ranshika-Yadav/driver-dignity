# Driver Dignity — Creative full-stack website

An upgraded version of the supplied Driver Dignity website. Retains the existing homepage, respect quiz, pledge, guides, contact and volunteer forms; adds Driver Diaries, bilingual Support Hub, moderated Respect Wall, and admin dashboard.

## Run locally

Requires Python 3.9+; **no pip dependencies**.

```bash
cd saferoad-india
export ADMIN_PASSWORD='replace-with-a-long-unique-password'
python3 server.py
```

Open http://localhost:8000/ and admin at http://localhost:8000/admin.html. On Windows PowerShell, use `$env:ADMIN_PASSWORD="..."` instead of `export`.

## How it works

- Contact and volunteer submissions are stored in `driver_dignity.db` (SQLite) and appear in the admin dashboard.
- Respect Wall messages start as **pending**. Admin can approve/reject them; only approved messages appear publicly.
- Admin sessions are HttpOnly SameSite cookies, expire after 8 hours, and are stored in server memory. A restart logs admins out.
- Email notifications are **optional**, and contain no personal message content. Set `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `NOTIFY_EMAIL` to enable them. Without configuration, submissions still save and appear in admin.
- Set `PORT` to change port, `DRIVER_DIGNITY_DB` to change database path. For HTTPS deployment set `COOKIE_SECURE=1`.

## Before production

Use HTTPS with a reverse proxy, set a strong admin password via secret environment variables, configure email, backups, privacy/consent policy, retention limits, CAPTCHA or robust rate limiting, and monitoring. The bundled server is intended for demo/small controlled deployment, **not a hardened production service**. Do not publish admin credentials. External Unsplash images and Google Fonts require internet; verify photo subject, permissions and licenses before launch. Photo scenes are illustrative and **not claimed to depict named drivers**. Diary stories are illustrative, not genuine interviews. Replace these with consented verified stories before publishing.

## Smoke tests

```bash
python3 -m unittest discover -s tests -v
```

## Structure

`index.html`, `styles.css`, `script.js`, `creative.js`: preserved original site. `enhancements.css/js`: new interactive sections. `admin.html/js/css`: moderation dashboard. `server.py`: backend. `tests/`: API tests.
