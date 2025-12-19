#!/bin/bash
# Generate self-signed SSL certificate for development

mkdir -p ssl

echo "Generating self-signed SSL certificate for development..."
echo "This certificate will be valid for 365 days."
echo ""

openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -days 365 \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

echo ""
echo "SSL certificate generated successfully!"
echo "Certificate: ssl/cert.pem"
echo "Private key: ssl/key.pem"
echo ""
echo "Note: Browsers will show a security warning for self-signed certificates."
echo "You'll need to accept the certificate in your browser when accessing the backend."

