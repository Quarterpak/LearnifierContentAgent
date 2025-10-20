# tenant_manager.py
import os
import json
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TENANT_REGISTRY_PATH = os.getenv("TENANT_REGISTRY_PATH", "tenants.json")

class TenantManager:
    """Manages tenant information and registry."""
    
    def __init__(self, registry_path: str = TENANT_REGISTRY_PATH):
        self.registry_path = registry_path
        self.tenants = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load tenant registry from JSON file."""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_registry(self):
        """Save tenant registry to JSON file."""
        with open(self.registry_path, 'w') as f:
            json.dump(self.tenants, f, indent=2)
        print(f"✅ Registry saved to {self.registry_path}")
    
    def register_tenant(
        self,
        tenant_id: str,
        name: str,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Register a new tenant or update existing one.
        
        Args:
            tenant_id: Unique identifier (matches folder name in data/)
            name: Display name of the tenant
            api_key: Optional API key for this tenant
            email: Contact email
            metadata: Any additional metadata
        
        Returns:
            The tenant record
        """
        if tenant_id in self.tenants:
            print(f"⚠️  Tenant '{tenant_id}' already exists. Updating...")
        
        tenant_record = {
            "tenant_id": tenant_id,
            "name": name,
            "api_key": api_key,
            "email": email,
            "metadata": metadata or {},
            "status": "active"
        }
        
        self.tenants[tenant_id] = tenant_record
        self._save_registry()
        
        print(f"✅ Registered tenant: {tenant_id} ({name})")
        return tenant_record
    
    def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """Get tenant information by ID."""
        return self.tenants.get(tenant_id)
    
    def get_tenant_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Find tenant by their API key."""
        for tenant_id, tenant in self.tenants.items():
            if tenant.get("api_key") == api_key:
                return tenant
        return None
    
    def list_tenants(self) -> List[Dict]:
        """List all registered tenants."""
        return list(self.tenants.values())
    
    def list_tenant_ids(self) -> List[str]:
        """List all tenant IDs."""
        return list(self.tenants.keys())
    
    def deactivate_tenant(self, tenant_id: str):
        """Mark a tenant as inactive (soft delete)."""
        if tenant_id in self.tenants:
            self.tenants[tenant_id]["status"] = "inactive"
            self._save_registry()
            print(f"🔒 Tenant '{tenant_id}' deactivated")
        else:
            print(f"⚠️  Tenant '{tenant_id}' not found")
    
    def delete_tenant(self, tenant_id: str):
        """Remove tenant from registry (hard delete)."""
        if tenant_id in self.tenants:
            del self.tenants[tenant_id]
            self._save_registry()
            print(f"🗑️  Tenant '{tenant_id}' deleted from registry")
        else:
            print(f"⚠️  Tenant '{tenant_id}' not found")
    
    def auto_discover_tenants(self, base_data_dir: str = "data") -> List[str]:
        """
        Auto-discover tenants from data directory structure.
        Returns list of folder names found.
        """
        if not os.path.exists(base_data_dir):
            print(f"⚠️  Base data directory not found: {base_data_dir}")
            return []
        
        discovered = [
            d for d in os.listdir(base_data_dir)
            if os.path.isdir(os.path.join(base_data_dir, d))
        ]
        
        print(f"📁 Discovered {len(discovered)} tenant folders: {discovered}")
        return discovered
    
    def sync_with_filesystem(self, base_data_dir: str = "data", auto_register: bool = False):
        """
        Compare registry with filesystem and report differences.
        
        Args:
            base_data_dir: Base directory containing tenant folders
            auto_register: If True, automatically register new tenants found
        """
        discovered = self.auto_discover_tenants(base_data_dir)
        registered = set(self.list_tenant_ids())
        discovered_set = set(discovered)
        
        # Tenants in filesystem but not registered
        unregistered = discovered_set - registered
        # Tenants registered but not in filesystem
        orphaned = registered - discovered_set
        
        print("\n" + "="*60)
        print("TENANT SYNC REPORT")
        print("="*60)
        
        if unregistered:
            print(f"\n⚠️  Found {len(unregistered)} unregistered tenant(s):")
            for tenant_id in unregistered:
                print(f"   - {tenant_id}")
                if auto_register:
                    self.register_tenant(
                        tenant_id=tenant_id,
                        name=tenant_id.replace("_", " ").title(),
                        metadata={"auto_discovered": True}
                    )
        else:
            print("\n✅ All filesystem tenants are registered")
        
        if orphaned:
            print(f"\n⚠️  Found {len(orphaned)} orphaned tenant(s) (registered but no data folder):")
            for tenant_id in orphaned:
                print(f"   - {tenant_id}")
        else:
            print("✅ All registered tenants have data folders")
        
        print("="*60 + "\n")
        
        return {
            "unregistered": list(unregistered),
            "orphaned": list(orphaned),
            "synced": list(discovered_set & registered)
        }


# CLI interface
if __name__ == "__main__":
    import sys
    
    manager = TenantManager()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tenant_manager.py list")
        print("  python tenant_manager.py register <tenant_id> <name> [api_key] [email]")
        print("  python tenant_manager.py get <tenant_id>")
        print("  python tenant_manager.py discover")
        print("  python tenant_manager.py sync [--auto-register]")
        print("  python tenant_manager.py deactivate <tenant_id>")
        print("  python tenant_manager.py delete <tenant_id>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        tenants = manager.list_tenants()
        print(f"\n📋 Registered Tenants ({len(tenants)}):\n")
        for tenant in tenants:
            status_icon = "✅" if tenant.get("status") == "active" else "🔒"
            print(f"{status_icon} {tenant['tenant_id']}")
            print(f"   Name: {tenant.get('name', 'N/A')}")
            print(f"   Email: {tenant.get('email', 'N/A')}")
            print(f"   API Key: {'***' + tenant['api_key'][-4:] if tenant.get('api_key') else 'N/A'}")
            print()
    
    elif command == "register":
        if len(sys.argv) < 4:
            print("Usage: python tenant_manager.py register <tenant_id> <name> [api_key] [email]")
            sys.exit(1)
        
        tenant_id = sys.argv[2]
        name = sys.argv[3]
        api_key = sys.argv[4] if len(sys.argv) > 4 else None
        email = sys.argv[5] if len(sys.argv) > 5 else None
        
        manager.register_tenant(tenant_id, name, api_key, email)
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: python tenant_manager.py get <tenant_id>")
            sys.exit(1)
        
        tenant_id = sys.argv[2]
        tenant = manager.get_tenant(tenant_id)
        
        if tenant:
            print(f"\n📄 Tenant Information:\n")
            print(json.dumps(tenant, indent=2))
        else:
            print(f"❌ Tenant '{tenant_id}' not found")
    
    elif command == "discover":
        manager.auto_discover_tenants()
    
    elif command == "sync":
        auto_register = "--auto-register" in sys.argv
        manager.sync_with_filesystem(auto_register=auto_register)
    
    elif command == "deactivate":
        if len(sys.argv) < 3:
            print("Usage: python tenant_manager.py deactivate <tenant_id>")
            sys.exit(1)
        
        manager.deactivate_tenant(sys.argv[2])
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python tenant_manager.py delete <tenant_id>")
            sys.exit(1)
        
        manager.delete_tenant(sys.argv[2])
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)