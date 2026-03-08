#!/usr/bin/env python3
r"""
Agent Skills Framework - Modular Skill System for AI Employee

Provides a unified interface for AI capabilities organized as skills:
- CommunicationSkill: Email, WhatsApp, messaging
- AccountingSkill: Invoices, payments, financial data
- MarketingSkill: Social media, content generation
- PlanningSkill: Task analysis, planning, prioritization

Usage:
    from modules.skills import CommunicationSkill, AccountingSkill

    comm = CommunicationSkill(vault_path)
    comm.send_email(to, subject, body)
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable

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
class SkillResult:
    """Result of a skill operation."""
    success: bool
    action: str
    result: Any = None
    error: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class BaseSkill(ABC):
    """
    Base class for all AI skills.

    Provides common interface and logging for skill operations.
    """

    def __init__(self, vault_path: Path = None):
        """
        Initialize base skill.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.logs_folder = self.vault_path / "Logs"
        self.logs_folder.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def skill_name(self) -> str:
        """Return skill name."""
        pass

    @property
    @abstractmethod
    def available_actions(self) -> list:
        """Return list of available actions."""
        pass

    def _log_action(self, action: str, result: SkillResult):
        """Log skill action to vault."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_folder / f"{today}.json"

        # Load existing logs
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                logs = []

        # Add new entry
        logs.append({
            "timestamp": result.timestamp,
            "module": f"skills.{self.skill_name}",
            "action": action,
            "actor": "ai_employee",
            "result": "success" if result.success else "failed",
            "details": {
                "action": action,
                "error": result.error if not result.success else None
            }
        })

        # Save logs
        try:
            log_file.write_text(json.dumps(logs, indent=2))
        except Exception as e:
            logger.error(f"Failed to save log: {e}")

    def _create_result(self, success: bool, action: str, result: Any = None, error: str = "") -> SkillResult:
        """Create a skill result."""
        return SkillResult(
            success=success,
            action=action,
            result=result,
            error=error
        )


# =============================================================================
# Communication Skill
# =============================================================================

class CommunicationSkill(BaseSkill):
    """
    Communication Skill for AI Employee.

    Handles all communication-related operations:
    - send_email: Send email via Gmail
    - reply_whatsapp: Reply to WhatsApp messages
    - schedule_message: Schedule messages for later
    """

    @property
    def skill_name(self) -> str:
        return "communication"

    @property
    def available_actions(self) -> list:
        return ["send_email", "reply_whatsapp", "schedule_message"]

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str = None
    ) -> SkillResult:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            in_reply_to: Message ID for threading

        Returns:
            SkillResult with send status
        """
        try:
            # Import Gmail dependencies
            from auth_handler import GmailAuthHandler
            from googleapiclient.discovery import build
            import base64
            from email.message import EmailMessage

            # Authenticate
            creds_path = self.vault_path.parent / "credentials" / "gmail" / "credentials.json"
            token_path = self.vault_path.parent / "credentials" / "gmail" / "token.json"

            if not creds_path.exists():
                return self._create_result(
                    False, "send_email",
                    error="Gmail credentials not found"
                )

            auth = GmailAuthHandler(str(creds_path), str(token_path))
            creds = auth.authenticate()

            if not creds:
                return self._create_result(
                    False, "send_email",
                    error="Gmail authentication failed"
                )

            # Build service
            service = build("gmail", "v1", credentials=creds)

            # Create message
            msg = EmailMessage()
            msg["To"] = to
            msg["Subject"] = subject
            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to
            msg.set_content(body)

            # Encode and send
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            response = service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            message_id = response.get("id", "unknown")

            result = self._create_result(
                True, "send_email",
                result={"message_id": message_id, "to": to}
            )
            self._log_action("send_email", result)

            logger.info(f"Email sent to {to}: {message_id}")
            return result

        except Exception as e:
            result = self._create_result(
                False, "send_email",
                error=str(e)
            )
            self._log_action("send_email", result)
            logger.error(f"Failed to send email: {e}")
            return result

    def reply_whatsapp(
        self,
        recipient: str,
        message: str,
        original_message_id: str = None
    ) -> SkillResult:
        """
        Reply to a WhatsApp message.

        Args:
            recipient: Recipient phone number or name
            message: Reply message
            original_message_id: Original message ID for threading

        Returns:
            SkillResult with send status
        """
        try:
            # Create reply file in Approved folder for whatsapp_reply_sender.py to process
            approved_folder = self.vault_path / "Approved"
            approved_folder.mkdir(parents=True, exist_ok=True)

            reply_id = f"WHATSAPP_REPLY_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            reply_file = approved_folder / f"{reply_id}.md"

            content = f"""---
reply_id: {reply_id}
recipient: {recipient}
original_message_id: {original_message_id or ''}
status: approved
created_at: {datetime.now().isoformat()}
---

# WhatsApp Reply

## Recipient
{recipient}

## Message
```
{message}
```

---
*Generated by CommunicationSkill*
"""
            reply_file.write_text(content, encoding="utf-8")

            result = self._create_result(
                True, "reply_whatsapp",
                result={"reply_id": reply_id, "recipient": recipient}
            )
            self._log_action("reply_whatsapp", result)

            logger.info(f"WhatsApp reply queued for {recipient}")
            return result

        except Exception as e:
            result = self._create_result(
                False, "reply_whatsapp",
                error=str(e)
            )
            self._log_action("reply_whatsapp", result)
            logger.error(f"Failed to send WhatsApp reply: {e}")
            return result

    def schedule_message(
        self,
        platform: str,
        recipient: str,
        message: str,
        scheduled_time: datetime
    ) -> SkillResult:
        """
        Schedule a message for later sending.

        Args:
            platform: Platform (email, whatsapp)
            recipient: Recipient
            message: Message content
            scheduled_time: When to send

        Returns:
            SkillResult with schedule status
        """
        try:
            # Create scheduled message file
            scheduled_folder = self.vault_path / "Scheduled_Messages"
            scheduled_folder.mkdir(parents=True, exist_ok=True)

            schedule_id = f"SCHEDULED_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            schedule_file = scheduled_folder / f"{schedule_id}.md"

            content = f"""---
schedule_id: {schedule_id}
platform: {platform}
recipient: {recipient}
scheduled_time: {scheduled_time.isoformat()}
status: pending
created_at: {datetime.now().isoformat()}
---

# Scheduled Message

## Platform
{platform.upper()}

## Recipient
{recipient}

## Message
```
{message}
```

## Scheduled Time
{scheduled_time.isoformat()}

---
*Generated by CommunicationSkill*
"""
            schedule_file.write_text(content, encoding="utf-8")

            result = self._create_result(
                True, "schedule_message",
                result={"schedule_id": schedule_id, "scheduled_time": scheduled_time.isoformat()}
            )
            self._log_action("schedule_message", result)

            logger.info(f"Message scheduled for {scheduled_time}")
            return result

        except Exception as e:
            result = self._create_result(
                False, "schedule_message",
                error=str(e)
            )
            self._log_action("schedule_message", result)
            logger.error(f"Failed to schedule message: {e}")
            return result


