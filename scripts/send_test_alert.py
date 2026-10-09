#!/usr/bin/env python3
"""Send a test heat alert to the ShiftShield alerts SNS topic."""
from __future__ import annotations

import sys
import boto3

REGION = "ap-south-1"
TOPIC_NAME = "shiftshield-prod-alerts"


def main():
    sns = boto3.client("sns", region_name=REGION)
    topics = sns.list_topics().get("Topics", [])
    topic_arn = None
    for t in topics:
        if TOPIC_NAME in t["TopicArn"]:
            topic_arn = t["TopicArn"]
            break

    if not topic_arn:
        print(f"[ERROR] Could not find SNS topic '{TOPIC_NAME}'")
        sys.exit(1)

    subject = "[ShiftShield] TEST HEAT ALERT — High WBGT Advisory"
    message = (
        "SHIFTSHIELD HEAT SAFETY ADVISORY\n"
        "----------------------------------------\n"
        "Site: Mumbai Pilot Construction (MH-01)\n"
        "Condition: WBGT 31.2 deg C (HIGH HEAT BAND)\n"
        "Prescribed Schedule: 30 min Work / 30 min Rest (NIOSH)\n"
        "Action Required: Move workers to shaded rest area.\n\n"
        "Acknowledge this alert:\n"
        "https://main.d2y1tc05g1s6r3.amplifyapp.com/ack/test-token-demo\n\n"
        "ShiftShield - The heat alert that proves the rest happened.\n"
    )

    print(f"Publishing test message to {topic_arn}...")
    resp = sns.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=message,
    )
    print(f"[OK] Published! MessageId: {resp.get('MessageId')}")


if __name__ == "__main__":
    main()
