#!/usr/bin/env python3
r"""
Facebook Agent - Social Media Automation

Provides Facebook integration for the AI Employee:
- Post generation and scheduling
- Post publishing via Graph API
- Engagement metrics collection
- Page management

Note: Requires Facebook App and Page Access Token.

Usage:
    from modules.social.facebook_agent import FacebookAgent

    agent = FacebookAgent(page_access_token)
    agent.publish_post("Hello World!", image_url="https://...")
    metrics = agent.get_engagement_metrics(post_id)
"""

import json
import logging
import os
import hashlib
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
class FacebookPost:
    """Facebook post data."""
    message: str
    link: str = ""
    image_url: str = ""
    video_url: str = ""
    scheduled_time: str = ""
    is_published: bool = False
    post_id: str = ""
    created_time: str = ""


@dataclass
class EngagementMetrics:
    """Engagement metrics for a post."""
    post_id: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    reactions: dict = None
    engagement_rate: float = 0.0
    reach: int = 0
    impressions: int = 0
    collected_at: str = ""

    def __post_init__(self):
        if self.reactions is None:
            self.reactions = {}
        if not self.collected_at:
            self.collected_at = datetime.now().isoformat()


class FacebookAgent:
    """
    Facebook Graph API Agent.

    Handles all Facebook operations including:
    - Publishing posts to pages
    - Scheduling posts
    - Retrieving engagement metrics
    - Managing page content
    """

    GRAPH_API_VERSION = "v18.0"
    GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(
        self,
        page_access_token: str = None,
        page_id: str = None,
        app_id: str = None,
        app_secret: str = None,
    ):
        """
        Initialize Facebook agent.

        Args:
            page_access_token: Facebook Page Access Token
            page_id: Facebook Page ID
            app_id: Facebook App ID
            app_secret: Facebook App Secret
        """
        # Load from environment if not provided
        self.page_access_token = page_access_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
        self.page_id = page_id or os.getenv("FACEBOOK_PAGE_ID", "")
        self.app_id = app_id or os.getenv("FACEBOOK_APP_ID", "")
        self.app_secret = app_secret or os.getenv("FACEBOOK_APP_SECRET", "")

        # Session
        self._session = requests.Session()

        # Validate configuration
        self._validate_config()

        logger.info(f"FacebookAgent initialized for page {self.page_id}")

    def _validate_config(self):
        """Validate configuration."""
        if not self.page_access_token:
            logger.warning("Facebook Page Access Token not configured")
        if not self.page_id:
            logger.warning("Facebook Page ID not configured")

    @property
    def is_configured(self) -> bool:
        """Check if agent is properly configured."""
        return bool(self.page_access_token and self.page_id)

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict = None,
        data: dict = None,
        files: dict = None
    ) -> dict:
        """
        Make a request to Facebook Graph API.

        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request body
            files: Files to upload

        Returns:
            API response as dictionary

        Raises:
            FacebookAPIError: If API call fails
        """
        url = f"{self.GRAPH_API_BASE}/{endpoint}"

        # Add access token to params
        if params is None:
            params = {}
        params["access_token"] = self.page_access_token

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
                raise FacebookAPIError(
                    f"Facebook API Error: {error.get('message', 'Unknown error')} "
                    f"(Code: {error.get('code', 'N/A')})"
                )

            return result

        except requests.RequestException as e:
            raise FacebookAPIError(f"Request failed: {e}")

    def get_page_info(self) -> dict:
        """
        Get page information.

        Returns:
            Page information dictionary
        """
        return self._make_request(
            self.page_id,
            params={"fields": "id,name,username,category,followers_count,likes,about,website"}
        )

    def publish_post(
        self,
        message: str,
        link: str = None,
        image_url: str = None,
        video_url: str = None,
        scheduled_time: str = None,
        published: bool = True
    ) -> FacebookPost:
        """
        Publish a post to Facebook page.

        Args:
            message: Post message/content
            link: Link to share
            image_url: URL of image to attach
            video_url: URL of video to attach
            scheduled_time: ISO 8601 datetime for scheduling
            published: Whether to publish immediately

        Returns:
            FacebookPost with post details
        """
        endpoint = f"{self.page_id}/feed"

        data = {
            "message": message,
            "published": str(published).lower()
        }

        if link:
            data["link"] = link
        if image_url:
            data["attached_media"] = json.dumps([{"media_url": image_url}])
        if video_url:
            data["attached_media"] = json.dumps([{"media_url": video_url}])
        if scheduled_time:
            data["scheduled_publish_time"] = scheduled_time
            data["published"] = "false"

        result = self._make_request(endpoint, method="POST", data=data)

        post = FacebookPost(
            message=message,
            link=link or "",
            image_url=image_url or "",
            video_url=video_url or "",
            scheduled_time=scheduled_time or "",
            is_published=published,
            post_id=result.get("id", ""),
            created_time=datetime.now().isoformat()
        )

        logger.info(f"Published Facebook post: {post.post_id}")
        return post

    def upload_photo(
        self,
        photo_url: str,
        caption: str = "",
        published: bool = True
    ) -> dict:
        """
        Upload a photo to Facebook page.

        Args:
            photo_url: URL of photo to upload
            caption: Photo caption
            published: Whether to publish immediately

        Returns:
            Photo upload result
        """
        endpoint = f"{self.page_id}/photos"

        data = {
            "url": photo_url,
            "caption": caption,
            "published": str(published).lower()
        }

        result = self._make_request(endpoint, method="POST", data=data)
        logger.info(f"Uploaded Facebook photo: {result.get('id', '')}")
        return result

    def upload_video(
        self,
        video_url: str,
        title: str,
        description: str = "",
        published: bool = True
    ) -> dict:
        """
        Upload a video to Facebook page.

        Args:
            video_url: URL of video to upload
            title: Video title
            description: Video description
            published: Whether to publish immediately

        Returns:
            Video upload result
        """
        endpoint = f"{self.page_id}/videos"

        data = {
            "file_url": video_url,
            "title": title,
            "description": description,
            "published": str(published).lower()
        }

        result = self._make_request(endpoint, method="POST", data=data)
        logger.info(f"Uploaded Facebook video: {result.get('id', '')}")
        return result

    def get_engagement_metrics(self, post_id: str = None) -> EngagementMetrics:
        """
        Get engagement metrics for a post.

        Args:
            post_id: Post ID (uses latest if not provided)

        Returns:
            EngagementMetrics object
        """
        # If no post_id, get latest post
        if not post_id:
            posts = self.get_recent_posts(limit=1)
            if posts:
                post_id = posts[0].get("id", "")

        if not post_id:
            return EngagementMetrics(post_id="")

        # Get post insights
        fields = [
            "message", "created_time", "permalink_url",
            "likes.summary(true)",
            "comments.summary(true)",
            "shares"
        ]

        result = self._make_request(
            post_id,
            params={"fields": ",".join(fields)}
        )

        likes_data = result.get("likes", {})
        comments_data = result.get("comments", {})
        shares_data = result.get("shares", {})

        likes_count = likes_data.get("summary", {}).get("total_count", 0)
        comments_count = comments_data.get("summary", {}).get("total_count", 0)
        shares_count = shares_data.get("count", 0)

        # Get detailed reactions
        reactions = self._get_reactions(post_id)

        # Calculate engagement rate (simplified)
        total_engagement = likes_count + comments_count + shares_count
        page_info = self.get_page_info()
        followers = page_info.get("followers_count", 1)
        engagement_rate = (total_engagement / followers * 100) if followers > 0 else 0

        return EngagementMetrics(
            post_id=post_id,
            likes=likes_count,
            comments=comments_count,
            shares=shares_count,
            reactions=reactions,
            engagement_rate=round(engagement_rate, 2),
            collected_at=datetime.now().isoformat()
        )

    def _get_reactions(self, post_id: str) -> dict:
        """Get detailed reaction breakdown."""
        try:
            result = self._make_request(
                f"{post_id}/reactions",
                params={"summary": "true"}
            )

            # Count reaction types
            reactions = {"like": 0, "love": 0, "wow": 0, "haha": 0, "sad": 0, "angry": 0}
            for reaction in result.get("data", []):
                reaction_type = reaction.get("type", "like").lower()
                if reaction_type in reactions:
                    reactions[reaction_type] += 1

            return reactions
        except FacebookAPIError:
            return {}

    def get_recent_posts(self, limit: int = 10) -> list:
        """
        Get recent posts from page.

        Args:
            limit: Number of posts to retrieve

        Returns:
            List of post dictionaries
        """
        result = self._make_request(
            f"{self.page_id}/feed",
            params={
                "fields": "id,message,created_time,permalink_url,full_picture,type",
                "limit": limit
            }
        )
        return result.get("data", [])

    def get_scheduled_posts(self) -> list:
        """
        Get scheduled posts.

        Returns:
            List of scheduled post dictionaries
        """
        result = self._make_request(
            f"{self.page_id}/scheduled_posts",
            params={"fields": "id,message,scheduled_publish_time,created_time"}
        )
        return result.get("data", [])

    def delete_post(self, post_id: str) -> bool:
        """
        Delete a post.

        Args:
            post_id: Post ID to delete

        Returns:
            True if successful
        """
        try:
            self._make_request(post_id, method="DELETE")
            logger.info(f"Deleted Facebook post: {post_id}")
            return True
        except FacebookAPIError as e:
            logger.error(f"Failed to delete post {post_id}: {e}")
            return False

    def get_insights(
        self,
        metric_names: list = None,
        since: str = None,
        until: str = None
    ) -> dict:
        """
        Get page insights.

        Args:
            metric_names: List of metrics to retrieve
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)

        Returns:
            Insights dictionary
        """
        if metric_names is None:
            metric_names = [
                "page_impressions",
                "page_reach",
                "page_engaged_users",
                "page_post_engagements",
                "page_likes"
            ]

        params = {
            "metric": ",".join(metric_names),
            "period": "day"
        }

        if since:
            params["since"] = since
        if until:
            params["until"] = until

        result = self._make_request(
            f"{self.page_id}/insights",
            params=params
        )

        # Process insights into cleaner format
        insights = {}
        for item in result.get("data", []):
            name = item.get("name", "")
            values = item.get("values", [])
            insights[name] = {
                "values": values,
                "title": item.get("title", ""),
                "description": item.get("description", "")
            }

        return insights

    def generate_post_content(
        self,
        post_type: str = "educational",
        topic: str = "",
        brand_voice: str = "professional"
    ) -> dict:
        """
        Generate post content based on type.

        Args:
            post_type: Type of post (educational, case_study, sales_cta)
            topic: Topic for the post
            brand_voice: Brand voice (professional, casual, friendly)

        Returns:
            Dictionary with generated content
        """
        templates = {
            "educational": {
                "hook": "📚 Did you know?",
                "structure": "tip_explanation",
                "cta": "Save this for later! 💾",
                "hashtags": ["#LearnWithUs", "#Tips", "#Education"]
            },
            "case_study": {
                "hook": "🎯 Success Story",
                "structure": "problem_solution_result",
                "cta": "Want similar results? Let's talk!",
                "hashtags": ["#CaseStudy", "#Success", "#Results"]
            },
            "sales_cta": {
                "hook": "🚀 Special Offer",
                "structure": "benefit_urgency_cta",
                "cta": "Click the link to get started!",
                "hashtags": ["#SpecialOffer", "#LimitedTime", "#ActNow"]
            }
        }

        template = templates.get(post_type, templates["educational"])

        content = {
            "post_type": post_type,
            "hook": template["hook"],
            "topic": topic,
            "brand_voice": brand_voice,
            "suggested_hashtags": template["hashtags"],
            "cta": template["cta"],
            "generated_at": datetime.now().isoformat()
        }

        return content


