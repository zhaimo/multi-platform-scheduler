"""Encryption utilities for sensitive data"""

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using AES-256"""
    
    def __init__(self):
        """Initialize encryption service with key from settings"""
        settings = get_settings()
        
        # Derive encryption key from secret key using PBKDF2
        # This ensures we have a proper 32-byte key for Fernet (AES-256)
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'multi-platform-scheduler-salt',  # In production, use a random salt stored securely
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(
            kdf.derive(settings.jwt_secret_key.encode())
        )
        
        self._cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return plaintext
        
        try:
            encrypted_bytes = self._cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise ValueError("Failed to encrypt data")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ciphertext
        
        try:
            decrypted_bytes = self._cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError("Failed to decrypt data")
    
    def encrypt_token(self, token: str) -> str:
        """
        Encrypt an OAuth token.
        
        Args:
            token: OAuth token to encrypt
            
        Returns:
            Encrypted token
        """
        return self.encrypt(token)
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt an OAuth token.
        
        Args:
            encrypted_token: Encrypted OAuth token
            
        Returns:
            Decrypted token
        """
        return self.decrypt(encrypted_token)


# Global encryption service instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """Get or create global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
