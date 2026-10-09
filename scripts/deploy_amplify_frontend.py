#!/usr/bin/env python3
"""Deploy ShiftShield frontend/dist to AWS Amplify Hosting (ap-south-1)."""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import time
import zipfile
import urllib.request
import boto3

REGION = "ap-south-1"
APP_NAME = "shiftshield-web"
BRANCH_NAME = "main"
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))


def make_zip() -> bytes:
    if not os.path.isdir(DIST_DIR):
        raise FileNotFoundError(f"Directory not found: {DIST_DIR}. Did you run 'pnpm run build'?")
    print(f"Zipping {DIST_DIR}...")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(DIST_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, DIST_DIR).replace("\\", "/")
                zf.write(abs_path, rel_path)
    data = buf.getvalue()
    print(f"Created zip archive: {len(data) / 1024:.1f} KB")
    return data


def get_or_create_app(client) -> tuple[str, str]:
    apps = client.list_apps().get("apps", [])
    for app in apps:
        if app["name"] == APP_NAME:
            print(f"Found existing Amplify App: {app['appId']} ({app['name']})")
            return app["appId"], app["defaultDomain"]

    print(f"Creating new Amplify App: {APP_NAME}...")
    spa_rules = [
        {
            "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>",
            "target": "/index.html",
            "status": "200",
        }
    ]
    resp = client.create_app(
        name=APP_NAME,
        description="ShiftShield Web Dashboard & Worker Rest Verification App",
        customRules=spa_rules,
        environmentVariables={
            "VITE_API_BASE_URL": "https://hrzm2jaosj.execute-api.ap-south-1.amazonaws.com",
        },
    )
    app = resp["app"]
    return app["appId"], app["defaultDomain"]


def get_or_create_branch(client, app_id: str) -> None:
    branches = client.list_branches(appId=app_id).get("branches", [])
    for b in branches:
        if b["branchName"] == BRANCH_NAME:
            print(f"Found existing branch: {BRANCH_NAME}")
            return
    print(f"Creating branch: {BRANCH_NAME}...")
    client.create_branch(
        appId=app_id,
        branchName=BRANCH_NAME,
        stage="PRODUCTION",
        enableAutoBuild=False,
    )


def deploy(client, app_id: str, zip_bytes: bytes) -> str:
    print(f"Requesting deployment slot for {BRANCH_NAME}...")
    dep = client.create_deployment(appId=app_id, branchName=BRANCH_NAME)
    job_id = dep["jobId"]
    upload_url = dep["zipUploadUrl"]
    print(f"Deployment job ID: {job_id}")

    print("Uploading zip payload to Amplify S3 signed URL...")
    req = urllib.request.Request(
        upload_url,
        data=zip_bytes,
        headers={"Content-Type": "application/zip"},
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        if resp.getcode() not in (200, 204):
            raise RuntimeError(f"Zip upload failed with status: {resp.getcode()}")
    print("Zip uploaded successfully.")

    print("Starting deployment...")
    client.start_deployment(appId=app_id, branchName=BRANCH_NAME, jobId=job_id)

    print("Waiting for deployment to complete...")
    for _ in range(60):
        time.sleep(3)
        job = client.get_job(appId=app_id, branchName=BRANCH_NAME, jobId=job_id)["job"]
        status = job["summary"]["status"]
        print(f"  Current status: {status}")
        if status == "SUCCEED":
            print("[SUCCESS] Deployment completed successfully!")
            return f"https://{BRANCH_NAME}.{app_id}.amplifyapp.com"
        if status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Amplify deployment ended with status: {status}")

    return f"https://{BRANCH_NAME}.{app_id}.amplifyapp.com"


def main():
    print(f"==================================================")
    print(f"ShiftShield Frontend Amplify Deployment")
    print(f"Region: {REGION} | App: {APP_NAME}")
    print(f"==================================================")

    zip_bytes = make_zip()
    client = boto3.client("amplify", region_name=REGION)

    app_id, domain = get_or_create_app(client)
    get_or_create_branch(client, app_id)
    url = deploy(client, app_id, zip_bytes)

    print(f"\n==================================================")
    print(f"[OK] Live Frontend URL: {url}")
    print(f"Default Domain: https://{BRANCH_NAME}.{domain}")
    print(f"==================================================")


if __name__ == "__main__":
    main()
