# 新能源汽车财报问答

这是一个面向 15 家新能源汽车相关上市公司 2025 年年度报告的本地问答项目。系统使用 TF-IDF 向量检索与 BM25 关键词检索召回年报片段，再调用 DeepSeek 根据片段作答，并标注公司、章节和 PDF 页码。

## 项目内容

- `download_reports.py`：读取报告清单，从巨潮资讯下载 PDF。
- `report_manifest.csv`：报告公司、年份、PDF 文件名及巨潮资讯来源链接。
- `extract_pdfs.py`：基础 PDF 文字提取，输出 `pages.jsonl`。
- `extract_tables.py`：表格提取检查脚本，输出 `tables.jsonl`。
- `extract_layout_all.py`：按页面布局提取年报，保留表格结构，输出 `layout_pages.jsonl`。
- `build_chunks.py`：按章节和页面切块，输出 `chunks.jsonl`。
- `build_index.py`：建立 TF-IDF + BM25 混合索引。
- `app.py`：Streamlit 问答页面，使用 DeepSeek 生成带出处的回答。
- `evaluation_log.md`：10 道题的评测记录，包括两道跨公司全景题及失败案例。

PDF、提取结果、索引、虚拟环境和 `.env` 不提交到代码仓库。`.gitignore` 已配置相应忽略规则。

## 安装与配置

在 Windows PowerShell 中进入项目目录，然后运行：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

在 `.env` 中填写自己的 DeepSeek API key：

```env
DEEPSEEK_API_KEY=在这里填写自己的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

`.env` 只保存在本地，不要提交到 GitHub，也不要把 key 发到聊天中。

## 下载年报与建立知识库

报告清单中的链接指向巨潮资讯。运行以下命令下载 PDF 到 `data/raw/`：

```powershell
.\.venv\Scripts\python.exe .\download_reports.py
```

生成布局分析结果、检索块和索引：

```powershell
.\.venv\Scripts\python.exe .\extract_layout_all.py
.\.venv\Scripts\python.exe .\build_chunks.py
.\.venv\Scripts\python.exe .\build_index.py
```

`extract_pdfs.py` 和 `extract_tables.py` 用于基础文字/表格提取与检查；最终问答索引使用布局提取生成的 `layout_pages.jsonl`。

## 启动问答页面

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\app.py
```

浏览器打开 Streamlit 显示的本地地址（通常为 `http://localhost:8501`）。明确提到单家公司的问题会自动筛选该公司；跨公司全景问题保留全部公司检索。每次提问都会调用 DeepSeek API，可能产生用量费用。

## 评测与已知局限

评测问题、召回来源、回答结果和错误原因见 [`evaluation_log.md`](evaluation_log.md)。单家公司且指标明确的问题表现较好。跨公司全景题存在召回覆盖不足；风险类问题可能召回到相邻章节；母公司与合并报表口径也可能混淆。因此结论应以召回原文和对应页码为准，证据不足时应记录为未能回答。