# =============================================================================
# Accounting Skill
# =============================================================================

class AccountingSkill(BaseSkill):
    """
    Accounting Skill for AI Employee.

    Handles all accounting-related operations:
    - create_invoice: Create invoice in Odoo
    - fetch_transactions: Get financial transactions
    - generate_financial_summary: Generate financial report
    - record_payment: Record payment
    """

    def __init__(self, vault_path: Path = None, odoo_client=None):
        """
        Initialize accounting skill.

        Args:
            vault_path: Path to vault
            odoo_client: Optional pre-configured Odoo client
        """
        super().__init__(vault_path)
        self._odoo_client = odoo_client

    @property
    def skill_name(self) -> str:
        return "accounting"

    @property
    def available_actions(self) -> list:
        return ["create_invoice", "fetch_transactions", "generate_financial_summary", "record_payment"]

    def _get_odoo_client(self):
        """Get or create Odoo client."""
        if self._odoo_client:
            return self._odoo_client

        try:
            from modules.accounting.odoo_client import OdooClient
            client = OdooClient()
            client.authenticate()
            self._odoo_client = client
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Odoo client: {e}")
            return None

    def create_invoice(
        self,
        partner_name: str,
        partner_email: str = "",
        lines: list = None,
        invoice_date: str = None,
        notes: str = ""
    ) -> SkillResult:
        """
        Create an invoice.

        Args:
            partner_name: Customer name
            partner_email: Customer email
            lines: Invoice line items
            invoice_date: Invoice date
            notes: Additional notes

        Returns:
            SkillResult with invoice details
        """
        try:
            odoo = self._get_odoo_client()

            if not odoo:
                # Fallback: create invoice file for manual processing
                return self._create_invoice_fallback(
                    partner_name, partner_email, lines, invoice_date, notes
                )

            # Find or create partner
            partners = odoo.get_partners(
                domain=[("email", "=", partner_email)] if partner_email else [("name", "=ilike", partner_name)],
                limit=1
            )

            if partners:
                partner_id = partners[0]["id"]
            else:
                partner_id = odoo.create_partner(
                    name=partner_name,
                    email=partner_email or ""
                )

            if not partner_id:
                return self._create_result(
                    False, "create_invoice",
                    error="Failed to create/find partner"
                )

            # Create invoice
            invoice_id = odoo.create_invoice(
                partner_id=partner_id,
                invoice_type="out_invoice",
                lines=lines or [{"name": "Service", "quantity": 1, "price_unit": 0}],
                invoice_date=invoice_date,
                narration=notes
            )

            if invoice_id:
                odoo.validate_invoice(invoice_id)

                result = self._create_result(
                    True, "create_invoice",
                    result={"invoice_id": invoice_id, "partner": partner_name}
                )
                self._log_action("create_invoice", result)

                logger.info(f"Invoice created: {invoice_id}")
                return result

            return self._create_result(
                False, "create_invoice",
                error="Failed to create invoice"
            )

        except Exception as e:
            result = self._create_result(
                False, "create_invoice",
                error=str(e)
            )
            self._log_action("create_invoice", result)
            logger.error(f"Failed to create invoice: {e}")
            return result

    def _create_invoice_fallback(
        self,
        partner_name: str,
        partner_email: str,
        lines: list,
        invoice_date: str,
        notes: str
    ) -> SkillResult:
        """Create invoice file as fallback when Odoo unavailable."""
        try:
            pending_folder = self.vault_path / "Pending_Approval"
            pending_folder.mkdir(parents=True, exist_ok=True)

            invoice_id = f"INVOICE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            invoice_file = pending_folder / f"{invoice_id}.md"

            total = sum(line.get("price_unit", 0) * line.get("quantity", 1) for line in (lines or []))

            content = f"""---
invoice_id: {invoice_id}
partner_name: {partner_name}
partner_email: {partner_email}
invoice_date: {invoice_date or datetime.now().strftime('%Y-%m-%d')}
total_amount: {total}
status: pending_approval
---

# Invoice Draft

## Customer
- Name: {partner_name}
- Email: {partner_email}

## Line Items

| Description | Quantity | Unit Price | Total |
|-------------|----------|------------|-------|
"""
            for line in (lines or []):
                line_total = line.get("price_unit", 0) * line.get("quantity", 1)
                content += f"| {line.get('name', 'Service')} | {line.get('quantity', 1)} | {line.get('price_unit', 0)} | {line_total} |\n"

            content += f"""
## Notes
{notes}

---
*Move to Approved/ to create in Odoo*
"""
            invoice_file.write_text(content, encoding="utf-8")

            result = self._create_result(
                True, "create_invoice",
                result={"invoice_id": invoice_id, "fallback": True}
            )
            self._log_action("create_invoice", result)

            return result

        except Exception as e:
            return self._create_result(
                False, "create_invoice",
                error=str(e)
            )

    def fetch_transactions(
        self,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ) -> SkillResult:
        """
        Fetch financial transactions.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum transactions

        Returns:
            SkillResult with transactions
        """
        try:
            odoo = self._get_odoo_client()

            if not odoo:
                return self._create_result(
                    False, "fetch_transactions",
                    error="Odoo client not available"
                )

            # Build domain
            domain = [("state", "=", "posted")]

            if start_date:
                domain.append(("date", ">=", start_date))
            if end_date:
                domain.append(("date", "<=", end_date))

            # Fetch invoices as transactions
            invoices = odoo.get_invoices(
                domain=domain,
                limit=limit,
                fields=["id", "name", "partner_id", "date", "amount_total", "state"]
            )

            result = self._create_result(
                True, "fetch_transactions",
                result={"transactions": invoices or [], "count": len(invoices or [])}
            )
            self._log_action("fetch_transactions", result)

            return result

        except Exception as e:
            result = self._create_result(
                False, "fetch_transactions",
                error=str(e)
            )
            self._log_action("fetch_transactions", result)
            logger.error(f"Failed to fetch transactions: {e}")
            return result

    def generate_financial_summary(
        self,
        period: str = "month"
    ) -> SkillResult:
        """
        Generate financial summary.

        Args:
            period: Period type (week, month, year)

        Returns:
            SkillResult with summary
        """
        try:
            odoo = self._get_odoo_client()

            if not odoo:
                # Return empty summary
                summary = {
                    "revenue": 0,
                    "expenses": 0,
                    "profit": 0,
                    "period": period
                }
                return self._create_result(
                    True, "generate_financial_summary",
                    result=summary
                )

            # Get balance sheet and revenue summary
            balance_sheet = odoo.get_balance_sheet()
            revenue_summary = odoo.get_revenue_summary(period=period)

            summary = {
                "period": period,
                "assets": balance_sheet.get("assets", {}).get("total", 0),
                "liabilities": balance_sheet.get("liabilities", {}).get("total", 0),
                "equity": balance_sheet.get("equity", {}).get("total", 0),
                "revenue_by_period": revenue_summary.get("data", {})
            }

            result = self._create_result(
                True, "generate_financial_summary",
                result=summary
            )
            self._log_action("generate_financial_summary", result)

            return result

        except Exception as e:
            result = self._create_result(
                False, "generate_financial_summary",
                error=str(e)
            )
            self._log_action("generate_financial_summary", result)
            logger.error(f"Failed to generate financial summary: {e}")
            return result

    def record_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_date: str = None,
        reference: str = ""
    ) -> SkillResult:
        """
        Record a payment.

        Args:
            invoice_id: Invoice ID
            amount: Payment amount
            payment_date: Payment date
            reference: Payment reference

        Returns:
            SkillResult with payment status
        """
        try:
            odoo = self._get_odoo_client()

            if not odoo:
                return self._create_result(
                    False, "record_payment",
                    error="Odoo client not available"
                )

            payment_id = odoo.register_payment(
                invoice_id=invoice_id,
                amount=amount,
                payment_date=payment_date,
                payment_reference=reference
            )

            if payment_id:
                result = self._create_result(
                    True, "record_payment",
                    result={"payment_id": payment_id, "amount": amount}
                )
            else:
                result = self._create_result(
                    False, "record_payment",
                    error="Failed to record payment"
                )

            self._log_action("record_payment", result)
            return result

        except Exception as e:
            result = self._create_result(
                False, "record_payment",
                error=str(e)
            )
            self._log_action("record_payment", result)
            logger.error(f"Failed to record payment: {e}")
            return result


