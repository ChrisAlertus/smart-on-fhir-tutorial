# Backend Setup Guide (Flask)

## Quick Start

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Generate SSL certificate (for development):**
   ```bash
   ./generate_ssl.sh
   ```

3. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the backend:**
   ```bash
   python main.py
   ```

The backend will be available at `https://localhost:8443`

## Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

```env
# Server Configuration
PORT=8443
HOST=0.0.0.0

# SSL Configuration (required for HTTPS)
SSL_CERTFILE=ssl/cert.pem
SSL_KEYFILE=ssl/key.pem

# CORS Configuration - Comma-separated list of allowed HTTPS origins
ALLOWED_ORIGINS=https://localhost:8000,https://127.0.0.1:8000

# FHIR Server Configuration
FHIR_BASE_URL=https://fhir-open.cerner.com/dstu2/ec2458f2-1e24-41c8-b71b-0e701af7583d
```

## SSL Certificates

### Development (Self-Signed)

Run the provided script:
```bash
./generate_ssl.sh
```

This creates:
- `ssl/cert.pem` - Certificate
- `ssl/key.pem` - Private key

**Note**: Browsers will show a security warning. Click "Advanced" and "Proceed to localhost" to accept the certificate.

### Production (Let's Encrypt)

1. Install certbot:
   ```bash
   sudo apt-get install certbot
   ```

2. Obtain certificate:
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```

3. Update `.env`:
   ```env
   SSL_CERTFILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
   SSL_KEYFILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   ```

## Frontend Configuration

Update `example-smart-app/index.html` to point to your backend:

```javascript
window.BACKEND_API_URL = 'https://localhost:8443';
```

Or for production:
```javascript
window.BACKEND_API_URL = 'https://api.yourdomain.com';
```

## Testing

1. Start the backend
2. Open the frontend in a browser
3. Accept the SSL certificate warning (for self-signed certs)
4. Launch the SMART app and authenticate
5. The app should fetch data through the backend

## Troubleshooting

### Certificate Errors
- Ensure SSL certificates exist in the `ssl/` directory
- Check file permissions on certificate files
- For self-signed certs, accept the certificate in your browser

### CORS Errors
- Verify your frontend URL is in `ALLOWED_ORIGINS`
- Ensure both frontend and backend use HTTPS
- Check that origins match exactly (including protocol and port)

### Connection Errors
- Verify the backend is running
- Check that the port matches your configuration
- Ensure firewall allows connections on the configured port

