# Tenant Setup & Management Guide

## Quick Start: Setting Up Your First Tenant

### Step 1: Create Directory Structure
```bash
mkdir -p data/learnifier/sv
mkdir -p data/learnifier/en
```

### Step 2: Add Your Content
```bash
# Move your existing files
mv data/learnifier_blog_posts_sv/*.md data/learnifier/sv/

# Or add new files
cp my_blog_posts/*.md data/learnifier/sv/
```

### Step 3: Register the Tenant
```bash
# Option A: Using CLI
python tenant_manager.py register learnifier "Learnifier AB" "api_key_abc123" "contact@learnifier.com"

# Option B: Auto-discover and register
python tenant_manager.py sync --auto-register
```

### Step 4: Verify Registration
```bash
# List all tenants
python tenant_manager.py list

# Check specific tenant
python tenant_manager.py get learnifier
```

### Step 5: Ingest Data
```bash
# Ingest this tenant's data
python ingest.py learnifier
```

## Managing Multiple Tenants

### Adding a Second Tenant

```bash
# 1. Create folders
mkdir -p data/company2/en
mkdir -p data/company2/sv

# 2. Add content
cp /path/to/company2/content/*.md data/company2/en/

# 3. Register
python tenant_manager.py register company2 "Company 2 Inc" "api_key_xyz789" "admin@company2.com"

# 4. Ingest
python ingest.py company2
```

### Tenant Registry File (tenants.json)

After registration, a `tenants.json` file is created:

```json
{
  "learnifier": {
    "tenant_id": "learnifier",
    "name": "Learnifier AB",
    "api_key": "api_key_abc123",
    "email": "contact@learnifier.com",
    "metadata": {},
    "status": "active"
  },
  "company2": {
    "tenant_id": "company2",
    "name": "Company 2 Inc",
    "api_key": "api_key_xyz789",
    "email": "admin@company2.com",
    "metadata": {},
    "status": "active"
  }
}
```

**💡 Store this file safely!** This is your source of truth for tenant IDs and API keys.

## Common Workflows

### Check What's in the Filesystem vs Registry

```bash
python tenant_manager.py sync
```

Output:
```
============================================================
TENANT SYNC REPORT
============================================================

⚠️  Found 1 unregistered tenant(s):
   - new_company

✅ All registered tenants have data folders
============================================================
```

### Auto-Register All Discovered Tenants

```bash
python tenant_manager.py sync --auto-register
```

This will:
1. Find all folders in `data/`
2. Check which ones aren't registered
3. Automatically register them with default settings

### View Tenant Statistics

```bash
# Via CLI (requires running the API)
curl "http://localhost:8000/admin/tenant/learnifier/stats" \
  -H "x-api-key: YOUR_SERVICE_API_KEY"
```

Response:
```json
{
  "tenant_id": "learnifier",
  "total_chunks": 450,
  "languages": {
    "sv": 300,
    "en": 150
  },
  "content_types": {
    "blog": 400,
    "site": 50
  }
}
```

## API Usage with Tenant IDs

### Generate Content for a Tenant

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_SERVICE_API_KEY" \
  -d '{
    "tenant_id": "learnifier",
    "topic": "Digital Learning Trends",
    "keywords": ["lms", "elearning", "digital transformation"],
    "language": "sv",
    "word_count": 800
  }'
```

### Search Within Tenant's Content

```bash
curl "http://localhost:8000/search?query=learning&tenant_id=learnifier&language=sv" \
  -H "x-api-key: YOUR_SERVICE_API_KEY"
```

### List All Tenants

```bash
curl "http://localhost:8000/admin/tenants" \
  -H "x-api-key: YOUR_SERVICE_API_KEY"
```

## Best Practices

### 1. Tenant ID Naming Convention

Use lowercase, URL-safe identifiers:
- ✅ `learnifier`, `company-two`, `acme_corp`
- ❌ `Learnifier Inc.`, `company #2`, `Acme Corp!`

### 2. Folder Structure

Keep it consistent:
```
data/
├── {tenant_id}/
│   ├── en/          # English content
│   ├── sv/          # Swedish content
│   └── no/          # Norwegian, etc.
```

### 3. API Key Management

- Generate unique API keys per tenant
- Store them securely (environment variables, secrets manager)
- Consider using the tenant's API key as their authentication method

### 4. Backup tenants.json

```bash
# Backup before changes
cp tenants.json tenants.backup.json

# Version control
git add tenants.json
git commit -m "Add new tenant: company2"
```

## Troubleshooting

### "Tenant not found" Error

```bash
# Check if tenant exists
python tenant_manager.py get my_tenant

# If not, register it
python tenant_manager.py register my_tenant "My Tenant Name"
```

### Data Folder Exists but Tenant Not Registered

```bash
# Auto-sync will find it
python tenant_manager.py sync --auto-register
```

### Re-ingesting After Content Updates

```bash
# Just run ingest again (it will update existing chunks)
python ingest.py learnifier
```

### Removing a Tenant Completely

```bash
# 1. Delete from ChromaDB
curl -X DELETE "http://localhost:8000/admin/tenant/old_company" \
  -H "x-api-key: YOUR_API_KEY"

# 2. Remove from registry
python tenant_manager.py delete old_company

# 3. Optionally remove data folder
rm -rf data/old_company
```

## Integration with Your Frontend

### Store Tenant ID on User Login

```javascript
// When user logs in, store their tenant_id
const user = await login(email, password);
localStorage.setItem('tenant_id', user.tenant_id);
```

### Include in All API Calls

```javascript
async function generateContent(topic, keywords) {
  const tenantId = localStorage.getItem('tenant_id');
  
  const response = await fetch('/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY
    },
    body: JSON.stringify({
      tenant_id: tenantId,  // Include in every request
      topic,
      keywords,
      language: 'sv'
    })
  });
  
  return response.json();
}
```

## Security Considerations

1. **Never expose tenant_ids publicly** - treat them as semi-sensitive
2. **Validate tenant_id on backend** - ensure user has access to that tenant
3. **Use separate API keys per tenant** for better access control
4. **Audit log tenant access** - track who accessed what tenant's data

## Summary

Your tenant IDs come from the **folder names** in your `data/` directory:
- `data/learnifier/` → tenant_id: `learnifier`
- `data/company2/` → tenant_id: `company2`

Store these in `tenants.json` using the tenant_manager, and always include `tenant_id` in your API requests for complete data isolation! 🎯
