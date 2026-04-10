import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";

/**
 * DynamoStack
 * -----------
 * Provisions all 8 DynamoDB tables for the Lemon platform.
 *
 * Table inventory:
 *   1.  SimUsers            – pk / sk  (no GSI)
 *   1b. SimState            – pk / sk  (no GSI)  pk=SIM#<simId> sk=STATE
 *   2.  SimEvents           – pk / sk  + GSI1 (gsi1pk/gsi1sk) + GSI2 (gsi2pk/gsi2sk)
 *   3.  UserSprintFacts     – pk / sk  + GSI1 + GSI2
 *   4.  UserSprintContext   – pk / sk  (no GSI)
 *   5.  Projects            – pk / sk  (no GSI)
 *   6.  ProjectMappings     – pk / sk  + GSI1
 *   7.  ProjectFacts        – pk / sk  + GSI1
 *   8.  ProjectSprintContext– pk / sk  + GSI1 (gsi1pk/gsi1sk)
 *
 * All tables use:
 *   - PAY_PER_REQUEST billing
 *   - AWS-managed encryption (SSE)
 *   - Deletion protection (RETAIN removal policy)
 *   - Point-in-time recovery
 */
export class DynamoStack extends cdk.Stack {
  /** Expose tables so other stacks can grant permissions */
  public readonly tables: Record<string, dynamodb.Table> = {};

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ── Shared attribute definitions ──────────────────────────────────────
    const PK: dynamodb.Attribute = { name: "pk", type: dynamodb.AttributeType.STRING };
    const SK: dynamodb.Attribute = { name: "sk", type: dynamodb.AttributeType.STRING };
    const GSI1PK: dynamodb.Attribute = { name: "gsi1pk", type: dynamodb.AttributeType.STRING };
    const GSI1SK: dynamodb.Attribute = { name: "gsi1sk", type: dynamodb.AttributeType.STRING };
    const GSI2PK: dynamodb.Attribute = { name: "gsi2pk", type: dynamodb.AttributeType.STRING };
    const GSI2SK: dynamodb.Attribute = { name: "gsi2sk", type: dynamodb.AttributeType.STRING };

    // ── Helper: base table ────────────────────────────────────────────────
    const makeTable = (logicalId: string, tableName: string): dynamodb.Table => {
      const table = new dynamodb.Table(this, logicalId, {
        tableName,
        partitionKey: PK,
        sortKey: SK,
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,   // never auto-delete data
        pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        deletionProtection: true,
      });
      this.tables[logicalId] = table;
      return table;
    };

    // ── Helper: add GSI with pk+sk ────────────────────────────────────────
    const addGsi = (
      table: dynamodb.Table,
      indexName: string,
      partitionKey: dynamodb.Attribute,
      sortKey: dynamodb.Attribute
    ) => {
      table.addGlobalSecondaryIndex({
        indexName,
        partitionKey,
        sortKey,
        projectionType: dynamodb.ProjectionType.ALL,
      });
    };

    // ── 1. SimUsers ───────────────────────────────────────────────────────
    // Stores simulated user profiles.
    // pk = USER#<userId>   sk = PROFILE
    makeTable("SimUsersTable", "SimUsers");

    // ── 1b. SimState ──────────────────────────────────────────────────────
    // Stores simulation run state (active/paused/completed) per simulation.
    // pk = SIM#<simId>   sk = STATE
    makeTable("SimStateTable", "SimState");

    // ── 2. SimEvents ──────────────────────────────────────────────────────
    // Stores all simulated activity events (tickets, comments, PRs, etc.)
    // pk = USER#<userId>   sk = EVENT#<timestamp>#<eventId>
    // GSI1: gsi1pk = SPRINT#<sprintId>   gsi1sk = EVENT#<timestamp>
    // GSI2: gsi2pk = PROJECT#<projectId> gsi2sk = EVENT#<timestamp>
    const simEvents = makeTable("SimEventsTable", "SimEvents");
    addGsi(simEvents, "gsi1pk-gsi1sk-index", GSI1PK, GSI1SK);
    addGsi(simEvents, "gsi2pk-gsi2sk-index", GSI2PK, GSI2SK);

    // ── 3. UserSprintFacts ────────────────────────────────────────────────
    // Stores structured facts extracted per user per sprint.
    // pk = USER#<userId>   sk = SPRINT#<sprintId>#FACT#<factId>
    // GSI1: gsi1pk = SPRINT#<sprintId>   gsi1sk = USER#<userId>
    // GSI2: gsi2pk = FACT_TYPE#<type>    gsi2sk = SPRINT#<sprintId>
    const userSprintFacts = makeTable("UserSprintFactsTable", "UserSprintFacts");
    addGsi(userSprintFacts, "gsi1pk-gsi1sk-index", GSI1PK, GSI1SK);
    addGsi(userSprintFacts, "gsi2pk-gsi2sk-index", GSI2PK, GSI2SK);

    // ── 4. UserSprintContext ──────────────────────────────────────────────
    // Stores the precomputed sprint context summary per user per sprint.
    // pk = USER#<userId>   sk = SPRINT#<sprintId>
    makeTable("UserSprintContextTable", "UserSprintContext");

    // ── 5. Projects ───────────────────────────────────────────────────────
    // Stores project metadata.
    // pk = PROJECT#<projectId>   sk = METADATA
    makeTable("ProjectsTable", "Projects");

    // ── 6. ProjectMappings ────────────────────────────────────────────────
    // Maps users/tickets to projects.
    // pk = PROJECT#<projectId>   sk = USER#<userId>  (or TICKET#<ticketId>)
    // GSI1: gsi1pk = USER#<userId>   gsi1sk = PROJECT#<projectId>
    const projectMappings = makeTable("ProjectMappingsTable", "ProjectMappings");
    addGsi(projectMappings, "gsi1pk-gsi1sk-index", GSI1PK, GSI1SK);

    // ── 7. ProjectFacts ───────────────────────────────────────────────────
    // Stores structured project-level facts (blockers, risks, decisions).
    // pk = PROJECT#<projectId>   sk = SPRINT#<sprintId>#FACT#<factId>
    // GSI1: gsi1pk = SPRINT#<sprintId>   gsi1sk = PROJECT#<projectId>
    const projectFacts = makeTable("ProjectFactsTable", "ProjectFacts");
    addGsi(projectFacts, "gsi1pk-gsi1sk-index", GSI1PK, GSI1SK);

    // ── 8. ProjectSprintContext ───────────────────────────────────────────
    // Stores the precomputed sprint context summary per project per sprint.
    // pk = PROJECT#<projectId>   sk = SPRINT#<sprintId>
    // GSI1: gsi1pk = SPRINT#<sprintId>   gsi1sk = PROJECT#<projectId>  (list all projects in a sprint)
    const projectSprintContext = makeTable("ProjectSprintContextTable", "ProjectSprintContext");
    addGsi(projectSprintContext, "gsi1pk-gsi1sk-index", GSI1PK, GSI1SK);

    // ── Outputs ───────────────────────────────────────────────────────────
    Object.entries(this.tables).forEach(([name, table]) => {
      new cdk.CfnOutput(this, `${name}Arn`, {
        value: table.tableArn,
        exportName: `Lemon-${name}-Arn`,
      });
      new cdk.CfnOutput(this, `${name}Name`, {
        value: table.tableName,
        exportName: `Lemon-${name}-Name`,
      });
    });
  }
}
