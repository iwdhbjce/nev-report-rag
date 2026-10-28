import json
import re
from pathlib import Path

import jieba
import joblib
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer


def tokenize(text):
    """清理少量 Markdown 符号后，对中文文本分词。"""
    text = re.sub(r"<br\s*/?>", " ", str(text), flags=re.IGNORECASE)
    text = re.sub(r"[|#*_`]+", " ", text)

    return [
        word.strip().lower()
        for word in jieba.lcut(text)
        if word.strip() and re.search(r"[\u4e00-\u9fffA-Za-z0-9]", word)
    ]


project_dir = Path(__file__).resolve().parent
chunks_path = project_dir / "data" / "extracted" / "chunks.jsonl"
index_dir = project_dir / "data" / "index"
index_path = index_dir / "hybrid_index.joblib"

if not chunks_path.exists():
    raise FileNotFoundError(f"找不到切块文件：{chunks_path}")

documents = []
with chunks_path.open("r", encoding="utf-8") as file:
    for line in file:
        record = json.loads(line)
        if str(record.get("text", "")).strip():
            documents.append(record)

if not documents:
    raise ValueError("切块文件里没有可检索的文本。")

print(f"读取完成：{len(documents)} 个检索块")
print("正在中文分词并准备 BM25 索引……")

tokenized_documents = []
for number, document in enumerate(documents, start=1):
    tokenized_documents.append(tokenize(document["text"]))
    if number % 500 == 0:
        print(f"分词进度：{number}/{len(documents)}")

bm25_index = BM25Okapi(tokenized_documents)

print("正在建立 TF-IDF 向量索引……")
vectorizer = TfidfVectorizer(
    tokenizer=tokenize,
    token_pattern=None,
    lowercase=False,
    sublinear_tf=True,
    max_features=200000,
    dtype=np.float32,
)
tfidf_matrix = vectorizer.fit_transform(
    [document["text"] for document in documents]
)

index_dir.mkdir(parents=True, exist_ok=True)
joblib.dump(
    {
        "documents": documents,
        "bm25": bm25_index,
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
    },
    index_path,
    compress=3,
)

print(f"索引建立完成：{len(documents)} 个检索块")
print(f"向量词条数：{len(vectorizer.get_feature_names_out())}")
print(f"索引文件：{index_path}")