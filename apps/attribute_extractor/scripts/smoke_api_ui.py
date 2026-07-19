#!/usr/bin/env python3
"""End-to-end API (+ UI proxy) smoke for attribute_extractor.

Covers every frontend client method against live compose.
Process step is exercised for error path; success/result uses a mocked
extractions checkpoint (no OCR/LLM required).
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("Need openpyxl on host: uv pip install openpyxl", file=sys.stderr)
    raise

API = "http://127.0.0.1:8000"
UI = "http://127.0.0.1:5173"
PROXY = f"{UI}/api"
DEMO_PDF = (
    Path(__file__).resolve().parents[3]
    / "research"
    / "datasets"
    / "demo"
    / "pdf"
    / "TU-DEMO-001.pdf"
)
PDF_NAME = "TU-DEMO-001.pdf"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name, ok, detail))
        mark = "OK" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]


def request(
    base: str,
    method: str,
    path: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    expect: int | tuple[int, ...] = 200,
) -> tuple[int, bytes, dict[str, str]]:
    url = f"{base}{path}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            status = resp.status
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
        resp_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
    allowed = expect if isinstance(expect, tuple) else (expect,)
    if status not in allowed:
        raise AssertionError(f"{method} {path} -> {status}, expected {allowed}: {body[:500]!r}")
    return status, body, resp_headers


def json_req(base: str, method: str, path: str, payload: dict | None = None, expect: int | tuple[int, ...] = 200):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    status, body, headers_out = request(base, method, path, data=data, headers=headers, expect=expect)
    parsed = json.loads(body.decode("utf-8")) if body else None
    return status, parsed, headers_out


def multipart_upload(base: str, path: str, file_path: Path, field: str = "file", extra: dict[str, str] | None = None):
    body = _multipart_bytes(file_path, field=field, extra=extra)
    headers = {
        "Content-Type": "multipart/form-data; boundary=----SmokeBoundary7MA4YWxkTrZu0gW",
        "Accept": "application/json",
    }
    status, resp_body, _ = request(base, "POST", path, data=body, headers=headers, expect=200)
    return status, json.loads(resp_body.decode("utf-8"))


def _multipart_bytes(file_path: Path, field: str = "file", extra: dict[str, str] | None = None) -> bytes:
    boundary = "----SmokeBoundary7MA4YWxkTrZu0gW"
    chunks: list[bytes] = []
    for key, value in (extra or {}).items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        chunks.append(f"{value}\r\n".encode())
    file_bytes = file_path.read_bytes()
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(
        f'Content-Disposition: form-data; name="{field}"; filename="{file_path.name}"\r\n'.encode()
    )
    chunks.append(b"Content-Type: application/octet-stream\r\n\r\n")
    chunks.append(file_bytes)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks)


def build_registry(pdf_name: str, dest: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "registry"
    headers = [
        "Номер документа в ИС ЕОНКОМ",
        "Имя файла с расширением",
        "Номер для обработки",
        "RECPart",
        "Исполнение",
    ]
    ws.append(headers)
    ws.append(["TZ-SMOKE-001", pdf_name, 0, "REC-SMOKE-001", "basic"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dest)
    return dest


def mock_completed_processing(task_id: str, package_id: str, tz_id: str, attr_id: str) -> None:
    """Write fake extractions + checkpoint and mark task done inside the backend container."""
    script = f"""
import json, sqlite3
from pathlib import Path
from datetime import datetime, timezone

task_id = {task_id!r}
package_id = {package_id!r}
tz_id = {tz_id!r}
attr_id = {attr_id!r}

root = Path('/app/apps/attribute_extractor/backend/.cache/tasks') / task_id
out_dir = root / 'output' / 'REC-SMOKE-001'
out_dir.mkdir(parents=True, exist_ok=True)
extractions = {{
  'extractions': [
    {{
      'attribute_id': attr_id,
      'value': '1.6',
      'unit': 'МПа',
      'source_section_id': 0,
      'high_confidence': True,
      'error': False,
      'raw_quote': 'smoke mock',
    }}
  ]
}}
(out_dir / 'extractions.json').write_text(json.dumps(extractions, ensure_ascii=False, indent=2), encoding='utf-8')
(out_dir / 'source_chunks.json').write_text(
  json.dumps({{attr_id: {{'0': 'Рабочее давление 1.6 МПа'}}}}, ensure_ascii=False),
  encoding='utf-8',
)
checkpoints = {{
  'pipeline_version': '1.0',
  'checkpoints': {{
    '1': {{
      'package_id': package_id,
      'tz_id': tz_id,
      'collection_name': 'smoke',
      'output_path': 'output/REC-SMOKE-001/extractions.json',
      'source_chunks_path': 'output/REC-SMOKE-001/source_chunks.json',
      'pipeline_version': '1.0',
      'created_at': datetime.now(timezone.utc).isoformat(),
    }}
  }}
}}
(root / 'artifacts').mkdir(parents=True, exist_ok=True)
(root / 'output').mkdir(parents=True, exist_ok=True)
(root / 'output' / 'tz_checkpoints.json').write_text(json.dumps(checkpoints, ensure_ascii=False, indent=2), encoding='utf-8')

