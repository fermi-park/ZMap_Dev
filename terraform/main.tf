provider "aws" {
  region = var.aws_region
}

# VPC and Networking
resource "aws_vpc" "zmap_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "zmap-vpc"
  }
}

resource "aws_subnet" "zmap_subnet" {
  vpc_id                  = aws_vpc.zmap_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"
  tags = {
    Name = "zmap-subnet"
  }
}

resource "aws_internet_gateway" "zmap_igw" {
  vpc_id = aws_vpc.zmap_vpc.id
  tags = {
    Name = "zmap-igw"
  }
}

resource "aws_route_table" "zmap_route_table" {
  vpc_id = aws_vpc.zmap_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.zmap_igw.id
  }
  tags = {
    Name = "zmap-route-table"
  }
}

resource "aws_route_table_association" "zmap_rta" {
  subnet_id      = aws_subnet.zmap_subnet.id
  route_table_id = aws_route_table.zmap_route_table.id
}

# Security Group
resource "aws_security_group" "zmap_sg" {
  name        = "zmap-security-group"
  description = "Security group for ZMap scanner"
  vpc_id      = aws_vpc.zmap_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
    description = "SSH"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "zmap-sg"
  }
}

# S3 Bucket for Data and Results
resource "aws_s3_bucket" "zmap_data_bucket" {
  bucket = var.s3_bucket_name
  tags = {
    Name = "ZMap Scanner Data Bucket"
  }
}

resource "aws_s3_bucket_ownership_controls" "zmap_bucket_ownership" {
  bucket = aws_s3_bucket.zmap_data_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "zmap_bucket_acl" {
  depends_on = [aws_s3_bucket_ownership_controls.zmap_bucket_ownership]
  bucket     = aws_s3_bucket.zmap_data_bucket.id
  acl        = "private"
}

# IAM Role for EC2
resource "aws_iam_role" "zmap_role" {
  name = "zmap-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "zmap_s3_policy" {
  name        = "zmap-s3-access-policy"
  description = "Policy for ZMap Scanner to access S3"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.zmap_data_bucket.arn}",
          "${aws_s3_bucket.zmap_data_bucket.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "zmap_s3_policy_attachment" {
  role       = aws_iam_role.zmap_role.name
  policy_arn = aws_iam_policy.zmap_s3_policy.arn
}

resource "aws_iam_instance_profile" "zmap_instance_profile" {
  name = "zmap-instance-profile"
  role = aws_iam_role.zmap_role.name
}

# EC2 Instance
resource "aws_instance" "zmap_instance" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.zmap_subnet.id
  vpc_security_group_ids = [aws_security_group.zmap_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.zmap_instance_profile.name

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Update system
    sudo apt-get update
    sudo apt-get upgrade -y
    
    # Install dependencies
    sudo apt-get install -y git python3 python3-pip zmap docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Install AWS CLI
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    
    # Create project directory
    mkdir -p /home/ubuntu/zmap-scanner
    cd /home/ubuntu/zmap-scanner
    
    # Clone the repository or download from S3
    aws s3 cp s3://${var.s3_bucket_name}/code/zmap-scanner.zip .
    unzip zmap-scanner.zip
    
    # Create directories
    mkdir -p Data output
    
    # Download input data
    aws s3 cp s3://${var.s3_bucket_name}/data/input.csv Data/
    
    # Install Python requirements
    pip3 install -r requirements.txt
    
    # Set up cron job to run the scanner daily
    echo "0 0 * * * cd /home/ubuntu/zmap-scanner && sudo python3 Scripts/zmap_postal_code_availability.py --input Data/input.csv --output output/scan_\$(date +\%Y\%m\%d).png >> /var/log/zmap_scan.log 2>&1" | sudo tee -a /var/spool/cron/crontabs/ubuntu
    sudo chmod 600 /var/spool/cron/crontabs/ubuntu
    
    # Upload script for syncing results
    cat > /home/ubuntu/zmap-scanner/upload_results.sh <<'UPLOADSCRIPT'
    #!/bin/bash
    cd /home/ubuntu/zmap-scanner
    aws s3 sync output/ s3://${var.s3_bucket_name}/results/
    aws s3 cp networks_and_ips.csv s3://${var.s3_bucket_name}/results/
    UPLOADSCRIPT
    
    chmod +x /home/ubuntu/zmap-scanner/upload_results.sh
    
    # Add cron job to upload results
    echo "30 0 * * * /home/ubuntu/zmap-scanner/upload_results.sh >> /var/log/zmap_upload.log 2>&1" | sudo tee -a /var/spool/cron/crontabs/ubuntu
    
    # Set proper permissions
    sudo chown -R ubuntu:ubuntu /home/ubuntu/zmap-scanner
  EOF

  tags = {
    Name = "zmap-scanner-instance"
  }
}

# CloudWatch Alarm for High CPU Utilization
resource "aws_cloudwatch_metric_alarm" "zmap_cpu_alarm" {
  alarm_name          = "zmap-high-cpu-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This alarm triggers when CPU usage is above 80% for 10 minutes"
  
  dimensions = {
    InstanceId = aws_instance.zmap_instance.id
  }
}

# Outputs
output "instance_id" {
  value = aws_instance.zmap_instance.id
}

output "instance_public_ip" {
  value = aws_instance.zmap_instance.public_ip
}

output "s3_bucket_name" {
  value = aws_s3_bucket.zmap_data_bucket.bucket
}