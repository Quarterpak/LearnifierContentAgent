# LearnifierContentAgent

## Commands

- Start API
  uvicorn main:app --reload

- Delete old chroma DB folder
  Remove-Item -Recurse -Force .\chroma_store

- Ingest blogs
  python rag/ingest.py
