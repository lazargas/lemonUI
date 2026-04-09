#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { DynamoStack } from "../lib/dynamo-stack";
import { Ec2Stack } from "../lib/ec2-stack";
import { ApiGatewayStack } from "../lib/apigateway-stack";
import { OpenSearchStack } from "../lib/opensearch-stack";

const app = new cdk.App();

const env: cdk.Environment = {
  account: "375243950000",
  region: "us-east-1",
};

// ── 1. DynamoDB tables ────────────────────────────────────────────────────
const dynamoStack = new DynamoStack(app, "LemonDynamoStack", {
  env,
  description: "Lemon – DynamoDB tables",
});

// ── 2. EC2 instance (hosts the FastAPI app) ───────────────────────────────
const ec2Stack = new Ec2Stack(app, "LemonEc2Stack", {
  env,
  description: "Lemon – EC2 instance for FastAPI",
});
ec2Stack.addDependency(dynamoStack);

// ── 3. OpenSearch Serverless (vector search) ──────────────────────────────
const openSearchStack = new OpenSearchStack(app, "LemonOpenSearchStack", {
  env,
  description: "Lemon – OpenSearch Serverless vector search collection",
  ec2RoleArn: ec2Stack.ec2Role.roleArn,  // exact ARN via cross-stack reference
});
openSearchStack.addDependency(ec2Stack);

// ── 4. API Gateway (HTTP API → EC2) ───────────────────────────────────────
const apiStack = new ApiGatewayStack(app, "LemonApiGatewayStack", {
  env,
  description: "Lemon – API Gateway HTTP API",
  ec2PublicDns: ec2Stack.instancePublicDns,
});
apiStack.addDependency(ec2Stack);

app.synth();
