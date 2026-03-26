"""
PaddleOCR-VL 任务提交与轮询（与 workspace-main 方法说明一致）。
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests


def _headers_multipart(token: str) -> dict[str, str]:
    return {"Authorization": f"bearer {token.strip()}"}


def submit_pdf_job(
    file_path: str | Path,
    *,
    use_doc_orientation_classify: bool = False,
    use_doc_unwarping: bool = False,
    use_chart_recognition: bool = False,
) -> str:
    token = os.environ.get("PADDLE_OCR_TOKEN", "").strip()
    if not token:
        raise ValueError("PADDLE_OCR_TOKEN is not set")

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    optional_payload = {
        "useDocOrientationClassify": use_doc_orientation_classify,
        "useDocUnwarping": use_doc_unwarping,
        "useChartRecognition": use_chart_recognition,
    }

    url = os.environ.get(
        "PADDLE_JOB_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
    )
    model = os.environ.get("PADDLE_MODEL", "PaddleOCR-VL-1.5")

    with open(path, "rb") as f:
        data = {"model": model, "optionalPayload": json.dumps(optional_payload)}
        files = {"file": (path.name, f, "application/pdf")}
        r = requests.post(url, headers=_headers_multipart(token), data=data, files=files, timeout=120)

    if r.status_code != 200:
        raise RuntimeError(f"Paddle job submit failed: {r.status_code} {r.text}")

    body = r.json()
    job_id = body.get("data", {}).get("jobId")
    if not job_id:
        raise RuntimeError(f"Unexpected submit response: {body}")
    return job_id


def poll_job_until_done(
    job_id: str, *, poll_seconds: float | None = None, max_wait_seconds: float = 3600.0
) -> dict[str, Any]:
    token = os.environ.get("PADDLE_OCR_TOKEN", "").strip()
    base_url = os.environ.get(
        "PADDLE_JOB_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
    ).rstrip("/")
    interval = poll_seconds
    if interval is None:
        try:
            interval = float(os.environ.get("PADDLE_POLL_INTERVAL_SECONDS", "2.0"))
        except ValueError:
            interval = 2.0
    if interval < 0.5:
        interval = 0.5

    url = f"{base_url}/{job_id}"
    deadline = time.monotonic() + max_wait_seconds

    while time.monotonic() < deadline:
        r = requests.get(url, headers=_headers_multipart(token), timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"Paddle job poll failed: {r.status_code} {r.text}")
        data = r.json().get("data", {})
        state = data.get("state")
        if state == "done":
            return data
        if state == "failed":
            raise RuntimeError(f"Paddle job failed: {data.get('errorMsg', data)}")
        time.sleep(interval)

    raise TimeoutError(f"Paddle job {job_id} did not finish within {max_wait_seconds}s")


def download_jsonl_text(jsonl_url: str) -> str:
    r = requests.get(jsonl_url, timeout=120)
    r.raise_for_status()
    return r.text


def run_parse_pipeline(file_path: str | Path) -> tuple[str, list[dict[str, Any]]]:
    """
    提交 PDF，轮询，下载 JSONL，返回 (raw_jsonl_text, 每行解析后的 dict 列表)。
    """
    job_id = submit_pdf_job(file_path)
    done = poll_job_until_done(job_id)
    jsonl_url = (done.get("resultUrl") or {}).get("jsonUrl")
    if not jsonl_url:
        raise RuntimeError(f"No jsonUrl in done payload: {done}")

    text = download_jsonl_text(jsonl_url)
    lines: list[dict[str, Any]] = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        lines.append(json.loads(line))
    return text, lines
