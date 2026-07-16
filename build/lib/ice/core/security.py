import base64
import json
import time
import uuid
import os
import subprocess
import orjson
import jwt # Import PyJWT
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import hashlib
import logging
import sys # Add sys
from typing import Optional, Dict, Any

logger = logging.getLogger("ice_security")

# Dopove's official AWS KMS public key for JWT verification
DOPOVE_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4ElmVYVjxdUM2FSFCNGV
8eOkdG17Pd0mks4TXuGejaNmkKPnVqFngfx50WNe44/swcDqkRgTvJusjNHq6NB2
k/T9cjW7YpMTlZACEKlRgEZQRje02k14X6dXjCT3PN4L8Sx9oBGi5SdkJZHgLm5D
YsDmAuH+I+3nli7diMONEL4n1j2V/hyUHfs9+dZa1XiGYqzrrmd2Ph6HBr9z7Fi1
ypQPdOsHyNUAHuyKFYkpyPJN/XPZeQCvH8llsO7Bf8Pbh38AgeyrghR8Nd19o7YE
ZI5iETAYvkL6/PFhphuWSndV4DYVQQkMHkne/24vGZTQRRv1Zq7hfJqPCxXIPYyU
GQIDAQAB
-----END PUBLIC KEY-----"""

class SecurityManager:
    """
    Handles Hardware-Bound Licensing and IP Protection for ICE v3.0.0.
    Binds execution to specific CPU-IDs using AWS License Manager JWT logic.
    """
    def __init__(self, license_key: Optional[str] = None):
        self.license_key = license_key or self.get_license_jwt()

    @staticmethod
    def get_machine_keypair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """
        Retrieves or generates the root-protected cryptographic machine keypair.
        This completely replaces the fragile CPU-ID fingerprinting.
        """
        key_path = os.path.expanduser("~/.ice/machine.key")
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                    backend=default_backend()
                )
            return private_key, private_key.public_key()
            
        # Generate new keypair if it doesn't exist
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        private_key = ed25519.Ed25519PrivateKey.generate()
        
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Save securely (0400 permissions where possible)
        with open(key_path, "wb") as key_file:
            key_file.write(pem)
        
        try:
            os.chmod(key_path, 0o400)
        except Exception:
            pass # Windows or specific setups might not support chmod 400
            
        logger.info("ICE: Generated new cryptographic installation keypair.")
        return private_key, private_key.public_key()

    @staticmethod
    def safe_uuid(id_str: str) -> uuid.UUID:
        """
        Safely converts a string to a UUID. 
        If malformed, returns a deterministic null UUID to prevent kernel crash.
        """
        try:
            if isinstance(id_str, uuid.UUID): return id_str
            return uuid.UUID(str(id_str))
        except (ValueError, TypeError, AttributeError):
            logger.error(f"SECURITY: Malformed Tenant/User ID detected: {id_str}")
            return uuid.UUID("00000000-0000-0000-0000-000000000000")

    def verify_license(self, jwt_token: str) -> bool:
        """
        High-Performance License Verification using offline JWT.
        """
        try:
            # 1. Verify JWT signature with Dopove's public key
            payload = jwt.decode(jwt_token, DOPOVE_PUBLIC_KEY_PEM, algorithms=["RS256"], audience="ICE-Embedded-Engine")

            # 2. Check expiration
            if time.time() > payload.get("exp", float('inf')):
                logger.error("License has expired.")
                return False
            
            # 3. Basic product/SKU check (can be expanded)
            try:
                from ice.build_config import ICE_SKU
            except ImportError:
                ICE_SKU = "ICE-DEVELOPMENT"

            allowed_skus = [ICE_SKU]
            if ICE_SKU == "ICE-DEVELOPMENT" or ICE_SKU == "ICE-UNLIMITED":
                # Allow dev/unlimited builds to run any product type for testing
                allowed_skus = ["ICE-COMMUNITY", "ICE-DEVELOPER-PRO", "ICE-ENTERPRISE", "ICE-DEVELOPMENT", "ICE-UNLIMITED"]

            if payload.get("product") not in allowed_skus:
                logger.error(f"SKU MISMATCH: Expected one of {allowed_skus}, but license is for {payload.get('product')}.")
                return False

            # 4. Verify machine binding
            _private_key, public_key = self.get_machine_keypair()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            if payload.get("machine_public_key") != public_key_pem:
                logger.error("License is not bound to this machine.")
                return False

            self.license_payload = payload # Store the decoded payload
            return True

        except jwt.exceptions.ExpiredSignatureError:
            logger.error("License has expired (JWT ExpiredSignatureError).")
            return False
        except jwt.exceptions.InvalidTokenError as e:
            logger.error(f"Invalid License Token (JWT InvalidTokenError): {e}")
            return False
        except Exception as e:
            logger.error(f"Activation Engine Failure: {e}")
            return False

    def get_license_jwt(self) -> Optional[str]:
        """
        Retrieves the license JWT from local storage or environment.
        """
        # 1. Check local seal (~/.ice/license.ice)
        seal_path = os.path.expanduser("~/.ice/license.jwt") # Fixed file extension
        if os.path.exists(seal_path):
            try:
                with open(seal_path, "r") as f:
                    return f.read().strip()
            except: pass
        
        # 2. Check environment variable
        return os.getenv("ICE_LICENSE_JWT")

    async def register_node(self):
        """
        Enforces node counts by registering the current machine in the database.
        """
        if not self.db_pool or not getattr(self, 'license_payload', None):
            return

        max_nodes = self.license_payload.get("max_nodes", 1)
        tenant_id = self.license_payload.get("tenant_id")
        if not tenant_id:
            logger.error("License payload missing tenant_id")
            self.trigger_self_destruct()
            sys.exit(1)
            
        _, public_key = self.get_machine_keypair()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        node_id = hashlib.sha256(public_key_pem.encode()).hexdigest()

        try:
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    # 1. Clean up stale nodes (e.g., no heartbeat for 5 minutes)
                    await conn.execute("DELETE FROM active_nodes WHERE last_heartbeat < NOW() - INTERVAL '5 minutes'")

                    # 2. Check current active nodes for this tenant
                    active_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM active_nodes WHERE tenant_id = $1 AND node_id != $2",
                        self.safe_uuid(tenant_id), node_id
                    )

                    # 3. Enforce limit
                    if active_count >= max_nodes:
                        logger.error(f"LICENSE ERROR: Maximum node limit ({max_nodes}) reached. Cannot register new node.")
                        self.trigger_self_destruct()
                        sys.exit(1)

                    # 4. Register / Update heartbeat
                    await conn.execute(
                        """
                        INSERT INTO active_nodes (node_id, tenant_id, last_heartbeat)
                        VALUES ($1, $2, NOW())
                        ON CONFLICT (node_id) DO UPDATE SET last_heartbeat = NOW()
                        """,
                        node_id, self.safe_uuid(tenant_id)
                    )
                    logger.info(f"Node registered successfully. Active nodes: {active_count + 1}/{max_nodes}")
        except Exception as e:
            logger.error(f"Failed to register node: {e}")
            self.trigger_self_destruct()
            sys.exit(1)

    def verify_or_exit(self):
        """
        Strict gate: Verifies the current hardware against the license.
        """
        try:
            from ice.build_config import ICE_SKU
            print(f"DEBUG: verify_or_exit - ICE_SKU from build_config: {ICE_SKU}")
        except ImportError:
            ICE_SKU = "ICE-DEVELOPMENT"
            print(f"DEBUG: verify_or_exit - ICE_SKU defaulted to: {ICE_SKU}")

        if ICE_SKU == "ICE-UNLIMITED":
            return True

        if not self.license_key:
            print("❌ [ICE ERROR] No license found. Run 'ice license setup'.")
            sys.exit(1)

        if not self.verify_license(self.license_key):
            self.trigger_self_destruct()
            sys.exit(1)
        return True

    def trigger_self_destruct(self):
        """
        Safety gate for unauthorized hardware.
        """
        print(f"\n" + "="*60)
        print(f"🛑 [LICENSE ERROR] UNAUTHORIZED HARDWARE DETECTED")
        print(f"Reason: This machine is not authorized to run ICE v3.0.0.")
        print("="*60 + "\n")

        # We only self-destruct if explicitly configured to do so in production builds
        if os.getenv("ICE_STRICT_DRM") == "1":
            print("[SECURITY] Initiating self-destruct as ICE_STRICT_DRM=1...")
            try:
                # 1. Purge the local seal
                seal_path = os.path.expanduser("~/.ice/license.ice")
                if os.path.exists(seal_path):
                    os.remove(seal_path)
                    print("[SECURITY] Local seal purged.")

                # 2. Corrupt core module files to prevent restart
                import shutil
                core_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
                if os.path.exists(os.path.join(core_path, "core")):
                    shutil.rmtree(os.path.join(core_path, "core"), ignore_errors=True)
                    print("[SECURITY] Core proprietary modules purged.")
            except Exception as e:
                print(f"[SECURITY] Self-destruct partial failure: {e}")
        
        sys.exit(1)

def enforce_licensing():
    """
    Called at startup. If license is missing or invalid, shuts down the process.
    """
    try:
        from ice.build_config import ICE_SKU
        print(f"DEBUG: verify_or_exit - ICE_SKU from build_config: {ICE_SKU}")
    except ImportError:
        ICE_SKU = "ICE-DEVELOPMENT"
        print(f"DEBUG: verify_or_exit - ICE_SKU defaulted to: {ICE_SKU}")

    if ICE_SKU == "ICE-UNLIMITED":
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("ICE v3.0.0: UNLIMITED EDITION")
        print("Hardware-bound licensing is permanently bypassed for this build.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return
    sec = SecurityManager()
    jwt_env = os.getenv("ICE_LICENSE_JWT")
    
    # Check for local seal first
    if sec.verify_license(""):
        return

    if not jwt_env:
        print("\n" + "="*60)
        print("🛑 [LICENSE ERROR] No license found. Set ICE_LICENSE_JWT environment variable.")
        print("="*60 + "\n")
        sec.trigger_self_destruct()
        sys.exit(1)
        
    if not sec.verify_license(jwt_env):
        sec.trigger_self_destruct()
    
    return sec
