# ZMap Scanner AWS Deployment

This directory contains Terraform scripts to deploy the ZMap scanner on AWS infrastructure.

## Prerequisites

1. [AWS CLI](https://aws.amazon.com/cli/) installed and configured
2. [Terraform](https://www.terraform.io/downloads.html) v1.0.0 or newer
3. SSH key pair created in your AWS account

## Deployment Steps

### 1. Prepare your code and data

Zip your ZMap scanner code:
```bash
cd /path/to/ZMap_Dev
zip -r zmap-scanner.zip .
```

### 2. Configure variables

Edit `terraform.tfvars` with your specific values:
```
aws_region      = "us-east-1"
allowed_ssh_cidr = "YOUR_IP/32"  # Replace with your IP for better security
s3_bucket_name  = "your-zmap-scanner-data"  # Must be globally unique
key_name        = "your-key-pair-name"
```

### 3. Deploy the infrastructure

Initialize Terraform:
```bash
terraform init
```

Review the deployment plan:
```bash
terraform plan
```

Apply the configuration:
```bash
terraform apply
```

### 4. Upload your code and data

Use the output commands to upload your code and data:
```bash
# Upload code
cd /path/to/ZMap_Dev
zip -r zmap-scanner.zip .
aws s3 cp zmap-scanner.zip s3://your-zmap-scanner-data/code/

# Upload input data
aws s3 cp Data/input.csv s3://your-zmap-scanner-data/data/
```

### 5. Connect to your instance

SSH to your instance:
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

### 6. Verify deployment

Check if the scanner is set up correctly:
```bash
cd /home/ubuntu/zmap-scanner
ls -la
cat /var/spool/cron/crontabs/ubuntu
```

### 7. Manual execution (if needed)

Run the scanner manually:
```bash
cd /home/ubuntu/zmap-scanner
sudo python3 Scripts/zmap_postal_code_availability.py --input Data/input.csv --output output/manual_scan.png
```

## Scheduled Execution

The scanner is configured to run daily at midnight and upload results to S3 at 12:30 AM.

## Monitoring

Check CloudWatch for CPU usage alarms and logs:
```bash
# View scan logs
tail -f /var/log/zmap_scan.log

# View upload logs
tail -f /var/log/zmap_upload.log
```

## Results

Download results from S3:
```bash
aws s3 sync s3://your-zmap-scanner-data/results/ ./local-results/
```

## Clean Up

To destroy all resources:
```bash
terraform destroy
```

Note: This will not delete the S3 bucket contents. Empty the bucket before destroying if needed:
```bash
aws s3 rm s3://your-zmap-scanner-data --recursive
```

## Security Considerations

1. Restrict SSH access to your IP only
2. Review AWS acceptable use policy regarding network scanning
3. Consider adding VPC endpoints for S3 access
4. Implement additional security measures for production use