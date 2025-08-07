# LearnifierContentAgent

## Commands

- Start API
  uvicorn main:app --reload

- Delete old chroma DB folder
  Mac:
  rm -rf chroma_store

  Windows:
  Remove-Item -Recurse -Force .\chroma_store

- Ingest blogs
  python rag/ingest.py
