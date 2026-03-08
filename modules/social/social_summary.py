#!/usr/bin/env python3
r"""
Social Media Summary Generator - Engagement Analytics and Reporting

Generates comprehensive social media performance reports:
- Cross-platform engagement metrics
- Post performance analysis
- Growth tracking
- Weekly/monthly summaries
- Recommendations for improvement

Usage:
    from modules.social.social_summary import SocialSummaryGenerator

    generator = SocialSummaryGenerator(vault_path)
    summary = generator.generate_weekly_summary()
    generator.save_summary(summary)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict, field

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
class PlatformMetrics:
    """Metrics for a single platform."""
    platform: str
    posts_count: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_reach: int = 0
    total_impressions: int = 0
    avg_engagement_rate: float = 0.0
    top_post_id: str = ""
    top_post_engagement: int = 0
    follower_count: int = 0
    follower_change: int = 0


@dataclass
class PostPerformance:
    """Individual post performance data."""
    post_id: str
    platform: str
    content_preview: str
    posted_at: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    reach: int = 0
    engagement_rate: float = 0.0


@dataclass
class SocialSummary:
    """Complete social media summary."""
    summary_id: str
    period_start: str
    period_end: str
    generated_at: str
    platform_metrics: list = field(default_factory=list)
    top_posts: list = field(default_factory=list)
    total_posts: int = 0
    total_engagement: int = 0
    avg_engagement_rate: float = 0.0
    best_performing_platform: str = ""
    recommendations: list = field(default_factory=list)
    insights: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class SocialSummaryGenerator:
    """
    Social Media Summary Generator.

    Generates comprehensive reports on social media performance:
    - Aggregates metrics from all platforms
    - Identifies top-performing content
    - Tracks growth trends
    - Provides actionable recommendations
    """

    def __init__(self, vault_path: Path = None):
        """
        Initialize summary generator.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.logs_path = self.vault_path / "Logs"
        self.social_folder = self.vault_path / "Social_Media"
        self.reports_folder = self.social_folder / "Reports"

        # Create folders
        for folder in [self.logs_path, self.social_folder, self.reports_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        # Metrics cache
        self.metrics_cache_file = self.social_folder / "metrics_cache.json"
        self._load_metrics_cache()

        logger.info(f"SocialSummaryGenerator initialized at {self.reports_folder}")

    def _load_metrics_cache(self):
        """Load cached metrics from file."""
        if self.metrics_cache_file.exists():
            try:
                data = json.loads(self.metrics_cache_file.read_text())
                self.metrics_cache = data.get("metrics", {})
            except Exception as e:
                logger.warning(f"Could not load metrics cache: {e}")
                self.metrics_cache = {}
        else:
            self.metrics_cache = {}

    def _save_metrics_cache(self):
        """Save metrics cache to file."""
        data = {
            "metrics": self.metrics_cache,
            "updated_at": datetime.now().isoformat()
        }
        self.metrics_cache_file.write_text(json.dumps(data, indent=2))

    def cache_metrics(self, platform: str, post_id: str, metrics: dict):
        """
        Cache metrics for a post.

        Args:
            platform: Platform name
            post_id: Post ID
            metrics: Metrics dictionary
        """
        if platform not in self.metrics_cache:
            self.metrics_cache[platform] = {}

        self.metrics_cache[platform][post_id] = {
            **metrics,
            "cached_at": datetime.now().isoformat()
        }
        self._save_metrics_cache()

    def get_cached_metrics(self, platform: str, post_id: str) -> Optional[dict]:
        """
        Get cached metrics for a post.

        Args:
            platform: Platform name
            post_id: Post ID

        Returns:
            Metrics dictionary or None
        """
        return self.metrics_cache.get(platform, {}).get(post_id)

    def generate_weekly_summary(
        self,
        end_date: datetime = None,
        include_recommendations: bool = True
    ) -> SocialSummary:
        """
        Generate weekly social media summary.

        Args:
            end_date: End date for the period (defaults to today)
            include_recommendations: Whether to include recommendations

        Returns:
            SocialSummary object
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=7)

        summary_id = f"SOCIAL_WEEKLY_{end_date.strftime('%Y%m%d')}"

        summary = SocialSummary(
            summary_id=summary_id,
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            generated_at=datetime.now().isoformat()
        )

        # Collect metrics from each platform
        platform_metrics = []
        all_posts = []

        for platform in ["facebook", "instagram", "twitter"]:
            try:
                metrics, posts = self._collect_platform_metrics(platform, start_date, end_date)
                platform_metrics.append(metrics)
                all_posts.extend(posts)
            except Exception as e:
                logger.warning(f"Could not collect {platform} metrics: {e}")
                platform_metrics.append(PlatformMetrics(platform=platform))

        summary.platform_metrics = platform_metrics
        summary.total_posts = sum(m.posts_count for m in platform_metrics)

        # Calculate total engagement
        summary.total_engagement = sum(
            m.total_likes + m.total_comments + m.total_shares
            for m in platform_metrics
        )

        # Calculate average engagement rate
        rates = [m.avg_engagement_rate for m in platform_metrics if m.avg_engagement_rate > 0]
        summary.avg_engagement_rate = sum(rates) / len(rates) if rates else 0

        # Find top posts
        all_posts.sort(key=lambda p: p.engagement_rate, reverse=True)
        summary.top_posts = [asdict(p) for p in all_posts[:5]]

        # Find best performing platform
        if platform_metrics:
            best = max(platform_metrics, key=lambda m: m.avg_engagement_rate)
            summary.best_performing_platform = best.platform

        # Generate insights and recommendations
        if include_recommendations:
            summary.insights = self._generate_insights(platform_metrics, all_posts)
            summary.recommendations = self._generate_recommendations(summary)

        return summary

    def _collect_platform_metrics(
        self,
        platform: str,
        start_date: datetime,
        end_date: datetime
    ) -> tuple:
        """
        Collect metrics for a specific platform.

        Args:
            platform: Platform name
            start_date: Period start
            end_date: Period end

        Returns:
            Tuple of (PlatformMetrics, list of PostPerformance)
        """
        metrics = PlatformMetrics(platform=platform)
        posts = []

        try:
            if platform == "facebook":
                from .facebook_agent import FacebookAgent
                agent = FacebookAgent()

                if agent.is_configured:
                    # Get recent posts
                    fb_posts = agent.get_recent_posts(limit=50)

                    for post in fb_posts:
                        post_date = datetime.fromisoformat(post.get("created_time", "").replace("Z", "+00:00")).replace(tzinfo=None)
                        if start_date <= post_date <= end_date:
                            # Get engagement metrics
                            post_metrics = agent.get_engagement_metrics(post.get("id"))

                            metrics.posts_count += 1
                            metrics.total_likes += post_metrics.likes
                            metrics.total_comments += post_metrics.comments
                            metrics.total_shares += post_metrics.shares

                            if post_metrics.engagement_rate > metrics.avg_engagement_rate:
                                metrics.avg_engagement_rate = post_metrics.engagement_rate
                                metrics.top_post_id = post_metrics.post_id
                                metrics.top_post_engagement = post_metrics.likes + post_metrics.comments + post_metrics.shares

                            posts.append(PostPerformance(
                                post_id=post.get("id", ""),
                                platform=platform,
                                content_preview=post.get("message", "")[:100],
                                posted_at=post.get("created_time", ""),
                                likes=post_metrics.likes,
                                comments=post_metrics.comments,
                                shares=post_metrics.shares,
                                engagement_rate=post_metrics.engagement_rate
                            ))

            elif platform == "instagram":
                from .instagram_agent import InstagramAgent
                agent = InstagramAgent()

                if agent.is_configured:
                    # Get recent media
                    ig_media = agent.get_recent_media(limit=50)

                    for media in ig_media:
                        media_date = datetime.fromisoformat(media.get("timestamp", "").replace("Z", "+00:00")).replace(tzinfo=None)
                        if start_date <= media_date <= end_date:
                            # Get engagement metrics
                            post_metrics = agent.get_engagement_metrics(media.get("id"))

                            metrics.posts_count += 1
                            metrics.total_likes += post_metrics.likes
                            metrics.total_comments += post_metrics.comments

                            if post_metrics.engagement_rate > metrics.avg_engagement_rate:
                                metrics.avg_engagement_rate = post_metrics.engagement_rate
                                metrics.top_post_id = post_metrics.media_id
                                metrics.top_post_engagement = post_metrics.likes + post_metrics.comments

                            posts.append(PostPerformance(
                                post_id=media.get("id", ""),
                                platform=platform,
                                content_preview=media.get("caption", "")[:100],
                                posted_at=media.get("timestamp", ""),
                                likes=post_metrics.likes,
                                comments=post_metrics.comments,
                                engagement_rate=post_metrics.engagement_rate
                            ))

            elif platform == "twitter":
                from .twitter_agent import TwitterAgent
                agent = TwitterAgent()

                if agent.is_configured:
                    # Get recent tweets
                    tw_posts = agent.get_recent_tweets(limit=50)

                    for tweet in tw_posts:
                        tweet_date = datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00")).replace(tzinfo=None)
                        if start_date <= tweet_date <= end_date:
                            # Get engagement metrics
                            post_metrics = agent.get_tweet_metrics(tweet.get("id"))

                            metrics.posts_count += 1
                            metrics.total_likes += post_metrics.likes
                            metrics.total_comments += post_metrics.replies
                            metrics.total_shares += post_metrics.retweets

                            if post_metrics.engagement_rate > metrics.avg_engagement_rate:
                                metrics.avg_engagement_rate = post_metrics.engagement_rate
                                metrics.top_post_id = post_metrics.tweet_id
                                metrics.top_post_engagement = post_metrics.likes + post_metrics.replies + post_metrics.retweets

                            posts.append(PostPerformance(
                                post_id=tweet.get("id", ""),
                                platform=platform,
                                content_preview=tweet.get("text", "")[:100],
                                posted_at=tweet.get("created_at", ""),
                                likes=post_metrics.likes,
                                comments=post_metrics.replies,
                                shares=post_metrics.retweets,
                                engagement_rate=post_metrics.engagement_rate
                            ))

        except ImportError:
            logger.warning(f"{platform} agent not available")
        except Exception as e:
            logger.error(f"Error collecting {platform} metrics: {e}")

        return metrics, posts

    def _generate_insights(self, platform_metrics: list, posts: list) -> list:
        """
        Generate insights from metrics.

        Args:
            platform_metrics: List of platform metrics
            posts: List of post performances

        Returns:
            List of insight strings
        """
        insights = []

        # Total posts insight
        total_posts = sum(m.posts_count for m in platform_metrics)
        if total_posts > 0:
            insights.append(f"Published {total_posts} posts across all platforms this week")

        # Best platform insight
        if platform_metrics:
            best = max(platform_metrics, key=lambda m: m.posts_count)
            if best.posts_count > 0:
                insights.append(f"Most active platform: {best.platform} ({best.posts_count} posts)")

        # Engagement insight
        active_platforms = [m for m in platform_metrics if m.posts_count > 0]
        if active_platforms:
            best_engagement = max(active_platforms, key=lambda m: m.avg_engagement_rate)
            insights.append(
                f"Highest engagement rate: {best_engagement.platform} "
                f"({best_engagement.avg_engagement_rate:.2f}%)"
            )

        # Top post insight
        if posts:
            top_post = posts[0]
            insights.append(
                f"Top performing post on {top_post.platform} with "
                f"{top_post.likes + top_post.comments + top_post.shares} engagements"
            )

        return insights

    def _generate_recommendations(self, summary: SocialSummary) -> list:
        """
        Generate recommendations based on summary.

        Args:
            summary: Social summary

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Posting frequency
        if summary.total_posts < 7:
            recommendations.append(
                "Consider increasing posting frequency to at least 1 post per day "
                "for better audience engagement"
            )

        # Platform focus
        if summary.best_performing_platform:
            recommendations.append(
                f"Focus more content on {summary.best_performing_platform} "
                f"as it shows the highest engagement rate"
            )

        # Engagement rate
        if summary.avg_engagement_rate < 1.0 and summary.total_posts > 0:
            recommendations.append(
                "Engagement rate is below 1%. Consider: "
                "- Using more compelling visuals "
                "- Asking questions to encourage comments "
                "- Posting at optimal times for your audience"
            )

        # Content variety
        platforms_with_posts = [m for m in summary.platform_metrics if m.posts_count > 0]
        if len(platforms_with_posts) < 2:
            recommendations.append(
                "Expand your presence to multiple platforms for broader reach"
            )

        # If no recommendations
        if not recommendations:
            recommendations.append(
                "Great job! Continue maintaining consistent posting schedule "
                "and engaging with your audience"
            )

        return recommendations

    def save_summary(self, summary: SocialSummary) -> Path:
        """
        Save summary to vault.

        Args:
            summary: Summary to save

        Returns:
            Path to saved file
        """
        filename = f"SOCIAL_SUMMARY_{summary.period_end}.md"
        filepath = self.logs_path / filename

        content = self._format_summary_as_markdown(summary)
        filepath.write_text(content, encoding="utf-8")

        logger.info(f"Saved social summary: {filepath}")
        return filepath

    def _format_summary_as_markdown(self, summary: SocialSummary) -> str:
        """Format summary as Markdown."""
        content = f"""---
summary_id: {summary.summary_id}
period_start: {summary.period_start}
period_end: {summary.period_end}
generated_at: {summary.generated_at}
total_posts: {summary.total_posts}
total_engagement: {summary.total_engagement}
avg_engagement_rate: {summary.avg_engagement_rate:.2f}%
best_platform: {summary.best_performing_platform}
---

# Social Media Summary

## Period: {summary.period_start} to {summary.period_end}

## Overview

| Metric | Value |
|--------|-------|
| Total Posts | {summary.total_posts} |
| Total Engagement | {summary.total_engagement} |
| Avg Engagement Rate | {summary.avg_engagement_rate:.2f}% |
| Best Platform | {summary.best_performing_platform} |

## Platform Breakdown

| Platform | Posts | Likes | Comments | Shares | Engagement Rate |
|----------|-------|-------|----------|--------|-----------------|
"""
        for pm in summary.platform_metrics:
            content += f"| {pm.platform} | {pm.posts_count} | {pm.total_likes} | {pm.total_comments} | {pm.total_shares} | {pm.avg_engagement_rate:.2f}% |\n"

        content += f"""
## Top Performing Posts

"""
        for i, post in enumerate(summary.top_posts, 1):
            content += f"""
### {i}. {post['platform']} - {post['post_id'][:20]}...

- **Content**: {post['content_preview']}
- **Posted**: {post['posted_at']}
- **Likes**: {post['likes']} | **Comments**: {post['comments']} | **Shares**: {post['shares']}
- **Engagement Rate**: {post['engagement_rate']:.2f}%

---
"""

        content += f"""
## Insights

"""
        for insight in summary.insights:
            content += f"- {insight}\n"

        content += f"""
## Recommendations

"""
        for rec in summary.recommendations:
            content += f"- {rec}\n"

        content += f"""
---
*Generated by AI Employee Social Media Summary Generator*
"""
        return content

    def generate_monthly_summary(self, year: int = None, month: int = None) -> SocialSummary:
        """
        Generate monthly social media summary.

        Args:
            year: Year (defaults to current)
            month: Month (defaults to current)

        Returns:
            SocialSummary object
        """
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        # Calculate month boundaries
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

        summary_id = f"SOCIAL_MONTHLY_{year}{month:02d}"

        summary = SocialSummary(
            summary_id=summary_id,
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            generated_at=datetime.now().isoformat()
        )

        # Collect metrics (same as weekly but for month period)
        platform_metrics = []
        all_posts = []

        for platform in ["facebook", "instagram", "twitter"]:
            try:
                metrics, posts = self._collect_platform_metrics(platform, start_date, end_date)
                platform_metrics.append(metrics)
                all_posts.extend(posts)
            except Exception as e:
                logger.warning(f"Could not collect {platform} metrics: {e}")

        summary.platform_metrics = platform_metrics
        summary.total_posts = sum(m.posts_count for m in platform_metrics)
        summary.total_engagement = sum(
            m.total_likes + m.total_comments + m.total_shares
            for m in platform_metrics
        )

        rates = [m.avg_engagement_rate for m in platform_metrics if m.avg_engagement_rate > 0]
        summary.avg_engagement_rate = sum(rates) / len(rates) if rates else 0

        all_posts.sort(key=lambda p: p.engagement_rate, reverse=True)
        summary.top_posts = [asdict(p) for p in all_posts[:5]]

        if platform_metrics:
            best = max(platform_metrics, key=lambda m: m.avg_engagement_rate)
            summary.best_performing_platform = best.platform

        summary.insights = self._generate_insights(platform_metrics, all_posts)
        summary.recommendations = self._generate_recommendations(summary)

        return summary


# =============================================================================
# Factory Function
# =============================================================================

def create_summary_generator(vault_path: Path = None) -> SocialSummaryGenerator:
    """
    Create a social summary generator.

    Args:
        vault_path: Path to vault

    Returns:
        SocialSummaryGenerator instance
    """
    return SocialSummaryGenerator(vault_path)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for social summary generator."""
    import argparse

    parser = argparse.ArgumentParser(description="Social Media Summary Generator")
    parser.add_argument("--vault", type=str, help="Vault path")
    parser.add_argument("--weekly", action="store_true", help="Generate weekly summary")
    parser.add_argument("--monthly", action="store_true", help="Generate monthly summary")
    parser.add_argument("--year", type=int, help="Year for monthly summary")
    parser.add_argument("--month", type=int, help="Month for monthly summary")

    args = parser.parse_args()

    print("=" * 70)
    print("Social Media Summary Generator")
    print("=" * 70)

    try:
        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        generator = SocialSummaryGenerator(vault_path)

        if args.weekly or not (args.weekly or args.monthly):
            print("\n📊 Generating weekly summary...")
            summary = generator.generate_weekly_summary()
            filepath = generator.save_summary(summary)

            print(f"\n{'='*70}")
            print(f"Period: {summary.period_start} to {summary.period_end}")
            print(f"Total Posts: {summary.total_posts}")
            print(f"Total Engagement: {summary.total_engagement}")
            print(f"Avg Engagement Rate: {summary.avg_engagement_rate:.2f}%")
            print(f"Best Platform: {summary.best_performing_platform}")
            print(f"\nSaved to: {filepath}")

        elif args.monthly:
            print("\n📊 Generating monthly summary...")
            summary = generator.generate_monthly_summary(args.year, args.month)
            filepath = generator.save_summary(summary)

            print(f"\n{'='*70}")
            print(f"Period: {summary.period_start} to {summary.period_end}")
            print(f"Total Posts: {summary.total_posts}")
            print(f"Total Engagement: {summary.total_engagement}")
            print(f"Saved to: {filepath}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
