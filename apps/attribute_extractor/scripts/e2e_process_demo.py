#!/usr/bin/env python3
"""Real end-to-end process smoke: upload demo PDF → validate → process → wait → result.

Requires compose with INSTALL_PIPELINE=1 and root .env (LLM/Qdrant).
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import openpyxl

API = "http://127.0.0.1:8000"
DEMO_PDF = (
    Path(__file__).resolve().parents[3]
    / "research"
    / "datasets"
    / "demo"
    / "pdf"
    / "TU-DEMO-001.pdf"
)
PDF_NAME = "TU-DEMO-001.pdf"
# Object type with seeded attribute sets in the app
OBJECT_TYPE = "tanks"
POLL_SEC = 10
TIMEOUT_SEC = 60 * 45  # OCR+LLM on one PDF can take a while


def request(method: str, path: str, data: bytes | None = None, headers: dict | None = None, expect=(200,)):
    req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
            status = resp.status
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
        hdrs = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
    if status not in expect:
        raise SystemExit(f"{method} {path} -> {status}: {body[:800]!r}")
    return status, body, hdrs


def json_req(method: str, path: str, payload=None, expect=(200,)):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    status, body, hdrs = request(method, path, data=data, headers=headers, expect=expect)
    return status, (json.loads(body) if body else None), hdrs


def multipart(path: str, file_path: Path):
    boundary = "----E2EBoundary"
    parts = []
    raw = file_path.read_bytes()
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode()
    )
    parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
    parts.append(raw)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    status, resp, _ = request("POST", path, data=body, headers=headers, expect=(200,))
    return json.loads(resp)


def build_registry(dest: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "registry"
    ws.append(
        [
            "Номер документа в ИС ЕОНКОМ",
            "Имя файла с расширением",
            "Номер для обработки",
            "RECPart",
            "Исполнение",
        ]
    )
    ws.append(["TZ-E2E-001", PDF_NAME, 0, "REC-E2E-001", "basic"])
    wb.save(dest)
    return dest


def main() -> int:
    if not DEMO_PDF.is_file():
        raise SystemExit(f"Missing demo PDF: {DEMO_PDF}")

    _, health, _ = json_req("GET", "/health")
    print("health", health)

    # Sanity: pipeline imports inside container
    import subprocess

    check = subprocess.run(
        [
            "docker",
            "exec",
            "attribute-extractor-backend",
            "python",
            "-c",
            "import qdrant_client, dedoc, langchain_openai; print('pipeline_imports_ok')",
        ],
        capture_output=True,
        text=True,
    )
    print(check.stdout.strip() or check.stderr.strip())
    if check.returncode != 0:
        raise SystemExit("Backend image missing pipeline deps — rebuild with INSTALL_PIPELINE=1")

    name = f"E2E real {int(time.time())}"
    _, task, _ = json_req("POST", "/tasks", {"name": name, "object_type": OBJECT_TYPE}, expect=(201,))
    task_id = task["id"]
    print("task", task_id)

    with tempfile.TemporaryDirectory() as tmp:
        registry = build_registry(Path(tmp) / "registry.xlsx")
        multipart(f"/tasks/{task_id}/registry", registry)
        multipart(f"/tasks/{task_id}/documents", DEMO_PDF)

    _, report, _ = json_req("POST", f"/tasks/{task_id}/validate")
    print("validate", report.get("is_valid"), "packages", len(report.get("packages") or []))
    if not report.get("is_valid"):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit("validation failed")

    _, proc, _ = json_req("POST", f"/tasks/{task_id}/process", {"mode": "from_start"})
    print("process started", proc.get("status"))

    started = time.time()
    while True:
        _, cur, _ = json_req("GET", f"/tasks/{task_id}")
        status = cur.get("status")
        step = cur.get("progress_step")
        msg = cur.get("progress_message")
        print(f"  [{int(time.time()-started):4d}s] status={status} step={step} msg={msg}")
        if status in {"done", "error"}:
            break
        if time.time() - started > TIMEOUT_SEC:
            raise SystemExit("timeout waiting for process")
        time.sleep(POLL_SEC)

    if status != "done":
        print("ERROR", cur.get("error_message"))
        # dump log tail from container
        subprocess.run(
            [
                "docker",
                "exec",
                "attribute-extractor-backend",
                "bash",
                "-lc",
                f"tail -n 80 /app/apps/attribute_extractor/backend/.cache/tasks/{task_id}/logs/processing.log || true",
            ]
        )
        return 1

    status_code, xlsx, headers = request("GET", f"/tasks/{task_id}/result", expect=(200,))
    out = Path(tempfile.gettempdir()) / f"ae_e2e_result_{task_id[:8]}.xlsx"
    out.write_bytes(xlsx)
    print("result_ok", out, "bytes", len(xlsx), "cd", headers.get("content-disposition", "")[:100])

    # keep task for inspection; uncomment to delete:
    # request("DELETE", f"/tasks/{task_id}", expect=(204,))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
