# ZMap Network Scanner

A friendly tool that checks if networks are working and organizes results by postal code.

## What This Tool Does

ZMap Network Scanner is like a postal worker for the internet. It goes to different neighborhoods (networks) and checks which houses (computers) are accepting visitors. Then it organizes this information by postal code so you can see which areas have better connectivity.

Here's what it can do:

- Check if computers on a network are responding (like knocking on doors)
- Store all the results in a database so you can look at them later
- Provide a simple way for other programs to use the results
- Create pretty charts and maps showing which areas have better connectivity
- Run inside containers (like little shipping boxes for software)
- Work in the cloud (AWS) so you don't need a powerful computer
- Work in "pretend mode" if you just want to test without actually scanning

## How It's Built

The system has three main parts that work together:

1. **The Storage Box** (Database) - Keeps track of all scan results, like a filing cabinet
2. **The Assistant** (API Service) - Takes requests and returns results, like a helpful librarian
3. **The Scanner** (Scanner Service) - Does the actual work of checking networks, like a postal inspector

### How Information Flows

Think of it like a delivery service:

1. You give the system a list of addresses (networks) with their postal codes
2. The Assistant creates a new job and puts it in the filing cabinet
3. The Scanner checks each address to see if anyone's home
4. All the results get organized and stored in the filing cabinet
5. When you want to know the results, the Assistant looks them up for you
6. If you want, the results can also be saved to the cloud for safekeeping

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

### Running in a Container

Containers are like shippable packages for software. They include everything needed to run the program.

#### Simple Way (One Container)

```bash
# Create the container package
docker build -t zmap-scanner -f docker_scanner_build .

# Run the program in its container
docker run -v $(pwd)/Data:/app/data -v $(pwd)/output:/app/output zmap-scanner
```

#### Better Way (Multiple Containers Working Together)

```bash
# Start all the parts of the system
docker-compose up -d

# Run a test scan
docker-compose run --rm scanner --input-file /app/data/input.csv --simulate

# Open the web documentation to learn more
open http://localhost:8000/docs

# Ask for a scan using the Assistant (API)
curl -X POST http://localhost:8000/scans \
  -H "Content-Type: application/json" \
  -d '{
    "input_file": "/app/data/input.csv",
    "port": 80,
    "bandwidth": "10M",
    "simulate": true,
    "description": "Test scan"
  }'

# See the results
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

### Talking to the Assistant (API)

The system has a helpful Assistant (API) that understands certain commands. It's like asking a librarian for information:

#### Things You Can Ask For:
- **Start a new scan**: Say "I want a new scan" with details about what to scan
- **See all your scans**: Say "Show me all my scans"
- **Look at one specific scan**: Say "Tell me about scan #5" (or whatever number)
- **Get results**: Say "Show me the results for scan #5"
- **Check if everything's working**: Say "Are you healthy?"

Example of asking for a new scan:
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

When the Assistant is running, you can see a complete guide to all commands at `http://localhost:8000/docs`.

## How It Works Inside

The system is built with pieces that each have a special job:
1. **The Scanner**: Like a mail carrier, it goes to each address to see if someone's home
2. **The Calculator**: Counts how many houses answered the door in each postal code
3. **The Artist**: Creates colorful charts and maps to show the results
4. **The House**: The container that keeps everything running, either on your computer or in the cloud

## Files You Need to Provide

The program needs a special file with two pieces of information:
- **Network addresses**: Where to look for computers (like "192.168.1.0/24")
- **Postal codes**: Which neighborhood each network belongs to

This file should be a CSV (comma-separated values) file that looks like:
```
network,postal_code
192.168.1.0/24,12345
10.0.0.0/16,54321
```

## What You Get Back

After running the program, you'll receive:
1. A detailed list of every house (IP) that was checked
2. Colorful pictures showing which postal codes have the most online computers
3. A message telling you the percentage of computers that responded in each area

## Running in the Cloud (AWS)

### Simple Way: On One Computer in the Cloud

Follow the [beginner's guide](terraform/README.md) to set up a single computer in the cloud.

### Advanced Way: Using Multiple Cloud Services (Recommended)

This method creates a complete system in the cloud with:
- Special computers just for running our containers
- A professional database for storing results
- Cloud storage for your files
- A system that balances the workload
- Security settings to keep everything safe
- Tracking tools to see how everything's running

See the [detailed cloud setup guide](AWS_SETUP.md) for instructions.

## Important Safety Notes

- Always get permission before checking if someone's home (scanning networks)
- Checking too many houses too quickly can cause problems (like knocking on every door in a neighborhood at 3am)
- Our program tries to be polite by:
  - Running with limited permissions
  - Only allowing certain people to access the cloud version
  - Using "pretend mode" when you're just testing

Remember: Just because you can knock on doors doesn't mean you should knock on ALL doors!

## License

[Your license choice]

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.