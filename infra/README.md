# Lemon – CDK Infrastructure

This package provisions the AWS infrastructure for the Lemon FastAPI application.

## Stacks

| Stack | Description |
|---|---|
| `LemonDynamoStack` | DynamoDB tables (lemon-items, lemon-users) |
| `LemonEc2Stack` | EC2 t3.small running FastAPI, security group whitelisted to developer IP only |
| `LemonApiGatewayStack` | HTTP API Gateway proxying all traffic to the EC2 instance |

## Prerequisites

```bash
# 1. Authenticate with your burner account
ada credentials update --account=375243950000 --provider=conduit --role=IibsAdminAccess-DO-NOT-DELETE

# 2. Install CDK dependencies
cd infra
npm install

# 3. Bootstrap CDK (first time only)
npx cdk bootstrap aws://375243950000/us-east-1
```

## Deploy

```bash
# Deploy all stacks
npm run deploy

# Or deploy individually
npx cdk deploy LemonDynamoStack
npx cdk deploy LemonEc2Stack
npx cdk deploy LemonApiGatewayStack
```

## Destroy

```bash
npm run destroy
```

## Security Notes

- ⚠️  The EC2 security group **only allows inbound traffic from `15.248.5.71/32`** (current developer IP).
- No `0.0.0.0/0` inbound rules are used anywhere.
- The EC2 instance uses an IAM instance profile to access DynamoDB — no hardcoded credentials.
- SSH key is stored in AWS SSM Parameter Store automatically by CDK.

## Retrieve SSH Key

```bash
aws ssm get-parameter \
  --name /ec2/keypair/<key-pair-id> \
  --with-decryption \
  --query Parameter.Value \
  --output text > lemon-keypair.pem

chmod 400 lemon-keypair.pem
ssh -i lemon-keypair.pem ec2-user@<instance-public-dns>
```
