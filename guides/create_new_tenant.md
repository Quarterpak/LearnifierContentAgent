# Create new tenant

## 1. Create folder structure

mkdir -p data/newcompany/sv
mkdir -p data/newcompany/en

## 2. Add the markdown files

cp /path/to/your/files/*.md data/newcompany/sv/

## 3. Register the tenant

python tenant_manager.py register newcompany "New Company AB" "" "contact@newcompany.com" "NewCo"

## 4. Ingest the data

python ingest.py newcompany