# =============================================================================
# Marketing Skill
# =============================================================================

class MarketingSkill(BaseSkill):
    """
    Marketing Skill for AI Employee.

    Handles all marketing-related operations:
    - generate_post: Generate social media content
    - publish_post: Publish to social platforms
    - collect_engagement_metrics: Get engagement data
    """

    @property
    def skill_name(self) -> str:
        return "marketing"

    @property
    def available_actions(self) -> list:
        return ["generate_post", "publish_post", "collect_engagement_metrics"]

    def generate_post(
        self,
        post_type: str = "educational",
        topic: str = "",
        platform: str = "facebook"
    ) -> SkillResult:
        """
        Generate social media post content.

        Args:
            post_type: Type of post (educational, case_study, sales_cta)
            topic: Post topic
            platform: Target platform

        Returns:
            SkillResult with generated content
        """
        try:
            content = {
                "post_type": post_type,
                "topic": topic,
                "platform": platform,
                "content": "",
                "hashtags": []
            }

            # Generate based on type
            if post_type == "educational":
                content["content"] = f"""📚 Did you know?

{topic or 'Industry Tip'}

Here's something valuable to help you succeed...

💡 Save this for later!

#LearnWithUs #Tips #Education"""

            elif post_type == "case_study":
                content["content"] = f"""🎯 Success Story

How we helped achieve amazing results with {topic or 'our solution'}...

✅ Problem identified
✅ Solution implemented  
✅ Results delivered

Want similar results? Let's talk!

#CaseStudy #Success #Results"""

            elif post_type == "sales_cta":
                content["content"] = f"""🚀 Special Offer

Ready to transform your business with {topic or 'our services'}?

⏰ Limited time offer
📞 Contact us today

Click the link to get started!

#SpecialOffer #LimitedTime #ActNow"""

            content["hashtags"] = self._extract_hashtags(content["content"])

            result = self._create_result(
                True, "generate_post",
                result=content
            )
            self._log_action("generate_post", result)

            logger.info(f"Generated {post_type} post for {platform}")
            return result

        except Exception as e:
            result = self._create_result(
                False, "generate_post",
                error=str(e)
            )
            self._log_action("generate_post", result)
            logger.error(f"Failed to generate post: {e}")
            return result

    def _extract_hashtags(self, content: str) -> list:
        """Extract or generate hashtags from content."""
        # Common hashtags by category
        base_hashtags = [
            "#Business", "#Growth", "#Success", "#Entrepreneur",
            "#SmallBusiness", "#Marketing", "#Tips"
        ]
        return base_hashtags[:5]

    def publish_post(
        self,
        platform: str,
        content: str,
        media_url: str = None,
        scheduled_time: datetime = None
    ) -> SkillResult:
        """
        Publish post to social platform.

        Args:
            platform: Target platform (facebook, instagram, twitter)
            content: Post content
            media_url: Media URL to attach
            scheduled_time: When to publish

        Returns:
            SkillResult with publish status
        """
        try:
            if scheduled_time:
                # Schedule for later
                from modules.social.social_scheduler import SocialScheduler
                scheduler = SocialScheduler(self.vault_path)

                post = scheduler.schedule_post(
                    platform=platform,
                    content=content,
                    scheduled_time=scheduled_time,
                    media_urls=[media_url] if media_url else []
                )

                result = self._create_result(
                    True, "publish_post",
                    result={"post_id": post.post_id, "scheduled": True}
                )
            else:
                # Publish immediately based on platform
                if platform == "facebook":
                    result = self._publish_to_facebook(content, media_url)
                elif platform == "instagram":
                    result = self._publish_to_instagram(content, media_url)
                elif platform == "twitter":
                    result = self._publish_to_twitter(content, media_url)
                else:
                    result = self._create_result(
                        False, "publish_post",
                        error=f"Unsupported platform: {platform}"
                    )

            self._log_action("publish_post", result)
            return result

        except Exception as e:
            result = self._create_result(
                False, "publish_post",
                error=str(e)
            )
            self._log_action("publish_post", result)
            logger.error(f"Failed to publish post: {e}")
            return result

    def _publish_to_facebook(self, content: str, media_url: str = None) -> SkillResult:
        """Publish to Facebook."""
        try:
            from modules.social.facebook_agent import FacebookAgent
            agent = FacebookAgent()

            if not agent.is_configured:
                return self._create_result(
                    False, "publish_post",
                    error="Facebook not configured"
                )

            post = agent.publish_post(message=content, image_url=media_url)

            return self._create_result(
                True, "publish_post",
                result={"platform": "facebook", "post_id": post.post_id}
            )
        except ImportError:
            return self._create_result(
                False, "publish_post",
                error="Facebook agent not available"
            )

    def _publish_to_instagram(self, content: str, media_url: str = None) -> SkillResult:
        """Publish to Instagram."""
        try:
            from modules.social.instagram_agent import InstagramAgent
            agent = InstagramAgent()

            if not agent.is_configured:
                return self._create_result(
                    False, "publish_post",
                    error="Instagram not configured"
                )

            if not media_url:
                return self._create_result(
                    False, "publish_post",
                    error="Instagram requires an image"
                )

            post = agent.publish_post(image_url=media_url, caption=content)

            return self._create_result(
                True, "publish_post",
                result={"platform": "instagram", "media_id": post.media_id}
            )
        except ImportError:
            return self._create_result(
                False, "publish_post",
                error="Instagram agent not available"
            )

    def _publish_to_twitter(self, content: str, media_url: str = None) -> SkillResult:
        """Publish to Twitter."""
        try:
            from modules.social.twitter_agent import TwitterAgent
            agent = TwitterAgent()

            if not agent.is_configured:
                return self._create_result(
                    False, "publish_post",
                    error="Twitter not configured"
                )

            tweet = agent.publish_tweet(
                text=content,
                media_urls=[media_url] if media_url else []
            )

            return self._create_result(
                True, "publish_post",
                result={"platform": "twitter", "tweet_id": tweet.tweet_id}
            )
        except ImportError:
            return self._create_result(
                False, "publish_post",
                error="Twitter agent not available"
            )

    def collect_engagement_metrics(
        self,
        platform: str,
        post_id: str
    ) -> SkillResult:
        """
        Collect engagement metrics for a post.

        Args:
            platform: Platform name
            post_id: Post/Media/Tweet ID

        Returns:
            SkillResult with metrics
        """
        try:
            metrics = {"platform": platform, "post_id": post_id}

            if platform == "facebook":
                from modules.social.facebook_agent import FacebookAgent
                agent = FacebookAgent()
                if agent.is_configured:
                    post_metrics = agent.get_engagement_metrics(post_id)
                    metrics = {
                        "platform": platform,
                        "post_id": post_id,
                        "likes": post_metrics.likes,
                        "comments": post_metrics.comments,
                        "shares": post_metrics.shares,
                        "engagement_rate": post_metrics.engagement_rate
                    }

            elif platform == "instagram":
                from modules.social.instagram_agent import InstagramAgent
                agent = InstagramAgent()
                if agent.is_configured:
                    post_metrics = agent.get_engagement_metrics(post_id)
                    metrics = {
                        "platform": platform,
                        "post_id": post_id,
                        "likes": post_metrics.likes,
                        "comments": post_metrics.comments,
                        "saves": post_metrics.saves,
                        "engagement_rate": post_metrics.engagement_rate
                    }

            elif platform == "twitter":
                from modules.social.twitter_agent import TwitterAgent
                agent = TwitterAgent()
                if agent.is_configured:
                    post_metrics = agent.get_tweet_metrics(post_id)
                    metrics = {
                        "platform": platform,
                        "post_id": post_id,
                        "likes": post_metrics.likes,
                        "retweets": post_metrics.retweets,
                        "replies": post_metrics.replies,
                        "engagement_rate": post_metrics.engagement_rate
                    }

            result = self._create_result(
                True, "collect_engagement_metrics",
                result=metrics
            )
            self._log_action("collect_engagement_metrics", result)

            return result

        except Exception as e:
            result = self._create_result(
                False, "collect_engagement_metrics",
                error=str(e)
            )
            self._log_action("collect_engagement_metrics", result)
            logger.error(f"Failed to collect metrics: {e}")
            return result


