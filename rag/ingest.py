# ingest.py
import os, re, glob, hashlib
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from langdetect import detect

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma_store")
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

def make_id(tenant_id: str, source: str, idx: int) -> str:
    """Stable, short IDs with tenant prefix; avoids duplicate-id errors."""
    h = hashlib.md5(f"{tenant_id}-{source}-{idx}".encode("utf-8")).hexdigest()[:12]
    return f"{tenant_id}-{h}-{idx}"

def extract_tenant_from_path(file_path: str, base_data_dir: str = "data") -> Optional[str]:
    """
    Extract tenant ID from file path structure: data/tenantName/language/file.md
    Returns the tenant name (folder directly under 'data')
    """
    path = Path(file_path)
    parts = path.parts
    
    try:
        # Find the index of the base_data_dir in the path
        data_idx = parts.index(base_data_dir)
        # The next part should be the tenant name
        if data_idx + 1 < len(parts):
            return parts[data_idx + 1]
    except (ValueError, IndexError):
        pass
    
    return None

def ingest(tenant_id: Optional[str] = None):
    """
    Ingest files with tenant isolation.
    
    If tenant_id is provided, only ingest that tenant's data.
    Otherwise, ingest all tenants found in the data directory.
    """
    base_data_dir = "data"
    
    if tenant_id:
        # Ingest specific tenant
        tenants_to_process = [tenant_id]
    else:
        # Auto-discover all tenants from data/ directory structure
        if not os.path.exists(base_data_dir):
            print(f"⚠️ Base data directory not found: {base_data_dir}")
            return
        
        tenants_to_process = [
            d for d in os.listdir(base_data_dir)
            if os.path.isdir(os.path.join(base_data_dir, d))
        ]
    
    print(f"🏢 Tenants to process: {tenants_to_process}")
    
    for tenant in tenants_to_process:
        tenant_path = os.path.join(base_data_dir, tenant)
        
        if not os.path.exists(tenant_path):
            print(f"⚠️ Tenant directory not found: {tenant_path}")
            continue
        
        print(f"\n{'='*60}")
        print(f"📁 Processing tenant: {tenant}")
        print(f"{'='*60}")
        
        # Find all markdown files in tenant directory (including subdirectories)
        all_files = glob.glob(os.path.join(tenant_path, "**/*.md"), recursive=True)
        
        print(f"📄 Found {len(all_files)} markdown files for tenant '{tenant}'")
        
        for file in all_files:
            with open(file, "r", encoding="utf-8") as f:
                text = f.read()

            chunks = chunk_text(text)
            m = re.search(r"source:\s*(\S+)", text)
            source_url = m.group(1) if m else file
            ctype = detect_content_type(source_url)
            langs = [safe_detect_language(c) for c in chunks]
            
            # Generate tenant-specific IDs
            ids = [make_id(tenant, source_url, i) for i in range(len(chunks))]

            vectors = embed_batch(chunks)

            # Upsert: remove existing IDs before add (Chroma errors on dup IDs)
            try:
                collection.delete(ids=ids)
            except Exception:
                pass

            # Add tenant_id to metadata for filtering
            collection.add(
                documents=chunks,
                embeddings=vectors,
                metadatas=[{
                    "tenant_id": tenant,  # KEY: Add tenant ID to metadata
                    "source": source_url,
                    "chunk": i,
                    "language": langs[i],
                    "content_type": ctype
                } for i in range(len(chunks))],
                ids=ids,
            )
            print(f"✅ Ingested {len(chunks)} chunks from {file} ({ctype}) for tenant '{tenant}'")
        
        print(f"🎉 Completed ingestion for tenant '{tenant}': {len(all_files)} files processed")

def delete_tenant_data(tenant_id: str):
    """Delete all data for a specific tenant."""
    try:
        # Query all documents for this tenant
        result = collection.get(
            where={"tenant_id": tenant_id},
            include=["metadatas"]
        )
        
        ids_to_delete = result.get("ids", [])
        
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            print(f"🗑️ Deleted {len(ids_to_delete)} chunks for tenant '{tenant_id}'")
        else:
            print(f"ℹ️ No data found for tenant '{tenant_id}'")
            
    except Exception as e:
        print(f"❌ Error deleting tenant data: {e}")

if __name__ == "__main__":
    import sys
    
    print(f"Using CHROMA_PATH={CHROMA_PATH}, collection={COLLECTION_NAME}")
    
    # Support command-line arguments for specific tenant ingestion
    # Usage: python ingest.py [tenant_id]
    # Or: python ingest.py --delete tenant_id
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--delete" and len(sys.argv) > 2:
            delete_tenant_data(sys.argv[2])
        else:
            ingest(tenant_id=sys.argv[1])
    else:
        # Ingest all tenants
        ingest()