"""Download annual-report PDFs listed in report_manifest.csv from CNINFO."""

import csv
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests


PROJECT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = PROJECT_DIR / "report_manifest.csv"
OUTPUT_DIR = PROJECT_DIR / "data" / "raw"
ALLOWED_HOST = "static.cninfo.com.cn"
REQUIRED_COLUMNS = {"ticker", "company", "year", "report_type", "file_name", "source_url"}


def main():
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            f"找不到报告清单：{MANIFEST_PATH}。请将 report_manifest.csv 放在项目根目录。"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"清单缺少列：{', '.join(sorted(missing))}")
        rows = list(reader)

    if not rows:
        raise ValueError("report_manifest.csv 中没有报告记录。")

    failures = []
    for number, row in enumerate(rows, start=1):
        filename = Path((row.get("file_name") or "").strip()).name
        url = (row.get("source_url") or "").strip()
        company = (row.get("company") or "未知公司").strip()
        parsed_url = urlparse(url)

        if not filename or filename in {".", ".."}:
            failures.append(f"第 {number} 行：文件名为空或无效")
            continue
        if parsed_url.scheme != "https" or parsed_url.hostname != ALLOWED_HOST:
            failures.append(f"{company}：下载地址不是允许的巨潮资讯 HTTPS 地址")
            continue

        destination = OUTPUT_DIR / filename
        if destination.is_file() and destination.stat().st_size > 0:
            print(f"已存在，跳过：{company} - {filename}")
            continue

        temporary_path = None
        try:
            with requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 financial-report-course-project"},
                stream=True,
                timeout=(15, 120),
            ) as response:
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=OUTPUT_DIR, suffix=".part", delete=False
                ) as temporary_file:
                    temporary_path = Path(temporary_file.name)
                    first_bytes = b""
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if not chunk:
                            continue
                        if not first_bytes:
                            first_bytes = chunk[:8]
                        temporary_file.write(chunk)

            if not first_bytes.startswith(b"%PDF-"):
                raise ValueError("下载内容不是有效 PDF")
            os.replace(temporary_path, destination)
            temporary_path = None
            print(f"完成：{company} - {filename}")
        except (requests.RequestException, OSError, ValueError) as error:
            failures.append(f"{company}：{error}")
            print(f"失败：{company} - {error}", file=sys.stderr)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    print(f"\n清单报告数：{len(rows)}；失败数：{len(failures)}")
    print(f"PDF 保存位置：{OUTPUT_DIR}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()