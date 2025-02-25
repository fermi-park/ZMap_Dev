output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i your-key.pem ubuntu@${aws_instance.zmap_instance.public_ip}"
}

output "s3_data_upload_command" {
  description = "Command to upload input data to S3"
  value       = "aws s3 cp input.csv s3://${aws_s3_bucket.zmap_data_bucket.bucket}/data/"
}

output "s3_code_upload_command" {
  description = "Command to upload code to S3"
  value       = "cd /path/to/zmap-scanner && zip -r zmap-scanner.zip . && aws s3 cp zmap-scanner.zip s3://${aws_s3_bucket.zmap_data_bucket.bucket}/code/"
}

output "s3_results_download_command" {
  description = "Command to download results from S3"
  value       = "aws s3 sync s3://${aws_s3_bucket.zmap_data_bucket.bucket}/results/ ./results/"
}