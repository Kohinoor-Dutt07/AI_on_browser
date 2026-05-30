"""
Tests for the credential manager
"""
import os
import tempfile
from src.credential_manager import (
    get_credential,
    set_credential,
    list_available_credentials,
    SecureCredentialManager
)


def test_plain_text_credentials():
    """Test backward compatibility with plain text credentials"""
    # Set plain text credential
    os.environ["CREDENTIALS_TESTSITE"] = "user|pass"

    # Should be able to get it
    creds = get_credential("testsite")
    assert creds is not None
    assert creds["username"] == "user"
    assert creds["password"] == "pass"

    # Clean up
    del os.environ["CREDENTIALS_TESTSITE"]


def test_encrypted_credentials():
    """Test encrypted credential functionality"""
    # Set a master key for testing
    os.environ["SECURE_CREDENTIALS_KEY"] = "test_master_key_32_bytes_long!!"

    # Set encrypted credential via the function (which uses SecureCredentialManager internally)
    set_credential("encryptedsite", "encrypted_user", "encrypted_pass")

    # Should be able to get it decrypted
    creds = get_credential("encryptedsite")
    assert creds is not None
    assert creds["username"] == "encrypted_user"
    assert creds["password"] == "encrypted_pass"

    # List should show the site
    credentials = list_available_credentials()
    assert "encryptedsite" in credentials
    assert credentials["encryptedsite"] == "encrypted_user"

    # Clean up
    env_key = "CREDENTIALS_ENCRYPTEDSITE"
    if env_key in os.environ:
        del os.environ[env_key]
    del os.environ["SECURE_CREDENTIALS_KEY"]


def test_secure_credential_manager_directly():
    """Test the SecureCredentialManager class directly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary file to store the key for testing
        key_file = os.path.join(tmpdir, "test.key")
        master_key = "test_master_key_32_bytes_long!!"

        # Write key to file (simulating external secret management)
        with open(key_file, "w") as f:
            f.write(master_key)

        # Read key from file
        with open(key_file, "r") as f:
            key_from_file = f.read().strip()

        # Initialize manager with the key
        manager = SecureCredentialManager(master_key=key_from_file)

        # Set a credential
        manager.set_credential("directsite", "direct_user", "direct_pass")

        # Get it back
        creds = manager.get_credential("directsite")
        assert creds is not None
        assert creds["username"] == "direct_user"
        assert creds["password"] == "direct_pass"

        # List credentials
        creds_list = manager.list_available_credentials()
        assert "directsite" in creds_list
        assert creds_list["directsite"] == "direct_user"


def test_fallback_to_plain_text():
    """Test that if secure manager fails, it falls back to plain text"""
    # Break the secure manager by setting an invalid key
    os.environ["SECURE_CREDENTIALS_KEY"] = "invalid_key_not_32_bytes"

    # Set a plain text credential
    os.environ["CREDENTIALS_FALLBACKSITE"] = "fallback_user|fallback_pass"

    # Should still work via fallback
    creds = get_credential("fallbacksite")
    assert creds is not None
    assert creds["username"] == "fallback_user"
    assert creds["password"] == "fallback_pass"

    # Clean up
    del os.environ["CREDENTIALS_FALLBACKSITE"]
    del os.environ["SECURE_CREDENTIALS_KEY"]


if __name__ == "__main__":
    test_plain_text_credentials()
    test_encrypted_credentials()
    test_secure_credential_manager_directly()
    test_fallback_to_plain_text()
    print("All tests passed!")