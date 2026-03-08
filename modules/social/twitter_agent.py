#!/usr/bin/env python3
r"""
Twitter (X) Agent - Social Media Automation

Provides Twitter/X integration for the AI Employee:
- Tweet generation and publishing
- Thread creation
- Engagement metrics collection
- Reply management
- Hashtag optimization

Note: Requires Twitter API v2 access (Developer or Enterprise).

Usage:
    from modules.social.twitter_agent import TwitterAgent

    agent = TwitterAgent(api_key, api_secret, access_token, access_secret)
    agent.publish_tweet("Hello World!")
    metrics = agent.get_tweet_metrics(tweet_id)
"""

import json
import logging
import os
import base64
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
from urllib.parse import quote

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
class Tweet:
    """Tweet data."""
    text: str
    media_urls: list = None
    reply_to: str = ""
    is_thread: bool = False
    tweet_id: str = ""
    created_at: str = ""


@dataclass
class EngagementMetrics:
    """Engagement metrics for a tweet."""
    tweet_id: str
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    quotes: int = 0
    impressions: int = 0
    profile_clicks: int = 0
    url_clicks: int = 0
    engagement_rate: float = 0.0
    collected_at: str = ""

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now().isoformat()


class TwitterAgent:
    """
    Twitter API v2 Agent.

    Handles all Twitter operations including:
    - Publishing tweets
    - Creating threads
    - Managing media uploads
    - Retrieving engagement metrics
    - Monitoring mentions and replies
    """

    API_BASE_URL = "https://api.twitter.com"
    API_UPLOAD_URL = "https://upload.twitter.com"
    API_VERSION = "2"

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        access_token: str = None,
        access_token_secret: str = None,
        bearer_token: str = None,
    ):
        """
        Initialize Twitter agent.

        Args:
            api_key: Twitter API Key
            api_secret: Twitter API Secret
            access_token: Twitter Access Token
            access_token_secret: Twitter Access Token Secret
            bearer_token: Twitter Bearer Token (for app-only auth)
        """
        # Load from environment if not provided
        self.api_key = api_key or os.getenv("TWITTER_API_KEY", "")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET", "")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.access_token_secret = access_token_secret or os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN", "")

        # Session
        self._session = requests.Session()

        # User ID cache
        self._user_id = None

        # Validate configuration
        self._validate_config()

        logger.info("TwitterAgent initialized")

    def _validate_config(self):
        """Validate configuration."""
        if self.bearer_token:
            logger.info("Using Bearer Token authentication")
        elif self.api_key and self.api_secret:
            logger.info("Using OAuth 1.0a authentication")
        else:
            logger.warning("Twitter credentials not configured")

    @property
    def is_configured(self) -> bool:
        """Check if agent is properly configured."""
        return bool(self.bearer_token or (self.api_key and self.api_secret))

    def _get_auth_headers(self, method: str = "GET", url: str = "", params: dict = None) -> dict:
        """
        Get authentication headers for API request.

        Args:
            method: HTTP method
            url: Request URL
            params: Request parameters

        Returns:
            Headers dictionary
        """
        if self.bearer_token:
            return {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
        else:
            # OAuth 1.0a signature
            return self._generate_oauth_header(method, url, params)

    def _generate_oauth_header(
        self,
        method: str,
        url: str,
        params: dict = None
    ) -> dict:
        """Generate OAuth 1.0a authorization header."""
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_token": self.access_token,
            "oauth_nonce": hashlib.sha256(os.urandom(32)).hexdigest(),
            "oauth_timestamp": str(int(time.time())),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_version": "1.0"
        }

        # Combine parameters
        all_params = {**oauth_params, **(params or {})}

        # Create signature base string
        base_string = "&".join([
            method.upper(),
            quote(url, safe=""),
            "&".join(f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in sorted(all_params.items()))
        ])

        # Create signing key
        signing_key = f"{quote(self.api_secret, safe='')}&{quote(self.access_token_secret, safe='')}"

        # Generate signature
        signature = hmac.new(
            signing_key.encode(),
            base_string.encode(),
            hashlib.sha1
        ).digest()
        signature = base64.b64encode(signature).decode()

        # Build authorization header
        oauth_params["oauth_signature"] = signature
        auth_header = "OAuth " + ", ".join(
            f'{k}="{quote(str(v), safe="")}"' for k, v in sorted(oauth_params.items())
        )

        return {
            "Authorization": auth_header,
            "Content-Type": "application/json"
        }

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict = None,
        data: dict = None,
        files: dict = None,
        use_upload: bool = False
    ) -> dict:
        """
        Make a request to Twitter API.

        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request body
            files: Files to upload
            use_upload: Use upload.twitter.com instead

        Returns:
            API response as dictionary

        Raises:
            TwitterAPIError: If API call fails
        """
        base_url = self.API_UPLOAD_URL if use_upload else f"{self.API_BASE_URL}/{self.API_VERSION}"
        url = f"{base_url}/{endpoint}"

        headers = self._get_auth_headers(method, url, params)

        try:
            if method == "GET":
                response = self._session.get(url, params=params, headers=headers, timeout=30)
            elif method == "POST":
                if files:
                    response = self._session.post(url, params=params, headers=headers, files=files, data=data, timeout=30)
                else:
                    response = self._session.post(url, params=params, headers=headers, json=data, timeout=30)
            elif method == "DELETE":
                response = self._session.delete(url, params=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            if response.content:
                return response.json()
            return {}

        except requests.RequestException as e:
            raise TwitterAPIError(f"Request failed: {e}")

    def get_user_id(self) -> str:
        """
        Get authenticated user's ID.

        Returns:
            User ID string
        """
        if self._user_id:
            return self._user_id

        result = self._make_request("users/me", params={"user.fields": "id,username,name"})
        self._user_id = result.get("data", {}).get("id", "")
        return self._user_id

    def get_me(self) -> dict:
        """
        Get authenticated user information.

        Returns:
            User information dictionary
        """
        result = self._make_request("users/me", params={
            "user.fields": "id,username,name,description,public_metrics,profile_image_url,verified"
        })
        return result.get("data", {})

    def publish_tweet(
        self,
        text: str,
        media_urls: list = None,
        reply_to: str = None,
        quote_tweet: str = None
    ) -> Tweet:
        """
        Publish a tweet.

        Args:
            text: Tweet text (max 280 characters)
            media_urls: List of media URLs to attach
            reply_to: Tweet ID to reply to
            quote_tweet: Tweet ID to quote

        Returns:
            Tweet with tweet details
        """
        # Prepare tweet payload
        payload = {"text": text}

        # Handle media attachments
        if media_urls:
            media_ids = []
            for media_url in media_urls:
                media_id = self._upload_media(media_url)
                if media_id:
                    media_ids.append(media_id)

            if media_ids:
                payload["media"] = {"media_ids": media_ids}

        # Handle reply
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}

        # Handle quote tweet
        if quote_tweet:
            payload["quote_tweet_id"] = quote_tweet

        # Publish tweet
        result = self._make_request("tweets", method="POST", data=payload)

        tweet_data = result.get("data", {})
        tweet = Tweet(
            text=text,
            media_urls=media_urls or [],
            reply_to=reply_to or "",
            tweet_id=tweet_data.get("id", ""),
            created_at=datetime.now().isoformat()
        )

        logger.info(f"Published tweet: {tweet.tweet_id}")
        return tweet

    def publish_thread(self, tweets: list) -> list:
        """
        Publish a thread of tweets.

        Args:
            tweets: List of tweet texts in order

        Returns:
            List of Tweet objects
        """
        if not tweets:
            return []

        published_tweets = []
        previous_tweet_id = None

        for i, text in enumerate(tweets):
            # First tweet in thread
            if i == 0:
                tweet = self.publish_tweet(text)
            else:
                # Reply to previous tweet
                tweet = self.publish_tweet(text, reply_to=previous_tweet_id)

            if tweet.tweet_id:
                published_tweets.append(tweet)
                previous_tweet_id = tweet.tweet_id
                time.sleep(1)  # Rate limiting

        logger.info(f"Published thread with {len(published_tweets)} tweets")
        return published_tweets

    def _upload_media(self, media_url: str) -> Optional[str]:
        """
        Upload media to Twitter.

        Args:
            media_url: URL of media to upload

        Returns:
            Media ID string or None
        """
        try:
            # Download media
            response = requests.get(media_url, timeout=30)
            response.raise_for_status()
            media_data = response.content

            # Determine media type
            content_type = response.headers.get("content-type", "image/jpeg")

            # INIT upload
            init_result = self._make_request(
                "media/upload",
                method="POST",
                params={
                    "command": "INIT",
                    "media_type": content_type,
                    "total_bytes": len(media_data)
                },
                use_upload=True
            )
            media_id = init_result.get("media_id_string", "")

            if not media_id:
                logger.error("Failed to initialize media upload")
                return None

            # APPEND upload
            # Twitter requires chunked upload for large files
            # For simplicity, we'll use single chunk for small files
            self._make_request(
                "media/upload",
                method="POST",
                params={"command": "APPEND", "media_id": media_id, "segment_index": 0},
                data=media_data,
                use_upload=True
            )

            # FINALIZE upload
            self._make_request(
                "media/upload",
                method="POST",
                params={"command": "FINALIZE", "media_id": media_id},
                use_upload=True
            )

            # Check processing status (for videos/GIFs)
            status_result = self._check_media_status(media_id)
            if status_result == "failed":
                return None

            return media_id

        except Exception as e:
            logger.error(f"Media upload failed: {e}")
            return None

    def _check_media_status(self, media_id: str, timeout: int = 30) -> str:
        """
        Check media processing status.

        Args:
            media_id: Media ID
            timeout: Maximum wait time

        Returns:
            Status string (succeeded, failed, processing)
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = self._make_request(
                "media/upload",
                params={"command": "STATUS", "media_id": media_id},
                use_upload=True
            )

            status = result.get("processing_info", {}).get("state", "succeeded")

            if status == "succeeded":
                return "succeeded"
            elif status == "failed":
                return "failed"

            time.sleep(2)

        return "processing"

    def get_tweet_metrics(self, tweet_id: str = None) -> EngagementMetrics:
        """
        Get engagement metrics for a tweet.

        Args:
            tweet_id: Tweet ID (uses latest if not provided)

        Returns:
            EngagementMetrics object
        """
        # If no tweet_id, get latest tweet
        if not tweet_id:
            tweets = self.get_recent_tweets(limit=1)
            if tweets:
                tweet_id = tweets[0].get("id", "")

        if not tweet_id:
            return EngagementMetrics(tweet_id="")

        # Get tweet with public metrics
        result = self._make_request(
            f"tweets/{tweet_id}",
            params={
                "tweet.fields": "public_metrics,created_at,text",
                "expansions": "author_id"
            }
        )

        tweet_data = result.get("data", {})
        metrics = tweet_data.get("public_metrics", {})

        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        quotes = metrics.get("quote_count", 0)

        # Calculate engagement rate (simplified)
        total_engagement = likes + retweets + replies + quotes
        # Note: impressions require elevated API access
        engagement_rate = total_engagement  # Fallback without impressions

        return EngagementMetrics(
            tweet_id=tweet_id,
            likes=likes,
            retweets=retweets,
            replies=replies,
            quotes=quotes,
            engagement_rate=engagement_rate
        )

    def get_recent_tweets(self, limit: int = 10) -> list:
        """
        Get recent tweets from authenticated user.

        Args:
            limit: Number of tweets to retrieve

        Returns:
            List of tweet dictionaries
        """
        user_id = self.get_user_id()

        if not user_id:
            return []

        result = self._make_request(
            f"users/{user_id}/tweets",
            params={
                "max_results": min(limit, 100),
                "tweet.fields": "id,text,created_at,public_metrics,entities"
            }
        )

        return result.get("data", [])

    def get_mentions(self, limit: int = 10) -> list:
        """
        Get recent mentions of the authenticated user.

        Args:
            limit: Number of mentions to retrieve

        Returns:
            List of mention dictionaries
        """
        user_id = self.get_user_id()

        if not user_id:
            return []

        result = self._make_request(
            f"users/{user_id}/mentions",
            params={
                "max_results": min(limit, 100),
                "tweet.fields": "id,text,created_at,author_id,public_metrics"
            }
        )

        return result.get("data", [])

    def reply_to_tweet(
        self,
        tweet_id: str,
        text: str,
        media_urls: list = None
    ) -> Tweet:
        """
        Reply to a tweet.

        Args:
            tweet_id: Tweet ID to reply to
            text: Reply text
            media_urls: Media URLs to attach

        Returns:
            Tweet with reply details
        """
        return self.publish_tweet(text, media_urls=media_urls, reply_to=tweet_id)

    def retweet(self, tweet_id: str) -> bool:
        """
        Retweet a tweet.

        Args:
            tweet_id: Tweet ID to retweet

        Returns:
            True if successful
        """
        user_id = self.get_user_id()

        result = self._make_request(
            f"users/{user_id}/retweets",
            method="POST",
            data={"tweet_id": tweet_id}
        )

        success = result.get("data", {}).get("retweeted", False)
        if success:
            logger.info(f"Retweeted: {tweet_id}")
        return success

    def like_tweet(self, tweet_id: str) -> bool:
        """
        Like a tweet.

        Args:
            tweet_id: Tweet ID to like

        Returns:
            True if successful
        """
        user_id = self.get_user_id()

        result = self._make_request(
            f"users/{user_id}/likes",
            method="POST",
            data={"tweet_id": tweet_id}
        )

        success = result.get("data", {}).get("liked", False)
        if success:
            logger.info(f"Liked: {tweet_id}")
        return success

    def delete_tweet(self, tweet_id: str) -> bool:
        """
        Delete a tweet.

        Args:
            tweet_id: Tweet ID to delete

        Returns:
            True if successful
        """
        try:
            self._make_request(f"tweets/{tweet_id}", method="DELETE")
            logger.info(f"Deleted tweet: {tweet_id}")
            return True
        except TwitterAPIError as e:
            logger.error(f"Failed to delete tweet {tweet_id}: {e}")
            return False

    def generate_tweet_content(
        self,
        post_type: str = "educational",
        topic: str = "",
        include_hashtags: bool = True
    ) -> dict:
        """
        Generate tweet content based on type.

        Args:
            post_type: Type of post (educational, case_study, sales_cta, thread)
            topic: Topic for the tweet
            include_hashtags: Whether to include hashtags

        Returns:
            Dictionary with generated content
        """
        templates = {
            "educational": {
                "structure": "hook + tip + takeaway",
                "max_length": 260,
                "hashtags": ["#LearnOnTwitter", "#Tips", "#Thread"]
            },
            "case_study": {
                "structure": "problem + solution + result + CTA",
                "max_length": 260,
                "hashtags": ["#CaseStudy", "#Results", "#Success"]
            },
            "sales_cta": {
                "structure": "benefit + urgency + CTA",
                "max_length": 260,
                "hashtags": ["#SpecialOffer", "#LimitedTime"]
            },
            "thread": {
                "structure": "hook + numbered points + summary",
                "max_length": 280,
                "hashtags": ["#Thread", "#TwitterThread"]
            }
        }

        template = templates.get(post_type, templates["educational"])

        content = {
            "post_type": post_type,
            "topic": topic,
            "structure": template["structure"],
            "max_length": template["max_length"],
            "suggested_hashtags": template["hashtags"] if include_hashtags else [],
            "generated_at": datetime.now().isoformat()
        }

        return content


class TwitterAPIError(Exception):
    """Custom exception for Twitter API errors."""
    pass


# =============================================================================
# Factory Function
# =============================================================================

def create_twitter_agent(
    api_key: str = None,
    api_secret: str = None,
    access_token: str = None,
    access_token_secret: str = None,
    bearer_token: str = None
) -> TwitterAgent:
    """
    Create a Twitter agent.

    Args:
        api_key: API Key
        api_secret: API Secret
        access_token: Access Token
        access_token_secret: Access Token Secret
        bearer_token: Bearer Token

    Returns:
        TwitterAgent instance
    """
    return TwitterAgent(
        api_key=api_key,
        api_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        bearer_token=bearer_token
    )


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for Twitter agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Twitter Agent")
    parser.add_argument("--api-key", type=str, help="Twitter API Key")
    parser.add_argument("--api-secret", type=str, help="Twitter API Secret")
    parser.add_argument("--access-token", type=str, help="Access Token")
    parser.add_argument("--access-secret", type=str, help="Access Token Secret")
    parser.add_argument("--bearer-token", type=str, help="Bearer Token")
    parser.add_argument("--tweet", type=str, help="Post a tweet")
    parser.add_argument("--metrics", type=str, help="Get metrics for tweet ID")
    parser.add_argument("--recent", action="store_true", help="Get recent tweets")
    parser.add_argument("--mentions", action="store_true", help="Get mentions")
    parser.add_argument("--info", action="store_true", help="Get user info")

    args = parser.parse_args()

    print("=" * 70)
    print("Twitter (X) Agent")
    print("=" * 70)

    try:
        agent = TwitterAgent(
            api_key=args.api_key,
            api_secret=args.api_secret,
            access_token=args.access_token,
            access_token_secret=args.access_secret,
            bearer_token=args.bearer_token
        )

        if not agent.is_configured:
            print("\n⚠️  Twitter not configured.")
            print("Set TWITTER_API_KEY, TWITTER_API_SECRET, etc. in .env")
            return

        if args.info:
            print("\n👤 User Information:")
            info = agent.get_me()
            for key, value in info.items():
                print(f"   {key}: {value}")

        elif args.tweet:
            print(f"\n📝 Publishing tweet...")
            result = agent.publish_tweet(args.tweet)
            print(f"   ✅ Tweet published: {result.tweet_id}")

        elif args.metrics:
            print(f"\n📊 Getting metrics for tweet {args.metrics}...")
            metrics = agent.get_tweet_metrics(args.metrics)
            print(f"   Likes: {metrics.likes}")
            print(f"   Retweets: {metrics.retweets}")
            print(f"   Replies: {metrics.replies}")
            print(f"   Quotes: {metrics.quotes}")

        elif args.recent:
            print("\n📜 Recent Tweets:")
            tweets = agent.get_recent_tweets(limit=5)
            for tweet in tweets:
                print(f"   - {tweet.get('id', 'N/A')}: {tweet.get('text', '')[:50]}...")

        elif args.mentions:
            print("\n📬 Recent Mentions:")
            mentions = agent.get_mentions(limit=5)
            for mention in mentions:
                print(f"   - {mention.get('id', 'N/A')}: {mention.get('text', '')[:50]}...")

        else:
            print("\nUsage: python -m modules.social.twitter_agent --info|--tweet|--metrics|--recent|--mentions")

    except TwitterAPIError as e:
        print(f"\n❌ Twitter API Error: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
