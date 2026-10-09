#!/usr/bin/env python3
"""Verification and health-check script for ShiftShield AWS infrastructure (ap-south-1)."""
from __future__ import annotations

import sys
import boto3

REGION = "ap-south-1"
EXPECTED_TABLES = [
    "sites",
    "site-state",
    "alert-keys",
    "issue-log",
    "acks",
    "rest-confirms",
    "rulebooks",
    "obligation-log",
    "replay-runs",
]


def check_dynamodb(env: str = "prod") -> bool:
    print(f"\n[1/4] Checking DynamoDB Tables for environment: {env}...")
    client = boto3.client("dynamodb", region_name=REGION)
    tables = client.list_tables().get("TableNames", [])
    all_ok = True
    for suffix in EXPECTED_TABLES:
        table_name = f"shiftshield-{env}-{suffix}"
        if table_name in tables:
            desc = client.describe_table(TableName=table_name)
            status = desc["Table"]["TableStatus"]
            print(f"  [OK] {table_name}: {status}")
        else:
            print(f"  [--] {table_name}: NOT FOUND")
            all_ok = False
    return all_ok


def check_sns(env: str = "prod") -> bool:
    print(f"\n[2/4] Checking SNS Topics for environment: {env}...")
    client = boto3.client("sns", region_name=REGION)
    topics = client.list_topics().get("Topics", [])
    expected_topic_part = f"shiftshield-{env}-alerts"
    found = [t["TopicArn"] for t in topics if expected_topic_part in t["TopicArn"]]
    if found:
        print(f"  [OK] Found Alert Topic: {found[0]}")
        subs = client.list_subscriptions_by_topic(TopicArn=found[0]).get("Subscriptions", [])
        print(f"    Active subscriptions: {len(subs)}")
        for s in subs:
            print(f"      - {s.get('Protocol')}: {s.get('Endpoint')} ({s.get('SubscriptionArn')})")
        return True
    else:
        print(f"  [--] Topic '{expected_topic_part}' not found")
        return False


def check_lambda(env: str = "prod") -> bool:
    print(f"\n[3/4] Checking Lambda Functions for environment: {env}...")
    client = boto3.client("lambda", region_name=REGION)
    funcs = client.list_functions().get("Functions", [])
    found = [f["FunctionName"] for f in funcs if f"shiftshield-{env}" in f["FunctionName"]]
    if found:
        for f in found:
            print(f"  [OK] Function: {f}")
        return True
    else:
        print(f"  [--] No functions matching 'shiftshield-{env}' found yet")
        return False


def check_cloudwatch_alarms(env: str = "prod") -> bool:
    print(f"\n[4/4] Checking CloudWatch Alarms for environment: {env}...")
    client = boto3.client("cloudwatch", region_name=REGION)
    alarms = client.describe_alarms().get("MetricAlarms", [])
    found = [a["AlarmName"] for a in alarms if f"shiftshield-{env}" in a["AlarmName"]]
    if found:
        for a in found:
            print(f"  [OK] Alarm: {a}")
        return True
    else:
        print(f"  [--] No alarms matching 'shiftshield-{env}' found yet")
        return False


def main():
    env = sys.argv[1] if len(sys.argv) > 1 else "prod"
    print(f"==================================================")
    print(f"ShiftShield AWS Infrastructure Verification Tool")
    print(f"Region: {REGION} | Target Environment: {env}")
    print(f"==================================================")
    
    sts = boto3.client("sts", region_name=REGION)
    identity = sts.get_caller_identity()
    print(f"AWS Account: {identity.get('Account')} ({identity.get('Arn')})")

    ddb_ok = check_dynamodb(env)
    sns_ok = check_sns(env)
    lam_ok = check_lambda(env)
    cw_ok = check_cloudwatch_alarms(env)

    print("\nSummary:")
    print(f"  DynamoDB Tables : {'PASS' if ddb_ok else 'PENDING/FAIL'}")
    print(f"  SNS Topic       : {'PASS' if sns_ok else 'PENDING/FAIL'}")
    print(f"  Lambda Functions: {'PASS' if lam_ok else 'PENDING/FAIL'}")
    print(f"  CloudWatch      : {'PASS' if cw_ok else 'PENDING/FAIL'}")


if __name__ == "__main__":
    main()
