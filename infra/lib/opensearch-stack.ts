import * as cdk from "aws-cdk-lib";
import * as opensearchserverless from "aws-cdk-lib/aws-opensearchserverless";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

interface OpenSearchStackProps extends cdk.StackProps {
  /** IAM role ARN of the EC2 instance (needs read/write access to the collection) */
  ec2RoleArn: string;
}

export class OpenSearchStack extends cdk.Stack {
  public readonly collectionEndpoint: string;
  public readonly collectionArn: string;

  constructor(scope: Construct, id: string, props: OpenSearchStackProps) {
    super(scope, id, props);

    const collectionName = "lemon-activity";

    // ── Encryption Policy ─────────────────────────────────────────────────
    const encryptionPolicy = new opensearchserverless.CfnSecurityPolicy(
      this,
      "LemonEncryptionPolicy",
      {
        name: "lemon-encryption",
        type: "encryption",
        policy: JSON.stringify({
          Rules: [
            {
              ResourceType: "collection",
              Resource: [`collection/${collectionName}`],
            },
          ],
          AWSOwnedKey: true,
        }),
      }
    );

    // ── Network Policy ────────────────────────────────────────────────────
    // AllowFromPublic: true is required by AWS when no VPC endpoint is used.
    // Access is still secured by the data access policy (EC2 role only).
    const networkPolicy = new opensearchserverless.CfnSecurityPolicy(
      this,
      "LemonNetworkPolicy",
      {
        name: "lemon-network",
        type: "network",
        policy: JSON.stringify([
          {
            Rules: [
              {
                ResourceType: "collection",
                Resource: [`collection/${collectionName}`],
              },
              {
                ResourceType: "dashboard",
                Resource: [`collection/${collectionName}`],
              },
            ],
            AllowFromPublic: true,
          },
        ]),
      }
    );

    // ── Collection ────────────────────────────────────────────────────────
    const collection = new opensearchserverless.CfnCollection(
      this,
      "LemonCollection",
      {
        name: collectionName,
        type: "VECTORSEARCH",
        description: "Lemon – activity embeddings for semantic search",
      }
    );

    // Collection depends on policies being created first
    collection.addDependency(encryptionPolicy);
    collection.addDependency(networkPolicy);

    // ── Data Access Policy ────────────────────────────────────────────────
    // Grants the EC2 instance role full read/write access to the collection
    new opensearchserverless.CfnAccessPolicy(this, "LemonDataAccessPolicy", {
      name: "lemon-data-access",
      type: "data",
      policy: JSON.stringify([
        {
          Rules: [
            {
              ResourceType: "index",
              Resource: [`index/${collectionName}/*`],
              Permission: [
                "aoss:CreateIndex",
                "aoss:DeleteIndex",
                "aoss:UpdateIndex",
                "aoss:DescribeIndex",
                "aoss:ReadDocument",
                "aoss:WriteDocument",
              ],
            },
            {
              ResourceType: "collection",
              Resource: [`collection/${collectionName}`],
              Permission: ["aoss:CreateCollectionItems", "aoss:DescribeCollectionItems"],
            },
          ],
          Principal: [
            props.ec2RoleArn,
            // Also allow the deploying IAM principal for local testing
            `arn:aws:iam::${this.account}:root`,
          ],
        },
      ]),
    });

    this.collectionEndpoint = collection.attrCollectionEndpoint;
    this.collectionArn = collection.attrArn;

    // ── Outputs ───────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, "OpenSearchEndpoint", {
      value: collection.attrCollectionEndpoint,
      exportName: "Lemon-OpenSearchEndpoint",
      description: "Set this as OPENSEARCH_ENDPOINT in your .env",
    });
    new cdk.CfnOutput(this, "OpenSearchArn", {
      value: collection.attrArn,
      exportName: "Lemon-OpenSearchArn",
    });
    new cdk.CfnOutput(this, "CollectionName", {
      value: collectionName,
      exportName: "Lemon-OpenSearchCollectionName",
    });
  }
}
