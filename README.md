# ZMap Network Scanner

A containerized network scanning solution that analyzes connectivity by postal code with database storage and API access.

## Overview

ZMap Network Scanner provides automated infrastructure for scanning IP networks and analyzing availability rates by postal code. The system features:

- Network scanning via ZMap with configurable parameters
- Database storage for scan results (PostgreSQL)
- RESTful API for triggering scans and retrieving results
- Visualization of response rates via charts and heatmaps
- Multi-container Docker deployment with Docker Compose
- AWS deployment via Terraform and ECS
- S3 integration for input/output data
- Simulation mode for testing without network access

## System Architecture

The system consists of three main components:

1. **PostgreSQL Database** - Stores scan results and metadata
2. **API Service** - RESTful API for scan management and result querying
3. **Scanner Service** - Performs ZMap network scans and processes results

### Data Flow

1. Scanner receives input CSV with networks and postal codes
2. API service processes input and creates scan record in database
3. ZMap scans networks and identifies reachable IPs
4. Results are stored in database with postal code analysis
5. Availability statistics are calculated and accessible via API
6. Optional: Results are uploaded to S3 for persistence

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

#### Single Container (Legacy)

```bash
# Build the Docker image
docker build -t zmap-scanner -f docker_scanner_build .

# Run the container
docker run -v $(pwd)/Data:/app/data -v $(pwd)/output:/app/output zmap-scanner
```

#### Multi-Container (Recommended)

```bash
# Build and start all services
docker-compose up -d

# Run a scan using the scanner service
docker-compose run --rm scanner --input-file /app/data/input.csv --simulate

# Access the API documentation
open http://localhost:8000/docs

# Trigger a scan via API
curl -X POST http://localhost:8000/scans \
  -H "Content-Type: application/json" \
  -d '{
    "input_file": "/app/data/input.csv",
    "port": 80,
    "bandwidth": "10M",
    "simulate": true,
    "description": "Test scan"
  }'

# View scan results
curl http://localhost:8000/scans/{scan_id}/availability
```

### AWS Deployment: Beginner-Friendly Guide

This guide will help you deploy the ZMap Network Scanner to AWS, even if you have only basic computer science knowledge. We'll take it step-by-step with clear explanations.

#### What You'll Need

