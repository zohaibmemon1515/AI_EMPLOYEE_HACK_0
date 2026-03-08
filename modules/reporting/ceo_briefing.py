#!/usr/bin/env python3
r"""
CEO Briefing Generator - Weekly Executive Summary

Generates comprehensive weekly CEO briefings including:
- Business performance summary
- Revenue analysis
- Lead pipeline status
- Marketing performance
- AI employee activities
- Strategic recommendations

Usage:
    from modules.reporting.ceo_briefing import CEOBriefingGenerator

    generator = CEOBriefingGenerator(vault_path)
    briefing = generator.generate_weekly_briefing()
    generator.save_briefing(briefing)
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
class BusinessMetrics:
    """Key business metrics."""
    revenue: float = 0.0
    expenses: float = 0.0
    profit: float = 0.0
    outstanding_invoices: int = 0
    outstanding_amount: float = 0.0
    new_leads: int = 0
    converted_leads: int = 0
    conversion_rate: float = 0.0


@dataclass
class MarketingMetrics:
    """Marketing performance metrics."""
    posts_published: int = 0
    total_reach: int = 0
    total_engagement: int = 0
    avg_engagement_rate: float = 0.0
    top_platform: str = ""
    follower_growth: int = 0


@dataclass
class AIActivitySummary:
    """AI employee activity summary."""
    tasks_completed: int = 0
    emails_processed: int = 0
    emails_sent: int = 0
    whatsapp_messages: int = 0
    social_posts: int = 0
    invoices_created: int = 0
    proposals_generated: int = 0
    hours_saved: float = 0.0


@dataclass
class CEOBriefing:
    """Complete CEO briefing document."""
    briefing_id: str
    period_start: str
    period_end: str
    generated_at: str
    executive_summary: str = ""
    business_metrics: dict = None
    marketing_metrics: dict = None
    ai_activity: dict = None
    key_highlights: list = None
    areas_of_concern: list = None
    recommendations: list = None
    next_week_priorities: list = None

    def __post_init__(self):
        if self.business_metrics is None:
            self.business_metrics = {}
        if self.marketing_metrics is None:
            self.marketing_metrics = {}
        if self.ai_activity is None:
            self.ai_activity = {}
        if self.key_highlights is None:
            self.key_highlights = []
        if self.areas_of_concern is None:
            self.areas_of_concern = []
        if self.recommendations is None:
            self.recommendations = []
        if self.next_week_priorities is None:
            self.next_week_priorities = []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class CEOBriefingGenerator:
    """
    CEO Briefing Generator.

    Generates comprehensive weekly executive briefings
    for business leadership.
    """

    def __init__(self, vault_path: Path = None):
        """
        Initialize CEO briefing generator.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.logs_folder = self.vault_path / "Logs"
        self.done_folder = self.vault_path / "Done"
        self.social_folder = self.vault_path / "Social_Media"
        self.briefings_folder = self.vault_path / "CEO_Briefings"

        # Create folders
        for folder in [self.logs_folder, self.briefings_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        logger.info(f"CEOBriefingGenerator initialized at {self.vault_path}")

    def generate_weekly_briefing(
        self,
        end_date: datetime = None,
        include_recommendations: bool = True
    ) -> CEOBriefing:
        """
        Generate weekly CEO briefing.

        Args:
            end_date: End of reporting period
            include_recommendations: Whether to include AI recommendations

        Returns:
            CEOBriefing object
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=7)

        briefing_id = f"CEO_BRIEFING_{end_date.strftime('%Y%m%d')}"

        briefing = CEOBriefing(
            briefing_id=briefing_id,
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            generated_at=datetime.now().isoformat()
        )

        # Collect business metrics
        logger.info("Collecting business metrics...")
        business_metrics = self._collect_business_metrics(start_date, end_date)
        briefing.business_metrics = asdict(business_metrics)

        # Collect marketing metrics
        logger.info("Collecting marketing metrics...")
        marketing_metrics = self._collect_marketing_metrics(start_date, end_date)
        briefing.marketing_metrics = asdict(marketing_metrics)

        # Collect AI activity summary
        logger.info("Collecting AI activity summary...")
        ai_activity = self._collect_ai_activity(start_date, end_date)
        briefing.ai_activity = asdict(ai_activity)

        # Generate executive summary
        logger.info("Generating executive summary...")
        briefing.executive_summary = self._generate_executive_summary(
            business_metrics, marketing_metrics, ai_activity
        )

        # Generate highlights and concerns
        briefing.key_highlights = self._generate_highlights(
            business_metrics, marketing_metrics, ai_activity
        )
        briefing.areas_of_concern = self._generate_concerns(
            business_metrics, marketing_metrics
        )

        # Generate recommendations
        if include_recommendations:
            briefing.recommendations = self._generate_recommendations(
                business_metrics, marketing_metrics, ai_activity
            )

        # Generate next week priorities
        briefing.next_week_priorities = self._generate_priorities(
            business_metrics, briefing.areas_of_concern
        )

        logger.info(f"Generated briefing {briefing_id}")
        return briefing

    def _collect_business_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> BusinessMetrics:
        """Collect business metrics for the period."""
        metrics = BusinessMetrics()

        try:
            # Read activity logs
            log_files = list(self.logs_folder.glob("*.json"))

            total_revenue = 0.0
            total_expenses = 0.0
            outstanding_count = 0
            outstanding_amount = 0.0
            new_leads = 0
            converted_leads = 0

            for log_file in log_files:
                try:
                    data = json.loads(log_file.read_text())
                    if not isinstance(data, list):
                        continue

                    for entry in data:
                        action = entry.get("action_type", "")
                        timestamp = entry.get("timestamp", "")

                        # Check if within date range
                        if timestamp:
                            try:
                                entry_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                                if not (start_date <= entry_date <= end_date):
                                    continue
                            except:
                                continue

                        # Count actions
                        if action == "invoice_created":
                            amount = entry.get("details", {}).get("amount", 0)
                            total_revenue += float(amount) if amount else 0
                        elif action == "email_sent":
                            pass  # Counted in AI activity
                        elif action == "lead_created":
                            new_leads += 1
                        elif action == "lead_converted":
                            converted_leads += 1

                except Exception as e:
                    logger.debug(f"Error reading log {log_file}: {e}")

            # Count outstanding invoices from Done folder
            if self.done_folder.exists():
                for filepath in self.done_folder.glob("INVOICE_*.md"):
                    try:
                        content = filepath.read_text()
                        if "payment_state" in content and "paid" not in content.lower():
                            outstanding_count += 1
                    except:
                        pass

            metrics.revenue = total_revenue
            metrics.expenses = total_expenses
            metrics.profit = total_revenue - total_expenses
            metrics.outstanding_invoices = outstanding_count
            metrics.outstanding_amount = outstanding_amount
            metrics.new_leads = new_leads
            metrics.converted_leads = converted_leads
            metrics.conversion_rate = (converted_leads / new_leads * 100) if new_leads > 0 else 0

        except Exception as e:
            logger.error(f"Error collecting business metrics: {e}")

        return metrics

    def _collect_marketing_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> MarketingMetrics:
        """Collect marketing metrics for the period."""
        metrics = MarketingMetrics()

        try:
            # Read social media reports
            if self.social_folder.exists():
                reports_folder = self.social_folder / "Reports"
                if reports_folder.exists():
                    for report_file in reports_folder.glob("*.md"):
                        try:
                            content = report_file.read_text()
                            # Parse basic metrics from report
                            if "posts_count" in content:
                                metrics.posts_published += 1
                        except:
                            pass

            # Read social summary logs
            for log_file in self.logs_folder.glob("SOCIAL_SUMMARY_*.md"):
                try:
                    content = log_file.read_text()
                    # Extract metrics from summary
                    if "Total Posts" in content:
                        metrics.posts_published += 1
                except:
                    pass

            # Try to get live metrics from social agents
            try:
                from modules.social.social_summary import SocialSummaryGenerator
                generator = SocialSummaryGenerator(self.vault_path)
                summary = generator.generate_weekly_summary(end_date, include_recommendations=False)

                metrics.total_engagement = summary.total_engagement
                metrics.avg_engagement_rate = summary.avg_engagement_rate
                metrics.top_platform = summary.best_performing_platform

            except ImportError:
                logger.debug("Social summary generator not available")

        except Exception as e:
            logger.error(f"Error collecting marketing metrics: {e}")

        return metrics

    def _collect_ai_activity(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> AIActivitySummary:
        """Collect AI employee activity summary."""
        activity = AIActivitySummary()

        try:
            # Read activity logs
            for log_file in self.logs_folder.glob("*.json"):
                try:
                    data = json.loads(log_file.read_text())
                    if not isinstance(data, list):
                        continue

                    for entry in data:
                        timestamp = entry.get("timestamp", "")
                        actor = entry.get("actor", "").lower()

                        # Check if AI actor
                        if "ai" not in actor and "employee" not in actor:
                            continue

                        # Check date range
                        if timestamp:
                            try:
                                entry_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                                if not (start_date <= entry_date <= end_date):
                                    continue
                            except:
                                continue

                        action = entry.get("action_type", "")

                        if action == "email_processed":
                            activity.emails_processed += 1
                        elif action == "email_sent":
                            activity.emails_sent += 1
                        elif action == "message_processed":
                            activity.whatsapp_messages += 1
                        elif action == "task_completed":
                            activity.tasks_completed += 1
                        elif action == "invoice_created":
                            activity.invoices_created += 1
                        elif action == "proposal_generated":
                            activity.proposals_generated += 1

                except Exception as e:
                    logger.debug(f"Error reading log {log_file}: {e}")

            # Count social posts
            if self.social_folder.exists():
                published_folder = self.social_folder / "Published"
                if published_folder.exists():
                    activity.social_posts = len(list(published_folder.glob("*.md")))

            # Estimate hours saved (rough calculation)
            # Average 15 min per email, 10 min per message, 30 min per post
            total_minutes = (
                activity.emails_processed * 15 +
                activity.whatsapp_messages * 10 +
                activity.social_posts * 30 +
                activity.invoices_created * 20 +
                activity.proposals_generated * 45
            )
            activity.hours_saved = round(total_minutes / 60, 1)

        except Exception as e:
            logger.error(f"Error collecting AI activity: {e}")

        return activity

    def _generate_executive_summary(
        self,
        business: BusinessMetrics,
        marketing: MarketingMetrics,
        ai: AIActivitySummary
    ) -> str:
        """Generate executive summary text."""
        summary_parts = []

        # Revenue summary
        if business.revenue > 0:
            summary_parts.append(
                f"This week generated ${business.revenue:,.2f} in revenue "
                f"with ${business.profit:,.2f} profit."
            )
        else:
            summary_parts.append("No revenue recorded this week.")

        # Lead summary
        if business.new_leads > 0:
            summary_parts.append(
                f"{business.new_leads} new leads entered the pipeline "
                f"with a {business.conversion_rate:.1f}% conversion rate."
            )

        # Marketing summary
        if marketing.posts_published > 0:
            summary_parts.append(
                f"Marketing published {marketing.posts_published} posts "
                f"reaching {marketing.total_engagement} engagements."
            )

        # AI productivity
        if ai.tasks_completed > 0:
            summary_parts.append(
                f"AI Employee completed {ai.tasks_completed} tasks, "
                f"processing {ai.emails_processed} emails and "
                f"{ai.whatsapp_messages} messages, saving approximately "
                f"{ai.hours_saved} hours of work."
            )

        return " ".join(summary_parts)

    def _generate_highlights(
        self,
        business: BusinessMetrics,
        marketing: MarketingMetrics,
        ai: AIActivitySummary
    ) -> list:
        """Generate key highlights."""
        highlights = []

        if business.revenue > 0:
            highlights.append(f"💰 Revenue: ${business.revenue:,.2f}")

        if business.conversion_rate > 50:
            highlights.append(f"🎯 Strong lead conversion rate: {business.conversion_rate:.1f}%")

        if marketing.posts_published > 3:
            highlights.append(f"📱 Active social media: {marketing.posts_published} posts published")

        if marketing.avg_engagement_rate > 2:
            highlights.append(f"📈 Above average engagement rate: {marketing.avg_engagement_rate:.2f}%")

        if ai.hours_saved >= 10:
            highlights.append(f"🤖 AI saved {ai.hours_saved} hours this week")

        if ai.invoices_created > 0:
            highlights.append(f"📄 {ai.invoices_created} invoices processed")

        return highlights

    def _generate_concerns(
        self,
        business: BusinessMetrics,
        marketing: MarketingMetrics
    ) -> list:
        """Generate areas of concern."""
        concerns = []

        if business.outstanding_invoices > 5:
            concerns.append(
                f"⚠️ {business.outstanding_invoices} outstanding invoices "
                f"totaling ${business.outstanding_amount:,.2f}"
            )

        if business.new_leads > 0 and business.conversion_rate < 20:
            concerns.append(
                f"⚠️ Low lead conversion rate ({business.conversion_rate:.1f}%) "
                f"needs attention"
            )

        if marketing.posts_published == 0:
            concerns.append("⚠️ No social media activity this week")

        if business.revenue == 0:
            concerns.append("⚠️ No revenue recorded this week")

        return concerns

    def _generate_recommendations(
        self,
        business: BusinessMetrics,
        marketing: MarketingMetrics,
        ai: AIActivitySummary
    ) -> list:
        """Generate strategic recommendations."""
        recommendations = []

        if business.outstanding_invoices > 3:
            recommendations.append(
                "📋 Implement automated payment reminders for outstanding invoices"
            )

        if marketing.posts_published < 3:
            recommendations.append(
                "📱 Increase social media posting frequency to at least 3x per week"
            )

        if business.conversion_rate < 30 and business.new_leads > 0:
            recommendations.append(
                "🎯 Review lead qualification process to improve conversion rate"
            )

        if ai.hours_saved > 5:
            recommendations.append(
                f"🤖 Leverage AI capacity - currently saving {ai.hours_saved} hours/week, "
                f"consider expanding automation to additional workflows"
            )

        if marketing.top_platform:
            recommendations.append(
                f"📈 Double down on {marketing.top_platform} - showing best engagement"
            )

        if not recommendations:
            recommendations.append("✅ All systems performing well - maintain current strategy")

        return recommendations

    def _generate_priorities(
        self,
        business: BusinessMetrics,
        concerns: list
    ) -> list:
        """Generate next week priorities."""
        priorities = []

        if business.outstanding_invoices > 0:
            priorities.append("Follow up on outstanding invoices")

        if business.new_leads > 0:
            priorities.append("Nurture new leads in pipeline")

        priorities.append("Maintain consistent social media presence")
        priorities.append("Review and optimize AI workflows")

        return priorities[:4]  # Top 4 priorities

    def save_briefing(self, briefing: CEOBriefing) -> Path:
        """
        Save briefing to vault.

        Args:
            briefing: Briefing to save

        Returns:
            Path to saved file
        """
        filename = f"{briefing.briefing_id}.md"
        filepath = self.briefings_folder / filename

        content = self._format_briefing_as_markdown(briefing)
        filepath.write_text(content, encoding="utf-8")

        logger.info(f"Saved CEO briefing: {filepath}")
        return filepath

    def _format_briefing_as_markdown(self, briefing: CEOBriefing) -> str:
        """Format briefing as Markdown."""
        content = f"""---
briefing_id: {briefing.briefing_id}
period_start: {briefing.period_start}
period_end: {briefing.period_end}
generated_at: {briefing.generated_at}
---

# CEO Weekly Briefing

## Period: {briefing.period_start} to {briefing.period_end}

---

## Executive Summary

{briefing.executive_summary}

---

## Business Performance

| Metric | Value |
|--------|-------|
| Revenue | ${briefing.business_metrics.get('revenue', 0):,.2f} |
| Expenses | ${briefing.business_metrics.get('expenses', 0):,.2f} |
| Profit | ${briefing.business_metrics.get('profit', 0):,.2f} |
| New Leads | {briefing.business_metrics.get('new_leads', 0)} |
| Converted Leads | {briefing.business_metrics.get('converted_leads', 0)} |
| Conversion Rate | {briefing.business_metrics.get('conversion_rate', 0):.1f}% |
| Outstanding Invoices | {briefing.business_metrics.get('outstanding_invoices', 0)} |
| Outstanding Amount | ${briefing.business_metrics.get('outstanding_amount', 0):,.2f} |

---

## Marketing Performance

| Metric | Value |
|--------|-------|
| Posts Published | {briefing.marketing_metrics.get('posts_published', 0)} |
| Total Engagement | {briefing.marketing_metrics.get('total_engagement', 0)} |
| Avg Engagement Rate | {briefing.marketing_metrics.get('avg_engagement_rate', 0):.2f}% |
| Top Platform | {briefing.marketing_metrics.get('top_platform', 'N/A')} |

---

## AI Employee Activity

| Metric | Value |
|--------|-------|
| Tasks Completed | {briefing.ai_activity.get('tasks_completed', 0)} |
| Emails Processed | {briefing.ai_activity.get('emails_processed', 0)} |
| Emails Sent | {briefing.ai_activity.get('emails_sent', 0)} |
| WhatsApp Messages | {briefing.ai_activity.get('whatsapp_messages', 0)} |
| Social Posts | {briefing.ai_activity.get('social_posts', 0)} |
| Invoices Created | {briefing.ai_activity.get('invoices_created', 0)} |
| Proposals Generated | {briefing.ai_activity.get('proposals_generated', 0)} |
| **Hours Saved** | **{briefing.ai_activity.get('hours_saved', 0)}** |

---

## Key Highlights

"""
        for highlight in briefing.key_highlights:
            content += f"- {highlight}\n"

        content += "\n## Areas of Concern\n\n"
        if briefing.areas_of_concern:
            for concern in briefing.areas_of_concern:
                content += f"- {concern}\n"
        else:
            content += "- None identified\n"

        content += "\n## Recommendations\n\n"
        for rec in briefing.recommendations:
            content += f"- {rec}\n"

        content += "\n## Next Week Priorities\n\n"
        for priority in briefing.next_week_priorities:
            content += f"- {priority}\n"

        content += f"""
---
*Generated by AI Employee Reporting System*
*Report ID: {briefing.briefing_id}*
"""
        return content

    def get_recent_briefings(self, limit: int = 5) -> list:
        """
        Get recent briefings.

        Args:
            limit: Number of briefings to return

        Returns:
            List of briefing summaries
        """
        briefings = []

        for filepath in sorted(self.briefings_folder.glob("*.md"), reverse=True)[:limit]:
            try:
                content = filepath.read_text()
                # Extract basic info
                briefing_id = filepath.stem
                briefings.append({
                    "id": briefing_id,
                    "file": str(filepath),
                    "created": filepath.stat().st_mtime
                })
            except:
                pass

        return briefings


# =============================================================================
# Factory Function
# =============================================================================

def create_ceo_briefing_generator(vault_path: Path = None) -> CEOBriefingGenerator:
    """
    Create a CEO briefing generator.

    Args:
        vault_path: Path to vault

    Returns:
        CEOBriefingGenerator instance
    """
    return CEOBriefingGenerator(vault_path)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for CEO briefing generator."""
    import argparse

    parser = argparse.ArgumentParser(description="CEO Briefing Generator")
    parser.add_argument("--vault", type=str, help="Vault path")
    parser.add_argument("--generate", action="store_true", help="Generate weekly briefing")
    parser.add_argument("--recent", action="store_true", help="Show recent briefings")

    args = parser.parse_args()

    print("=" * 70)
    print("CEO Briefing Generator")
    print("=" * 70)

    try:
        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        generator = CEOBriefingGenerator(vault_path)

        if args.generate or not args.recent:
            print("\n📊 Generating weekly briefing...")
            briefing = generator.generate_weekly_briefing()
            filepath = generator.save_briefing(briefing)

            print(f"\n{'='*70}")
            print(f"Briefing: {briefing.briefing_id}")
            print(f"Period: {briefing.period_start} to {briefing.period_end}")
            print(f"\nExecutive Summary:")
            print(f"  {briefing.executive_summary}")
            print(f"\nKey Highlights:")
            for highlight in briefing.key_highlights[:5]:
                print(f"  {highlight}")
            print(f"\nSaved to: {filepath}")

        elif args.recent:
            briefings = generator.get_recent_briefings()
            print(f"\n📋 Recent Briefings:")
            for b in briefings:
                print(f"   - {b['id']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
