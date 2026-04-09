import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

// ⚠️  SECURITY: Only the current developer IP is whitelisted.
//    NO public 0.0.0.0/0 inbound rules are used.
const MY_IP_CIDR = "15.248.5.71/32";

export class Ec2Stack extends cdk.Stack {
  public readonly instance: ec2.Instance;
  public readonly instancePublicDns: string;
  public readonly ec2Role: iam.Role;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ── VPC ───────────────────────────────────────────────────────────────
    const vpc = new ec2.Vpc(this, "LemonVpc", {
      maxAzs: 2,
      natGateways: 0, // keep costs low for hackathon
      subnetConfiguration: [
        {
          name: "public",
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
      ],
    });

    // ── Security Group ────────────────────────────────────────────────────
    const sg = new ec2.SecurityGroup(this, "LemonSg", {
      vpc,
      description: "Lemon FastAPI security group developer IP only",
      allowAllOutbound: true,
    });

    // SSH – developer IP only
    sg.addIngressRule(
      ec2.Peer.ipv4(MY_IP_CIDR),
      ec2.Port.tcp(22),
      "SSH from developer IP only"
    );

    // FastAPI (port 8000) – developer IP only
    sg.addIngressRule(
      ec2.Peer.ipv4(MY_IP_CIDR),
      ec2.Port.tcp(8000),
      "FastAPI from developer IP only"
    );

    // HTTP (80) – developer IP only (for nginx reverse proxy if needed)
    sg.addIngressRule(
      ec2.Peer.ipv4(MY_IP_CIDR),
      ec2.Port.tcp(80),
      "HTTP from developer IP only"
    );

    // ── IAM Role (EC2 → DynamoDB) ─────────────────────────────────────────
    const role = new iam.Role(this, "LemonEc2Role", {
      assumedBy: new iam.ServicePrincipal("ec2.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonDynamoDBFullAccess"),
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "AmazonSSMManagedInstanceCore" // allows Session Manager access
        ),
      ],
    });

    // ── Key Pair ──────────────────────────────────────────────────────────
    const keyPair = new ec2.KeyPair(this, "LemonKeyPair", {
      keyPairName: "lemon-keypair",
    });

    // ── User Data (bootstrap script) ──────────────────────────────────────
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      "#!/bin/bash",
      "set -e",
      "yum update -y",

      // ── Install Docker ──────────────────────────────────
      "yum install -y docker git",
      "systemctl enable docker",
      "systemctl start docker",
      "usermod -aG docker ec2-user",

      // ── Install Docker Compose plugin ───────────────────
      'mkdir -p /usr/local/lib/docker/cli-plugins',
      'curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose',
      'chmod +x /usr/local/lib/docker/cli-plugins/docker-compose',

      // ── App directory ────────────────────────────────────
      "mkdir -p /opt/lemon",
      "cd /opt/lemon",

      // ── Write docker-compose.yml for EC2 ─────────────────
      // Uses IAM instance profile for AWS credentials (no keys needed)
      `cat > /opt/lemon/docker-compose.yml << 'COMPOSE'
version: "3.9"
services:
  api:
    image: lemon-api:latest
    container_name: lemon-api
    ports:
      - "8000:8000"
    environment:
      PROJECT_NAME: "Lemon"
      VERSION: "0.1.0"
      DEBUG: "false"
      AWS_REGION: "us-east-1"
      AWS_ACCOUNT_ID: "375243950000"
      DYNAMO_TABLE_PREFIX: "lemon"
      BEDROCK_MODEL_ID: "anthropic.claude-3-sonnet-20240229-v1:0"
      BEDROCK_EMBEDDING_MODEL_ID: "amazon.titan-embed-text-v2:0"
      OPENSEARCH_ENDPOINT: "https://9tekwdal9w5pd4utjhw0.us-east-1.aoss.amazonaws.com"
      OPENSEARCH_COLLECTION_NAME: "lemon-activity"
      OPENSEARCH_INDEX: "activity-embeddings"
      SECRET_KEY: "change-me-in-production"
      ALGORITHM: "HS256"
      ACCESS_TOKEN_EXPIRE_MINUTES: "30"
    restart: unless-stopped
COMPOSE`,

      // ── Systemd service to manage Docker Compose ─────────
      `cat > /etc/systemd/system/lemon.service << 'EOF'
[Unit]
Description=Lemon FastAPI Docker Container
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory=/opt/lemon
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF`,
      "systemctl daemon-reload",
      "systemctl enable lemon",
      "echo 'EC2 bootstrap complete. Push Docker image and run: systemctl start lemon'"
    );

    // ── EC2 Instance ──────────────────────────────────────────────────────
    this.instance = new ec2.Instance(this, "LemonInstance", {
      vpc,
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        ec2.InstanceSize.SMALL
      ),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      securityGroup: sg,
      role,
      keyPair,
      userData,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      associatePublicIpAddress: true,
    });

    this.instancePublicDns = this.instance.instancePublicDnsName;
    this.ec2Role = role;

    // ── Outputs ───────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, "InstanceId", {
      value: this.instance.instanceId,
      exportName: "Lemon-InstanceId",
    });
    new cdk.CfnOutput(this, "InstancePublicDns", {
      value: this.instance.instancePublicDnsName,
      exportName: "Lemon-InstancePublicDns",
    });
    new cdk.CfnOutput(this, "InstancePublicIp", {
      value: this.instance.instancePublicIp,
      exportName: "Lemon-InstancePublicIp",
    });
    new cdk.CfnOutput(this, "KeyPairName", {
      value: keyPair.keyPairName,
      description: "Download private key from SSM Parameter Store",
    });
  }
}
