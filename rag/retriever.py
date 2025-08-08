import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma_client = chromadb.PersistentClient(path="chroma_store")
collection = chroma_client.get_collection("learnifier_blogs")

def embed(text: str) -> list[float]:
    """Create an OpenAI embedding for a given text"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def retrieve_context(query: str, language: str = "en", n_results=3) -> str:
    """Fetch relevant past blog content to use as context"""
    query_embedding = embed(query)  # 🔹 embed with OpenAI

    results = collection.query(
        query_embeddings=[query_embedding],  # 🔹 pass embedding, not text
        n_results=n_results,
        where={"language": language}  # 🔹 filter by language
    )

    docs = results.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else ""
