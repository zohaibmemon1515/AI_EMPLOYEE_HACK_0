#!/usr/bin/env python3
r"""
Social Media Scheduler - Cross-Platform Post Scheduling

Provides unified scheduling for social media posts across:
- Facebook
- Instagram
- Twitter (X)

Features:
- Queue management
- Scheduled publishing
- Post templates
- Optimal time suggestions
- Batch operations

Usage:
    from modules.social.social_scheduler import SocialScheduler

    scheduler = SocialScheduler(vault_path)
    scheduler.schedule_post("facebook", content, scheduled_time)
    scheduler.process_queue()
"""

import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

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


class Platform(Enum):
    """Supported social media platforms."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


class PostStatus(Enum):
    """Post scheduling status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PostType(Enum):
    """Types of social media posts."""
    EDUCATIONAL = "educational"
    CASE_STUDY = "case_study"
    SALES_CTA = "sales_cta"
    ENGAGEMENT = "engagement"
    ANNOUNCEMENT = "announcement"
    BEHIND_THE_SCENES = "behind_the_scenes"


@dataclass
class ScheduledPost:
    """Scheduled post data."""
    post_id: str
    platform: str
    post_type: str
    content: str
    media_urls: list
    scheduled_time: str
    status: str
    hashtags: list = None
    metadata: dict = None
    created_at: str = ""
    published_at: str = ""
    result: dict = None

    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.result is None:
            self.result = {}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class SocialScheduler:
    """
    Social Media Post Scheduler.

    Manages scheduling and publishing of posts across multiple platforms:
    - Creates post queue in vault
    - Processes scheduled posts at appropriate times
    - Tracks publishing status
    - Generates post reports
    """

    def __init__(self, vault_path: Path = None):
        """
        Initialize social scheduler.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.pending_approval = self.vault_path / "Pending_Approval"
        self.social_folder = self.vault_path / "Social_Media"
        self.scheduled_folder = self.social_folder / "Scheduled"
        self.published_folder = self.social_folder / "Published"
        self.failed_folder = self.social_folder / "Failed"
        self.templates_folder = self.social_folder / "Templates"

        # Create folders
        for folder in [
            self.social_folder,
            self.scheduled_folder,
            self.published_folder,
            self.failed_folder,
            self.templates_folder,
            self.pending_approval
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        # Queue state
        self.queue_file = self.scheduled_folder / "queue.json"
        self._load_queue()

        logger.info(f"SocialScheduler initialized at {self.social_folder}")

    def _load_queue(self):
        """Load post queue from file."""
        if self.queue_file.exists():
            try:
                data = json.loads(self.queue_file.read_text())
                self.queue = data.get("posts", [])
                self.last_processed = data.get("last_processed")
            except Exception as e:
                logger.warning(f"Could not load queue: {e}")
                self.queue = []
                self.last_processed = None
        else:
            self.queue = []
            self.last_processed = None

    def _save_queue(self):
        """Save post queue to file."""
        data = {
            "posts": self.queue,
            "last_processed": self.last_processed,
            "updated_at": datetime.now().isoformat()
        }
        self.queue_file.write_text(json.dumps(data, indent=2))

    def schedule_post(
        self,
        platform: str,
        content: str,
        scheduled_time: datetime = None,
        post_type: str = "educational",
        media_urls: list = None,
        hashtags: list = None,
        metadata: dict = None
    ) -> ScheduledPost:
        """
        Schedule a post for publishing.

        Args:
            platform: Target platform (facebook, instagram, twitter)
            content: Post content/caption
            scheduled_time: When to publish (defaults to 1 hour from now)
            post_type: Type of post
            media_urls: Media URLs to attach
            hashtags: Hashtags to include
            metadata: Additional metadata

        Returns:
            ScheduledPost object
        """
        # Generate post ID
        post_id = f"SOCIAL_{platform.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Default scheduled time
        if scheduled_time is None:
            scheduled_time = datetime.now() + timedelta(hours=1)

        # Create scheduled post
        post = ScheduledPost(
            post_id=post_id,
            platform=platform,
            post_type=post_type,
            content=content,
            media_urls=media_urls or [],
            scheduled_time=scheduled_time.isoformat(),
            status=PostStatus.SCHEDULED.value,
            hashtags=hashtags or [],
            metadata=metadata or {}
        )

        # Add to queue
        self.queue.append(post.to_dict())
        self._save_queue()

        # Create markdown file for approval
        self._create_post_file(post)

        logger.info(f"Scheduled {platform} post: {post_id} for {scheduled_time}")
        return post

    def _create_post_file(self, post: ScheduledPost):
        """Create markdown file for the scheduled post."""
        filepath = self.pending_approval / f"{post.post_id}.md"

        content = f"""---
