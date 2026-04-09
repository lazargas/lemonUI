import * as cdk from "aws-cdk-lib";
import * as apigwv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";
import { Construct } from "constructs";

interface ApiGatewayStackProps extends cdk.StackProps {
  /** Public DNS of the EC2 instance running FastAPI */
  ec2PublicDns: string;
}

export class ApiGatewayStack extends cdk.Stack {
  public readonly apiUrl: string;

  constructor(scope: Construct, id: string, props: ApiGatewayStackProps) {
    super(scope, id, props);

    const { ec2PublicDns } = props;

    // ── HTTP API ──────────────────────────────────────────────────────────
    const httpApi = new apigwv2.HttpApi(this, "LemonHttpApi", {
      apiName: "lemon-api",
      description: "Lemon FastAPI – HTTP API Gateway",
      corsPreflight: {
        allowHeaders: ["Content-Type", "Authorization"],
        allowMethods: [
          apigwv2.CorsHttpMethod.GET,
          apigwv2.CorsHttpMethod.POST,
          apigwv2.CorsHttpMethod.PUT,
          apigwv2.CorsHttpMethod.PATCH,
          apigwv2.CorsHttpMethod.DELETE,
          apigwv2.CorsHttpMethod.OPTIONS,
        ],
        allowOrigins: ["*"],
      },
    });

    // ── HTTP Integration → EC2 ────────────────────────────────────────────
    const integration = new integrations.HttpUrlIntegration(
      "LemonEc2Integration",
      `http://${ec2PublicDns}:8000/{proxy}`,
      {
        method: apigwv2.HttpMethod.ANY,
      }
    );

    // Proxy all routes to FastAPI
    httpApi.addRoutes({
      path: "/{proxy+}",
      methods: [apigwv2.HttpMethod.ANY],
      integration,
    });

    // Health check route
    httpApi.addRoutes({
      path: "/health",
      methods: [apigwv2.HttpMethod.GET],
      integration: new integrations.HttpUrlIntegration(
        "LemonHealthIntegration",
        `http://${ec2PublicDns}:8000/health`
      ),
    });

    this.apiUrl = httpApi.apiEndpoint;

    // ── Outputs ───────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, "ApiEndpoint", {
      value: httpApi.apiEndpoint,
      exportName: "Lemon-ApiEndpoint",
      description: "API Gateway endpoint URL",
    });
    new cdk.CfnOutput(this, "ApiId", {
      value: httpApi.apiId,
      exportName: "Lemon-ApiId",
    });
  }
}
