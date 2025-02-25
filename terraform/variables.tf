variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the instance"
  type        = string
  default     = "0.0.0.0/0"  # Replace with your IP for better security
}

variable "s3_bucket_name" {
  description = "Name for the S3 bucket to store data and results"
  type        = string
  default     = "zmap-scanner-data"  # Must be globally unique
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance (Ubuntu Server 22.04 LTS)"
  type        = string
  default     = "ami-0c7217cdde317cfec"  # Ubuntu 22.04 in us-east-1, update for other regions
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"  # Adjust based on scanning requirements
}

variable "key_name" {
  description = "Name of the SSH key pair to use for the EC2 instance"
  type        = string
  # No default - must be provided by user
}