post_id: {post.post_id}
platform: {post.platform}
post_type: {post.post_type}
scheduled_time: {post.scheduled_time}
status: {post.status}
created_at: {post.created_at}
---

# Social Media Post: {post.post_id}

## Platform
{post.platform.upper()}

## Post Type
{post.post_type}

## Content

```
{post.content}
```

## Hashtags
{', '.join(post.hashtags) if post.hashtags else 'None'}

## Media
{chr(10).join(f'- {url}' for url in post.media_urls) if post.media_urls else 'None'}

## Scheduled Time
{post.scheduled_time}

---
*Move to Approved/ to publish, Rejected/ to cancel*
"""
        filepath.write_text(content, encoding="utf-8")

    def get_queue(self, status: str = None, platform: str = None) -> list:
        """
        Get posts from queue.

        Args:
            status: Filter by status
            platform: Filter by platform

        Returns:
            List of post dictionaries
        """
        posts = self.queue

        if status:
            posts = [p for p in posts if p.get("status") == status]

        if platform:
            posts = [p for p in posts if p.get("platform") == platform]

        # Sort by scheduled time
        posts = sorted(posts, key=lambda p: p.get("scheduled_time", ""))

        return posts

    def get_due_posts(self) -> list:
        """
        Get posts that are due for publishing.

        Returns:
            List of due post dictionaries
        """
        now = datetime.now()

        due_posts = []
        for post in self.queue:
            if post.get("status") != PostStatus.SCHEDULED.value:
                continue

            scheduled_time = datetime.fromisoformat(post.get("scheduled_time", ""))
            if scheduled_time <= now:
                due_posts.append(post)

        return due_posts

    def process_queue(self) -> dict:
        """
        Process due posts in the queue.

        Returns:
            Processing result dictionary
        """
        result = {
            "processed": 0,
            "published": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        due_posts = self.get_due_posts()

        if not due_posts:
            logger.info("No posts due for publishing")
            return result

        logger.info(f"Processing {len(due_posts)} due posts")

        for post_data in due_posts:
            try:
                # Check if post file is approved
                post_file = self.pending_approval / f"{post_data['post_id']}.md"
                approved_file = self.vault_path / "Approved" / f"{post_data['post_id']}.md"

                if not approved_file.exists() and not post_file.exists():
                    result["skipped"] += 1
                    continue

                # Publish the post
                publish_result = self._publish_post(post_data)

                if publish_result.get("success"):
                    post_data["status"] = PostStatus.PUBLISHED.value
                    post_data["published_at"] = datetime.now().isoformat()
                    post_data["result"] = publish_result.get("data", {})
                    result["published"] += 1

                    # Move file to published
                    if post_file.exists():
                        shutil.move(str(post_file), str(self.published_folder / post_file.name))
                    if approved_file.exists():
                        approved_file.unlink()

                    logger.info(f"Published post: {post_data['post_id']}")
                else:
                    post_data["status"] = PostStatus.FAILED.value
                    post_data["result"] = {"error": publish_result.get("error", "Unknown error")}
                    result["failed"] += 1
                    result["errors"].append(f"{post_data['post_id']}: {publish_result.get('error')}")

                    # Move file to failed
                    if post_file.exists():
                        shutil.move(str(post_file), str(self.failed_folder / post_file.name))

            except Exception as e:
                post_data["status"] = PostStatus.FAILED.value
                post_data["result"] = {"error": str(e)}
                result["failed"] += 1
                result["errors"].append(f"{post_data['post_id']}: {str(e)}")
                logger.error(f"Failed to process post {post_data['post_id']}: {e}")

            result["processed"] += 1

        self.last_processed = datetime.now().isoformat()
        self._save_queue()

        return result

    def _publish_post(self, post_data: dict) -> dict:
        """
        Publish a post to the target platform.

        Args:
            post_data: Post data dictionary

        Returns:
            Publish result dictionary
        """
        platform = post_data.get("platform", "")
        content = post_data.get("content", "")
        media_urls = post_data.get("media_urls", [])
        hashtags = post_data.get("hashtags", [])

        # Add hashtags to content
        if hashtags:
            hashtag_text = " " + " ".join(hashtags)
            if len(content) + len(hashtag_text) <= 280:  # Twitter limit
                content = content + hashtag_text

        try:
            if platform == "facebook":
                return self._publish_to_facebook(content, media_urls)
            elif platform == "instagram":
                return self._publish_to_instagram(content, media_urls)
            elif platform == "twitter":
                return self._publish_to_twitter(content, media_urls)
            else:
                return {"success": False, "error": f"Unsupported platform: {platform}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _publish_to_facebook(self, content: str, media_urls: list) -> dict:
        """Publish to Facebook."""
        try:
            from .facebook_agent import FacebookAgent

            agent = FacebookAgent()
            if not agent.is_configured:
                return {"success": False, "error": "Facebook not configured"}

            image_url = media_urls[0] if media_urls else None
            post = agent.publish_post(message=content, image_url=image_url)

            return {
                "success": True,
                "data": {
                    "post_id": post.post_id,
                    "platform": "facebook"
                }
            }
        except ImportError:
            return {"success": False, "error": "Facebook agent not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _publish_to_instagram(self, content: str, media_urls: list) -> dict:
        """Publish to Instagram."""
        try:
            from .instagram_agent import InstagramAgent

            agent = InstagramAgent()
            if not agent.is_configured:
                return {"success": False, "error": "Instagram not configured"}

            image_url = media_urls[0] if media_urls else None
            if not image_url:
                return {"success": False, "error": "Instagram requires an image"}

            post = agent.publish_post(image_url=image_url, caption=content)

            return {
                "success": True,
                "data": {
                    "media_id": post.media_id,
                    "platform": "instagram"
                }
            }
        except ImportError:
            return {"success": False, "error": "Instagram agent not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _publish_to_twitter(self, content: str, media_urls: list) -> dict:
        """Publish to Twitter."""
        try:
            from .twitter_agent import TwitterAgent

            agent = TwitterAgent()
            if not agent.is_configured:
                return {"success": False, "error": "Twitter not configured"}

            tweet = agent.publish_tweet(text=content, media_urls=media_urls)

            return {
                "success": True,
                "data": {
                    "tweet_id": tweet.tweet_id,
                    "platform": "twitter"
                }
            }
        except ImportError:
            return {"success": False, "error": "Twitter agent not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_post(self, post_id: str) -> bool:
        """
        Cancel a scheduled post.

        Args:
            post_id: Post ID to cancel

        Returns:
            True if successful
        """
        for post in self.queue:
            if post.get("post_id") == post_id:
                post["status"] = PostStatus.CANCELLED.value
                self._save_queue()

                # Move file
                post_file = self.pending_approval / f"{post_id}.md"
                if post_file.exists():
                    post_file.unlink()

                logger.info(f"Cancelled post: {post_id}")
                return True

        return False

    def get_optimal_posting_times(self, platform: str = None) -> dict:
        """
        Get optimal posting times based on best practices.

        Args:
            platform: Specific platform or None for all

        Returns:
            Dictionary of optimal times by platform
        """
        optimal_times = {
            "facebook": {
                "weekdays": ["09:00", "13:00", "15:00"],
                "weekend": ["12:00", "13:00", "16:00"],
                "best_day": "Wednesday"
            },
            "instagram": {
                "weekdays": ["09:00", "11:00", "19:00"],
                "weekend": ["10:00", "11:00", "14:00"],
                "best_day": "Tuesday"
            },
            "twitter": {
                "weekdays": ["08:00", "12:00", "17:00"],
                "weekend": ["09:00", "10:00", "12:00"],
                "best_day": "Wednesday"
            }
        }

        if platform:
            return optimal_times.get(platform, {})

        return optimal_times

    def generate_weekly_content_plan(
        self,
        start_date: datetime = None,
        posts_per_day: int = 1,
        platforms: list = None
    ) -> list:
        """
        Generate a weekly content plan.

        Args:
            start_date: Start date (defaults to next Monday)
            posts_per_day: Posts per day
            platforms: Platforms to include

        Returns:
            List of scheduled post suggestions
        """
        if start_date is None:
            # Next Monday
            today = datetime.now()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            start_date = today + timedelta(days=days_until_monday)

        if platforms is None:
            platforms = ["facebook", "instagram", "twitter"]

        # Post type rotation
        post_types = [
            PostType.EDUCATIONAL.value,
            PostType.CASE_STUDY.value,
            PostType.SALES_CTA.value,
            PostType.ENGAGEMENT.value,
            PostType.ANNOUNCEMENT.value
        ]

        plan = []
        current_date = start_date

        for day_offset in range(7):  # 7 days
            current_day = current_date + timedelta(days=day_offset)
            is_weekend = current_day.weekday() >= 5

            optimal_times = self.get_optimal_posting_times()

            for post_idx in range(posts_per_day):
                for platform in platforms:
                    platform_times = optimal_times.get(platform, {})
                    times = platform_times.get("weekend" if is_weekend else "weekdays", ["12:00"])

                    time_str = times[post_idx % len(times)]
                    hour, minute = map(int, time_str.split(":"))

                    scheduled_time = current_day.replace(hour=hour, minute=minute, second=0)

                    plan.append({
                        "platform": platform,
                        "post_type": post_types[(day_offset * posts_per_day + post_idx) % len(post_types)],
                        "scheduled_date": current_day.strftime("%Y-%m-%d"),
                        "scheduled_time": scheduled_time.isoformat(),
                        "day_of_week": current_day.strftime("%A")
                    })

        return plan

    def create_post_template(
        self,
        name: str,
        post_type: str,
        template_content: str,
        platform: str = "all",
        hashtags: list = None
    ) -> Path:
        """
        Create a reusable post template.

        Args:
            name: Template name
            post_type: Type of post
            template_content: Template content with {{placeholders}}
            platform: Target platform
            hashtags: Default hashtags

        Returns:
            Path to template file
        """
        filepath = self.templates_folder / f"{name}.md"

        content = f"""---