db = Path('/app/apps/attribute_extractor/backend/.cache/backend.sqlite3')
conn = sqlite3.connect(db)
conn.execute(
  \"\"\"UPDATE tasks SET status=?, result_file_name=?, progress_step=?, progress_message=?,
           error_message=NULL, failed_tz_id=NULL, failed_tz_index=NULL,
           updated_at=? WHERE id=?\"\"\",
  ('done', 'result.xlsx', 'done', 'Обработка завершена (smoke mock)',
   datetime.now(timezone.utc).isoformat(), task_id),
)
conn.commit()
conn.close()
print('mocked', task_id)
"""
    import subprocess

    subprocess.run(
        ["docker", "exec", "-i", "attribute-extractor-backend", "python", "-"],
        input=script.encode("utf-8"),
        check=True,
    )


def pick_attr_id() -> str:
    import subprocess

    out = subprocess.check_output(
        [
            "docker",
            "exec",
            "attribute-extractor-backend",
            "python",
            "-c",
            "import json; from pathlib import Path; "
            "p=Path('/app/apps/attribute_extractor/backend/reference_data/tanks/attributes_set.json'); "
            "data=json.loads(p.read_text()); "
            "attrs=data['attributes']; "
            "aid=next(k for k,v in attrs.items() if v.get('for_extraction') and v.get('has_unit')); "
            "print(aid)",
        ],
        text=True,
    ).strip()
    return out


def run_suite(base: str, label: str, report: Report, *, with_ui_assets: bool = False) -> str:
    """Full API flow against base URL. Returns task_id."""
    # Health / object types
    _, health, _ = json_req(base, "GET", "/health")
    report.add(f"{label}/health", health.get("status") == "ok", str(health))

    _, types, _ = json_req(base, "GET", "/object-types")
    report.add(f"{label}/object-types", isinstance(types, list) and len(types) >= 1, f"n={len(types)}")

    # Registry template
    status, blob, headers = request(base, "GET", "/registry-template", expect=200)
    report.add(
        f"{label}/registry-template",
        status == 200 and len(blob) > 100,
        f"bytes={len(blob)} ctype={headers.get('content-type','')}",
    )

    # Tasks CRUD
    unique = f"{label}-{int(time.time() * 1000)}"
    _, task, _ = json_req(
        base,
        "POST",
        "/tasks",
        {"name": f"Smoke {unique}", "object_type": "tanks"},
        expect=201,
    )
    task_id = task["id"]
    report.add(f"{label}/tasks create", bool(task_id), task_id)

    _, listed, _ = json_req(base, "GET", "/tasks?limit=20&offset=0")
    report.add(f"{label}/tasks list", listed.get("total", 0) >= 1, f"total={listed.get('total')}")

    _, got, _ = json_req(base, "GET", f"/tasks/{task_id}")
    report.add(f"{label}/tasks get", got["id"] == task_id)

    _, patched, _ = json_req(base, "PATCH", f"/tasks/{task_id}", {"name": f"Smoke renamed {unique}"})
    report.add(f"{label}/tasks patch", patched["name"].startswith("Smoke renamed"))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        registry = build_registry(PDF_NAME, tmp_path / "registry.xlsx")
        if not DEMO_PDF.is_file():
            report.add(f"{label}/demo pdf present", False, str(DEMO_PDF))
            return task_id
        report.add(f"{label}/demo pdf present", True, DEMO_PDF.name)

        _, after_reg = multipart_upload(base, f"/tasks/{task_id}/registry", registry)
        report.add(
            f"{label}/upload registry",
            after_reg.get("registry_file_name") is not None,
            f"registry_file_name={after_reg.get('registry_file_name')}",
        )

        status, reg_blob, _ = request(base, "GET", f"/tasks/{task_id}/registry", expect=200)
        report.add(f"{label}/download registry", status == 200 and len(reg_blob) > 100)

        _, after_doc = multipart_upload(base, f"/tasks/{task_id}/documents", DEMO_PDF)
        report.add(
            f"{label}/upload document",
            after_doc.get("id") == task_id,
            f"status={after_doc.get('status')}",
        )

        _, docs, _ = json_req(base, "GET", f"/tasks/{task_id}/documents")
        report.add(f"{label}/list documents", isinstance(docs, list) and len(docs) >= 1, str(docs))

        status, pdf_blob, _ = request(
            base, "GET", f"/tasks/{task_id}/documents/{PDF_NAME}", expect=200
        )
        report.add(f"{label}/download document", status == 200 and len(pdf_blob) > 100)

        # validate ready
        _, report_valid, _ = json_req(base, "POST", f"/tasks/{task_id}/validate")
        report.add(
            f"{label}/validate",
            report_valid.get("is_valid") is True and len(report_valid.get("packages") or []) == 1,
            json.dumps(report_valid.get("issues") or [], ensure_ascii=False)[:200],
        )

        # Mutations while status=ready (before process locks sources)
        _, after_del, _ = json_req(base, "DELETE", f"/tasks/{task_id}/documents/{PDF_NAME}")
        report.add(f"{label}/delete document", True, f"status={after_del.get('status')}")
        _, after_reup = multipart_upload(base, f"/tasks/{task_id}/documents", DEMO_PDF)
        report.add(f"{label}/re-upload document", after_reup.get("id") == task_id)

        # Re-validate after re-upload
        _, report_valid, _ = json_req(base, "POST", f"/tasks/{task_id}/validate")
        report.add(
            f"{label}/re-validate",
            report_valid.get("is_valid") is True,
            json.dumps(report_valid.get("issues") or [], ensure_ascii=False)[:200],
        )

        gt_path = tmp_path / "gt.xlsx"
        wb = openpyxl.Workbook()
        wb.active.title = "gt"
        attr_id = pick_attr_id()
        # Intentionally incomplete GT shape — API must reject with structured error.
        wb.active.append(["RECPart", attr_id])
        wb.active.append(["REC-SMOKE-001", "1.6"])
        wb.save(gt_path)
        try:
            status, gt_body, _ = request(
                base,
                "POST",
                f"/tasks/{task_id}/ground-truth",
                data=_multipart_bytes(gt_path),
                headers={
                    "Content-Type": "multipart/form-data; boundary=----SmokeBoundary7MA4YWxkTrZu0gW",
                    "Accept": "application/json",
                },
                expect=(200, 400),
            )
            if status == 200:
                after_gt = json.loads(gt_body.decode("utf-8"))
                report.add(
                    f"{label}/upload ground-truth",
                    after_gt.get("has_ground_truth") is True,
                    f"has_gt={after_gt.get('has_ground_truth')}",
                )
                status_v, _, _ = request(
                    base,
                    "POST",
                    f"/tasks/{task_id}/ground-truth/validate",
                    expect=(200, 400, 409, 422),
                )
                report.add(f"{label}/ground-truth validate responds", True, f"status={status_v}")
                status_d, _, _ = request(base, "GET", f"/tasks/{task_id}/ground-truth", expect=(200, 404))
                report.add(f"{label}/download ground-truth", status_d in (200, 404), f"status={status_d}")
                _, after_gt_del, _ = json_req(base, "DELETE", f"/tasks/{task_id}/ground-truth")
                report.add(f"{label}/delete ground-truth", after_gt_del.get("has_ground_truth") is False)
            else:
                err = json.loads(gt_body.decode("utf-8"))
                code = (err.get("error") or {}).get("code", "")
                report.add(
                    f"{label}/ground-truth rejects bad format",
                    code.startswith("ground_truth"),
                    f"status={status} code={code}",
                )
        except AssertionError as exc:
            report.add(f"{label}/ground-truth flow", False, str(exc))
        except Exception as exc:
            report.add(f"{label}/ground-truth flow", False, str(exc))

        # result before done → 409
        try:
            request(base, "GET", f"/tasks/{task_id}/result", expect=409)
            report.add(f"{label}/result not ready (409)", True)
        except AssertionError as exc:
            report.add(f"{label}/result not ready (409)", False, str(exc))

        if not report_valid.get("is_valid"):
            report.add(f"{label}/skip mock-result (invalid kit)", True)
            request(base, "DELETE", f"/tasks/{task_id}", expect=204)
            report.add(f"{label}/tasks delete", True)
            return task_id

        # mock done + download result
        packages = (report_valid.get("packages") or [{}])[0]
        package_id = packages.get("package_id") or packages.get("recpart") or packages.get("tz_id")
        tz_id = packages.get("tz_id") or "TZ-SMOKE-001"
        mock_completed_processing(task_id, package_id, tz_id, attr_id)

        _, done_task, _ = json_req(base, "GET", f"/tasks/{task_id}")
        report.add(f"{label}/mock done status", done_task.get("status") == "done", done_task.get("status"))

        status, xlsx, headers = request(base, "GET", f"/tasks/{task_id}/result", expect=200)
        report.add(
            f"{label}/result download",
            status == 200 and len(xlsx) > 500,
            f"bytes={len(xlsx)} cd={headers.get('content-disposition','')[:80]}",
        )

    # cleanup main task (mock path must not race a live /process)
    request(base, "DELETE", f"/tasks/{task_id}", expect=204)
    report.add(f"{label}/tasks delete", True)

    # Separate probe: POST /process starts (may finish error without deps, or keep
    # processing when INSTALL_PIPELINE=1). Do not wait for full OCR/LLM.
    try:
        _, probe, _ = json_req(
            base,
            "POST",
            "/tasks",
            {"name": f"Smoke process {unique}", "object_type": "tanks"},
            expect=201,
        )
        probe_id = probe["id"]
        with tempfile.TemporaryDirectory() as tmp2:
            reg2 = build_registry(PDF_NAME, Path(tmp2) / "registry.xlsx")
            multipart_upload(base, f"/tasks/{probe_id}/registry", reg2)
            multipart_upload(base, f"/tasks/{probe_id}/documents", DEMO_PDF)
            json_req(base, "POST", f"/tasks/{probe_id}/validate")
            _, process_task, _ = json_req(
                base,
                "POST",
                f"/tasks/{probe_id}/process",
                {"mode": "from_start"},
                expect=(200, 409),
            )
            status_now = (process_task or {}).get("status")
            report.add(
                f"{label}/process accepted",
                status_now in {"processing", "error", "done"},
                f"status={status_now}",
            )
            final = process_task or {}
            for _ in range(20):
                _, final, _ = json_req(base, "GET", f"/tasks/{probe_id}")
                if final.get("status") != "processing":
                    break
                time.sleep(0.5)
            # Without pipeline deps → error/done quickly. With pipeline → may still be processing.
            report.add(
                f"{label}/process started or finished",
                final.get("status") in {"processing", "error", "done"},
                f"status={final.get('status')} err={final.get('error_message')}",
            )
        # Best-effort cleanup; 409 if still processing is acceptable for smoke.
        try:
            request(base, "DELETE", f"/tasks/{probe_id}", expect=(204, 409))
            report.add(f"{label}/process probe cleanup", True)
        except AssertionError as exc:
            report.add(f"{label}/process probe cleanup", False, str(exc))
    except AssertionError as exc:
        report.add(f"{label}/process probe", False, str(exc))

    if with_ui_assets:
        status, html, _ = request(UI, "GET", "/", expect=200)
        report.add("ui/index", status == 200 and b"<html" in html.lower(), f"bytes={len(html)}")
        import re

        assets = re.findall(rb'(?:src|href)="(/assets/[^"]+)"', html)
        for asset in assets[:5]:
            path = asset.decode()
            st, body, _ = request(UI, "GET", path, expect=200)
            report.add(f"ui/asset {path}", st == 200 and len(body) > 10, f"bytes={len(body)}")

    return task_id


def main() -> int:
    report = Report()
    # sanity
    try:
        request(API, "GET", "/health", expect=200)
    except Exception as exc:
        print(f"Backend not reachable at {API}: {exc}", file=sys.stderr)
        return 2

    run_suite(API, "api", report)
    run_suite(PROXY, "ui-proxy", report, with_ui_assets=True)

    failed = report.failed
    print("\n=== SUMMARY ===")
    print(f"passed={len(report.checks) - len(failed)} failed={len(failed)} total={len(report.checks)}")
    for item in failed:
        print(f"  FAIL {item.name}: {item.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
