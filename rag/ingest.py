import os
import re
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
import glob
from langdetect import detect

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma_client = chromadb.PersistentClient(path="chroma_store")
collection = chroma_client.get_or_create_collection("learnifier_blogs")

def detect_language(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

def detect_content_type(source: str) -> str:
    """
    Very simple content type detector based on URL or file path.
    """
    s = source.lower()
    if "/blog" in s:
        return "blog"
    elif "/customer" in s or "customer-story" in s:
        return "customer_story"
    elif "/event" in s or "/events" in s:
        return "event"
    elif "/guide" in s:
        return "guide"
    else:
        return "site"

# --- Embedding helper ---
def embed(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# --- Simple chunking function ---
def chunk_text(text: str, max_tokens: int = 500) -> list[str]:
    """
    Splits text into chunks of ~500 tokens (roughly 350-500 words).
    """
    words = text.split()
    chunks, current = [], []

    for word in words:
        current.append(word)
        if len(current) >= max_tokens:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks

# --- Ingest all Markdown files from multiple folders ---
def ingest():
    folders = ["data/site/en", "data/site/sv", "data/blogs"]  # add more if needed
    all_files = []

    for folder in folders:
        folder_path = os.path.abspath(folder)
        if os.path.exists(folder_path):
            md_files = glob.glob(os.path.join(folder_path, "*.md"))
            all_files.extend(md_files)
            print(f"📂 Found {len(md_files)} markdown files in {folder_path}")
        else:
            print(f"⚠️ Folder not found: {folder_path}")

    print(f"📄 Total files to ingest: {len(all_files)}")

    for file in all_files:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)

        # Try to read URL from metadata in file (first few lines starting with 'source:')
        match = re.search(r"source:\s*(\S+)", text)
        source_url = match.group(1) if match else file
        content_type = detect_content_type(source_url)

        for i, chunk in enumerate(chunks):
            embedding = embed(chunk)
            lang = detect_language(chunk)

            collection.add(
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{
                    "source": source_url,
                    "chunk": i,
                    "language": lang,
                    "content_type": content_type
                }],
                ids=[f"{os.path.basename(file)}-{i}"]
            )

        print(f"✅ Ingested {len(chunks)} chunks from {file} ({content_type})")

if __name__ == "__main__":
    ingest()
