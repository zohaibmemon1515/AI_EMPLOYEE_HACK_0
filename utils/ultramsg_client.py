#!/usr/bin/env python3
r"""
UltraMsg Client - WhatsApp Business API Integration

Provides WhatsApp messaging via UltraMsg API:
- Send text messages
- Send media messages
- Get message status
- Read delivery reports

Usage:
    from utils.ultramsg_client import UltraMsgClient
    
    client = UltraMsgClient(instance_id, token)
    result = client.send_message("+1234567890", "Hello!")
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import dotenv

# Load environment variables
dotenv.load_dotenv()

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


@dataclass
class MessageResult:
    """Result of sending a message."""
    success: bool
    message_id: str = ""
    status: str = ""
    error: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class UltraMsgClient:
    """
    UltraMsg WhatsApp API Client.

    Send WhatsApp messages via UltraMsg service.
    """

    def __init__(
        self,
        instance_id: str = None,
        token: str = None
    ):
        """
        Initialize UltraMsg client.

        Args:
            instance_id: UltraMsg instance ID
            token: UltraMsg API token
        """
        self.instance_id = instance_id or os.getenv("ULTRAMSG_INSTANCE_ID", "")
        self.token = token or os.getenv("ULTRAMSG_TOKEN", "")
        self.base_url = f"https://api.ultramsg.com/{self.instance_id}/messages/chat"

        self._validate_config()

    def _validate_config(self):
        """Validate configuration."""
        if not self.instance_id:
            logger.warning("UltraMsg instance ID not configured")
        if not self.token:
            logger.warning("UltraMsg token not configured")

    @property
    def is_configured(self) -> bool:
        """Check if client is configured."""
        return bool(self.instance_id and self.token)

    def send_message(
        self,
        to: str,
        message: str,
        priority: int = 1
    ) -> MessageResult:
        """
        Send a text message via WhatsApp.

        Args:
            to: Recipient phone number (with country code)
            message: Message text
            priority: Message priority (1-10)

        Returns:
            MessageResult with send status
        """
        if not self.is_configured:
            return MessageResult(
                success=False,
                error="UltraMsg not configured"
            )

        try:
            payload = {
                "token": self.token,
                "to": to,
                "body": message,
                "priority": priority
            }

            response = requests.post(
                self.base_url,
                data=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            if result.get("sent") == "true":
                return MessageResult(
                    success=True,
                    message_id=result.get("id", ""),
                    status="sent"
                )
            else:
                return MessageResult(
                    success=False,
                    error=result.get("error", "Unknown error")
                )

        except requests.RequestException as e:
            logger.error(f"UltraMsg API error: {e}")
            return MessageResult(
                success=False,
                error=str(e)
            )

    def send_image(
        self,
        to: str,
        image_url: str,
        caption: str = ""
    ) -> MessageResult:
        """
        Send an image via WhatsApp.

        Args:
            to: Recipient phone number
            image_url: URL of image
            caption: Image caption

        Returns:
            MessageResult with send status
        """
        if not self.is_configured:
            return MessageResult(
                success=False,
                error="UltraMsg not configured"
            )

        try:
            payload = {
                "token": self.token,
                "to": to,
                "image": image_url,
                "caption": caption
            }

            response = requests.post(
                f"https://api.ultramsg.com/{self.instance_id}/messages/image",
                data=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            if result.get("sent") == "true":
                return MessageResult(
                    success=True,
                    message_id=result.get("id", ""),
                    status="sent"
                )
            else:
                return MessageResult(
                    success=False,
                    error=result.get("error", "Unknown error")
                )

        except requests.RequestException as e:
            logger.error(f"UltraMsg image API error: {e}")
            return MessageResult(
                success=False,
                error=str(e)
            )

    def get_message_status(self, message_id: str) -> dict:
        """
        Get message delivery status.

        Args:
            message_id: Message ID from send result

        Returns:
            Status dictionary
        """
        if not self.is_configured:
            return {"error": "UltraMsg not configured"}

        try:
            payload = {
                "token": self.token,
                "id": message_id
            }

            response = requests.post(
                f"https://api.ultramsg.com/{self.instance_id}/messages/status",
                data=payload,
                timeout=30
            )
            response.raise_for_status()

            return response.json()

        except requests.RequestException as e:
            logger.error(f"UltraMsg status API error: {e}")
            return {"error": str(e)}


# =============================================================================
# Factory Function
# =============================================================================

def create_ultramsg_client(
    instance_id: str = None,
    token: str = None
) -> UltraMsgClient:
    """
    Create UltraMsg client.

    Args:
        instance_id: Instance ID
        token: API token

    Returns:
        UltraMsgClient instance
    """
    return UltraMsgClient(instance_id, token)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for UltraMsg client."""
    import argparse

    parser = argparse.ArgumentParser(description="UltraMsg Client")
    parser.add_argument("--to", type=str, help="Recipient phone number")
    parser.add_argument("--message", type=str, help="Message text")
    parser.add_argument("--instance", type=str, help="Instance ID")
    parser.add_argument("--token", type=str, help="API token")

    args = parser.parse_args()

    print("=" * 70)
    print("UltraMsg WhatsApp Client")
    print("=" * 70)

    try:
        client = UltraMsgClient(args.instance, args.token)

        if not client.is_configured:
            print("\n⚠️  UltraMsg not configured")
            print("Set ULTRAMSG_INSTANCE_ID and ULTRAMSG_TOKEN in .env")
            return

        if args.to and args.message:
            print(f"\n📤 Sending message to {args.to}...")
            result = client.send_message(args.to, args.message)

            if result.success:
                print(f"✅ Message sent! ID: {result.message_id}")
            else:
                print(f"❌ Failed: {result.error}")
        else:
            print("\nUsage: python -m utils.ultramsg_client --to +1234567890 --message 'Hello'")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
