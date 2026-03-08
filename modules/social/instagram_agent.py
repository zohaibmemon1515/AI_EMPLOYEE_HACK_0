#!/usr/bin/env python3
r"""
Instagram Agent - Social Media Automation

Provides Instagram integration for the AI Employee:
- Post generation and scheduling
- Story publishing
- Reels publishing
- Engagement metrics collection
- Hashtag optimization

Note: Requires Instagram Business Account and Facebook App.

Usage:
    from modules.social.instagram_agent import InstagramAgent

    agent = InstagramAgent(instagram_business_account_id, access_token)
    agent.publish_post(image_url, caption="Hello World!")
    metrics = agent.get_engagement_metrics(media_id)
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict

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
class InstagramPost:
    """Instagram post data."""
    caption: str
    image_url: str = ""
    video_url: str = ""
    is_carousel: bool = False
    carousel_media: list = None
    hashtags: list = None
    location_id: str = ""
    media_id: str = ""
    container_id: str = ""
    is_published: bool = False
    created_time: str = ""


@dataclass
class EngagementMetrics:
    """Engagement metrics for a post."""
    media_id: str
    likes: int = 0
    comments: int = 0
    saves: int = 0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0
    collected_at: str = ""

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now().isoformat()


class InstagramAgent:
    """
    Instagram Graph API Agent.

    Handles all Instagram operations including:
    - Publishing posts (image, video, carousel)
    - Publishing stories
    - Publishing reels
    - Retrieving engagement metrics
    - Managing media library
    """

    GRAPH_API_VERSION = "v18.0"
    GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(
        self,
        instagram_business_account_id: str = None,
        access_token: str = None,
        facebook_page_id: str = None,
    ):
        """
        Initialize Instagram agent.

        Args:
            instagram_business_account_id: Instagram Business Account ID
            access_token: Facebook/Instagram Access Token
            facebook_page_id: Connected Facebook Page ID
        """
        # Load from environment if not provided
        self.instagram_business_account_id = instagram_business_account_id or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        self.facebook_page_id = facebook_page_id or os.getenv("FACEBOOK_PAGE_ID", "")

        # Session
        self._session = requests.Session()

        # Validate configuration
        self._validate_config()

        logger.info(f"InstagramAgent initialized for account {self.instagram_business_account_id}")

    def _validate_config(self):
        """Validate configuration."""
        if not self.instagram_business_account_id:
            logger.warning("Instagram Business Account ID not configured")
        if not self.access_token:
            logger.warning("Instagram Access Token not configured")

    @property
    def is_configured(self) -> bool:
        """Check if agent is properly configured."""
        return bool(self.instagram_business_account_id and self.access_token)

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict = None,
        data: dict = None,
        files: dict = None
    ) -> dict:
        """
        Make a request to Instagram Graph API.

        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request body
            files: Files to upload

        Returns:
            API response as dictionary

        Raises:
            InstagramAPIError: If API call fails
        """
        url = f"{self.GRAPH_API_BASE}/{endpoint}"

        # Add access token to params
        if params is None:
            params = {}
        params["access_token"] = self.access_token

        try:
            if method == "GET":
                response = self._session.get(url, params=params, timeout=30)
            elif method == "POST":
                response = self._session.post(url, params=params, data=data, files=files, timeout=30)
            elif method == "DELETE":
                response = self._session.delete(url, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            result = response.json()

            # Check for API errors
            if isinstance(result, dict) and "error" in result:
                error = result["error"]
                raise InstagramAPIError(
                    f"Instagram API Error: {error.get('message', 'Unknown error')} "
                    f"(Code: {error.get('code', 'N/A')})"
                )

            return result

        except requests.RequestException as e:
            raise InstagramAPIError(f"Request failed: {e}")

    def _wait_for_container(self, container_id: str, timeout: int = 60) -> bool:
        """
        Wait for container to be ready for publishing.

        Args:
            container_id: Container ID to check
            timeout: Maximum wait time in seconds

        Returns:
            True if ready, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = self._make_request(
                    container_id,
                    params={"fields": "status_code"}
                )
                if result.get("status_code") == "FINISHED":
                    return True
            except InstagramAPIError:
                pass
            time.sleep(2)
        return False

    def get_account_info(self) -> dict:
        """
        Get Instagram business account information.

        Returns:
            Account information dictionary
        """
        return self._make_request(
            self.instagram_business_account_id,
            params={
                "fields": "id,username,biography,website,followers_count,follows_count,media_count,profile_picture_url"
            }
        )

    def publish_post(
        self,
        image_url: str,
        caption: str,
        is_carousel: bool = False,
        carousel_media: list = None,
        location_id: str = None,
        share_to_feed: bool = True
    ) -> InstagramPost:
        """
        Publish an image post to Instagram.

        Args:
            image_url: URL of image to publish
            caption: Post caption
            is_carousel: Whether this is a carousel post
            carousel_media: List of media URLs for carousel
            location_id: Location ID to tag
            share_to_feed: Whether to share to feed

        Returns:
            InstagramPost with post details
        """
        # Step 1: Create media container
        container_params = {
            "image_url": image_url,
            "caption": caption,
            "media_type": "IMAGE"
        }

        if location_id:
            container_params["location_id"] = location_id

        if is_carousel and carousel_media:
            # Create containers for each carousel item
            children_ids = []
            for media_url in carousel_media:
                child_result = self._make_request(
                    f"{self.instagram_business_account_id}/media",
                    method="POST",
                    data={
                        "image_url": media_url,
                        "media_type": "IMAGE",
                        "is_carousel_item": "true"
                    }
                )
                children_ids.append(child_result.get("id", ""))
                time.sleep(1)  # Rate limiting

            container_params["media_type"] = "CAROUSEL"
            container_params["children"] = ",".join(children_ids)

        container_result = self._make_request(
            f"{self.instagram_business_account_id}/media",
            method="POST",
            data=container_params
        )

        container_id = container_result.get("id", "")

        # Step 2: Wait for container to be ready
        if not self._wait_for_container(container_id):
            raise InstagramAPIError("Container did not finish processing")

        # Step 3: Publish the media
        publish_result = self._make_request(
            f"{self.instagram_business_account_id}/media_publish",
            method="POST",
            data={
                "creation_id": container_id,
                "share_to_feed": str(share_to_feed).lower()
            }
        )

        media_id = publish_result.get("id", "")

        post = InstagramPost(
            caption=caption,
            image_url=image_url,
            is_carousel=is_carousel,
            carousel_media=carousel_media or [],
            location_id=location_id or "",
            media_id=media_id,
            container_id=container_id,
            is_published=True,
            created_time=datetime.now().isoformat()
        )

        logger.info(f"Published Instagram post: {media_id}")
        return post

    def publish_reel(
        self,
        video_url: str,
        caption: str,
        thumbnail_url: str = None,
        share_to_feed: bool = True
    ) -> InstagramPost:
        """
        Publish a Reel to Instagram.

        Args:
            video_url: URL of video to publish
            caption: Reel caption
            thumbnail_url: URL of thumbnail image
            share_to_feed: Whether to share to feed

        Returns:
            InstagramPost with reel details
        """
        # Step 1: Create reel container
        container_params = {
            "video_url": video_url,
            "media_type": "REELS",
            "caption": caption
        }

        if thumbnail_url:
            container_params["thumbnail_url"] = thumbnail_url

        container_result = self._make_request(
            f"{self.instagram_business_account_id}/media",
            method="POST",
            data=container_params
        )

        container_id = container_result.get("id", "")

        # Step 2: Wait for container to be ready (reels take longer)
        if not self._wait_for_container(container_id, timeout=120):
            raise InstagramAPIError("Reel container did not finish processing")

        # Step 3: Publish the reel
        publish_result = self._make_request(
            f"{self.instagram_business_account_id}/media_publish",
            method="POST",
            data={
                "creation_id": container_id,
                "share_to_feed": str(share_to_feed).lower()
            }
        )

        media_id = publish_result.get("id", "")

        post = InstagramPost(
            caption=caption,
            video_url=video_url,
            media_id=media_id,
            container_id=container_id,
            is_published=True,
            created_time=datetime.now().isoformat()
        )

        logger.info(f"Published Instagram reel: {media_id}")
        return post

    def publish_story(
        self,
        image_url: str,
        caption: str = ""
    ) -> InstagramPost:
        """
        Publish a story to Instagram.

        Args:
            image_url: URL of image for story
            caption: Story caption/sticker text

        Returns:
            InstagramPost with story details
        """
        # Create story container
        container_result = self._make_request(
            f"{self.instagram_business_account_id}/media",
            method="POST",
            data={
                "image_url": image_url,
                "media_type": "STORIES",
                "caption": caption
            }
        )

        container_id = container_result.get("id", "")

        # Wait for container
        if not self._wait_for_container(container_id):
            raise InstagramAPIError("Story container did not finish processing")

        # Publish story
        publish_result = self._make_request(
            f"{self.instagram_business_account_id}/media_publish",
            method="POST",
            data={"creation_id": container_id}
        )

        media_id = publish_result.get("id", "")

        post = InstagramPost(
            caption=caption,
            image_url=image_url,
            media_id=media_id,
            container_id=container_id,
            is_published=True,
            created_time=datetime.now().isoformat()
        )

        logger.info(f"Published Instagram story: {media_id}")
        return post

    def get_engagement_metrics(self, media_id: str = None) -> EngagementMetrics:
        """
        Get engagement metrics for a post.

        Args:
            media_id: Media ID (uses latest if not provided)

        Returns:
            EngagementMetrics object
        """
        # If no media_id, get latest media
        if not media_id:
            media = self.get_recent_media(limit=1)
            if media:
                media_id = media[0].get("id", "")

        if not media_id:
            return EngagementMetrics(media_id="")

        # Get media insights
        fields = [
            "like_count",
            "comments_count",
            "saved_count",
            "reach",
            "impressions"
        ]

        try:
            result = self._make_request(
                media_id,
                params={"fields": ",".join(fields)}
            )

            likes = result.get("like_count", 0) or 0
            comments = result.get("comments_count", 0) or 0
            saves = result.get("saved_count", 0) or 0
            reach = result.get("reach", 0) or 0
            impressions = result.get("impressions", 0) or 0

            # Calculate engagement rate
            total_engagement = likes + comments + saves
            engagement_rate = (total_engagement / reach * 100) if reach > 0 else 0

            return EngagementMetrics(
                media_id=media_id,
                likes=likes,
                comments=comments,
                saves=saves,
                reach=reach,
                impressions=impressions,
                engagement_rate=round(engagement_rate, 2)
            )

        except InstagramAPIError as e:
            logger.warning(f"Could not get metrics for {media_id}: {e}")
            return EngagementMetrics(media_id=media_id)

    def get_recent_media(self, limit: int = 10) -> list:
        """
        Get recent media from Instagram account.

        Args:
            limit: Number of media items to retrieve

        Returns:
            List of media dictionaries
        """
        result = self._make_request(
            f"{self.instagram_business_account_id}/media",
            params={
                "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
                "limit": limit
            }
        )
        return result.get("data", [])

    def get_media_insights(self, media_id: str) -> dict:
        """
        Get detailed insights for a media item.

        Args:
            media_id: Media ID

        Returns:
            Insights dictionary
        """
        result = self._make_request(
            f"{media_id}/insights",
            params={
                "metric": "reach,impressions,engagement,saved,video_views"
            }
        )

        insights = {}
        for item in result.get("data", []):
            name = item.get("name", "")
            values = item.get("values", [])
            insights[name] = values[0].get("value", 0) if values else 0

        return insights

    def get_account_insights(
        self,
        metric_names: list = None,
        since: str = None,
        until: str = None
    ) -> dict:
        """
        Get account-level insights.

        Args:
            metric_names: List of metrics to retrieve
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)

        Returns:
            Insights dictionary
        """
        if metric_names is None:
            metric_names = [
                "follower_count",
                "reach",
                "impressions",
                "profile_views",
                "website_clicks"
            ]

        params = {"metric": ",".join(metric_names)}

        if since:
            params["since"] = since
        if until:
            params["until"] = until

        result = self._make_request(
            f"{self.instagram_business_account_id}/insights",
            params=params
        )

        insights = {}
        for item in result.get("data", []):
            name = item.get("name", "")
            values = item.get("values", [])
            insights[name] = {
                "values": values,
                "title": item.get("title", "")
            }

        return insights

    def generate_hashtags(
        self,
        topic: str,
        count: int = 30,
        category: str = "mixed"
    ) -> list:
        """
        Generate relevant hashtags for a post.

        Args:
            topic: Post topic
            count: Number of hashtags to generate
            category: Category type (trending, niche, mixed)

        Returns:
            List of hashtags
        """
        # Base hashtag templates by category
        hashtag_templates = {
            "trending": [
                "#trending", "#viral", "#explore", "#fyp", "#instagood",
                "#photooftheday", "#beautiful", "#happy", "#love", "#follow"
            ],
            "niche": [
                "#smallbusiness", "#entrepreneur", "#businesstips", "#marketing",
                "#growth", "#success", "#motivation", "#inspiration", "#goals"
            ],
            "engagement": [
                "#likeforlikes", "#followforfollowback", "#instadaily",
                "#instalike", "#instamood", "#picoftheday", "#daily"
            ]
        }

        # Generate topic-specific hashtags
        topic_tags = [
            f"#{topic.replace(' ', '')}",
            f"#{topic.lower().replace(' ', '')}",
        ]

        # Select based on category
        if category == "mixed":
            selected = []
            for cat_tags in hashtag_templates.values():
                selected.extend(cat_tags[:count // 3])
        else:
            selected = hashtag_templates.get(category, hashtag_templates["niche"])

        # Combine and limit
        all_tags = topic_tags + selected
        return all_tags[:min(count, 30)]

    def delete_media(self, media_id: str) -> bool:
        """
        Delete a media item.

        Args:
            media_id: Media ID to delete

        Returns:
            True if successful
        """
        try:
            self._make_request(media_id, method="DELETE")
            logger.info(f"Deleted Instagram media: {media_id}")
            return True
        except InstagramAPIError as e:
            logger.error(f"Failed to delete media {media_id}: {e}")
            return False


class InstagramAPIError(Exception):
    """Custom exception for Instagram API errors."""
    pass


# =============================================================================
# Factory Function
# =============================================================================

def create_instagram_agent(
    instagram_business_account_id: str = None,
    access_token: str = None
) -> InstagramAgent:
    """
    Create an Instagram agent.

    Args:
        instagram_business_account_id: Business Account ID
        access_token: Access Token

    Returns:
        InstagramAgent instance
    """
    return InstagramAgent(instagram_business_account_id, access_token)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for Instagram agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Instagram Agent")
    parser.add_argument("--account-id", type=str, help="Instagram Business Account ID")
    parser.add_argument("--token", type=str, help="Access Token")
    parser.add_argument("--post-image", type=str, help="Image URL to post")
    parser.add_argument("--caption", type=str, help="Post caption")
    parser.add_argument("--metrics", type=str, help="Get metrics for media ID")
    parser.add_argument("--recent", action="store_true", help="Get recent media")
    parser.add_argument("--info", action="store_true", help="Get account info")

    args = parser.parse_args()

    print("=" * 70)
    print("Instagram Agent")
    print("=" * 70)

    try:
        agent = InstagramAgent(
            instagram_business_account_id=args.account_id,
            access_token=args.token
        )

        if not agent.is_configured:
            print("\n⚠️  Instagram not configured.")
            print("Set INSTAGRAM_BUSINESS_ACCOUNT_ID and INSTAGRAM_ACCESS_TOKEN in .env")
            return

        if args.info:
            print("\n📄 Account Information:")
            info = agent.get_account_info()
            for key, value in info.items():
                print(f"   {key}: {value}")

        elif args.post_image and args.caption:
            print(f"\n📝 Publishing post...")
            result = agent.publish_post(args.post_image, args.caption)
            print(f"   ✅ Post published: {result.media_id}")

        elif args.metrics:
            print(f"\n📊 Getting metrics for media {args.metrics}...")
            metrics = agent.get_engagement_metrics(args.metrics)
            print(f"   Likes: {metrics.likes}")
            print(f"   Comments: {metrics.comments}")
            print(f"   Saves: {metrics.saves}")
            print(f"   Reach: {metrics.reach}")
            print(f"   Engagement Rate: {metrics.engagement_rate}%")

        elif args.recent:
            print("\n📜 Recent Media:")
            media = agent.get_recent_media(limit=5)
            for item in media:
                print(f"   - {item.get('id', 'N/A')}: {item.get('caption', '')[:50]}...")

        else:
            print("\nUsage: python -m modules.social.instagram_agent --info|--post|--metrics|--recent")

    except InstagramAPIError as e:
        print(f"\n❌ Instagram API Error: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
