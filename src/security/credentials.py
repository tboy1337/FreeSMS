"""
Secure credentials management - Provides utilities for secure storage of API keys
"""
import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional

# For simplicity, we're using base64 encoding in this example
# In a production app, use proper encryption with a secure key like keyring/cryptography

class CredentialsManager:
    """Manages secure storage and retrieval of API credentials"""
    
    def __init__(self):
        """Initialize the credentials manager"""
        # Create secure storage directory
        self.creds_dir = Path.home() / '.sms_sender' / 'credentials'
        self.creds_dir.mkdir(parents=True, exist_ok=True)
        
        # Secure the directory permissions (on Unix-like systems)
        try:
            os.chmod(str(self.creds_dir), 0o700)  # Only owner can access
        except:
            pass  # May fail on Windows, which is fine
    
    def save_credentials(self, service_name: str, credentials: Dict[str, Any]) -> bool:
        """Securely save credentials for a service"""
        try:
            # Convert credentials to JSON
            if isinstance(credentials, dict):
                creds_json = json.dumps(credentials)
            else:
                creds_json = str(credentials)
                
            # Encode credentials (in production, encrypt this)
            encoded = base64.b64encode(creds_json.encode()).decode()
            
            # Save to file
            creds_file = self.creds_dir / f"{service_name.lower()}.creds"
            with open(creds_file, 'w') as f:
                f.write(encoded)
                
            # Secure file permissions (on Unix-like systems)
            try:
                os.chmod(str(creds_file), 0o600)  # Only owner can read/write
            except:
                pass
                
            return True
            
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False
    
    def load_credentials(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Securely load credentials for a service"""
        try:
            # Get credentials file
            creds_file = self.creds_dir / f"{service_name.lower()}.creds"
            if not creds_file.exists():
                return None
                
            # Read and decode credentials
            with open(creds_file, 'r') as f:
                encoded = f.read().strip()
                
            # Decode (in production, decrypt this)
            creds_json = base64.b64decode(encoded.encode()).decode()
            
            # Parse JSON
            return json.loads(creds_json)
            
        except json.JSONDecodeError:
            # If not valid JSON, return as string
            return {'raw': creds_json}
            
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def delete_credentials(self, service_name: str) -> bool:
        """Delete credentials for a service"""
        try:
            creds_file = self.creds_dir / f"{service_name.lower()}.creds"
            if creds_file.exists():
                os.remove(str(creds_file))
            return True
            
        except Exception as e:
            print(f"Error deleting credentials: {e}")
            return False
    
    def list_services(self) -> list:
        """List all services with saved credentials"""
        services = []
        for file in self.creds_dir.glob('*.creds'):
            services.append(file.stem)
        return services 