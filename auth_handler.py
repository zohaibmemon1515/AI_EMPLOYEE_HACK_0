#!/usr/bin/env python3
r"""
Authentication Handler - Gmail OAuth 2.0 Management

Handles OAuth 2.0 Desktop Application flow for Gmail API:
- First-run: Opens browser for Google login
- Subsequent runs: Uses existing token.json
- Auto-refresh: Refreshes expired tokens automatically
- Secure storage: Stores tokens outside Obsidian vault

Usage:
    from auth_handler import GmailAuthHandler
    
    auth = GmailAuthHandler(credentials_path, token_path)
    creds = auth.authenticate()  # Opens browser on first run
    service = build("gmail", "v1", credentials=creds)
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Windows-safe logging setup
import logging
class WindowsSafeHandler(logging.StreamHandler):
    """Logging handler that replaces emojis with ASCII on Windows."""
    EMOJI_MAP = {
        '👁️': '[O]', '📋': '[T]', '🤖': '[AI]', '✅': '[OK]', '❌': '[X]',
        '⚠️': '[!]', '📝': '[N]', '🔄': '[~]', '📊': '[D]', '📁': '[F]',
    }
    def emit(self, record):
        try:
            msg = self.format(record)
            if sys.platform == "win32":
                for emoji, repl in self.EMOJI_MAP.items():
                    msg = msg.replace(emoji, repl)
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            try:
                msg = self.format(record).encode('ascii', 'ignore').decode('ascii')
                self.stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                pass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = WindowsSafeHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


class GmailAuthHandler:
    """
    Handles Gmail OAuth 2.0 authentication with automatic browser flow.
    
    Features:
    - First-run: Automatically opens browser for Google login
    - Token management: Saves/loads token.json securely
    - Auto-refresh: Refreshes expired tokens automatically
    - Graceful error handling
    """
    
    # Required Gmail API scopes
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    
    def __init__(
        self,
        credentials_path: str | Path,
        token_path: str | Path,
    ):
        """
        Initialize the authentication handler.
        
        Args:
            credentials_path: Path to credentials.json (from Google Cloud)
            token_path: Path to store token.json (auto-generated)
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        
        # Validate credentials file exists
        if not self.credentials_path.exists():
            logger.error(f"Credentials file not found: {self.credentials_path}")
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_path}\n"
                f"Please download credentials.json from Google Cloud Console and save it to this location."
            )
        
        # Ensure token directory exists
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        
        # OAuth2 client (lazy loaded)
        self._oauth_client = None
        self._credentials = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        return self._credentials is not None and self._credentials.valid
    
    @property
    def has_token_file(self) -> bool:
        """Check if token.json exists."""
        return self.token_path.exists()
    
    def _load_oauth_client(self):
        """Load OAuth2 client from credentials file."""
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        
        try:
            # Load credentials.json
            with open(self.credentials_path, "r") as f:
                client_config = json.load(f)
            
            # Validate structure
            if "installed" not in client_config:
                raise ValueError("Invalid credentials.json format - missing 'installed' key")
            
            # Create OAuth2 flow
            self._flow = InstalledAppFlow.from_client_config(
                client_config,
                self.SCOPES
            )
            
            logger.info("OAuth2 client loaded successfully")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in credentials file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load OAuth2 client: {e}")
            raise
    
    def _load_existing_token(self) -> bool:
        """
        Load existing token from token.json.
        
        Returns:
            True if token loaded successfully, False otherwise
        """
        from google.oauth2.credentials import Credentials
        
        if not self.token_path.exists():
            logger.debug("No existing token file found")
            return False
        
        try:
            self._credentials = Credentials.from_authorized_user_file(
                self.token_path,
                self.SCOPES
            )
            
            if self._credentials.valid:
                logger.info("Loaded valid token from token.json")
                return True
            elif self._credentials.expired and self._credentials.refresh_token:
                logger.info("Token expired but refreshable")
                return True  # Will refresh below
            else:
                logger.warning("Token invalid and not refreshable")
                self._credentials = None
                return False
                
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            self._credentials = None
            return False
    
    def _refresh_token(self) -> bool:
        """
        Refresh expired token using refresh_token.
        
        Returns:
            True if refresh successful, False otherwise
        """
        from google.auth.transport.requests import Request
        
        if not self._credentials or not self._credentials.expired:
            return False
        
        if not self._credentials.refresh_token:
            logger.warning("No refresh token available")
            return False
        
        try:
            logger.info("Refreshing expired token...")
            self._credentials.refresh(Request())
            self._save_token()
            logger.info("Token refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False
    
    def _save_token(self):
        """Save current credentials to token.json."""
        if not self._credentials:
            logger.warning("No credentials to save")
            return
        
        try:
            token_data = {
                "token": self._credentials.token,
                "refresh_token": self._credentials.refresh_token,
                "token_uri": self._credentials.token_uri,
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
                "scopes": self._credentials.scopes,
                "expiry": self._credentials.expiry.isoformat() if self._credentials.expiry else None,
            }
            
            with open(self.token_path, "w") as f:
                json.dump(token_data, f, indent=2)
            
            # Set restrictive permissions (Unix-like systems)
            try:
                os.chmod(self.token_path, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod
            
            logger.info(f"Token saved to: {self.token_path}")
            
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            raise
    
    def _open_browser_for_auth(self) -> bool:
        """
        Open browser for first-time authentication.
        
        Returns:
            True if authentication successful, False otherwise
        """
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        print("\n" + "=" * 70)
        print("🔐 GMAIL AUTHENTICATION REQUIRED")
        print("=" * 70)
        print()
        print("This is the first time running the AI Employee Gmail integration.")
        print()
        print("📋 What will happen:")
        print("   1. Browser will open automatically")
        print("   2. Sign in with your Google account")
        print("   3. Grant permissions to access Gmail")
        print("   4. Browser will close automatically")
        print("   5. Token will be saved securely")
        print()
        print("⚠️  IMPORTANT:")
        print("   - Only grant permissions to accounts you trust")
        print("   - Token is stored securely outside Obsidian vault")
        print("   - You can revoke access anytime from Google Account settings")
        print()
        print("=" * 70)
        print()
        
        try:
            # Run local server and open browser
            print("🌐 Opening browser for authentication...")
            print("   (If browser doesn't open, check console for URL)")
            print()
            
            # Run OAuth flow with local server
            self._flow.run_local_server(
                port=8080,
                bind_addr="127.0.0.1",
                open_browser=True,
                redirect_uri_trailing_slash=True,
            )
            
            # Get credentials from flow
            self._credentials = self._flow.credentials
            
            if self._credentials:
                self._save_token()
                print()
                print("=" * 70)
                print("✅ AUTHENTICATION SUCCESSFUL!")
                print("=" * 70)
                print()
                print(f"✓ Token saved to: {self.token_path}")
                print(f"✓ Scopes granted: {', '.join(self._credentials.scopes)}")
                print(f"✓ Token expires: {self._credentials.expiry}")
                print()
                print("🚀 Starting Gmail monitoring...")
                print("=" * 70)
                return True
            else:
                logger.error("Authentication flow completed but no credentials received")
                return False
                
        except Exception as e:
            logger.error(f"Browser authentication failed: {e}")
            print()
            print("=" * 70)
            print("❌ AUTHENTICATION FAILED")
            print("=" * 70)
            print()
            print(f"Error: {e}")
            print()
            print("Troubleshooting:")
            print("1. Check that credentials.json is valid")
            print("2. Ensure Gmail API is enabled in Google Cloud Console")
            print("3. Check that OAuth consent screen is configured")
            print("4. Try running again")
            print()
            return False
    
    def authenticate(self, force_reauth: bool = False) -> Optional[object]:
        """
        Authenticate with Gmail API.

        Authentication Flow:
        1. Check if we have valid credentials in memory
        2. Check if token.json exists and is valid
        3. Try to refresh expired token
        4. If no token or refresh fails → Open browser for first-run auth

        Args:
            force_reauth: Force re-authentication even if token exists

        Returns:
            Credentials object if successful, None otherwise
        """
        from google.oauth2.credentials import Credentials

        # Load OAuth client FIRST
        self._load_oauth_client()

        # Check if already authenticated
        if self._credentials and self._credentials.valid and not force_reauth:
            logger.debug("Already authenticated with valid credentials")
            return self._credentials

        # Try to load existing token (skip if force reauth)
        if not force_reauth:
            if self._load_existing_token():
                # Try to refresh if expired
                if self._credentials.expired:
                    if self._refresh_token():
                        logger.info("Authentication successful (token refreshed)")
                        return self._credentials
                    else:
                        logger.warning("Token refresh failed, will re-authenticate")
                        self._credentials = None
                else:
                    logger.info("Authentication successful (existing token)")
                    return self._credentials

        # No valid token - need to authenticate via browser
        print()
        logger.info("No valid token found - initiating first-run authentication")

        if self._open_browser_for_auth():
            if self._credentials and self._credentials.valid:
                logger.info("First-run authentication successful")
                return self._credentials

        # Authentication failed
        logger.error("Authentication failed")
        return None
    
    def get_credentials(self) -> Optional[object]:
        """
        Get current credentials (must call authenticate() first).
        
        Returns:
            Credentials object or None
        """
        return self._credentials
    
    def revoke_token(self) -> bool:
        """
        Revoke current token and delete token.json.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self._credentials and self._credentials.refresh_token:
                from google.oauth2.credentials import Credentials
                import requests
                
                # Revoke token with Google
                revoke_url = "https://oauth2.googleapis.com/revoke"
                response = requests.post(
                    revoke_url,
                    params={"token": self._credentials.refresh_token},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
                
                if response.status_code == 200:
                    logger.info("Token revoked from Google")
                else:
                    logger.warning(f"Revoke response: {response.status_code}")
            
            # Delete local token file
            if self.token_path.exists():
                self.token_path.unlink()
                logger.info(f"Deleted local token: {self.token_path}")
            
            self._credentials = None
            logger.info("Token revoked successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    def get_token_info(self) -> dict:
        """
        Get information about current token.
        
        Returns:
            Dictionary with token information
        """
        info = {
            "authenticated": self.is_authenticated,
            "has_token_file": self.has_token_file,
            "token_path": str(self.token_path),
            "credentials_path": str(self.credentials_path),
            "scopes": self.SCOPES,
        }
        
        if self._credentials:
            info.update({
                "token_valid": self._credentials.valid,
                "token_expired": self._credentials.expired if hasattr(self._credentials, "expired") else None,
                "token_expiry": self._credentials.expiry.isoformat() if hasattr(self._credentials, "expiry") and self._credentials.expiry else None,
                "has_refresh_token": bool(self._credentials.refresh_token),
            })
        
        return info


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for authentication testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gmail OAuth 2.0 Authentication Handler")
    parser.add_argument(
        "--credentials",
        type=str,
        default="./credentials/gmail/credentials.json",
        help="Path to credentials.json",
    )
    parser.add_argument(
        "--token",
        type=str,
        default="./credentials/gmail/token.json",
        help="Path to token.json",
    )
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Revoke existing token",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show token information",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-authentication",
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Gmail OAuth 2.0 Authentication Handler")
    print("=" * 70)
    print()
    
    try:
        auth = GmailAuthHandler(
            credentials_path=args.credentials,
            token_path=args.token,
        )
        
        if args.info:
            info = auth.get_token_info()
            print("Token Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
            return
        
        if args.revoke:
            if auth.revoke_token():
                print("✅ Token revoked successfully")
            else:
                print("❌ Failed to revoke token")
            return
        
        # Authenticate
        print("Authenticating with Gmail API...")
        creds = auth.authenticate(force_reauth=args.force)
        
        if creds:
            print()
            print("✅ Authentication successful!")
            print()
            info = auth.get_token_info()
            print("Token Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print()
            print("❌ Authentication failed")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Authentication failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
