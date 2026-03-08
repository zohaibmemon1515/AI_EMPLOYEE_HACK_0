#!/usr/bin/env python3
r"""
Weekly Business Audit - Comprehensive Business Performance Analysis

Performs weekly audit of business operations:
- Revenue analysis
- Expense tracking
- Lead pipeline review
- Conversion analysis
- Social performance metrics
- AI employee efficiency

Usage:
    from modules.reporting.weekly_audit import WeeklyAudit

    audit = WeeklyAudit(vault_path)
    result = audit.run_weekly_audit()
"""

import json
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

import dotenv

# Load environment variables
dotenv.load_dotenv()

# Windows-safe logging setup
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


class AuditStatus(Enum):
    """Audit result status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RevenueAudit:
    """Revenue audit results."""
    total_revenue: float = 0.0
    previous_revenue: float = 0.0
    growth_rate: float = 0.0
    invoices_count: int = 0
    paid_invoices: int = 0
    pending_invoices: int = 0
    avg_invoice_value: float = 0.0
    largest_invoice: float = 0.0
    revenue_by_source: dict = None

    def __post_init__(self):
        if self.revenue_by_source is None:
            self.revenue_by_source = {}


@dataclass
class ExpenseAudit:
    """Expense audit results."""
    total_expenses: float = 0.0
    previous_expenses: float = 0.0
    expense_categories: dict = None
    largest_expense: float = 0.0
    recurring_expenses: float = 0.0

    def __post_init__(self):
        if self.expense_categories is None:
            self.expense_categories = {}


@dataclass
class LeadAudit:
    """Lead pipeline audit results."""
    new_leads: int = 0
    qualified_leads: int = 0
    converted_leads: int = 0
    lost_leads: int = 0
    conversion_rate: float = 0.0
    avg_deal_value: float = 0.0
    pipeline_value: float = 0.0
    leads_by_source: dict = None

    def __post_init__(self):
        if self.leads_by_source is None:
            self.leads_by_source = {}


@dataclass
class SocialAudit:
    """Social media audit results."""
    posts_published: int = 0
    total_reach: int = 0
    total_engagement: int = 0
    avg_engagement_rate: float = 0.0
    follower_growth: int = 0
    platform_breakdown: dict = None
    top_performing_post: dict = None

    def __post_init__(self):
        if self.platform_breakdown is None:
            self.platform_breakdown = {}


@dataclass
class AIEfficiencyAudit:
    """AI employee efficiency audit."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0  # seconds
    hours_saved: float = 0.0
    cost_savings: float = 0.0
    automation_coverage: float = 0.0


@dataclass
class AuditFinding:
    """Single audit finding."""
    category: str
    severity: str  # low, medium, high, critical
    title: str
    description: str
    impact: str = ""
    recommendation: str = ""


