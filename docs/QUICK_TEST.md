# Quick Testing Guide - 5 Minutes

## Fastest Option: Ngrok (Recommended for Immediate Testing)

### Step 1: Install Ngrok (if not already installed)

```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download
# Or use: curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt update && sudo apt install ngrok
```

### Step 2: Start Your Backend Locally

```bash
cd backend

# Generate SSL certs if you haven't already
./generate_ssl.sh

# Start the backend (in one terminal)
python main.py
```

Backend will run on `https://localhost:8443`

### Step 3: Create Ngrok Tunnel

In a **new terminal**:

```bash
ngrok http 8443
```

You'll see output like:
```
Forwarding  https://abc123xyz.ngrok.io -> http://localhost:8443
```

**Copy the HTTPS URL** (e.g., `https://abc123xyz.ngrok.io`)

### Step 4: Update Frontend Configuration

Edit `example-smart-app/index.html` and find this line:
```javascript
window.BACKEND_API_URL = window.BACKEND_API_URL || 'https://localhost:8443';
```

Change it to:
```javascript
window.BACKEND_API_URL = 'https://YOUR-NGROK-URL.ngrok.io';
```

Replace `YOUR-NGROK-URL` with the URL from step 3.

### Step 5: Update CORS in Backend

Edit `backend/.env` (or create it) and add:
```env
ALLOWED_ORIGINS=https://chrisalertus.github.io
FHIR_BASE_URL=https://fhir-open.cerner.com/dstu2/ec2458f2-1e24-41c8-b71b-0e701af7583d
```

Or set it when starting:
```bash
ALLOWED_ORIGINS=https://chrisalertus.github.io python main.py
```

### Step 6: Commit and Push to GitHub Pages

```bash
git add example-smart-app/index.html
git commit -m "Update backend URL for testing"
git push origin gh-pages
```

Wait 1-2 minutes for GitHub Pages to update.

### Step 7: Test with Cerner Code Console

1. Go to https://code.cerner.com/developer/smart-on-fhir/apps
2. Your app should already be registered with:
   - **Redirect URI**: `https://chrisalertus.github.io/smart-on-fhir-tutorial/example-smart-app/`
   - **SMART Launch URI**: `https://chrisalertus.github.io/smart-on-fhir-tutorial/example-smart-app/launch.html`
3. Click "Begin Testing" and launch your app
4. The frontend (GitHub Pages) will call your ngrok backend

## Important Notes

1. **Ngrok URL Changes**: Free ngrok URLs change each time you restart. For a fixed URL:
   - Sign up for free ngrok account: https://dashboard.ngrok.com/signup
   - Get authtoken: `ngrok config add-authtoken YOUR_TOKEN`
   - Use reserved domain (paid) or keep restarting ngrok

2. **Keep Both Terminals Open**:
   - Terminal 1: Backend running (`python main.py`)
   - Terminal 2: Ngrok tunnel (`ngrok http 8443`)

3. **CORS**: Make sure `ALLOWED_ORIGINS` includes your GitHub Pages URL

4. **Testing Flow**:
   - User clicks launch in Cerner → Goes to GitHub Pages launch.html
   - OAuth happens → Redirects back to GitHub Pages index.html
   - Frontend calls ngrok backend → Backend validates token → Backend calls FHIR server

## Troubleshooting

**CORS Errors:**
- Check `ALLOWED_ORIGINS` includes `https://chrisalertus.github.io`
- Make sure no trailing slash in CORS config

**Connection Refused:**
- Make sure backend is running on port 8443
- Make sure ngrok is forwarding to 8443

**Token Errors:**
- Check that tokens are being stored in cookies
- Verify backend can reach FHIR server

## For Permanent Solution

See `DEPLOYMENT.md` for options like Render, Railway, or Fly.io for permanent free hosting.

