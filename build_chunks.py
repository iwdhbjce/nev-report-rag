import json
import re
from pathlib import Path

MAX_CHARS = 1200

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SECTION_RESET_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百]+[章节]|[一二三四五六七八九十百]+、)"
)


def section_path(stack):
    if not stack:
        return "未识别章节"
    return " > ".join(stack[level] for level in sorted(stack))


def likely_toc_page(text):
    chapter_count = len(
        re.findall(r"第[一二三四五六七八九十百]+[章节]", text)
    )

    if "目录" in text and chapter_count >= 2:
        return True

    if chapter_count >= 5 and len(text) < 5000 and "|---" not in text:
        return True

    return False


project_dir = Path(__file__).resolve().parent
input_path = project_dir / "data" / "extracted" / "layout_pages.jsonl"
output_path = project_dir / "data" / "extracted" / "chunks.jsonl"

if not input_path.exists():
    raise FileNotFoundError(f"找不到输入文件：{input_path}")

total_chunks = 0
skipped_toc_pages = 0
current_source = None
heading_stack = {}

with input_path.open("r", encoding="utf-8") as source_file, \
     output_path.open("w", encoding="utf-8") as output_file:

    for line in source_file:
        record = json.loads(line)

        if record["source_file"] != current_source:
            current_source = record["source_file"]
            heading_stack = {}

        text = record.get("text", "")

        if not text.strip():
            continue

        if likely_toc_page(text):
            skipped_toc_pages += 1
            continue

        current_section = section_path(heading_stack)
        buffer_section = current_section
        buffer = []
        page_chunks = []

        def flush_buffer():
            chunk_text = "\n".join(buffer).strip()
            if chunk_text:
                page_chunks.append((chunk_text, buffer_section))
            buffer.clear()

        for text_line in text.splitlines():
            match = HEADING_RE.match(text_line)

            if match:
                level = len(match.group(1))
                title = match.group(2).strip()

                # 报告名称不是章节，避免它污染章节路径
                if "年度报告" in title and not SECTION_RESET_RE.match(title):
                    continue

                flush_buffer()

                if title == "目录":
                    heading_stack = {}
                    current_section = "未识别章节"
                    buffer_section = current_section
                    continue

                # 新的报告章节开始时，清除旧章节路径
                if SECTION_RESET_RE.match(title):
                    heading_stack = {}

                for old_level in list(heading_stack):
                    if old_level >= level:
                        del heading_stack[old_level]

                heading_stack[level] = title
                current_section = section_path(heading_stack)
                buffer_section = current_section
                buffer.append(text_line)
                continue

            current_size = sum(len(item) + 1 for item in buffer)

            if (
                text_line.strip()
                and buffer
                and current_size + len(text_line) > MAX_CHARS
            ):
                flush_buffer()
                buffer_section = current_section

            buffer.append(text_line)

        flush_buffer()

        for chunk_number, (chunk_text, section) in enumerate(
            page_chunks, start=1
        ):
            chunk = {
                "chunk_id": (
                    f'{record.get("ticker", "")}_'
                    f'{record.get("year", "")}_'
                    f'p{record.get("pdf_page", 0):04d}_'
                    f'c{chunk_number:02d}'
                ),
                "company": record.get("company", ""),
                "ticker": record.get("ticker", ""),
                "year": record.get("year", ""),
                "source_file": record.get("source_file", ""),
                "section": section,
                "pdf_page": record.get("pdf_page", ""),
                "text": chunk_text,
            }

            output_file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            total_chunks += 1

print(f"切块完成：{total_chunks} 个检索块")
print(f"跳过目录页：{skipped_toc_pages} 页")
print(f"结果文件：{output_path}")