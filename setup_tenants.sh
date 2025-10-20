#!/bin/bash
# setup_tenants.sh - Quick setup script for multi-tenant RAG system

set -e  # Exit on error

echo "🚀 Multi-Tenant RAG Setup Script"
echo "================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8+."
    exit 1
fi

print_success "Python 3 found"

# Step 1: Migrate existing data structure (if needed)
echo ""
echo "Step 1: Checking data structure..."
echo "-----------------------------------"

if [ -d "data/learnifier_blog_posts_sv" ]; then
    print_warning "Old data structure detected: data/learnifier_blog_posts_sv/"
    read -p "Do you want to migrate to new structure? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating new structure..."
        mkdir -p data/learnifier/sv
        
        if [ "$(ls -A data/learnifier_blog_posts_sv)" ]; then
            echo "Moving files..."
            mv data/learnifier_blog_posts_sv/*.md data/learnifier/sv/ 2>/dev/null || true
            print_success "Files moved to data/learnifier/sv/"
        fi
        
        # Optionally remove old directory
        read -p "Remove old directory? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf data/learnifier_blog_posts_sv
            print_success "Old directory removed"
        fi
    fi
else
    print_success "Data structure looks good or starting fresh"
fi

# Step 2: Discover tenants
echo ""
echo "Step 2: Discovering tenants..."
echo "-----------------------------------"

if [ ! -d "data" ]; then
    mkdir -p data
    print_warning "Created data/ directory. Please add your tenant folders."
    exit 0
fi

# Count tenant folders
tenant_count=$(find data -mindepth 1 -maxdepth 1 -type d | wc -l)

if [ "$tenant_count" -eq 0 ]; then
    print_warning "No tenant folders found in data/"
    echo "Please create folders like: data/your_company_name/{en,sv}/"
    exit 0
fi

print_success "Found $tenant_count potential tenant folder(s)"
ls -1 data/

# Step 3: Sync and register tenants
echo ""
echo "Step 3: Registering tenants..."
echo "-----------------------------------"

read -p "Auto-register all discovered tenants? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 tenant_manager.py sync --auto-register
    print_success "Tenants registered"
else
    print_warning "Please register tenants manually using:"
    echo "python3 tenant_manager.py register <tenant_id> <n>"
fi

# Step 4: List registered tenants
echo ""
echo "Step 4: Registered Tenants"
echo "-----------------------------------"
python3 tenant_manager.py list

# Step 5: Ingest data
echo ""
echo "Step 5: Ingesting data..."
echo "-----------------------------------"

read -p "Ingest data for all tenants? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 ingest.py
    print_success "Data ingestion complete"
else
    print_warning "You can ingest data later using:"
    echo "python3 ingest.py <tenant_id>"
fi

# Step 6: Summary
echo ""
echo "================================================"
echo "🎉 Setup Complete!"
echo "================================================"
echo ""
echo "📋 What's next:"
echo ""
echo "1. View your registered tenants:"
echo "   python3 tenant_manager.py list"
echo ""
echo "2. Check tenant statistics (with API running):"
echo "   curl 'http://localhost:8000/admin/tenant/<tenant_id>/stats' \\"
echo "     -H 'x-api-key: YOUR_API_KEY'"
echo ""
echo "3. Generate content:"
echo "   curl -X POST 'http://localhost:8000/generate' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -H 'x-api-key: YOUR_API_KEY' \\"
echo "     -d '{\"tenant_id\": \"<your_tenant>\", \"topic\": \"...\", ...}'"
echo ""
echo "4. Your tenant registry is stored in: tenants.json"
echo "   ⚠️  Keep this file safe and backed up!"
echo ""
echo "================================================"