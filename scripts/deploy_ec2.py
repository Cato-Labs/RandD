#!/usr/bin/env python3
import os
import sys
import time
import socket
import subprocess
import boto3
from dotenv import load_dotenv

# Load local .env
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(root_dir, '.env')
load_dotenv(env_path)

# Verify AWS credentials
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION", "us-east-1")

if not aws_access_key or not aws_secret_key:
    print("Error: AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not found in .env", file=sys.stderr)
    sys.exit(1)

print("=== AWS Credentials Verified ===")
print(f"Region: {aws_region}")

# Initialize Boto3 EC2 client/resource
session = boto3.Session(
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region
)
ec2_resource = session.resource('ec2')
ec2_client = session.client('ec2')

# 0. Build Frontend Locally
print("Building frontend locally...")
subprocess.run(["npm", "run", "build"], cwd=os.path.join(root_dir, "frontend"), check=True)
print("Frontend built successfully!")

# 1. SSH Key Pair Setup
key_name = 'strqc-key'
ssh_dir = os.path.expanduser('~/.ssh')
os.makedirs(ssh_dir, exist_ok=True)
key_path = os.path.join(ssh_dir, f'{key_name}.pem')

try:
    print(f"Checking if AWS Key Pair '{key_name}' exists...")
    ec2_client.describe_key_pairs(KeyNames=[key_name])
    print(f"Key Pair '{key_name}' exists in AWS.")
    if not os.path.exists(key_path):
        print(f"Warning: Key pair file '{key_path}' does not exist locally. Generating a new key pair...", file=sys.stderr)
        # Delete duplicate key from AWS to recreate
        ec2_client.delete_key_pair(KeyName=key_name)
        raise Exception("Recreate key")
except Exception:
    print(f"Creating new AWS Key Pair '{key_name}'...")
    key_pair = ec2_client.create_key_pair(KeyName=key_name)
    private_key = key_pair['KeyMaterial']
    with open(key_path, 'w') as f:
        f.write(private_key)
    os.chmod(key_path, 0o600)
    print(f"Saved private key to {key_path}")

# 2. Get Default VPC
print("Retrieving default VPC...")
vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
if not vpcs['Vpcs']:
    print("Error: No default VPC found in this region.", file=sys.stderr)
    sys.exit(1)
vpc_id = vpcs['Vpcs'][0]['VpcId']
print(f"Default VPC ID: {vpc_id}")

# 3. Security Group Setup
sg_name = 'strqc-sg'
sg_id = None
try:
    print(f"Checking if Security Group '{sg_name}' exists...")
    response = ec2_client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [sg_name]}])
    if response['SecurityGroups']:
        sg_id = response['SecurityGroups'][0]['GroupId']
        print(f"Using existing Security Group: {sg_id}")
    else:
        raise Exception("Create SG")
except Exception:
    print(f"Creating Security Group '{sg_name}'...")
    response = ec2_client.create_security_group(
        GroupName=sg_name,
        Description='Security group for STR QC platform',
        VpcId=vpc_id
    )
    sg_id = response['GroupId']
    print(f"Created Security Group: {sg_id}")
    
    # Configure Ingress Rules
    print("Configuring security group rules (SSH, HTTP, HTTPS)...")
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 443,
                'ToPort': 443,
                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS'}]
            }
        ]
    )
    print("Security group rules configured successfully.")

# 4. Find Latest Ubuntu 24.04 LTS AMI
print("Finding latest Ubuntu 24.04 LTS AMI...")
response = ec2_client.describe_images(
    Filters=[
        {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*']},
        {'Name': 'state', 'Values': ['available']}
    ],
    Owners=['099720109477'] # Canonical
)
images = response['Images']
images.sort(key=lambda x: x['CreationDate'], reverse=True)
ami_id = images[0]['ImageId']
print(f"AMI ID: {ami_id} ({images[0]['Name']})")

# 5. Find or Launch EC2 Instance
print("Checking if an instance named 'strqc-host' is already running...")
instances = list(ec2_resource.instances.filter(
    Filters=[
        {'Name': 'tag:Name', 'Values': ['strqc-host']},
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
))

if instances:
    instance = instances[0]
    print(f"Found existing running instance: {instance.id}")
else:
    print("Launching new t3.small EC2 Instance...")
    instances = ec2_resource.create_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t3.small',
        KeyName=key_name,
        SecurityGroupIds=[sg_id],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': 'strqc-host'}]
            }
        ]
    )
    instance = instances[0]
    print(f"Instance ID: {instance.id}")
    print("Waiting for instance to enter 'running' state...")
    instance.wait_until_running()

