#!/usr/bin/env python3
"""Subscribe an email address to the ShiftShield alerts SNS topic."""
from __future__ import annotations

import sys
import boto3

REGION = "ap-south-1"
TOPIC_NAME = "shiftshield-prod-alerts"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/subscribe_sns_alert.py <supervisor-email>")
        sys.exit(1)

    email = sys.argv[1].strip()
    if "@" not in email:
        print("[ERROR] Please provide a valid email address.")
        sys.exit(1)

    sns = boto3.client("sns", region_name=REGION)
    topics = sns.list_topics().get("Topics", [])
    topic_arn = None
    for t in topics:
        if TOPIC_NAME in t["TopicArn"]:
            topic_arn = t["TopicArn"]
            break

    if not topic_arn:
        print(f"[ERROR] Could not find SNS topic '{TOPIC_NAME}' in {REGION}")
        sys.exit(1)

    print(f"Subscribing {email} to {topic_arn}...")
    resp = sns.subscribe(
        TopicArn=topic_arn,
        Protocol="email",
        Endpoint=email,
        ReturnSubscriptionArn=True,
    )
    sub_arn = resp.get("SubscriptionArn", "pending confirmation")
    print(f"[OK] Subscription request sent! Status/ARN: {sub_arn}")
    print(f"Please check your inbox at {email} and click 'Confirm subscription' to complete.")


if __name__ == "__main__":
    main()