1. **Create an AWS Account**
   - Go to [AWS Sign Up](https://aws.amazon.com/) and follow the instructions to create an account
   - You'll need a credit card, but most of what we do fits in the free tier
   - After signing up, go to your email and confirm your account

2. **Set Up Your Computer**
   - We need to install two programs on your computer:
   
   First, install the AWS command line tool:
   - For Windows: Download from [AWS CLI Windows Installer](https://awscli.amazonaws.com/AWSCLIV2.msi) and run the installer
   - For Mac: In Terminal, type: `brew install awscli` (or install [Homebrew](https://brew.sh/) first if needed)
   
   Second, install Terraform:
   - Download from [Terraform Download](https://www.terraform.io/downloads.html)
   - For Windows: Extract the zip file and move terraform.exe to a folder in your PATH (like C:\Windows)
   - For Mac: In Terminal, type: `brew install terraform`

3. **Get Your AWS Security Keys**
   - Log in to AWS
   - Click on your name in the top right corner
   - Select "Security credentials"
   - Scroll to "Access keys" and click "Create access key"
   - Follow the prompts and at the end, download your key file
   - ⚠️ IMPORTANT: Keep these keys safe and don't share them with anyone!

4. **Connect AWS to Your Computer**
   - Open Terminal (Mac) or Command Prompt (Windows)
   - Type: `aws configure`
   - When prompted, enter:
     - Your AWS Access Key ID from the downloaded file
     - Your AWS Secret Access Key from the downloaded file
     - Default region: `us-east-1` (just press Enter)
     - Default output format: `json` (just press Enter)

5. **Create a Key to Access Your Server**
   - In Terminal/Command Prompt, type:
     ```
     ssh-keygen -t rsa -b 4096 -f ~/zmap_key
     ```
   - When asked for a passphrase, just press Enter twice
   - This creates a key on your computer to safely connect to your AWS server
   - Now upload this key to AWS:
     ```
     aws ec2 import-key-pair --key-name "zmap-key" --public-key-material fileb://~/zmap_key.pub
     ```

#### Setting Up Your Project

1. **Get the Code**
   - Download the project from GitHub:
     ```
     git clone https://github.com/fermi-park/ZMap_Dev.git
     cd ZMap_Dev
     ```
   - If you don't have Git installed:
     - Go to the [GitHub repository](https://github.com/fermi-park/ZMap_Dev)
     - Click the green "Code" button
     - Select "Download ZIP"
     - Extract the ZIP file
     - Open Terminal/Command Prompt and navigate to the extracted folder

2. **Set Up Your AWS Settings**
   - Go to the terraform folder:
     ```
     cd terraform
     ```
   - Create a settings file by typing:
     ```
     notepad terraform.tfvars
     ```
     (On Mac, use `nano terraform.tfvars` instead)
   - Copy and paste the following:
     ```
     aws_region       = "us-east-1"
     allowed_ssh_cidr = "0.0.0.0/0"
     s3_bucket_name   = "zmap-scanner-data-UNIQUENAME"
     key_name         = "zmap-key"
     ```
   - Replace UNIQUENAME with your name or some random numbers
   - Save and close the file

3. **Create Your AWS Resources**
   - In the terraform folder, type:
     ```
     terraform init
     ```
   - This downloads necessary files (you'll see some green text)
   - Then type:
     ```
     terraform apply
     ```
   - Type `yes` when prompted
   - Wait about 2-3 minutes for AWS to create your resources
   - When complete, you'll see green text with your server's IP address
   - Type:
     ```
     terraform output > my_server_info.txt
     ```
   - This saves your server information to a file

4. **Upload Your Project Files**
   - Go back to the main project folder:
     ```
     cd ..
     ```
   - Package your code:
     ```
     zip -r zmap-scanner.zip . -x "*.git*" "*.csv" "*.zip"
     ```
   - Find your bucket name:
     - Open my_server_info.txt in the terraform folder
     - Look for s3_bucket_name and copy the name between quotes
   - Upload your files (replace YOUR_BUCKET_NAME with the name you copied):
     ```
     aws s3 cp zmap-scanner.zip s3://YOUR_BUCKET_NAME/code/
     aws s3 cp Data/small_input.csv s3://YOUR_BUCKET_NAME/data/input.csv
     ```

5. **Connect to Your Server**
   - Find your server's IP address:
     - Open my_server_info.txt in the terraform folder
     - Look for instance_public_ip and copy the IP address
   - Wait 5 minutes for your server to finish setting up
   - Connect to your server:
     - On Mac/Linux, type:
       ```
       ssh -i ~/zmap_key ubuntu@YOUR_IP_ADDRESS
       ```
     - On Windows, you may need to use PuTTY. If so:
       - Download and install [PuTTY](https://www.putty.org/)
       - Use PuTTYgen to convert your private key
       - In PuTTY, enter the IP address, load your key, and connect

6. **Test Your Scanner**
   - Once connected to your server, you'll see a welcome message
   - Type:
     ```
     cd /home/ubuntu/zmap-scanner
     ls
     ```
   - You should see your project files
   - Run a test scan:
     ```
     sudo python3 Scripts/zmap_postal_code_availability.py --input Data/input.csv --output output/test.png --simulate
     ```
   - When it finishes, type:
     ```
     ls output
     ```
   - You should see test.png, which contains your scan results

7. **Download Your Results**
   - To get files from your server to your computer:
   - Open a new Terminal/Command Prompt window on your computer
   - Create a folder for results:
     ```
     mkdir ~/zmap_results
     ```
   - Download your results (replace YOUR_IP_ADDRESS):
     ```
     scp -i ~/zmap_key ubuntu@YOUR_IP_ADDRESS:/home/ubuntu/zmap-scanner/output/* ~/zmap_results/
     ```
   - Now the results are in the zmap_results folder on your computer

8. **When You're Finished**
   - To shut down all AWS resources (to avoid charges):
   - In your Terminal/Command Prompt, go to the terraform folder
   - Type:
     ```
     terraform destroy
     ```
   - Type `yes` when prompted
   - Wait for all resources to be removed
   - Type:
     ```
     aws s3 rm s3://YOUR_BUCKET_NAME --recursive
     ```
   - This ensures you won't be charged for AWS usage

**Troubleshooting Tips**
- If you get "permission denied" errors, make sure you're using sudo for commands on the server
- If connections fail, wait a few more minutes for the server to initialize
- If you can't connect to the server, check that you're using the correct key file path
- For Windows users, file paths use backslashes (\\) instead of forward slashes (/)
- If your commands don't work, try typing them exactly as shown, watching for typos

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

### API Endpoints

The system provides a RESTful API for managing scans and retrieving results:

#### Scan Management:
- `POST /scans`: Create a new scan
- `GET /scans`: List all scans
- `GET /scans/{scan_id}`: Get details of a specific scan

#### Results:
- `GET /scans/{scan_id}/availability`: Get availability statistics for a specific scan
- `GET /availability`: Get availability statistics for all scans

#### System:
- `GET /health`: Health check endpoint

Example API request to create a new scan:
```json
POST /scans
{
  "input_file": "/path/to/input.csv",
  "max_networks": 1000,
  "port": 80,
  "bandwidth": "10M",
  "simulate": false,
  "description": "Scan description"
}
```

For detailed API documentation, see the Swagger UI at `/docs` when the API service is running.

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

## AWS Deployment Options

### Option 1: EC2-Based Deployment

See the [terraform/README.md](terraform/README.md) for instructions on deploying to a single EC2 instance.

### Option 2: Container-Based Deployment (Recommended)

The Terraform configuration creates:
- ECS cluster for running containerized services
- RDS PostgreSQL instance for data storage
- S3 bucket for input/output data
- ECR repositories for container images
- Load balancer for API access
- IAM roles with required permissions
- CloudWatch for logging and monitoring

See [AWS_SETUP.md](AWS_SETUP.md) for detailed instructions on deploying the containerized version to AWS.

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