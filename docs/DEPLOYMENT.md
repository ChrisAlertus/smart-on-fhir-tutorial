# Deployment Guide for Public Testing

## Quick Testing Options

### Option 1: Ngrok (Fastest - 5 minutes)

Ngrok creates a public HTTPS tunnel to your local backend. Perfect for quick testing.

1. **Install ngrok:**
   ```bash
   # macOS
   brew install ngrok

   # Or download from https://ngrok.com/download
   ```

2. **Start your Flask backend locally:**
   ```bash
   cd backend
   python main.py
   # Backend runs on https://localhost:8443
   ```

3. **Create ngrok tunnel:**
   ```bash
   ngrok http 8443
   ```

4. **Update frontend configuration:**
   - Copy the HTTPS URL from ngrok (e.g., `https://abc123.ngrok.io`)
   - Update `example-smart-app/index.html`:
     ```javascript
     window.BACKEND_API_URL = 'https://abc123.ngrok.io';
     ```

5. **Update Cerner Code Console:**
   - Redirect URI: Keep your GitHub Pages URL
   - SMART Launch URI: Keep your GitHub Pages URL
   - The frontend will call the ngrok backend URL

**Note:** Ngrok free tier gives you a random URL that changes each time. For a fixed URL, use ngrok authtoken (free) or upgrade.

### Option 2: Render (Free, Permanent - 15 minutes)

Render offers free hosting with HTTPS and custom domains.

1. **Create a Render account:** https://render.com

2. **Prepare for deployment:**
   Create `backend/Procfile`:
   ```
   web: gunicorn main:app --bind 0.0.0.0:$PORT --certfile ssl/cert.pem --keyfile ssl/key.pem
   ```

   Actually, for Render, we'll use their built-in HTTPS, so update `backend/main.py` to work without SSL in production (Render handles SSL).

3. **Create `render.yaml` in project root:**
   ```yaml
   services:
     - type: web
       name: smart-fhir-backend
       env: python
       buildCommand: pip install -r backend/requirements.txt
       startCommand: cd backend && gunicorn main:app --bind 0.0.0.0:$PORT
       envVars:
         - key: FHIR_BASE_URL
           value: https://fhir-open.cerner.com/dstu2/ec2458f2-1e24-41c8-b71b-0e701af7583d
         - key: ALLOWED_ORIGINS
           value: https://chrisalertus.github.io
         - key: PORT
           value: 10000
   ```

4. **Deploy:**
   - Connect your GitHub repo to Render
   - Render will auto-deploy
   - Get your public URL (e.g., `https://smart-fhir-backend.onrender.com`)

5. **Update frontend:**
   - Update `example-smart-app/index.html` with Render URL
   - Commit and push to GitHub Pages

### Option 3: Railway (Free, Permanent - 10 minutes)

1. **Create Railway account:** https://railway.app

2. **Deploy:**
   - Connect GitHub repo
   - Create new project
   - Add service from GitHub repo
   - Set root directory to `backend`
   - Railway auto-detects Python and installs dependencies

3. **Set environment variables in Railway dashboard:**
   - `FHIR_BASE_URL`: Your FHIR server URL
   - `ALLOWED_ORIGINS`: `https://chrisalertus.github.io`
   - `PORT`: Railway sets this automatically

4. **Get public URL:**
   - Railway provides HTTPS URL automatically
   - Update frontend with this URL

### Option 4: Fly.io (Free, Permanent - 15 minutes)

1. **Install flyctl:**
   ```bash
   brew install flyctl
   ```

2. **Login:**
   ```bash
   fly auth login
   ```

3. **Create `backend/fly.toml`:**
   ```toml
   app = "smart-fhir-backend"
   primary_region = "iad"

   [build]

   [http_service]
     internal_port = 8443
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0

   [[services]]
     http_checks = []
     internal_port = 8443
     processes = ["app"]
     protocol = "tcp"
     script_checks = []
   ```

4. **Deploy:**
   ```bash
   cd backend
   fly launch
   ```

## Recommended: Quick Setup with Ngrok

For immediate testing, use ngrok:

1. **Install and run ngrok:**
   ```bash
   ngrok http 8443
   ```

2. **Update frontend temporarily:**
   Edit `example-smart-app/index.html` and add before the closing `</script>` tag:
   ```javascript
   // Temporary for testing - replace with your ngrok URL
   window.BACKEND_API_URL = 'https://YOUR-NGROK-URL.ngrok.io';
   ```

3. **Commit and push to GitHub Pages:**
   ```bash
   git add example-smart-app/index.html
   git commit -m "Add backend URL for testing"
   git push origin gh-pages
   ```

4. **Test with Cerner:**
   - Your GitHub Pages URLs stay the same
   - Frontend will call ngrok backend
   - Works immediately!

## For Production: Use Render or Railway

Both offer:
- Free HTTPS URLs
- Automatic deployments from GitHub
- Environment variable management
- No credit card required (free tier)

## Important Notes

1. **CORS Configuration:**
   - Make sure `ALLOWED_ORIGINS` includes your GitHub Pages URL
   - Format: `https://chrisalertus.github.io`

2. **SSL Certificates:**
   - For ngrok: Handled automatically
   - For Render/Railway: They provide SSL automatically
   - For local testing: Use self-signed certs

3. **Backend URL:**
   - Frontend calls backend API
   - Backend validates tokens and proxies to FHIR
   - Cerner only sees your GitHub Pages URLs (which is correct)

4. **Environment Variables:**
   - `FHIR_BASE_URL`: Your FHIR server
   - `ALLOWED_ORIGINS`: Your GitHub Pages domain
   - `PORT`: Usually set by hosting service

