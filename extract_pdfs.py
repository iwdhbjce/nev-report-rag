from pathlib import Path
import csv
import json
import pymupdf

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "data" / "raw"
MANIFEST = PROJECT_DIR / "report_manifest.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "extracted"
OUTPUT_FILE = OUTPUT_DIR / "pages.jsonl"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with MANIFEST.open("r", encoding="utf-8-sig", newline="") as f:
    reports = list(csv.DictReader(f))

if len(reports) != 15:
    raise SystemExit(f"清单应有15家公司，实际读到 {len(reports)} 家。")

total_pages = 0
missing_files = []
short_pages = []

with OUTPUT_FILE.open("w", encoding="utf-8") as out:
    for report in reports:
        pdf_path = SOURCE_DIR / report["file_name"]

        if not pdf_path.is_file():
            missing_files.append(report["file_name"])
            continue

        doc = pymupdf.open(str(pdf_path))
        page_count = doc.page_count

        try:
            for pdf_page, page in enumerate(doc, start=1):
                text = page.get_text().strip()

                record = {
                    "company": report["company"],
                    "ticker": report["ticker"],
                    "year": int(report["year"]),
                    "report_type": report["report_type"],
                    "section": "",
                    "source_file": report["file_name"],
                    "source_url": report["source_url"],
                    "pdf_page": pdf_page,
                    "text": text,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_pages += 1

                if len(text) < 40:
                    short_pages.append(
                        f"{report['company']} PDF第{pdf_page}页"
                    )
        finally:
            doc.close()

        print(f"完成：{report['company']}，{page_count} 页")

print(f"\n总页数：{total_pages}")
print(f"提取结果：{OUTPUT_FILE}")
print(f"文字较少的页面：{len(short_pages)} 页（之后抽查）")

if missing_files:
    print("\n找不到这些 PDF：")
    for name in missing_files:
        print(name)