@dataclass
class WeeklyAuditResult:
    """Complete weekly audit result."""
    audit_id: str
    period_start: str
    period_end: str
    generated_at: str
    status: str
    revenue: dict = None
    expenses: dict = None
    leads: dict = None
    social: dict = None
    ai_efficiency: dict = None
    findings: list = None
    health_score: int = 100
    summary: str = ""

    def __post_init__(self):
        if self.revenue is None:
            self.revenue = {}
        if self.expenses is None:
            self.expenses = {}
        if self.leads is None:
            self.leads = {}
        if self.social is None:
            self.social = {}
        if self.ai_efficiency is None:
            self.ai_efficiency = {}
        if self.findings is None:
            self.findings = []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class WeeklyAudit:
    """
    Weekly Business Audit System.

    Performs comprehensive audit of all business operations
    and generates actionable insights.
    """

    def __init__(self, vault_path: Path = None):
        """
        Initialize weekly audit.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.logs_folder = self.vault_path / "Logs"
        self.done_folder = self.vault_path / "Done"
        self.audits_folder = self.vault_path / "Audits"

        # Create folders
        for folder in [self.audits_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        logger.info(f"WeeklyAudit initialized at {self.vault_path}")

    def run_weekly_audit(
        self,
        end_date: datetime = None,
        compare_previous: bool = True
    ) -> WeeklyAuditResult:
        """
        Run comprehensive weekly audit.

        Args:
            end_date: End of audit period
            compare_previous: Compare with previous period

        Returns:
            WeeklyAuditResult
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=7)
        previous_start = start_date - timedelta(days=7)

        audit_id = f"AUDIT_WEEKLY_{end_date.strftime('%Y%m%d')}"

        logger.info(f"Starting weekly audit: {audit_id}")

        result = WeeklyAuditResult(
            audit_id=audit_id,
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            generated_at=datetime.now().isoformat(),
            status=AuditStatus.HEALTHY.value
        )

        # Run revenue audit
        logger.info("Auditing revenue...")
        revenue_audit = self._audit_revenue(start_date, end_date, previous_start if compare_previous else None)
        result.revenue = asdict(revenue_audit)

        # Run expense audit
        logger.info("Auditing expenses...")
        expense_audit = self._audit_expenses(start_date, end_date, previous_start if compare_previous else None)
        result.expenses = asdict(expense_audit)

        # Run lead audit
        logger.info("Auditing leads...")
        lead_audit = self._audit_leads(start_date, end_date)
        result.leads = asdict(lead_audit)

        # Run social audit
        logger.info("Auditing social media...")
        social_audit = self._audit_social(start_date, end_date)
        result.social = asdict(social_audit)

        # Run AI efficiency audit
        logger.info("Auditing AI efficiency...")
        ai_audit = self._audit_ai_efficiency(start_date, end_date)
        result.ai_efficiency = asdict(ai_audit)

        # Generate findings
        logger.info("Generating findings...")
        result.findings = self._generate_findings(
            revenue_audit, expense_audit, lead_audit, social_audit, ai_audit
        )

        # Calculate health score
        result.health_score = self._calculate_health_score(result)

        # Determine status
        if result.health_score >= 80:
            result.status = AuditStatus.HEALTHY.value
        elif result.health_score >= 60:
            result.status = AuditStatus.WARNING.value
        else:
            result.status = AuditStatus.CRITICAL.value

        # Generate summary
        result.summary = self._generate_summary(result)

        # Save audit report
        self._save_audit_report(result)

        logger.info(f"Audit complete: {result.status} (score: {result.health_score})")
        return result

    def _audit_revenue(
        self,
        start_date: datetime,
        end_date: datetime,
        previous_start: datetime = None
    ) -> RevenueAudit:
        """Audit revenue for the period."""
        audit = RevenueAudit()

        try:
            invoices = []
            revenue_by_source = {}

            # Read from logs
            for log_file in self.logs_folder.glob("*.json"):
                try:
                    data = json.loads(log_file.read_text())
                    if not isinstance(data, list):
                        continue

                    for entry in data:
                        if entry.get("action_type") == "invoice_created":
                            timestamp = entry.get("timestamp", "")
                            if timestamp:
                                try:
                                    entry_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                                    if start_date <= entry_date <= end_date:
                                        details = entry.get("details", {})
                                        amount = float(details.get("amount", 0))
                                        source = details.get("source", "unknown")

                                        invoices.append({"amount": amount, "source": source})
                                        revenue_by_source[source] = revenue_by_source.get(source, 0) + amount
                                except:
                                    pass
                except:
                    pass

            # Calculate metrics
            total_revenue = sum(inv["amount"] for inv in invoices)
            audit.total_revenue = total_revenue
            audit.invoices_count = len(invoices)
            audit.avg_invoice_value = total_revenue / len(invoices) if invoices else 0
            audit.largest_invoice = max((inv["amount"] for inv in invoices), default=0)
            audit.revenue_by_source = revenue_by_source

            # Count paid/pending from Done folder
            paid = 0
            pending = 0
            if self.done_folder.exists():
                for filepath in self.done_folder.glob("INVOICE_*.md"):
                    content = filepath.read_text().lower()
                    if "paid" in content:
                        paid += 1
                    else:
                        pending += 1

            audit.paid_invoices = paid
            audit.pending_invoices = pending

            # Compare with previous period
            if previous_start:
                prev_audit = self._audit_revenue(previous_start, start_date, None)
                audit.previous_revenue = prev_audit.total_revenue
                if prev_audit.total_revenue > 0:
                    audit.growth_rate = ((total_revenue - prev_audit.total_revenue) / prev_audit.total_revenue) * 100

        except Exception as e:
            logger.error(f"Revenue audit error: {e}")

        return audit

    def _audit_expenses(
        self,
        start_date: datetime,
        end_date: datetime,
        previous_start: datetime = None
    ) -> ExpenseAudit:
        """Audit expenses for the period."""
        audit = ExpenseAudit()

        try:
            expenses = []
            expense_categories = {}

            # Read expense logs
            for log_file in self.logs_folder.glob("*.json"):
                try:
                    data = json.loads(log_file.read_text())
                    if not isinstance(data, list):
                        continue

                    for entry in data:
                        if entry.get("action_type") == "expense_recorded":
                            timestamp = entry.get("timestamp", "")
                            if timestamp:
                                try:
                                    entry_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                                    if start_date <= entry_date <= end_date:
                                        details = entry.get("details", {})
                                        amount = float(details.get("amount", 0))
                                        category = details.get("category", "uncategorized")

                                        expenses.append(amount)
                                        expense_categories[category] = expense_categories.get(category, 0) + amount
                                except:
                                    pass
                except:
                    pass

            audit.total_expenses = sum(expenses)
            audit.expense_categories = expense_categories
            audit.largest_expense = max(expenses, default=0)

            # Previous period comparison
            if previous_start:
                prev_audit = self._audit_expenses(previous_start, start_date, None)
                audit.previous_expenses = prev_audit.total_expenses

        except Exception as e:
            logger.error(f"Expense audit error: {e}")

        return audit

    def _audit_leads(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> LeadAudit:
        """Audit lead pipeline."""
        audit = LeadAudit()

        try:
            leads = []
            leads_by_source = {}

            # Read lead logs
            for log_file in self.logs_folder.glob("*.json"):
                try:
                    data = json.loads(log_file.read_text())
                    if not isinstance(data, list):
                        continue

                    for entry in data:
                        action = entry.get("action_type", "")
                        timestamp = entry.get("timestamp", "")

                        if timestamp:
                            try:
                                entry_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                                if not (start_date <= entry_date <= end_date):
                                    continue
                            except:
                                continue

                        if action == "lead_created":
                            leads.append({"status": "new", "details": entry.get("details", {})})
                            source = entry.get("details", {}).get("source", "unknown")
                            leads_by_source[source] = leads_by_source.get(source, 0) + 1
                        elif action == "lead_converted":
                            leads.append({"status": "converted", "details": entry.get("details", {})})
                        elif action == "lead_lost":
                            leads.append({"status": "lost", "details": entry.get("details", {})})

                except:
                    pass

            new_leads = sum(1 for l in leads if l["status"] == "new")
            converted = sum(1 for l in leads if l["status"] == "converted")
            lost = sum(1 for l in leads if l["status"] == "lost")

            audit.new_leads = new_leads
            audit.converted_leads = converted
            audit.lost_leads = lost
            audit.qualified_leads = new_leads - lost
            audit.leads_by_source = leads_by_source

            if new_leads > 0:
                audit.conversion_rate = (converted / new_leads) * 100

        except Exception as e:
            logger.error(f"Lead audit error: {e}")

        return audit

    def _audit_social(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> SocialAudit:
        """Audit social media performance."""
        audit = SocialAudit()

        try:
            # Try to get data from social summary
            try:
                from modules.social.social_summary import SocialSummaryGenerator
                generator = SocialSummaryGenerator(self.vault_path)
                summary = generator.generate_weekly_summary(end_date, include_recommendations=False)

                audit.posts_published = summary.total_posts
                audit.total_engagement = summary.total_engagement
                audit.avg_engagement_rate = summary.avg_engagement_rate

                # Platform breakdown - handle both dict and dataclass
                for pm in summary.platform_metrics:
                    if isinstance(pm, dict):
                        platform = pm.get("platform", "unknown")
                        posts = pm.get("posts_count", 0)
                        engagement = pm.get("total_likes", 0) + pm.get("total_comments", 0) + pm.get("total_shares", 0)
                    else:
                        platform = getattr(pm, 'platform', 'unknown')
                        posts = getattr(pm, 'posts_count', 0)
                        engagement = getattr(pm, 'total_likes', 0) + getattr(pm, 'total_comments', 0) + getattr(pm, 'total_shares', 0)

                    audit.platform_breakdown[platform] = {
                        "posts": posts,
                        "engagement": engagement
                    }

            except ImportError:
                logger.debug("Social summary not available")

        except Exception as e:
            logger.error(f"Social audit error: {e}")

        return audit

    def _audit_ai_efficiency(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> AIEfficiencyAudit:
        """Audit AI employee efficiency."""
        audit = AIEfficiencyAudit()

        try:
            tasks_completed = 0
            tasks_failed = 0
            total_response_time = 0
            response_count = 0

            # Read activity logs
            for log_file in self.logs_folder.glob("*.json"):
                try:
                    data = json.loads(log_file.read_text())
                    if not isinstance(data, list):
                        continue

                    for entry in data:
                        actor = entry.get("actor", "").lower()
                        timestamp = entry.get("timestamp", "")

                        if "ai" not in actor and "employee" not in actor:
                            continue

                        if timestamp:
                            try:
                                entry_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                                if not (start_date <= entry_date <= end_date):
                                    continue
                            except:
                                continue

                        action = entry.get("action_type", "")
                        result = entry.get("result", "")

                        if "completed" in action or "sent" in action or "processed" in action:
                            tasks_completed += 1
                        elif "failed" in action or "error" in str(result).lower():
                            tasks_failed += 1

                except:
                    pass

            audit.tasks_completed = tasks_completed
            audit.tasks_failed = tasks_failed

            total_tasks = tasks_completed + tasks_failed
            if total_tasks > 0:
                audit.success_rate = (tasks_completed / total_tasks) * 100

            # Estimate hours saved
            # Average 15 min per automated task
            audit.hours_saved = round(tasks_completed * 0.25, 1)

            # Estimate cost savings (assuming $25/hour equivalent)
            audit.cost_savings = round(audit.hours_saved * 25, 2)

            # Automation coverage
            if total_tasks > 0:
                audit.automation_coverage = audit.success_rate

        except Exception as e:
            logger.error(f"AI efficiency audit error: {e}")

        return audit

    def _generate_findings(
        self,
        revenue: RevenueAudit,
        expenses: ExpenseAudit,
        leads: LeadAudit,
        social: SocialAudit,
        ai: AIEfficiencyAudit
    ) -> list:
        """Generate audit findings."""
        findings = []

        # Revenue findings
        if revenue.growth_rate < -10:
            findings.append({
                "category": "revenue",
                "severity": "high",
                "title": "Revenue Decline Detected",
                "description": f"Revenue decreased by {abs(revenue.growth_rate):.1f}% compared to previous period",
                "impact": "Reduced cash flow and profitability",
                "recommendation": "Review pricing strategy and sales pipeline"
            })

        if revenue.pending_invoices > 5:
            findings.append({
                "category": "revenue",
                "severity": "medium",
                "title": "High Pending Invoices",
                "description": f"{revenue.pending_invoices} invoices awaiting payment",
                "impact": "Delayed cash collection",
                "recommendation": "Implement automated payment reminders"
            })

        # Lead findings
        if leads.new_leads > 0 and leads.conversion_rate < 20:
            findings.append({
                "category": "leads",
                "severity": "medium",
                "title": "Low Conversion Rate",
                "description": f"Conversion rate is {leads.conversion_rate:.1f}%",
                "impact": "Inefficient lead utilization",
                "recommendation": "Review lead qualification and follow-up process"
            })

        if leads.new_leads == 0:
            findings.append({
                "category": "leads",
                "severity": "high",
                "title": "No New Leads",
                "description": "No new leads entered pipeline this week",
                "impact": "Future revenue at risk",
                "recommendation": "Increase marketing and outreach efforts"
            })

        # Social findings
        if social.posts_published == 0:
            findings.append({
                "category": "marketing",
                "severity": "low",
                "title": "No Social Media Activity",
                "description": "No posts published this week",
                "impact": "Reduced brand visibility",
                "recommendation": "Maintain consistent posting schedule"
            })

        # AI findings
        if ai.tasks_failed > 0:
            total_tasks = ai.tasks_completed + ai.tasks_failed
            failure_rate = (ai.tasks_failed / total_tasks * 100) if total_tasks > 0 else 0
            if failure_rate > 10:
                findings.append({
                    "category": "operations",
                    "severity": "medium",
                    "title": "AI Task Failures",
                    "description": f"{ai.tasks_failed} tasks failed ({failure_rate:.1f}%)",
                    "impact": "Reduced automation efficiency",
                    "recommendation": "Review failed tasks and improve error handling"
                })

        return findings

    def _calculate_health_score(self, result: WeeklyAuditResult) -> int:
        """Calculate overall health score (0-100)."""
        score = 100

        # Revenue impact
        revenue = result.revenue
        revenue_growth = revenue.get("growth_rate", 0) if isinstance(revenue, dict) else getattr(revenue, 'growth_rate', 0)
        revenue_pending = revenue.get("pending_invoices", 0) if isinstance(revenue, dict) else getattr(revenue, 'pending_invoices', 0)

        if revenue_growth < -20:
            score -= 25
        elif revenue_growth < -10:
            score -= 15
        elif revenue_growth < 0:
            score -= 5

        if revenue_pending > 10:
            score -= 10

        # Lead impact
        leads = result.leads
        leads_new = leads.get("new_leads", 0) if isinstance(leads, dict) else getattr(leads, 'new_leads', 0)
        leads_conversion = leads.get("conversion_rate", 0) if isinstance(leads, dict) else getattr(leads, 'conversion_rate', 0)

        if leads_new == 0:
            score -= 20
        if leads_conversion < 20:
            score -= 10

        # AI efficiency impact
        ai = result.ai_efficiency
        ai_success = ai.get("success_rate", 100) if isinstance(ai, dict) else getattr(ai, 'success_rate', 100)

        if ai_success < 80:
            score -= 15

        # Finding severity impact
        for finding in result.findings:
            severity = finding.get("severity") if isinstance(finding, dict) else getattr(finding, 'severity', '')
            if severity == "critical":
                score -= 20
            elif severity == "high":
                score -= 10
            elif severity == "medium":
                score -= 5

        return max(0, min(100, score))

    def _generate_summary(self, result: WeeklyAuditResult) -> str:
        """Generate audit summary text."""
        parts = []

        # Status summary
        status_emoji = {
            AuditStatus.HEALTHY.value: "✅",
            AuditStatus.WARNING.value: "⚠️",
            AuditStatus.CRITICAL.value: "🚨"
        }
        parts.append(f"{status_emoji.get(result.status, '')} Business Health: {result.status.upper()} (Score: {result.health_score}/100)")

        # Revenue summary
        revenue = result.revenue
        total_revenue = revenue.get("total_revenue", 0) if isinstance(revenue, dict) else getattr(revenue, 'total_revenue', 0)
        growth_rate = revenue.get("growth_rate", 0) if isinstance(revenue, dict) else getattr(revenue, 'growth_rate', 0)

        if total_revenue > 0:
            growth_str = f"+{growth_rate:.1f}%" if growth_rate > 0 else f"{growth_rate:.1f}%"
            parts.append(f"💰 Revenue: ${total_revenue:,.2f} ({growth_str})")

        # Lead summary
        leads = result.leads
        new_leads = leads.get("new_leads", 0) if isinstance(leads, dict) else getattr(leads, 'new_leads', 0)
        converted_leads = leads.get("converted_leads", 0) if isinstance(leads, dict) else getattr(leads, 'converted_leads', 0)
        conversion_rate = leads.get("conversion_rate", 0) if isinstance(leads, dict) else getattr(leads, 'conversion_rate', 0)

        parts.append(f"🎯 Leads: {new_leads} new, {converted_leads} converted ({conversion_rate:.1f}%)")

        # AI summary
        ai = result.ai_efficiency
        tasks_completed = ai.get("tasks_completed", 0) if isinstance(ai, dict) else getattr(ai, 'tasks_completed', 0)
        hours_saved = ai.get("hours_saved", 0) if isinstance(ai, dict) else getattr(ai, 'hours_saved', 0)

        parts.append(f"🤖 AI: {tasks_completed} tasks completed, {hours_saved} hours saved")

        return " | ".join(parts)

    def _get_value(self, obj, key, default=0):
        """Get value from dict or dataclass."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _save_audit_report(self, result: WeeklyAuditResult):
        """Save audit report to vault."""
        filepath = self.audits_folder / f"{result.audit_id}.md"

        # Convert dataclasses to dicts for easy access
        revenue = result.revenue if isinstance(result.revenue, dict) else asdict(result.revenue)
        leads = result.leads if isinstance(result.leads, dict) else asdict(result.leads)
        social = result.social if isinstance(result.social, dict) else asdict(result.social)
        ai_eff = result.ai_efficiency if isinstance(result.ai_efficiency, dict) else asdict(result.ai_efficiency)

        content = f"""---
audit_id: {result.audit_id}
period_start: {result.period_start}
period_end: {result.period_end}
generated_at: {result.generated_at}
status: {result.status}
health_score: {result.health_score}
---

# Weekly Business Audit Report

## Period: {result.period_start} to {result.period_end}

---

## Executive Summary

{result.summary}

---

## Revenue Analysis

| Metric | Value |
|--------|-------|
| Total Revenue | ${revenue.get('total_revenue', 0):,.2f} |
| Previous Period | ${revenue.get('previous_revenue', 0):,.2f} |
| Growth Rate | {revenue.get('growth_rate', 0):+.1f}% |
| Invoices Count | {revenue.get('invoices_count', 0)} |
| Paid Invoices | {revenue.get('paid_invoices', 0)} |
| Pending Invoices | {revenue.get('pending_invoices', 0)} |
| Avg Invoice Value | ${revenue.get('avg_invoice_value', 0):,.2f} |

---

## Lead Pipeline

| Metric | Value |
|--------|-------|
| New Leads | {leads.get('new_leads', 0)} |
| Qualified Leads | {leads.get('qualified_leads', 0)} |
| Converted Leads | {leads.get('converted_leads', 0)} |
| Lost Leads | {leads.get('lost_leads', 0)} |
| Conversion Rate | {leads.get('conversion_rate', 0):.1f}% |

---

## Social Media Performance

| Metric | Value |
|--------|-------|
| Posts Published | {social.get('posts_published', 0)} |
| Total Engagement | {social.get('total_engagement', 0)} |
| Avg Engagement Rate | {social.get('avg_engagement_rate', 0):.2f}% |

---

## AI Employee Efficiency

| Metric | Value |
|--------|-------|
| Tasks Completed | {ai_eff.get('tasks_completed', 0)} |
| Tasks Failed | {ai_eff.get('tasks_failed', 0)} |
| Success Rate | {ai_eff.get('success_rate', 0):.1f}% |
| Hours Saved | {ai_eff.get('hours_saved', 0)} |
| Cost Savings | ${ai_eff.get('cost_savings', 0):,.2f} |

---

## Findings

"""
        if result.findings:
            for i, finding in enumerate(result.findings, 1):
                finding_dict = finding if isinstance(finding, dict) else asdict(finding) if hasattr(finding, '__dataclass_fields__') else finding
                content += f"""
### {i}. {finding_dict.get('title', 'Finding')}

- **Category**: {finding_dict.get('category', 'general')}
- **Severity**: {finding_dict.get('severity', 'medium')}
- **Description**: {finding.get('description', '')}
- **Impact**: {finding.get('impact', '')}
- **Recommendation**: {finding.get('recommendation', '')}

---
"""
        else:
            content += "\n*No significant findings this week.*\n"

        content += f"""
---
*Generated by AI Employee Weekly Audit System*
"""
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved audit report: {filepath}")


# =============================================================================
# Factory Function
# =============================================================================

def create_weekly_audit(vault_path: Path = None) -> WeeklyAudit:
    """
    Create a weekly audit instance.

    Args:
        vault_path: Path to vault

    Returns:
        WeeklyAudit instance
    """
    return WeeklyAudit(vault_path)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for weekly audit."""
    import argparse

    parser = argparse.ArgumentParser(description="Weekly Business Audit")
    parser.add_argument("--vault", type=str, help="Vault path")
    parser.add_argument("--run", action="store_true", help="Run weekly audit")

    args = parser.parse_args()

    print("=" * 70)
    print("Weekly Business Audit")
    print("=" * 70)

    try:
        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        audit = WeeklyAudit(vault_path)

        if args.run or True:  # Default to running
            print("\n🔍 Running weekly audit...")
            result = audit.run_weekly_audit()

            print(f"\n{'='*70}")
            print(f"Audit: {result.audit_id}")
            print(f"Status: {result.status.upper()} (Score: {result.health_score}/100)")
            print(f"\nSummary: {result.summary}")

            if result.findings:
                print(f"\nFindings ({len(result.findings)}):")
                for finding in result.findings[:5]:
                    print(f"  - [{finding.get('severity', 'medium').upper()}] {finding.get('title', '')}")

        else:
            print("\nUsage: python -m modules.reporting.weekly_audit --run")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
