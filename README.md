# ZMap Network Scanner

A containerized network scanning solution that analyzes connectivity by postal code.

## Overview

ZMap Network Scanner provides automated infrastructure for scanning IP networks and analyzing availability rates by postal code. The system features:

- Network scanning via ZMap with configurable parameters
- Visualization of response rates via charts and heatmaps
- Docker containerization for easy deployment
- AWS deployment via Terraform
- Simulation mode for testing without network access

## Quick Start

### Local Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/zmap-scanner.git
cd zmap-scanner

# Install dependencies
pip install -r requirements.txt

# Install ZMap (if not already installed)
sudo apt-get install zmap   # Debian/Ubuntu
brew install zmap           # macOS

# Run a test scan (simulation mode)
python Scripts/zmap_postal_code_availability.py --input Data/input.csv --output output/test.png
```

### Docker Deployment

```bash
# Build the Docker image
docker build -t zmap-scanner -f docker_scanner_build .

# Run the container
docker run -v $(pwd)/Data:/app/data -v $(pwd)/output:/app/output zmap-scanner
```

### AWS Deployment

```bash
# Navigate to terraform directory
cd terraform

# Initialize terraform
terraform init

# Deploy (creates EC2 instance, S3 bucket, etc.)
terraform apply

# Upload scanner code and data
S3_BUCKET=$(terraform output -raw s3_bucket_name)
aws s3 cp ../zmap-scanner.zip s3://$S3_BUCKET/code/
aws s3 cp ../Data/input.csv s3://$S3_BUCKET/data/
```

## Usage

### Basic Scanning

```bash
python Scripts/zmap_postal_code_availability.py --input Data/input.csv --output results.png
```

### Visualization Options

```bash
python Scripts/zmap_visualizing_response_rate.py --input networks_and_ips.csv --output heatmap.png --viz-type heatmap
```

### Command Line Arguments

#### Scanner:
- `--input`: Input CSV file with networks and postal codes
- `--output`: Output visualization file
- `--max-networks`: Maximum networks to process
- `--port`: Port to scan (default: 80)
- `--bandwidth`: ZMap bandwidth cap (default: 10M)
- `--verbose`: Enable verbose logging

#### Visualizer:
- `--input`: Input data file with scan results
- `--output`: Output visualization file
- `--viz-type`: Visualization type (bar, heatmap)
- `--max-codes`: Maximum postal codes to display
- `--min-threshold`: Minimum response rate threshold

## Architecture

The system consists of:
1. **Scanner Module**: Processes networks and runs ZMap
2. **Analysis Module**: Calculates availability by postal code
3. **Visualization Module**: Creates charts and heatmaps
4. **Infrastructure**: Docker container and AWS deployment

## Input Format

The input CSV file should contain the following columns:
- `network`: IP network in CIDR notation (e.g., 192.168.1.0/24)
- `postal_code`: Postal code for the network

## Output

The script produces:
1. A CSV file with detailed results (`networks_and_ips.csv`)
2. Visualizations of response rates by postal code (bar chart or heatmap)
3. Log output with availability percentages

## AWS Deployment Details

The Terraform configuration creates:
- EC2 instance (Ubuntu) with ZMap installed
- S3 bucket for data storage and results
- IAM roles with required permissions
- Automated scanning via cron jobs
- Results synced to S3 bucket

See the [terraform/README.md](terraform/README.md) for detailed deployment instructions.

## Security Considerations

- ZMap requires special permissions for network scanning
- Review network scanning policies before use
- Docker container runs as non-root user
- AWS deployment restricts SSH access to specified IPs
- Ensure you have permission to scan the target networks

## License

[Your license choice]

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.