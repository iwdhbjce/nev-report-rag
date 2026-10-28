import json
import re
from pathlib import Path

import pymupdf4llm

# 项目目录：新能源汽车财报问答
project_dir = Path(__file__).resolve().parent

# 年报 PDF 所在目录：与项目文件夹同级的“原始年报”
pdf_dir = project_dir / "data" / "raw"

# 新结果文件，不覆盖之前的提取结果
output_path = project_dir / "data" / "extracted" / "layout_pages.jsonl"
output_path.parent.mkdir(parents=True, exist_ok=True)

pdf_files = sorted(pdf_dir.glob("*.pdf"))

if not pdf_files:
    raise FileNotFoundError(f"没有找到 PDF 文件，请检查目录：{pdf_dir}")

total_pages = 0

with output_path.open("w", encoding="utf-8") as output_file:
    for pdf_path in pdf_files:
        parts = pdf_path.stem.split("_")
        ticker = parts[0] if len(parts) >= 2 else ""
        company = parts[1] if len(parts) >= 2 else pdf_path.stem

        year_match = re.search(r"20\d{2}", pdf_path.stem)
        year = year_match.group(0) if year_match else ""

        # 按页提取版面内容，表格以 Markdown 行列形式保留
        pages = pymupdf4llm.to_markdown(
            str(pdf_path),
            page_chunks=True,
        )

        for pdf_page, page_data in enumerate(pages, start=1):
            record = {
                "company": company,
                "ticker": ticker,
                "year": year,
                "source_file": pdf_path.name,
                "pdf_page": pdf_page,
                "text": page_data.get("text", ""),
            }
            output_file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

        total_pages += len(pages)
        print(f"完成：{company}，{len(pages)} 页")

print(f"\n全部完成：{len(pdf_files)} 份报告，共 {total_pages} 页")
print(f"结果文件：{output_path}")