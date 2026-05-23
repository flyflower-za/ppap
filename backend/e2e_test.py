"""
End-to-End Verification Test Script
Performs: Login → Upload PDF → Poll for completion → Print checker results
Tests the full pipeline including real QR Code and Digital Signature checkers.
"""
import sys
import time
import json
import requests
import fitz  # PyMuPDF — generate test PDF with embedded QR
import cv2
import numpy as np
import os

BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "admin@ppap.com"

# ── Colors for terminal output ──
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def banner(msg):
    print(f"\n{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{CYAN}{'─' * 60}{RESET}")


def step(n, msg):
    print(f"\n{BOLD}[Step {n}]{RESET} {msg}")


def generate_test_pdf_with_qr() -> bytes:
    """Generate a test PDF with an embedded QR code for end-to-end testing."""
    print("  📄 Generating test PDF with embedded QR code...")

    # Create QR code image using OpenCV
    try:
        encoder = cv2.QRCodeEncoder.create()
        qr_img = encoder.encode("https://ppap.example.com/verify/e2e-test-2026")
    except (cv2.error, AttributeError):
        # Fallback: create a simple 100x100 black square as placeholder
        print("  ⚠️  OpenCV QRCodeEncoder not available, creating plain PDF")
        qr_img = None

    # Create PDF with PyMuPDF
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Add title text
    page.insert_text(
        fitz.Point(72, 80),
        "PPAP 文件校验平台 — 端到端测试文档",
        fontsize=16,
        fontname="helv",
    )
    page.insert_text(
        fitz.Point(72, 110),
        "此 PDF 由自动化测试脚本生成，用于验证 QR Code 和数字签名检测模块。",
        fontsize=10,
        fontname="helv",
    )

    # Embed QR code image if generated
    if qr_img is not None:
        qr_path = "/tmp/_e2e_test_qr.png"
        cv2.imwrite(qr_path, qr_img)
        rect = fitz.Rect(72, 150, 272, 350)  # 200x200 area
        page.insert_image(rect, filename=qr_path)
        os.remove(qr_path)
        page.insert_text(fitz.Point(72, 370), "↑ 嵌入二维码 (内容: ppap.example.com/verify/e2e-test-2026)", fontsize=9, fontname="helv")
    
    pdf_bytes = doc.tobytes()
    doc.close()
    print(f"  ✅ Test PDF generated: {len(pdf_bytes)} bytes")
    return pdf_bytes


