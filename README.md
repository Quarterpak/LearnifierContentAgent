# LearnifierContentAgent

## Commands

### Windows

-   Create Virtual Environment
    python -m venv venv

-   Activate Virtual Environment
    .\venv\Scripts\Activate.ps1

-   Deactivate Virtual Environment
    deactivate

-   Install Packages
    pip install -r requirements.txt

-   Start API
    uvicorn main:app --reload

-   Delete old chroma DB folder
    Remove-Item -Recurse -Force .\chroma_store

### Macintosh

-   Activate virtual environment
    source venv/bin/activate

-   Start API
    uvicorn main:app --reload

-   Delete old chroma DB folder
    Mac:
    rm -rf chroma_store

## Ingest blogs

python rag/ingest.py

## Docker

-   build the image
    docker build -t learnifier-agent:latest .

-   run it, load env vars, and expose port
    docker run --rm -p 8080:8080 --env-file .env learnifier-agent:latest