# =============================================================================
# Planning Skill
# =============================================================================

class PlanningSkill(BaseSkill):
    """
    Planning Skill for AI Employee.

    Handles all planning-related operations:
    - analyze_tasks: Analyze pending tasks
    - prioritize_tasks: Prioritize task queue
    - generate_execution_plan: Create execution plan
    """

    @property
    def skill_name(self) -> str:
        return "planning"

    @property
    def available_actions(self) -> list:
        return ["analyze_tasks", "prioritize_tasks", "generate_execution_plan"]

    def analyze_tasks(self, limit: int = 10) -> SkillResult:
        """
        Analyze pending tasks.

        Args:
            limit: Maximum tasks to analyze

        Returns:
            SkillResult with analysis
        """
        try:
            from modules.planning.planner_agent import PlannerAgent
            planner = PlannerAgent(self.vault_path)

            tasks = planner.get_pending_tasks()[:limit]
            analysis_results = []

            for task in tasks:
                analysis = planner.analyze_task(task)
                analysis_results.append({
                    "task_id": task.get("task_id"),
                    "title": task.get("title"),
                    "category": analysis.category,
                    "urgency": analysis.urgency,
                    "complexity": analysis.complexity,
                    "estimated_duration": analysis.estimated_duration
                })

            result = self._create_result(
                True, "analyze_tasks",
                result={
                    "tasks_analyzed": len(analysis_results),
                    "tasks": analysis_results
                }
            )
            self._log_action("analyze_tasks", result)

            return result

        except Exception as e:
            result = self._create_result(
                False, "analyze_tasks",
                error=str(e)
            )
            self._log_action("analyze_tasks", result)
            logger.error(f"Failed to analyze tasks: {e}")
            return result

    def prioritize_tasks(self) -> SkillResult:
        """
        Prioritize all pending tasks.

        Returns:
            SkillResult with prioritized list
        """
        try:
            from modules.planning.planner_agent import PlannerAgent
            planner = PlannerAgent(self.vault_path)

            tasks = planner.get_pending_tasks()
            prioritized = planner.prioritize_tasks(tasks)

            result = self._create_result(
                True, "prioritize_tasks",
                result={
                    "total_tasks": len(prioritized),
                    "prioritized_tasks": [
                        {"task_id": t.get("task_id"), "title": t.get("title")}
                        for t in prioritized
                    ]
                }
            )
            self._log_action("prioritize_tasks", result)

            return result

        except Exception as e:
            result = self._create_result(
                False, "prioritize_tasks",
                error=str(e)
            )
            self._log_action("prioritize_tasks", result)
            logger.error(f"Failed to prioritize tasks: {e}")
            return result

    def generate_execution_plan(self, task_id: str) -> SkillResult:
        """
        Generate execution plan for a task.

        Args:
            task_id: Task ID to plan

        Returns:
            SkillResult with execution plan
        """
        try:
            from modules.planning.planner_agent import PlannerAgent
            planner = PlannerAgent(self.vault_path)

            # Find task
            tasks = planner.get_pending_tasks()
            task = next((t for t in tasks if t.get("task_id") == task_id), None)

            if not task:
                return self._create_result(
                    False, "generate_execution_plan",
                    error=f"Task not found: {task_id}"
                )

            plan = planner.generate_plan(task)
            planner.save_plan(plan)

            result = self._create_result(
                True, "generate_execution_plan",
                result={
                    "plan_id": plan.plan_id,
                    "task_id": task_id,
                    "steps": len(plan.steps),
                    "estimated_duration": plan.total_estimated_duration
                }
            )
            self._log_action("generate_execution_plan", result)

            return result

        except Exception as e:
            result = self._create_result(
                False, "generate_execution_plan",
                error=str(e)
            )
            self._log_action("generate_execution_plan", result)
            logger.error(f"Failed to generate execution plan: {e}")
            return result