instance.load()
public_ip = instance.public_ip_address
print(f"EC2 Instance is RUNNING! Public IP: {public_ip}")

# 6. Wait for SSH to be ready
print("Waiting for SSH port 22 to accept connections...")
ssh_ready = False
for i in range(30):
    try:
        with socket.create_connection((public_ip, 22), timeout=5):
            print("SSH Port 22 is open and accepting connections!")
            ssh_ready = True
            break
    except (socket.timeout, ConnectionRefusedError):
        print("Waiting for SSH port (5s)...")
        time.sleep(5)

if not ssh_ready:
    print("Error: SSH port 22 failed to open within 150 seconds.", file=sys.stderr)
    sys.exit(1)

# Delay slightly to allow ssh daemon to fully initialize
time.sleep(5)

# 7. Create directory and adjust remote permissions
print("Preparing remote directory structures...")
ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
subprocess.run(
    ["ssh", "-i", key_path] + ssh_opts + [f"ubuntu@{public_ip}", "sudo mkdir -p /var/www/strqc && sudo chown -R ubuntu:ubuntu /var/www/strqc"],
    check=True
)

# 8. Rsync code to remote host
print("Syncing project files to EC2 via rsync...")
exclude_args = [
    "--exclude", "/.env",  # uploaded separately below
    "--exclude", "/.git/",
    "--exclude", "/str_qc.sqlite",  # production data is host-owned
    "--exclude", "/str_qc.sqlite.backup-*",
    "--exclude", "/backend/venv/",  # rebuilt on the host
    "--exclude", "/backend/workspace/",  # persistent agent workspace
    "--exclude", "node_modules/",
    "--exclude", ".pytest_cache/",
    "--exclude", ".ruff_cache/",
    "--exclude", "__pycache__/",
    "--exclude", "*.pyc",
    "--exclude", ".DS_Store",
    "--exclude", "._*",
]
rsync_cmd = [
    "rsync", "-avz", "--delete-delay", "--prune-empty-dirs"
] + exclude_args + [
    "-e", f"ssh -i {key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
    root_dir + "/",
    f"ubuntu@{public_ip}:/var/www/strqc/"
]
subprocess.run(rsync_cmd, check=True)

# 9. Modify and upload .env
print("Configuring and uploading .env file...")
with open(env_path, 'r') as f:
    env_content = f.read()

# Replace local paths /workspaces/RandD with /var/www/strqc
env_content = env_content.replace("/workspaces/RandD", "/var/www/strqc")
# Enforce production-safe host and port
env_content = env_content.replace("STRQC_API_HOST=0.0.0.0", "STRQC_API_HOST=127.0.0.1")

remote_env_path = os.path.join(root_dir, '.env.remote')
with open(remote_env_path, 'w') as f:
    f.write(env_content)

subprocess.run(
    ["scp", "-i", key_path] + ssh_opts + [remote_env_path, f"ubuntu@{public_ip}:/var/www/strqc/.env"],
    check=True
)
# Clean up temporary file
if os.path.exists(remote_env_path):
    os.remove(remote_env_path)

# 10. Copy and execute setup script
print("Executing remote configuration...")
remote_setup_script = os.path.join(root_dir, 'scripts', 'setup_remote_ec2.sh')
subprocess.run(
    ["scp", "-i", key_path] + ssh_opts + [remote_setup_script, f"ubuntu@{public_ip}:/tmp/setup.sh"],
    check=True
)
subprocess.run(
    ["ssh", "-i", key_path] + ssh_opts + [f"ubuntu@{public_ip}", "chmod +x /tmp/setup.sh && /tmp/setup.sh"],
    check=True
)

print("\n==========================================")
print("DEPLOYMENT SUCCESSFUL!")
print(f"Your application is now live at: http://{public_ip}")
print("==========================================\n")
