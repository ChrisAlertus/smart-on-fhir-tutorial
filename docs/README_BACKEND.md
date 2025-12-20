# SMART on FHIR Tutorial - Flask Backend

This document describes the Flask backend implementation for the SMART on FHIR tutorial.

## Architecture

The backend provides:
- **Token Validation**: Validates JWT tokens from frontend requests
- **FHIR API Proxy**: Proxies FHIR requests to the FHIR server after token validation

**Key Principle**: The frontend manages the entire OAuth2 token lifecycle (acquisition, storage, refresh, revocation). The backend only validates tokens and proxies requests.

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your configuration:

```bash
cp .env.example .env
```

Edit `.env` with your settings:
- `FHIR_BASE_URL`: Your FHIR server base URL
- `ALLOWED_ORIGINS`: Comma-separated list of HTTPS origins allowed for CORS
- `SSL_CERTFILE` and `SSL_KEYFILE`: Paths to SSL certificates

### 3. SSL Certificate Setup

#### For Development (Self-Signed Certificate)

Generate a self-signed certificate:

```bash
mkdir -p backend/ssl
openssl req -x509 -newkey rsa:4096 -nodes -keyout backend/ssl/key.pem -out backend/ssl/cert.pem -days 365
```

When prompted, you can use:
- Common Name: `localhost`
- Other fields can be left as default

**Note**: Browsers will show a security warning for self-signed certificates. You'll need to accept the certificate in your browser.

#### For Production (Let's Encrypt)

Use Let's Encrypt to obtain a free SSL certificate:

```bash
sudo certbot certonly --standalone -d yourdomain.com
```

Then update `.env`:
```
SSL_CERTFILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEYFILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### 4. Run the Backend

```bash
cd backend
python main.py
```

The backend will be available at `https://localhost:8443`

Or using Flask's development server with SSL:

```bash
cd backend
export SSL_CERTFILE=ssl/cert.pem
export SSL_KEYFILE=ssl/key.pem
python main.py
```

## API Endpoints

### Health Check

```
GET /health
```

Returns server health status.

### Token Validation

```
GET /api/auth/validate
Headers:
  Authorization: Bearer <token>
```

Validates a JWT token and returns validation result.

### FHIR Proxy Endpoints

#### Get Patient

```
GET /api/fhir/Patient/{patient_id}
Headers:
  Authorization: Bearer <token>
```

Returns patient resource for the given patient ID.

#### Get Observations

```
GET /api/fhir/Observation?patient={patient_id}&code={loinc_code}
Headers:
  Authorization: Bearer <token>
```

Returns observation resources with optional filters.

#### Search Patients

```
GET /api/fhir/Patient?identifier={identifier}&name={name}
Headers:
  Authorization: Bearer <token>
```

Searches for patients with optional filters.

## Frontend Configuration

Update `example-smart-app/index.html` to set the backend URL:

```javascript
window.BACKEND_API_URL = 'https://localhost:8443';
```

Or set it in your environment-specific configuration.

## Security Notes

1. **HTTPS Required**: All communication must use HTTPS. The backend will not run without SSL certificates (or will warn in development mode).

2. **CORS**: Only HTTPS origins are allowed. Update `ALLOWED_ORIGINS` in `.env` to include your frontend domain.

3. **Token Storage**: Tokens are never stored on the backend. They are validated and passed through to the FHIR server.

4. **Cookie Security**: Frontend uses secure cookies (secure flag) for HTTPS-only transmission.

## Troubleshooting

### Certificate Errors

If you see certificate errors:
- For development: Accept the self-signed certificate in your browser
- For production: Ensure your Let's Encrypt certificate is valid and not expired

### CORS Errors

If you see CORS errors:
- Ensure your frontend URL is in `ALLOWED_ORIGINS`
- Ensure both frontend and backend are using HTTPS
- Check that the origin in the error matches exactly (including port)

### Token Validation Errors

If tokens are being rejected:
- Ensure tokens are being sent in the `Authorization: Bearer <token>` header
- Check that tokens haven't expired
- Verify the token format is correct

## Development vs Production

### Development
- Use self-signed certificates
- Run on localhost
- Less strict CORS (but still HTTPS only)

### Production
- Use Let's Encrypt or other trusted CA certificates
- Use proper domain names
- Strict CORS with specific allowed origins
- Consider using a reverse proxy (nginx) for additional security

