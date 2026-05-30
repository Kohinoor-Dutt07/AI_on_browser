"""
Secure Credential Manager - Handles encrypted website credentials
"""
import os
import base64
from typing import Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureCredentialManager:
    """Manages website credentials with encryption"""

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the secure credential manager.

        Args:
            master_key: Master encryption key. If None, tries to get from env var SECURE_CREDENTIALS_KEY
        """
        if master_key is None:
            master_key = os.getenv("SECURE_CREDENTIALS_KEY")

        if master_key is None:
            # Generate a key if none exists (for first-time use)
            # In production, this should be set via environment variable
            master_key = self._generate_key()
            print(f"WARNING: No SECURE_CREDENTIALS_KEY found. Generated key: {master_key}")
            print("Please set SECURE_CREDENTIALS_KEY environment variable for production use.")

        self.cipher = self._create_cipher(master_key)

    def _generate_key(self) -> str:
        """Generate a random encryption key"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def _create_cipher(self, key: str) -> Fernet:
        """Create a Fernet cipher from the key"""
        # Ensure key is 32 bytes and URL-safe base64 encoded
        key_bytes = key.encode()
        if len(key_bytes) != 32:
            # Use PBKDF2 to derive a proper key if needed
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'ai_browser_agent_salt',  # In production, use random salt stored separately
                iterations=100000,
            )
            key_bytes = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        return Fernet(key_bytes)

    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64 encoded result"""
        encrypted_bytes = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded encrypted data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt credential: {e}")

    def get_credential(self, site: str) -> Optional[Dict[str, str]]:
        """
        Get decrypted credentials for a site from environment variables.
        Format in .env: CREDENTIALS_SITENAME=encrypted_username|encrypted_password

        Example:
            CREDENTIALS_LINKEDIN=gAAAAAB...|gAAAAAB...
        """
        env_key = f"CREDENTIALS_{site.upper().replace('.', '_').replace('-', '_')}"
        encrypted_credentials = os.getenv(env_key)

        if not encrypted_credentials:
            return None

        # Parse encrypted_username|encrypted_password format
        parts = encrypted_credentials.split("|")
        if len(parts) != 2:
            return None

        try:
            username = self.decrypt(parts[0].strip())
            password = self.decrypt(parts[1].strip())
            return {
                "username": username,
                "password": password
            }
        except Exception:
            return None

    def set_credential(self, site: str, username: str, password: str):
        """
        Programmatically set encrypted credentials (for runtime, not persistent).
        """
        encrypted_username = self.encrypt(username)
        encrypted_password = self.encrypt(password)
        env_key = f"CREDENTIALS_{site.upper().replace('.', '_').replace('-', '_')}"
        os.environ[env_key] = f"{encrypted_username}|{encrypted_password}"

    def list_available_credentials(self) -> Dict[str, str]:
        """
        List all available credentials from environment.
        Returns dict of site -> username (decrypted)
        """
        credentials = {}
        for key, value in os.environ.items():
            if key.startswith("CREDENTIALS_") and "|" in value:
                site = key.replace("CREDENTIALS_", "").lower().replace("_", ".")
                parts = value.split("|")
                if len(parts) == 2:
                    try:
                        username = self.decrypt(parts[0].strip())
                        credentials[site] = username
                    except Exception:
                        # Skip if decryption fails
                        continue
        return credentials


# Backward compatibility function - uses plain text if no secure manager available
def get_credential(site: str) -> Optional[Dict[str, str]]:
    """
    Get credentials for a site - tries secure manager first, falls back to plain text
    """
    try:
        # Try secure credential manager first
        secure_manager = SecureCredentialManager()
        creds = secure_manager.get_credential(site)
        if creds:
            return creds
    except Exception:
        # Fall back to original implementation if secure manager fails
        pass

    # Original plain text implementation for backward compatibility
    env_key = f"CREDENTIALS_{site.upper().replace('.', '_').replace('-', '_')}"
    credentials = os.getenv(env_key)

    if not credentials:
        return None

    # Parse username|password format
    parts = credentials.split("|")
    if len(parts) != 2:
        return None

    return {
        "username": parts[0].strip(),
        "password": parts[1].strip()
    }