import os
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


# --- Ingest all Markdown files ---
def ingest():
    blog_dir = "data/blogs"  # adjust if your blogs live elsewhere
    files = glob.glob(os.path.join(blog_dir, "*.md"))
    print(f"📂 Looking for markdown files in: {os.path.abspath(blog_dir)}")
    print(f"📄 Found {len(files)} files: {files}")

    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            embedding = embed(chunk)
            lang = detect_language(chunk)

            collection.add(
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{"source": file, "chunk": i, "language": lang}],
                ids=[f"{os.path.basename(file)}-{i}"]
            )

        print(f"✅ Ingested {len(chunks)} chunks from {file}")


if __name__ == "__main__":
    ingest()
