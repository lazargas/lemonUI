"""
scan_project_facts.py
---------------------
Standalone script to fetch ALL items from the ProjectFacts DynamoDB table.

Table ARN : arn:aws:dynamodb:us-west-2:445567091633:table/ProjectFacts
Region    : us-west-2

Usage
-----
# Print summary + dump to JSON file (default)
python scripts/scan_project_facts.py

# Print every item to stdout as pretty JSON (no file)
python scripts/scan_project_facts.py --print-items

# Save to a custom output file
python scripts/scan_project_facts.py --output /tmp/facts.json

# Use a specific AWS profile
AWS_PROFILE=my-profile python scripts/scan_project_facts.py

Auth
----
Uses the standard boto3 credential chain:
  1. Environment variables  (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)
  2. ~/.aws/credentials profile  (AWS_PROFILE env var or default)
  3. IAM instance / container role
"""

import argparse
import json
import os
import sys
from decimal import Decimal
from typing import Any, Dict, List

import boto3
import boto3.resources.factory
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

# ── Configuration ────────────────────────────────────────────────────────────
TABLE_NAME = "ProjectFacts"
REGION = os.environ.get("AWS_REGION", "us-east-1")
DEFAULT_OUTPUT_FILE = "project_facts_dump.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts Decimal → float so items are serialisable."""
    def default(self, o: Any) -> Any:  # noqa: E741
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def scan_all_items(table) -> List[Dict[str, Any]]:
    """
    Perform a full table scan with automatic pagination.

    DynamoDB returns at most 1 MB of data per call; we loop until
    LastEvaluatedKey is absent, meaning we've read every page.
    """
    items: List[Dict[str, Any]] = []
    kwargs: Dict[str, Any] = {}
    page = 0

    print(f"Scanning table '{TABLE_NAME}' in region '{REGION}' …")

    while True:
        page += 1
        response = table.scan(**kwargs)
        batch = response.get("Items", [])
        items.extend(batch)
        print(f"  Page {page:>3}: fetched {len(batch):>5} items  (running total: {len(items)})")

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    return items


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan all items from the ProjectFacts DynamoDB table."
    )
    parser.add_argument(
        "--print-items",
        action="store_true",
        help="Pretty-print every item to stdout (in addition to the summary).",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Path to write the JSON dump (default: {DEFAULT_OUTPUT_FILE}). "
             "Pass an empty string '' to skip file output.",
    )
    parser.add_argument(
        "--region",
        default=REGION,
        help=f"AWS region (default: {REGION} — your own stack account, overrides AWS_REGION env var).",
    )
    args = parser.parse_args()

    # ── Connect ───────────────────────────────────────────────────────────────
    try:
        dynamodb = boto3.resource("dynamodb", region_name=args.region)
        table = dynamodb.Table(TABLE_NAME)  # type: ignore[attr-defined]
        # Trigger a lightweight describe to validate credentials & table existence
        table.load()
    except NoCredentialsError:
        print(
            "ERROR: No AWS credentials found.\n"
            "Set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, or configure ~/.aws/credentials.",
            file=sys.stderr,
        )
        sys.exit(1)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        msg = exc.response["Error"]["Message"]
        print(f"ERROR [{code}]: {msg}", file=sys.stderr)
        sys.exit(1)
    except BotoCoreError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # ── Scan ──────────────────────────────────────────────────────────────────
    try:
        items = scan_all_items(table)
    except (BotoCoreError, ClientError) as exc:
        print(f"ERROR during scan: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n✅  Total items retrieved: {len(items)}")

    # ── Optional: print each item ─────────────────────────────────────────────
    if args.print_items:
        print("\n── Items ──────────────────────────────────────────────────────")
        for i, item in enumerate(items, start=1):
            print(f"\n[{i}] {json.dumps(item, indent=2, cls=DecimalEncoder)}")

    # ── Optional: write to file ───────────────────────────────────────────────
    if args.output:
        output_path = args.output
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(items, fh, indent=2, cls=DecimalEncoder)
        print(f"💾  Dumped {len(items)} items → {output_path}")

    # ── Quick stats ───────────────────────────────────────────────────────────
    if items:
        fact_types = {}
        active_count = 0
        for item in items:
            ft = item.get("fact_type", "UNKNOWN")
            fact_types[ft] = fact_types.get(ft, 0) + 1
            if item.get("is_active", False):
                active_count += 1

        print(f"\n── Summary ────────────────────────────────────────────────────")
        print(f"  Active facts   : {active_count}")
        print(f"  Inactive facts : {len(items) - active_count}")
        print(f"  Fact types     :")
        for ft, count in sorted(fact_types.items(), key=lambda x: -x[1]):
            print(f"    {ft:<30} {count}")


if __name__ == "__main__":
    main()
