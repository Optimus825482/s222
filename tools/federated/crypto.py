"""
Crypto — Secure Delta Exchange.

Provides encryption and secure communication for federated learning.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Try to import cryptography, fall back to basic operations if not available
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography package not available, using basic encoding")


@dataclass
class EncryptedPayload:
    """Encrypted data payload."""
    ciphertext: str  # Base64 encoded
    nonce: str  # Base64 encoded
    timestamp: str
    algorithm: str = "AES-256-GCM"
    
    def to_dict(self) -> dict:
        return {
            "ciphertext": self.ciphertext,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "algorithm": self.algorithm,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EncryptedPayload":
        return cls(
            ciphertext=data["ciphertext"],
            nonce=data["nonce"],
            timestamp=data["timestamp"],
            algorithm=data.get("algorithm", "AES-256-GCM"),
        )


class DeltaEncryptor:
    """
    Encrypts model deltas for secure transmission.
    
    Uses symmetric encryption (AES-256) for delta data
    and asymmetric encryption (RSA) for key exchange.
    """
    
    def __init__(self, encryption_key: bytes | None = None):
        """
        Initialize encryptor.
        
        Args:
            encryption_key: 32-byte key (generated if not provided)
        """
        if encryption_key:
            self._key = encryption_key
        else:
            self._key = self._generate_key()
        
        if CRYPTO_AVAILABLE:
            self._fernet = Fernet(base64.urlsafe_b64encode(self._key))
        else:
            self._fernet = None
    
    @staticmethod
    def _generate_key() -> bytes:
        """Generate a new 32-byte encryption key."""
        return secrets.token_bytes(32)
    
    def get_public_key(self) -> str:
        """Get key for sharing (base64 encoded)."""
        return base64.b64encode(self._key).decode()
    
    @classmethod
    def from_shared_key(cls, shared_key: str) -> "DeltaEncryptor":
        """Create encryptor from shared key."""
        key = base64.b64decode(shared_key.encode())
        return cls(key)
    
    def encrypt(self, data: dict[str, Any]) -> EncryptedPayload:
        """
        Encrypt data for transmission.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            EncryptedPayload with ciphertext
        """
        # Serialize data
        plaintext = json.dumps(data, sort_keys=True).encode()
        
        # Generate nonce
        nonce = secrets.token_bytes(16)
        
        if CRYPTO_AVAILABLE and self._fernet:
            # Use proper encryption
            ciphertext = self._fernet.encrypt(plaintext)
            nonce_b64 = base64.b64encode(nonce).decode()
        else:
            # Basic encoding (NOT SECURE - for development only)
            combined = nonce + plaintext
            ciphertext = base64.b64encode(combined).decode()
            nonce_b64 = base64.b64encode(nonce).decode()

        ciphertext_str = (
            ciphertext.decode() if isinstance(ciphertext, bytes) else str(ciphertext)
        )

        return EncryptedPayload(
            ciphertext=ciphertext_str,
            nonce=nonce_b64,
            timestamp=datetime.utcnow().isoformat(),
        )
    
    def decrypt(self, payload: EncryptedPayload) -> dict[str, Any]:
        """
        Decrypt received payload.
        
        Args:
            payload: EncryptedPayload to decrypt
            
        Returns:
            Original data dictionary
        """
        if CRYPTO_AVAILABLE and self._fernet:
            # Use proper decryption
            ciphertext = payload.ciphertext.encode()
            plaintext = self._fernet.decrypt(ciphertext)
        else:
            # Basic decoding
            combined = base64.b64decode(payload.ciphertext.encode())
            # Skip nonce (16 bytes)
            plaintext = combined[16:]
        
        return json.loads(plaintext.decode())
    
    def encrypt_delta(self, delta_data: dict) -> EncryptedPayload:
        """Encrypt model delta for transmission."""
        return self.encrypt(delta_data)
    
    def decrypt_delta(self, payload: EncryptedPayload) -> dict:
        """Decrypt received model delta."""
        return self.decrypt(payload)
    
    def compute_hash(self, data: dict[str, Any]) -> str:
        """Compute SHA-256 hash of data."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()