template_name: {name}
post_type: {post_type}
platform: {platform}
created_at: {datetime.now().isoformat()}
---

# Template: {name}

## Type
{post_type}

## Platform
{platform}

## Content Template

```
{template_content}
```

## Default Hashtags
{', '.join(hashtags) if hashtags else 'None'}

## Usage Notes

Replace the following placeholders:
- {{{{topic}}}}: Main topic of the post
- {{{{cta}}}}: Call to action
- {{{{link}}}}: URL to include

"""
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Created template: {name}")
        return filepath

    def get_stats(self) -> dict:
        """
        Get scheduler statistics.

        Returns:
            Statistics dictionary
        """
        status_counts = {}
        platform_counts = {}

        for post in self.queue:
            status = post.get("status", "unknown")
            platform = post.get("platform", "unknown")

            status_counts[status] = status_counts.get(status, 0) + 1
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        return {
            "total_posts": len(self.queue),
            "by_status": status_counts,
            "by_platform": platform_counts,
            "last_processed": self.last_processed,
            "queue_file": str(self.queue_file)
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_scheduler(vault_path: Path = None) -> SocialScheduler:
    """
    Create a social media scheduler.

    Args:
        vault_path: Path to vault

    Returns:
        SocialScheduler instance
    """
    return SocialScheduler(vault_path)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for social scheduler."""
    import argparse

    parser = argparse.ArgumentParser(description="Social Media Scheduler")
    parser.add_argument("--vault", type=str, help="Vault path")
    parser.add_argument("--schedule", type=str, help="Schedule a post")
    parser.add_argument("--platform", type=str, default="facebook", help="Target platform")
    parser.add_argument("--time", type=str, help="Scheduled time (ISO format)")
    parser.add_argument("--process", action="store_true", help="Process due posts")
    parser.add_argument("--queue", action="store_true", help="Show queue")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--plan", action="store_true", help="Generate weekly plan")

    args = parser.parse_args()

    print("=" * 70)
    print("Social Media Scheduler")
    print("=" * 70)

    try:
        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        scheduler = SocialScheduler(vault_path)

        if args.schedule:
            print(f"\n📅 Scheduling {args.platform} post...")
            scheduled_time = None
            if args.time:
                scheduled_time = datetime.fromisoformat(args.time)

            post = scheduler.schedule_post(
                platform=args.platform,
                content=args.schedule,
                scheduled_time=scheduled_time
            )
            print(f"   ✅ Post scheduled: {post.post_id}")
            print(f"   🕐 Time: {post.scheduled_time}")

        elif args.process:
            print("\n⚙️ Processing due posts...")
            result = scheduler.process_queue()
            print(f"\n{'='*70}")
            print(f"Processed: {result['processed']}")
            print(f"Published: {result['published']}")
            print(f"Failed: {result['failed']}")
            print(f"Skipped: {result['skipped']}")
            if result['errors']:
                print(f"Errors: {', '.join(result['errors'])}")

        elif args.queue:
            print("\n📋 Post Queue:")
            posts = scheduler.get_queue()
            if posts:
                for post in posts[:10]:
                    print(f"   - {post['post_id']}: {post['platform']} @ {post['scheduled_time']} ({post['status']})")
            else:
                print("   (empty)")

        elif args.stats:
            print("\n📊 Statistics:")
            stats = scheduler.get_stats()
            print(f"   Total Posts: {stats['total_posts']}")
            print(f"   By Status: {stats['by_status']}")
            print(f"   By Platform: {stats['by_platform']}")

        elif args.plan:
            print("\n📅 Weekly Content Plan:")
            plan = scheduler.generate_weekly_content_plan()
            for item in plan[:10]:
                print(f"   - {item['scheduled_date']} ({item['day_of_week']}): "
                      f"{item['platform']} - {item['post_type']} @ {item['scheduled_time']}")
            print(f"   ... and {len(plan) - 10} more" if len(plan) > 10 else "")

        else:
            print("\nUsage: python -m modules.social.social_scheduler --schedule|--process|--queue|--stats|--plan")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
