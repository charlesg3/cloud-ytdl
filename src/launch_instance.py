#!/usr/bin/env python3
import boto3
import base64
import time
import logging
from botocore.exceptions import ClientError


def launch_ytdlp_instance(
    video_id,
    s3_bucket,
    path="music",
    instance_type="t3.medium",
    vpc_id=None,
    key_name="enguard",
    subnet_id=None,  # Optional: specify Subnet ID (uses default subnet if None)
    wait_for_completion=True,
    tag_name="ytdlp-downloader-instance",
):
    """
    Launch an EC2 instance with Alpine Linux, install Docker and AWS CLI,
    download a video using the ytdlp-downloader container, and upload MP3s to S3.

    Args:
        video_id (str): YouTube video ID or URL to download
        s3_bucket (str): S3 bucket name for uploading MP3 files
        instance_type (str): EC2 instance type
        vpc_id (str, optional): VPC ID to launch the instance in
        wait_for_completion (bool): Whether to wait for the script to complete
        tag_name (str): Name tag for the EC2 instance

    Returns:
        dict: Information about the launched instance including Instance ID
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Initialize AWS clients
    ec2 = boto3.client("ec2")
    sts = boto3.client("sts")

    # Get AWS account ID
    account_id = sts.get_caller_identity()["Account"]

    # Find the latest Alpine Linux AMI
    logging.info("Finding the latest Amazon Linux AMI...")
    amis = ec2.describe_images(
        Filters=[
            {"Name": "name", "Values": ["al2023-ami-2023.*-kernel-6.*-x86_64"]},
            {"Name": "state", "Values": ["available"]},
            {"Name": "architecture", "Values": ["x86_64"]},
            {"Name": "root-device-type", "Values": ["ebs"]},
            {"Name": "virtualization-type", "Values": ["hvm"]},
        ],
        Owners=["amazon"],  # Alpine Linux official account
    )

    amis["Images"].sort(key=lambda x: x["CreationDate"], reverse=True)
    ami_id = amis["Images"][0]["ImageId"]
    logging.info(f"Using AL2023 AMI: {ami_id}")

    # Create user data script
    # This script will:
    # 1. Download and run the setup.sh script
    # 2. Shutdown the instance (optional)

    user_data_script = f"""Content-Type: text/x-shellscript; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="userdata.txt"

#!/bin/sh
# Log all output
exec > >(tee /var/log/user-data.log) 2>&1

echo "Starting setup script..."
echo "Video ID: {video_id}"
echo "S3 Bucket: {s3_bucket}"

aws s3 cp s3://{s3_bucket}/setup.sh .
chmod +x setup.sh
sudo ./setup.sh {s3_bucket} {video_id} {path}

# Optional: Shutdown the instance when done to save costs
# Note: Comment this out if you want the instance to stay running
echo "Shutting down instance..."
shutdown -h now
"""

    # Convert user data to base64
    user_data_b64 = base64.b64encode(user_data_script.encode()).decode()

    # Prepare network interface configuration (no public IP)
    network_interface = {
        "DeviceIndex": 0,
        "AssociatePublicIpAddress": False,  # No public IP address
    }

    if subnet_id:
        network_interface["SubnetId"] = subnet_id

    if security_group_id:
        network_interface["Groups"] = [security_group_id]

    # Prepare launch specification
    launch_args = {
        "ImageId": ami_id,
        "InstanceType": instance_type,
        "KeyName": key_name,
        "MaxCount": 1,
        "MinCount": 1,
        "UserData": user_data_b64,
        "NetworkInterfaces": [network_interface],
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": tag_name},
                    {"Key": "VideoID", "Value": video_id},
                    {"Key": "Purpose", "Value": "ytdlp-downloader"},
                ],
            }
        ],
        "InstanceInitiatedShutdownBehavior": "terminate",  # Terminate on shutdown
    }

    # Add IAM instance profile (ensure this role has S3 and ECR access permissions)
    launch_args["IamInstanceProfile"] = {
        "Name": "EC2InstanceProfileWithS3andECRAccess"  # Make sure this profile exists
    }

    # Launch the instance
    try:
        logging.info("Launching EC2 instance...")
        response = ec2.run_instances(**launch_args)
        instance_id = response["Instances"][0]["InstanceId"]
        logging.info(f"Launched instance: {instance_id}")

        # Wait for instance to be running
        if wait_for_completion:
            logging.info("Waiting for instance to enter running state...")
            waiter = ec2.get_waiter("instance_running")
            waiter.wait(InstanceIds=[instance_id])

            # Get instance details
            instance_info = ec2.describe_instances(InstanceIds=[instance_id])
            private_ip = instance_info["Reservations"][0]["Instances"][0].get("PrivateIpAddress")

            logging.info(f"Instance is running. Private IP: {private_ip}")

            # Return instance info (note: no public IP since we disabled it)
            return {
                "InstanceId": instance_id,
                "PrivateIp": private_ip,
                "VideoId": video_id,
                "S3Bucket": s3_bucket,
                "Status": "running",
            }

        # If not waiting, just return the instance ID
        return {"InstanceId": instance_id, "VideoId": video_id, "S3Bucket": s3_bucket, "Status": "launched"}

    except ClientError as e:
        logging.error(f"Error launching instance: {e}")
        return {"Error": str(e)}


# Example usage
if __name__ == "__main__":
    # Replace with your actual values
    result = launch_ytdlp_instance(video_id="https://youtu.be/Kq1TQzjZtxg", s3_bucket="cloudytdl-20250330150643")