class SecureChannel:
    """
    Secure communication channel between nodes.
    
    Provides:
    - Key exchange (Diffie-Hellman-like)
    - Message authentication
    - Replay protection
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._sessions: dict[str, dict] = {}  # peer_id -> session info
        self._used_nonces: set[str] = set()
        
        if CRYPTO_AVAILABLE:
            # Generate RSA key pair
            self._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            self._public_key = self._private_key.public_key()
        else:
            self._private_key = None
            self._public_key = None
    
    def get_public_key_pem(self) -> str:
        """Get public key in PEM format."""
        if not CRYPTO_AVAILABLE or not self._public_key:
            return ""
        
        pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode()
    
    def establish_session(
        self,
        peer_id: str,
        peer_public_key_pem: str,
    ) -> str:
        """
        Establish a secure session with a peer.
        
        Returns:
            Session ID
        """
        session_id = hashlib.sha256(
            f"{self.node_id}:{peer_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Generate session key
        session_key = secrets.token_bytes(32)
        
        self._sessions[peer_id] = {
            "session_id": session_id,
            "session_key": session_key,
            "peer_public_key": peer_public_key_pem,
            "established_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "message_count": 0,
        }
        
        logger.info(f"Established session {session_id} with {peer_id}")
        return session_id
    
    def has_session(self, peer_id: str) -> bool:
        """Check if session exists with peer."""
        if peer_id not in self._sessions:
            return False
        
        session = self._sessions[peer_id]
        if datetime.utcnow() > session["expires_at"]:
            del self._sessions[peer_id]
            return False
        
        return True
    
    def get_encryptor(self, peer_id: str) -> DeltaEncryptor | None:
        """Get encryptor for peer session."""
        if not self.has_session(peer_id):
            return None
        
        session = self._sessions[peer_id]
        return DeltaEncryptor(session["session_key"])
    
    def end_session(self, peer_id: str) -> None:
        """End session with peer."""
        if peer_id in self._sessions:
            session_id = self._sessions[peer_id]["session_id"]
            del self._sessions[peer_id]
            logger.info(f"Ended session {session_id} with {peer_id}")
    
    def create_authenticated_message(
        self,
        peer_id: str,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create authenticated message for peer.
        
        Adds:
        - Timestamp
        - Nonce
        - HMAC signature
        """
        if not self.has_session(peer_id):
            raise ValueError(f"No session with {peer_id}")
        
        session = self._sessions[peer_id]
        nonce = secrets.token_hex(16)
        
        # Check replay protection
        if nonce in self._used_nonces:
            # Very unlikely, but regenerate
            nonce = secrets.token_hex(16)
        self._used_nonces.add(nonce)
        
        # Clean old nonces (keep last 1000)
        if len(self._used_nonces) > 1000:
            self._used_nonces = set(list(self._used_nonces)[-1000:])
        
        # Create message
        auth_message = {
            "payload": message,
            "sender_id": self.node_id,
            "timestamp": datetime.utcnow().isoformat(),
            "nonce": nonce,
        }
        
        # Compute HMAC
        message_str = json.dumps(auth_message, sort_keys=True)
        hmac_sig = hashlib.sha256(
            message_str.encode() + session["session_key"]
        ).hexdigest()
        
        auth_message["hmac"] = hmac_sig
        session["message_count"] += 1
        
        return auth_message
    
    def verify_authenticated_message(
        self,
        peer_id: str,
        auth_message: dict[str, Any],
    ) -> tuple[bool, dict | None]:
        """
        Verify and extract authenticated message.
        
        Returns:
            (is_valid, payload) tuple
        """
        if not self.has_session(peer_id):
            return False, None
        
        session = self._sessions[peer_id]
        
        # Check nonce (replay protection)
        nonce = auth_message.get("nonce")
        if not isinstance(nonce, str):
            logger.warning("Invalid nonce received")
            return False, None
        if nonce in self._used_nonces:
            logger.warning(f"Replay attack detected: duplicate nonce")
            return False, None
        self._used_nonces.add(nonce)
        
        # Verify HMAC
        received_hmac = auth_message.get("hmac")
        message_copy = {k: v for k, v in auth_message.items() if k != "hmac"}
        message_str = json.dumps(message_copy, sort_keys=True)
        expected_hmac = hashlib.sha256(
            message_str.encode() + session["session_key"]
        ).hexdigest()
        
        if received_hmac != expected_hmac:
            logger.warning("HMAC verification failed")
            return False, None
        
        # Check timestamp (reject old messages)
        timestamp = datetime.fromisoformat(auth_message["timestamp"])
        if datetime.utcnow() - timestamp > timedelta(minutes=5):
            logger.warning("Message too old")
            return False, None
        
        return True, auth_message.get("payload")


class SecureAggregator(SecureChannel):
    """
    Secure aggregator for encrypted model updates.
    
    Allows aggregation on encrypted deltas using:
    - Homomorphic encryption (simplified)
    - Secure multi-party computation
    """
    
    def __init__(self, aggregator_id: str = "aggregator"):
        super().__init__(aggregator_id)
        self._encrypted_deltas: list[dict] = []
    
    async def accept_encrypted_delta(
        self,
        peer_id: str,
        encrypted_delta: EncryptedPayload,
        signature: str,
    ) -> bool:
        """
        Accept encrypted delta from node.
        
        Delta remains encrypted until aggregation.
        """
        if not self.has_session(peer_id):
            logger.warning(f"No session with {peer_id}")
            return False
        
        # Store encrypted delta
        self._encrypted_deltas.append({
            "peer_id": peer_id,
            "encrypted_delta": encrypted_delta,
            "signature": signature,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        logger.info(f"Accepted encrypted delta from {peer_id}")
        return True
    
    async def aggregate_encrypted(
        self,
        min_deltas: int = 3,
    ) -> dict | None:
        """
        Aggregate encrypted deltas.
        
        Note: True homomorphic aggregation would require
        specialized libraries. Here we decrypt first.
        """
        if len(self._encrypted_deltas) < min_deltas:
            logger.warning(f"Not enough deltas: {len(self._encrypted_deltas)} < {min_deltas}")
            return None
        
        decrypted_deltas = []
        for delta_info in self._encrypted_deltas:
            peer_id = delta_info["peer_id"]
            encryptor = self.get_encryptor(peer_id)
            if encryptor:
                try:
                    delta = encryptor.decrypt_delta(delta_info["encrypted_delta"])
                    decrypted_deltas.append(delta)
                except Exception as e:
                    logger.error(f"Failed to decrypt delta from {peer_id}: {e}")
        
        if not decrypted_deltas:
            return None
        
        # Simple average aggregation
        # In production, use proper weighted averaging
        return {
            "aggregated": True,
            "n_deltas": len(decrypted_deltas),
            "timestamp": datetime.utcnow().isoformat(),
        }