def main():
    banner("PPAP 本地化检测模块 — 端到端集成验证")

    # ── Step 1: Login ──
    step(1, "Login to get JWT token...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": TEST_EMAIL})
    if resp.status_code != 200:
        print(f"  {RED}❌ Login failed: {resp.status_code} {resp.text}{RESET}")
        sys.exit(1)

    token = resp.json()["access_token"]
    print(f"  {GREEN}✅ Login successful. Token: {token[:20]}...{RESET}")

    headers = {"Authorization": f"Bearer {token}"}

    # ── Step 2: Generate & Upload PDF ──
    step(2, "Generate test PDF and upload...")
    pdf_bytes = generate_test_pdf_with_qr()

    files = {"file": ("e2e_test_with_qr.pdf", pdf_bytes, "application/pdf")}
    resp = requests.post(
        f"{BASE_URL}/files/upload?file_type=quality_report",
        files=files,
        headers=headers,
    )
    if resp.status_code != 200:
        print(f"  {RED}❌ Upload failed: {resp.status_code} {resp.text}{RESET}")
        sys.exit(1)

    file_data = resp.json()
    file_id = file_data["id"]
    print(f"  {GREEN}✅ File uploaded: {file_data['original_filename']}{RESET}")
    print(f"     ID: {file_id}")
    print(f"     Status: {file_data['status']}")

    # ── Step 3: Poll for verification completion ──
    step(3, "Polling for verification completion (max 60s)...")
    max_wait = 60
    start = time.time()

    while time.time() - start < max_wait:
        resp = requests.get(f"{BASE_URL}/files/{file_id}", headers=headers)
        if resp.status_code != 200:
            print(f"  {RED}❌ Fetch failed: {resp.status_code}{RESET}")
            break

        data = resp.json()
        progress = data.get("verification_progress", 0)
        status = data.get("status", "unknown")
        elapsed = int(time.time() - start)

        print(f"  ⏳ [{elapsed}s] Progress: {progress}% | Status: {status}", end="\r")

        if status in ("completed", "warning", "failed") and progress >= 100:
            print()  # newline
            break

        time.sleep(2)
    else:
        print(f"\n  {YELLOW}⚠️  Timeout reached after {max_wait}s.{RESET}")

    # ── Step 4: Display final results ──
    step(4, "Verification Results:")
    resp = requests.get(f"{BASE_URL}/files/{file_id}", headers=headers)
    data = resp.json()

    print(f"  {BOLD}Final Status:{RESET} {data.get('status')}")
    print(f"  {BOLD}Pass Rate:{RESET}    {data.get('pass_rate')}%")
    print(f"  {BOLD}Duration:{RESET}     {data.get('duration_seconds')}s")

    verification_result = data.get("verification_result")
    if verification_result:
        if isinstance(verification_result, str):
            vr = json.loads(verification_result)
        else:
            vr = verification_result

        summary = vr.get("summary", {})
        print(f"\n  {BOLD}Summary:{RESET}")
        print(f"    Total Checks: {summary.get('total')}")
        print(f"    {GREEN}Pass: {summary.get('pass')}{RESET}")
        print(f"    {YELLOW}Warning: {summary.get('warning')}{RESET}")
        print(f"    {RED}Fail: {summary.get('fail')}{RESET}")

        print(f"\n  {BOLD}Detailed Check Results:{RESET}")
        for i, check in enumerate(vr.get("checks", []), 1):
            status_icon = {"pass": f"{GREEN}✅", "warning": f"{YELLOW}⚠️", "fail": f"{RED}❌"}.get(check["status"], "?")
            print(f"    {i}. {status_icon} {check['name']}{RESET}")
            print(f"       {check['message']}")

        # QR Code results
        qr_codes = vr.get("qr_codes", [])
        if qr_codes:
            print(f"\n  {BOLD}🔲 QR Codes Detected:{RESET}")
            for qr in qr_codes:
                print(f"    Page {qr['page']}: {CYAN}{qr['data']}{RESET}")

        # Digital Signature results
        sigs = vr.get("digital_signatures", {})
        print(f"\n  {BOLD}🔐 Digital Signatures:{RESET}")
        print(f"    Signed: {sigs.get('signed', False)}")
        for sig in sigs.get("signatures", []):
            print(f"    - {sig['signature_name']}: signer={sig.get('signer_cn')}, integrity={sig.get('integrity')}")
    else:
        print(f"  {YELLOW}⚠️  No verification_result JSON found in response{RESET}")

    # ── Step 5: Check notifications ──
    step(5, "Checking notifications...")
    resp = requests.get(f"{BASE_URL}/notifications?limit=5", headers=headers)
    if resp.status_code == 200:
        notifs = resp.json()
        if isinstance(notifs, list):
            for n in notifs[:3]:
                print(f"  🔔 [{n.get('type')}] {n.get('title')}")
                print(f"     {n.get('message')}")
        elif isinstance(notifs, dict) and "items" in notifs:
            for n in notifs["items"][:3]:
                print(f"  🔔 [{n.get('type')}] {n.get('title')}")
                print(f"     {n.get('message')}")
    else:
        print(f"  {YELLOW}⚠️  Could not fetch notifications: {resp.status_code}{RESET}")

    banner("端到端验证完成 ✅")


if __name__ == "__main__":
    main()