class FacebookAPIError(Exception):
    """Custom exception for Facebook API errors."""
    pass


# =============================================================================
# Factory Function
# =============================================================================

def create_facebook_agent(
    page_access_token: str = None,
    page_id: str = None
) -> FacebookAgent:
    """
    Create a Facebook agent.

    Args:
        page_access_token: Page Access Token
        page_id: Page ID

    Returns:
        FacebookAgent instance
    """
    return FacebookAgent(page_access_token, page_id)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for Facebook agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Facebook Agent")
    parser.add_argument("--page-id", type=str, help="Facebook Page ID")
    parser.add_argument("--token", type=str, help="Page Access Token")
    parser.add_argument("--post", type=str, help="Post a message")
    parser.add_argument("--metrics", type=str, help="Get metrics for post ID")
    parser.add_argument("--recent", action="store_true", help="Get recent posts")
    parser.add_argument("--info", action="store_true", help="Get page info")

    args = parser.parse_args()

    print("=" * 70)
    print("Facebook Agent")
    print("=" * 70)

    try:
        agent = FacebookAgent(
            page_access_token=args.token,
            page_id=args.page_id
        )

        if not agent.is_configured:
            print("\n⚠️  Facebook not configured.")
            print("Set FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID in .env")
            return

        if args.info:
            print("\n📄 Page Information:")
            info = agent.get_page_info()
            for key, value in info.items():
                print(f"   {key}: {value}")

        elif args.post:
            print(f"\n📝 Publishing post...")
            result = agent.publish_post(args.post)
            print(f"   ✅ Post published: {result.post_id}")

        elif args.metrics:
            print(f"\n📊 Getting metrics for post {args.metrics}...")
            metrics = agent.get_engagement_metrics(args.metrics)
            print(f"   Likes: {metrics.likes}")
            print(f"   Comments: {metrics.comments}")
            print(f"   Shares: {metrics.shares}")
            print(f"   Engagement Rate: {metrics.engagement_rate}%")

        elif args.recent:
            print("\n📜 Recent Posts:")
            posts = agent.get_recent_posts(limit=5)
            for post in posts:
                print(f"   - {post.get('id', 'N/A')}: {post.get('message', '')[:50]}...")

        else:
            print("\nUsage: python -m modules.social.facebook_agent --info|--post|--metrics|--recent")

    except FacebookAPIError as e:
        print(f"\n❌ Facebook API Error: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
