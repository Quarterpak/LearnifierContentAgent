import chromadb

chroma_client = chromadb.PersistentClient(path="chroma_store")
collection = chroma_client.get_collection("learnifier_blogs")

def retrieve_context(query: str, n_results=3) -> str:
    """Fetch relevant past blog content to use as context"""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    docs = results.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else ""
