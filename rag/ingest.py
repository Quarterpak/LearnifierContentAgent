import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma_client = chromadb.PersistentClient(path="chroma_store")
collection = chroma_client.get_or_create_collection("learnifier_blogs")

def embed_text(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def ingest_blogs(folder="data/blogs"):
    for filename in os.listdir(folder):
        if filename.endswith(".txt") or filename.endswith(".md"):
            path = os.path.join(folder, filename)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            embedding = embed_text(text)

            collection.add(
                documents=[text],
                embeddings=[embedding],
                ids=[filename]
            )
            print(f"✅ Ingested {filename}")

if __name__ == "__main__":
    ingest_blogs()
    print("🎉 All blog posts ingested into ChromaDB")
