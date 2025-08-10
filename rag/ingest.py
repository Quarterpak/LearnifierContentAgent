# ingest.py
import os, re, glob, hashlib
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from langdetect import detect

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma_store")  # /tmp is writable on Cloud Run
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "learnifier")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

def safe_detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"

def detect_content_type(source: str) -> str:
    s = source.lower()
    if "/blog" in s: return "blog"
    if "/customer" in s or "customer-story" in s: return "customer_story"
    if "/event" in s or "/events" in s: return "event"
    if "/guide" in s: return "guide"
    return "site"

def embed_batch(texts: List[str]) -> List[List[float]]:
    """Batch embedding for speed."""
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in resp.data]

def chunk_text(text: str, max_words: int = 500) -> List[str]:
    """Heuristic ~500-word chunks (good enough without tiktoken)."""
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)] or [""]

def make_id(source: str, idx: int) -> str:
    """Stable, short IDs; avoids duplicate-id errors."""
    h = hashlib.md5(f"{source}-{idx}".encode("utf-8")).hexdigest()[:12]
    return f"{h}-{idx}"

def ingest():
    folders_env = os.getenv("INGEST_FOLDERS")
    folders = [p.strip() for p in folders_env.split(",")] if folders_env else ["data/site/en", "data/site/sv", "data/blogs"]

    all_files: List[str] = []
    for folder in folders:
        folder_path = os.path.abspath(folder)
        if os.path.exists(folder_path):
            files = glob.glob(os.path.join(folder_path, "*.md"))
            all_files.extend(files)
            print(f"📂 Found {len(files)} markdown files in {folder_path}")
        else:
            print(f"⚠️ Folder not found: {folder_path}")

    print(f"📄 Total files to ingest: {len(all_files)}")
    for file in all_files:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)
        m = re.search(r"source:\s*(\S+)", text)
        source_url = m.group(1) if m else file
        ctype = detect_content_type(source_url)
        langs = [safe_detect_language(c) for c in chunks]
        ids = [make_id(source_url, i) for i in range(len(chunks))]

        vectors = embed_batch(chunks)

        # Upsert: remove existing IDs before add (Chroma errors on dup IDs)
        try:
            collection.delete(ids=ids)
        except Exception:
            pass

        collection.add(
            documents=chunks,
            embeddings=vectors,
            metadatas=[{
                "source": source_url,
                "chunk": i,
                "language": langs[i],
                "content_type": ctype
            } for i in range(len(chunks))],
            ids=ids,
        )
        print(f"✅ Ingested {len(chunks)} chunks from {file} ({ctype})")

if __name__ == "__main__":
    print(f"Using CHROMA_PATH={CHROMA_PATH}, collection={COLLECTION_NAME}")
    ingest()
