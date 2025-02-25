# ZMap Scanner AWS Deployment Guide

This guide explains how to deploy the ZMap Scanner with database and API components to AWS using Docker and ECS.

## Architecture Overview

The system consists of three main components:
1. **PostgreSQL Database**: Stores scan results and metadata
2. **API Service**: RESTful API for triggering scans and querying results
3. **Scanner Service**: Performs network scans and saves results to the database

## Prerequisites

1. AWS CLI installed and configured
2. Docker installed locally
3. AWS ECR repositories created for each container
4. Basic knowledge of AWS services (ECS, RDS, S3)

## Step 1: Set Up AWS Resources

Create required AWS resources using the AWS Management Console or Terraform:

### Using AWS Console

1. **Create an RDS PostgreSQL database**:
   - Navigate to RDS in AWS Console
   - Create a PostgreSQL database (version 14 or later)
   - Note the database endpoint, username, and password

2. **Create an S3 bucket**:
   - Navigate to S3 in AWS Console
   - Create a bucket for storing scan data and results
   - Enable versioning and appropriate lifecycle policies

3. **Create ECR repositories**:
   - Navigate to ECR in AWS Console
   - Create repositories for each container:
     - `zmap-scanner-api`
     - `zmap-scanner-scanner`

4. **Create ECS cluster**:
   - Navigate to ECS in AWS Console
   - Create a new cluster (Fargate recommended)

### Using Terraform (Recommended)

Use the `terraform` directory with updated configuration to create all resources at once:

```bash
cd terraform
terraform init
terraform apply
```

## Step 2: Build and Push Docker Images

Build and push Docker images to ECR:

```bash
# Log in to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and push API image
docker build -t YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zmap-scanner-api:latest -f docker/api.Dockerfile .
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zmap-scanner-api:latest

# Build and push Scanner image
docker build -t YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zmap-scanner-scanner:latest -f docker/scanner.Dockerfile .
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zmap-scanner-scanner:latest
```

## Step 3: Deploy the Services to ECS

### API Service

1. Create a task definition:
   - Navigate to ECS in AWS Console
   - Create a new task definition using the `zmap-scanner-api` image
   - Configure environment variables:
     ```
     DB_HOST=your-rds-endpoint.rds.amazonaws.com
     DB_PORT=5432
     DB_USER=postgres
     DB_PASSWORD=your-password
     DB_NAME=zmap_scanner
     API_PORT=8000
     ```

2. Create a service:
   - Create a new service in your ECS cluster
   - Use the API task definition
   - Configure a load balancer if needed
   - Set up service discovery for API

### Scanner Service

1. Create a task definition:
   - Create a new task definition using the `zmap-scanner-scanner` image
   - Configure environment variables:
     ```
     DB_HOST=your-rds-endpoint.rds.amazonaws.com
     DB_PORT=5432
     DB_USER=postgres
     DB_PASSWORD=your-password
     DB_NAME=zmap_scanner
     API_HOST=api-service-discovery-name
     API_PORT=8000
     AWS_REGION=us-east-1
     S3_BUCKET=your-bucket-name
     SERVICE_MODE=true
     ```
   - Add IAM role with S3 access permissions

2. Create a service or scheduled task:
   - For continuous operation: Create a service with desired count = 1
   - For scheduled scans: Create a scheduled task that runs periodically

## Step 4: Set Up IAM Permissions

Ensure proper IAM permissions for the services:

1. **Scanner Service IAM Role**:
   - S3 read/write access to your bucket
   - CloudWatch logs access

2. **API Service IAM Role**:
   - S3 read access to your bucket
   - CloudWatch logs access

## Step 5: Configure Network Security

Secure your deployment:

1. **Security Groups**:
   - RDS: Allow PostgreSQL access (port 5432) only from ECS security groups
   - API: Allow HTTP/HTTPS access on port 8000
   - Scanner: Allow outbound traffic for scanning

2. **Network ACLs**:
   - Configure appropriate network ACLs for your VPC

## Step 6: Test the Deployment

1. Access the API Swagger documentation:
   ```
   http://your-load-balancer-dns:8000/docs
   ```

2. Trigger a test scan:
   ```bash
   curl -X POST http://your-load-balancer-dns:8000/scans \
     -H "Content-Type: application/json" \
     -d '{
       "input_file": "s3://your-bucket-name/data/input.csv",
       "port": 80,
       "bandwidth": "10M",
       "simulate": true,
       "description": "Test scan"
     }'
   ```

3. Check the results:
   ```bash
   # List all scans
   curl http://your-load-balancer-dns:8000/scans

   # Get results for a specific scan
   curl http://your-load-balancer-dns:8000/scans/1/availability
   ```

## Monitoring and Maintenance

1. **CloudWatch Logs**:
   - Both services are configured to send logs to CloudWatch
   - Create CloudWatch dashboards to monitor performance

2. **Database Maintenance**:
   - Set up automatic backups for the RDS instance
   - Consider implementing a data retention policy

3. **S3 Lifecycle Policies**:
   - Configure lifecycle policies to move older results to cheaper storage tiers

## Troubleshooting

1. **Database Connection Issues**:
   - Verify security group rules allow traffic from ECS to RDS
   - Check database credentials in environment variables

2. **API Not Accessible**:
   - Verify load balancer health checks are passing
   - Check security group rules for the load balancer

3. **Scanner Not Working**:
   - Check logs in CloudWatch
   - Verify API service is accessible from scanner service
   - Check IAM permissions for S3 access