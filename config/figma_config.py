"""Nexus Flow - Figma OAuth Configuration.

Loads Figma OAuth credentials from environment variables.
Never exposes secrets to the frontend.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

FIGMA_CLIENT_ID = (os.getenv("FIGMA_CLIENT_ID") or "").strip()
FIGMA_CLIENT_SECRET = (os.getenv("FIGMA_CLIENT_SECRET") or "").strip()
FIGMA_REDIRECT_URI = (os.getenv("FIGMA_REDIRECT_URI") or "http://localhost:5000/auth/figma/callback").strip()

FIGMA_OAUTH_AUTHORIZE = "https://www.figma.com/oauth"
FIGMA_OAUTH_TOKEN = "https://www.figma.com/api/oauth/token"
FIGMA_API_BASE = "https://api.figma.com/v1"

# Scopes: configurable from .env, default to file_content:read only
FIGMA_SCOPES = os.getenv("FIGMA_SCOPES", "file_content:read").strip()

# Encryption key for stored tokens (derived from Flask secret or env)
TOKEN_ENCRYPTION_KEY = (os.getenv("FIGMA_TOKEN_KEY") or os.getenv("FLASK_SECRET_KEY") or "nexusflow123").strip()


def is_configured():
    """Check if Figma OAuth credentials are configured."""
    return bool(FIGMA_CLIENT_ID and FIGMA_CLIENT_SECRET)


def log_config():
    """Log Figma OAuth config (no secrets)."""
    logger.info("[Figma] OAuth configured: client_id=%s..., redirect_uri=%s, scopes=%s",
                FIGMA_CLIENT_ID[:8] if FIGMA_CLIENT_ID else "NONE",
                FIGMA_REDIRECT_URI,
                FIGMA_SCOPES)
