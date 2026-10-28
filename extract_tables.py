from pathlib import Path
import csv
import json
import pymupdf

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "data" / "raw"
MANIFEST = PROJECT_DIR / "report_manifest.csv"
OUTPUT_FILE = (
    Path(__file__).resolve().parent / "data" / "extracted" / "tables.jsonl"
)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with MANIFEST.open("r", encoding="utf-8-sig", newline="") as f:
    reports = list(csv.DictReader(f))

total_tables = 0
pages_with_tables = 0
errors = []
sample = None

with OUTPUT_FILE.open("w", encoding="utf-8") as out:
    for report in reports:
        pdf_path = SOURCE_DIR / report["file_name"]
        doc = pymupdf.open(str(pdf_path))
        report_tables = 0
        report_pages = 0

        try:
            for pdf_page, page in enumerate(doc, start=1):
                try:
                    found_tables = page.find_tables().tables
                except Exception as exc:
                    errors.append(
                        f"{report['company']} PDF第{pdf_page}页：{exc}"
                    )
                    continue

                if not found_tables:
                    continue

                report_pages += 1

                for table_index, table in enumerate(found_tables, start=1):
                    try:
                        extracted = table.extract()
                    except Exception as exc:
                        errors.append(
                            f"{report['company']} PDF第{pdf_page}页表格"
                            f"{table_index}：{exc}"
                        )
                        continue

                    rows = [
                        [
                            "" if cell is None
                            else " ".join(str(cell).split())
                            for cell in row
                        ]
                        for row in extracted
                    ]
                    rows = [row for row in rows if any(cell for cell in row)]

                    if not rows:
                        continue

                    table_text = "\n".join(
                        " | ".join(row) for row in rows
                    )

                    record = {
                        "company": report["company"],
                        "ticker": report["ticker"],
                        "year": int(report["year"]),
                        "source_file": report["file_name"],
                        "source_url": report["source_url"],
                        "pdf_page": pdf_page,
                        "table_index": table_index,
                        "rows": rows,
                        "text": table_text,
                    }
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")

                    report_tables += 1
                    total_tables += 1

                    if sample is None:
                        sample = (
                            report["company"],
                            pdf_page,
                            rows[:6],
                        )
        finally:
            doc.close()

        pages_with_tables += report_pages
        print(
            f"完成：{report['company']}，检测到 "
            f"{report_tables} 张表，分布在 {report_pages} 页"
        )

print(f"\n表格总数：{total_tables}")
print(f"含表格的页面数：{pages_with_tables}")
print(f"输出文件：{OUTPUT_FILE}")
print(f"检测错误数：{len(errors)}")

if sample:
    company, pdf_page, rows = sample
    print(f"\n首个样例：{company}，PDF第{pdf_page}页")
    for row in rows:
        print(" | ".join(row))

if errors:
    print("\n前几条检测错误：")
    for error in errors[:5]:
        print(error)