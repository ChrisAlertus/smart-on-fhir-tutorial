#!/bin/bash
# Quick start script for testing with ngrok

echo "Starting Flask backend for ngrok testing..."
echo ""

# Check if .env exists, create if not
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
ALLOWED_ORIGINS=https://chrisalertus.github.io
FHIR_BASE_URL=https://fhir-open.cerner.com/dstu2/ec2458f2-1e24-41c8-b71b-0e701af7583d
PORT=8443
EOF
    echo ".env file created!"
fi

# Check if SSL certs exist
if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
    echo "Generating SSL certificates..."
    ./generate_ssl.sh
fi

# Start the backend
echo "Starting Flask backend on https://localhost:8443"
echo "In another terminal, run: ngrok http 8443"
echo ""
python main.py