# =============================================================================
# Skill Registry
# =============================================================================

class SkillRegistry:
    """Registry for all AI skills."""

    def __init__(self, vault_path: Path = None):
        """
        Initialize skill registry.

        Args:
            vault_path: Path to vault
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self._skills = {}

        # Register default skills
        self.register("communication", CommunicationSkill(self.vault_path))
        self.register("accounting", AccountingSkill(self.vault_path))
        self.register("marketing", MarketingSkill(self.vault_path))
        self.register("planning", PlanningSkill(self.vault_path))

    def register(self, name: str, skill: BaseSkill):
        """Register a skill."""
        self._skills[name] = skill
        logger.info(f"Registered skill: {name}")

    def get(self, name: str) -> Optional[BaseSkill]:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list:
        """List all registered skills."""
        return list(self._skills.keys())

    def get_all_actions(self) -> dict:
        """Get all available actions from all skills."""
        actions = {}
        for name, skill in self._skills.items():
            actions[name] = skill.available_actions
        return actions


# =============================================================================
# Factory Functions
# =============================================================================

def create_communication_skill(vault_path: Path = None) -> CommunicationSkill:
    """Create communication skill."""
    return CommunicationSkill(vault_path)


def create_accounting_skill(vault_path: Path = None) -> AccountingSkill:
    """Create accounting skill."""
    return AccountingSkill(vault_path)


def create_marketing_skill(vault_path: Path = None) -> MarketingSkill:
    """Create marketing skill."""
    return MarketingSkill(vault_path)


def create_planning_skill(vault_path: Path = None) -> PlanningSkill:
    """Create planning skill."""
    return PlanningSkill(vault_path)


def create_skill_registry(vault_path: Path = None) -> SkillRegistry:
    """Create skill registry."""
    return SkillRegistry(vault_path)
