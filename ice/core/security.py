# SPDX-License-Identifier: BSL-1.1

import logging
import os
import warnings

logger = logging.getLogger("ice_security")

def verify_access_key(api_key: str) -> bool:
    """
    Simple placeholder for API key verification.
    In the OSS version, this defaults to True if ICE_DISABLE_AUTH is set.

    SECURITY WARNING: ICE_DISABLE_AUTH=true disables all authentication!
    Only use in development/test environments.
    """
    if os.getenv("ICE_DISABLE_AUTH", "false").lower() == "true":
        warnings.warn(
            "ICE_DISABLE_AUTH=true: Authentication is DISABLED. "
            "This is a SECURITY RISK in production environments.",
            SecurityWarning,
            stacklevel=2
        )
        return True
    return bool(api_key)

class SecurityWarning(UserWarning):
    """Warning for security-related configuration issues."""
    pass

class SecurityManager:
    """
    Handles authentication and security policies for the ICE engine.
    """
    def __init__(self):
        self.enabled = os.getenv("ICE_ENABLE_AUTH", "true").lower() == "true"

        if not self.enabled:
            warnings.warn(
                "ICE_ENABLE_AUTH=false: Authentication is DISABLED. "
                "This is a SECURITY RISK in production environments.",
                SecurityWarning,
                stacklevel=2
            )

    async def authenticate_request(self, request):
        """
        Authenticates the incoming request.
        """
        if not self.enabled:
            logger.warning("Authentication disabled - allowing request (SECURITY RISK)")
            return True

        # Implement custom authentication logic here
        return True
