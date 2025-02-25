#!/bin/bash
set -e

# Enable better error reporting
trap "echo \"An error occurred. Exiting...\" >&2" ERR

# Default values
INPUT_FILE="/app/data/input.csv"
MAX_NETWORKS=5000
PORT=80
BANDWIDTH="10M"
SIMULATE=false
WAIT_FOR_DB=true

# Help message
function show_help {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --input-file     Input CSV file location (default: /app/data/input.csv)"
  echo "  --max-networks   Maximum number of networks to scan (default: 5000)"
  echo "  --port           Port to scan (default: 80)"
  echo "  --bandwidth      ZMap bandwidth cap (default: 10M)"
  echo "  --simulate       Run in simulation mode (default: false)"
  echo "  --no-wait-db     Don't wait for database to be ready"
  echo "  --help           Show this help message"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input-file)
      INPUT_FILE="$2"
      shift 2
      ;;
    --max-networks)
      MAX_NETWORKS="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --bandwidth)
      BANDWIDTH="$2"
      shift 2
      ;;
    --simulate)
      SIMULATE=true
      shift 1
      ;;
    --no-wait-db)
      WAIT_FOR_DB=false
      shift 1
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done

# Wait for database to be ready
if [ "$WAIT_FOR_DB" = true ]; then
  echo "Waiting for database to be ready..."
  while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t 1; do
    echo "Waiting for database connection..."
    sleep 2
  done
  echo "Database is ready!"
fi

# Check if we need to download from S3
if [[ $INPUT_FILE == s3://* ]]; then
  echo "Downloading input file from S3..."
  LOCAL_INPUT="/app/data/input_$(date +%Y%m%d_%H%M%S).csv"
  aws s3 cp "$INPUT_FILE" "$LOCAL_INPUT"
  INPUT_FILE="$LOCAL_INPUT"
fi

# Create timestamp for output files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Run the scan
echo "Starting ZMap scan with the following parameters:"
echo "  Input file: $INPUT_FILE"
echo "  Max networks: $MAX_NETWORKS"
echo "  Port: $PORT"
echo "  Bandwidth: $BANDWIDTH"
echo "  Simulation mode: $SIMULATE"

# Use the API endpoint to trigger a scan
echo "Triggering scan through API..."

# Construct API URL based on environment
API_HOST="${API_HOST:-api}"
API_PORT="${API_PORT:-8000}"
API_URL="http://$API_HOST:$API_PORT/scans"

# Wait for API to be ready
echo "Waiting for API to be ready..."
while ! curl -s -f "http://$API_HOST:$API_PORT/health" > /dev/null; do
  echo "Waiting for API to start..."
  sleep 2
done

echo "API is ready!"

# Prepare the JSON request body
JSON_BODY=$(cat <<EOF
{
  "input_file": "$INPUT_FILE",
  "max_networks": $MAX_NETWORKS,
  "port": $PORT,
  "bandwidth": "$BANDWIDTH",
  "simulate": $SIMULATE,
  "description": "Scan started at $(date)"
}
EOF
)

# Send the request to the API
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "$JSON_BODY" "$API_URL")
SCAN_ID=$(echo "$RESPONSE" | grep -o '"scan_id":[0-9]*' | cut -d ':' -f2)

if [ -z "$SCAN_ID" ]; then
  echo "Error: Failed to get scan ID from API response"
  echo "Response: $RESPONSE"
  exit 1
fi

echo "Scan triggered successfully with ID: $SCAN_ID"
echo "Monitor progress at: http://$API_HOST:$API_PORT/scans/$SCAN_ID"

# Keep container running if we're in service mode
if [ "${SERVICE_MODE:-false}" = true ]; then
  echo "Running in service mode. Container will stay alive."
  # Sleep forever
  while true; do
    sleep 3600
  done
else
  echo "Waiting for scan to complete..."
  # Poll the API until the scan is complete
  while true; do
    SCAN_INFO=$(curl -s "http://$API_HOST:$API_PORT/scans/$SCAN_ID")
    RESULT_COUNT=$(echo "$SCAN_INFO" | grep -o '"result_count":[0-9]*' | cut -d ':' -f2)
    
    if [ -n "$RESULT_COUNT" ] && [ "$RESULT_COUNT" -gt 0 ]; then
      echo "Scan complete! $RESULT_COUNT results processed."
      break
    fi
    
    echo "Scan in progress..."
    sleep 10
  done
  
  # Get the results and show summary
  echo "Scan results summary:"
  curl -s "http://$API_HOST:$API_PORT/scans/$SCAN_ID/availability" | python3 -m json.tool
  
  echo "Scan completed successfully!"
fi