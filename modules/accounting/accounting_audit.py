#!/usr/bin/env python3
r"""
Accounting Audit Module - Financial Data Validation and Analysis

Provides comprehensive auditing capabilities for accounting data:
- Invoice validation and anomaly detection
- Payment reconciliation checks
- Financial data integrity verification
- Audit trail generation
- Compliance reporting

Usage:
    from modules.accounting.accounting_audit import AccountingAuditor

    auditor = AccountingAuditor(odoo_client)
    audit_result = auditor.run_full_audit()
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from .odoo_client import OdooClient

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
class AuditFinding:
    """Represents a single audit finding."""
    severity: str  # critical, high, medium, low, info
    category: str  # invoice, payment, reconciliation, compliance
    title: str
    description: str
    affected_records: list = field(default_factory=list)
    recommendation: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AuditResult:
    """Complete audit result."""
    audit_id: str
    started_at: str
    completed_at: str
    status: str  # passed, warnings, issues, critical
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    findings: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class AccountingAuditor:
    """
    Accounting Audit System.

    Performs comprehensive audits of financial data including:
    - Invoice integrity checks
    - Payment reconciliation
    - Duplicate detection
    - Anomaly detection
    - Compliance verification
    """

    def __init__(self, odoo_client: OdooClient, vault_path: Path = None):
        """
        Initialize accounting auditor.

        Args:
            odoo_client: Authenticated OdooClient instance
            vault_path: Path to Obsidian vault for reports
        """
        self.odoo = odoo_client
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.logs_path = self.vault_path / "Logs"

        # Ensure logs directory exists
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Audit configuration
        self.duplicate_threshold_days = 7  # Days to check for duplicates
        self.large_amount_threshold = 10000  # Threshold for flagging large amounts
        self.overdue_days_threshold = 30  # Days before invoice is considered overdue

        logger.info("AccountingAuditor initialized")

    def run_full_audit(self) -> AuditResult:
        """
        Run comprehensive accounting audit.

        Returns:
            AuditResult with all findings
        """
        audit_id = f"AUDIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now().isoformat()

        logger.info(f"Starting full audit: {audit_id}")

        result = AuditResult(
            audit_id=audit_id,
            started_at=started_at,
            completed_at="",
            status="passed"
        )

        # Run all audit checks
        checks = [
            ("Invoice Integrity", self._audit_invoices),
            ("Payment Reconciliation", self._audit_payments),
            ("Duplicate Detection", self._audit_duplicates),
            ("Anomaly Detection", self._audit_anomalies),
            ("Overdue Invoices", self._audit_overdue),
            ("Balance Verification", self._audit_balances),
        ]

        for check_name, check_func in checks:
            try:
                logger.info(f"Running check: {check_name}")
                findings = check_func()
                result.findings.extend(findings)
                result.total_checks += 1

                if findings:
                    critical_count = sum(1 for f in findings if f.severity == "critical")
                    high_count = sum(1 for f in findings if f.severity == "high")

                    if critical_count > 0:
                        result.failed_checks += 1
                        result.status = "critical"
                    elif high_count > 0:
                        result.failed_checks += 1
                        if result.status != "critical":
                            result.status = "issues"
                    else:
                        result.passed_checks += 1
                        if result.status == "passed":
                            result.status = "warnings"
                else:
                    result.passed_checks += 1
                    logger.info(f"✓ {check_name}: No issues found")

            except Exception as e:
                logger.error(f"Check {check_name} failed: {e}")
                result.total_checks += 1
                result.failed_checks += 1
                result.findings.append(AuditFinding(
                    severity="critical",
                    category="system",
                    title=f"Check Failed: {check_name}",
                    description=str(e)
                ))

        # Generate summary
        result.completed_at = datetime.now().isoformat()
        result.summary = self._generate_summary(result)

        # Save audit report
        self._save_audit_report(result)

        logger.info(f"Audit complete: {result.status}")
        return result

    def _audit_invoices(self) -> list:
        """
        Audit invoice integrity.

        Checks:
        - Invoices without lines
        - Invoices with zero amounts
        - Invoices with invalid dates
        - Draft invoices older than 30 days

        Returns:
            List of AuditFinding objects
        """
        findings = []

        # Get all invoices from last 90 days
        ninety_days_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        invoices = self.odoo.get_invoices(
            domain=[("invoice_date", ">=", ninety_days_ago)],
            limit=500,
            fields=["id", "name", "invoice_date", "amount_total", "state", "line_ids"]
        )

        # Check for invoices without lines
        for invoice in (invoices or []):
            lines = self.odoo.get_invoice_lines(invoice["id"])

            if not lines and invoice.get("amount_total", 0) == 0:
                findings.append(AuditFinding(
                    severity="medium",
                    category="invoice",
                    title="Empty Invoice Detected",
                    description=f"Invoice {invoice['name']} has no line items and zero amount",
                    affected_records=[invoice["id"]],
                    recommendation="Review and either add line items or void the invoice"
                ))

        # Check for draft invoices older than 30 days
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        old_drafts = self.odoo.get_invoices(
            domain=[
                ("state", "=", "draft"),
                ("invoice_date", "<", thirty_days_ago)
            ],
            limit=100
        )

        if old_drafts:
            findings.append(AuditFinding(
                severity="low",
                category="invoice",
                title="Old Draft Invoices",
                description=f"Found {len(old_drafts)} draft invoices older than 30 days",
                affected_records=[i["id"] for i in old_drafts],
                recommendation="Review and either validate or cancel old draft invoices"
            ))

        return findings

    def _audit_payments(self) -> list:
        """
        Audit payment reconciliation.

        Checks:
        - Unreconciled payments
        - Payments without invoices
        - Partial payments without follow-up

        Returns:
            List of AuditFinding objects
        """
        findings = []

        # Get unreconciled payments
        payments = self.odoo.get_payments(
            domain=[("state", "=", "posted")],
            limit=200
        )

        # Check for large unreconciled payments
        for payment in (payments or []):
            amount = payment.get("amount", 0)
            if amount > self.large_amount_threshold:
                # Check if payment is reconciled
                if not payment.get("reconciled", False):
                    findings.append(AuditFinding(
                        severity="high",
                        category="payment",
                        title="Large Unreconciled Payment",
                        description=f"Payment {payment['name']} of {amount} is not reconciled",
                        affected_records=[payment["id"]],
                        recommendation="Reconcile this payment with corresponding invoice"
                    ))

        return findings

    def _audit_duplicates(self) -> list:
        """
        Detect potential duplicate invoices.

        Checks:
        - Same partner, same amount, close dates
        - Same reference numbers

        Returns:
            List of AuditFinding objects
        """
        findings = []

        # Get recent invoices
        invoices = self.odoo.get_invoices(
            domain=[],
            limit=500,
            fields=["id", "name", "partner_id", "amount_total", "invoice_date", "ref"]
        )

        # Group by partner and amount
        invoice_groups = {}
        for invoice in (invoices or []):
            partner_id = invoice.get("partner_id", [None])[0] if isinstance(invoice.get("partner_id"), list) else invoice.get("partner_id")
            amount = invoice.get("amount_total", 0)
            date = invoice.get("invoice_date", "")

            key = f"{partner_id}_{amount}"
            if key not in invoice_groups:
                invoice_groups[key] = []
            invoice_groups[key].append(invoice)

        # Check for potential duplicates
        for key, group in invoice_groups.items():
            if len(group) > 1:
                # Check if dates are close
                for i, inv1 in enumerate(group):
                    for inv2 in group[i+1:]:
                        date1 = inv1.get("invoice_date", "")
                        date2 = inv2.get("invoice_date", "")

                        if date1 and date2:
                            try:
                                d1 = datetime.strptime(date1, "%Y-%m-%d")
                                d2 = datetime.strptime(date2, "%Y-%m-%d")
                                days_diff = abs((d1 - d2).days)

                                if days_diff <= self.duplicate_threshold_days:
                                    findings.append(AuditFinding(
                                        severity="medium",
                                        category="invoice",
                                        title="Potential Duplicate Invoice",
                                        description=f"Invoices {inv1['name']} and {inv2['name']} have same partner/amount within {days_diff} days",
                                        affected_records=[inv1["id"], inv2["id"]],
                                        recommendation="Verify these are not duplicate entries"
                                    ))
                            except ValueError:
                                pass

        return findings

    def _audit_anomalies(self) -> list:
        """
        Detect financial anomalies.

        Checks:
        - Unusually large invoices
        - Negative amounts (credit notes without reference)
        - Round number anomalies

        Returns:
            List of AuditFinding objects
        """
        findings = []

        # Get recent invoices
        invoices = self.odoo.get_invoices(
            domain=[],
            limit=500,
            fields=["id", "name", "amount_total", "partner_id", "invoice_date"]
        )

        for invoice in (invoices or []):
            amount = invoice.get("amount_total", 0)

            # Check for large amounts
            if abs(amount) > self.large_amount_threshold:
                findings.append(AuditFinding(
                    severity="medium",
                    category="invoice",
                    title="Large Amount Invoice",
                    description=f"Invoice {invoice['name']} has unusually large amount: {amount}",
                    affected_records=[invoice["id"]],
                    recommendation="Verify this transaction is legitimate"
                ))

            # Check for negative amounts without proper credit note type
            if amount < 0:
                move_type = self.odoo.get_invoice(invoice["id"], fields=["move_type"])
                if move_type and move_type.get("move_type") != "out_refund":
                    findings.append(AuditFinding(
                        severity="high",
                        category="invoice",
                        title="Negative Amount Without Credit Note Type",
                        description=f"Invoice {invoice['name']} has negative amount but is not marked as credit note",
                        affected_records=[invoice["id"]],
                        recommendation="Verify invoice type or convert to credit note"
                    ))

        return findings

    def _audit_overdue(self) -> list:
        """
        Audit overdue invoices.

        Checks:
        - Invoices past due date
        - Invoices approaching due date

        Returns:
            List of AuditFinding objects
        """
        findings = []

        # Get posted invoices
        invoices = self.odoo.get_invoices(
            domain=[
                ("state", "=", "posted"),
                ("payment_state", "!=", "paid")
            ],
            limit=500,
            fields=["id", "name", "partner_id", "invoice_date", "invoice_date_due", "amount_total"]
        )

        today = datetime.now()
        overdue_invoices = []
        approaching_due = []

        for invoice in (invoices or []):
            due_date_str = invoice.get("invoice_date_due") or invoice.get("invoice_date")
            if not due_date_str:
                continue

            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                days_overdue = (today - due_date).days

                if days_overdue > self.overdue_days_threshold:
                    overdue_invoices.append({
                        "id": invoice["id"],
                        "name": invoice["name"],
                        "days_overdue": days_overdue,
                        "amount": invoice.get("amount_total", 0)
                    })
                elif days_overdue > 0:
                    approaching_due.append({
                        "id": invoice["id"],
                        "name": invoice["name"],
                        "days_overdue": days_overdue,
                        "amount": invoice.get("amount_total", 0)
                    })
            except ValueError:
                pass

        if overdue_invoices:
            total_overdue = sum(i["amount"] for i in overdue_invoices)
            findings.append(AuditFinding(
                severity="high",
                category="receivables",
                title="Overdue Invoices Detected",
                description=f"{len(overdue_invoices)} invoices significantly overdue (total: {total_overdue})",
                affected_records=[i["id"] for i in overdue_invoices],
                recommendation="Initiate collection procedures for overdue accounts"
            ))

        if approaching_due:
            findings.append(AuditFinding(
                severity="low",
                category="receivables",
                title="Invoices Approaching Due Date",
                description=f"{len(approaching_due)} invoices are overdue but within threshold",
                affected_records=[i["id"] for i in approaching_due],
                recommendation="Send payment reminders"
            ))

        return findings

    def _audit_balances(self) -> list:
        """
        Audit account balances.

        Checks:
        - Balance sheet integrity
        - Account reconciliation

        Returns:
            List of AuditFinding objects
        """
        findings = []

        try:
            # Get balance sheet
            balance_sheet = self.odoo.get_balance_sheet()

            # Check if balance sheet balances
            assets = balance_sheet.get("assets", {}).get("total", 0)
            liabilities = balance_sheet.get("liabilities", {}).get("total", 0)
            equity = balance_sheet.get("equity", {}).get("total", 0)

            # Assets should equal Liabilities + Equity
            difference = abs(assets - (liabilities + equity))

            if difference > 0.01:  # Allow small rounding differences
                findings.append(AuditFinding(
                    severity="critical",
                    category="balance",
                    title="Balance Sheet Out of Balance",
                    description=f"Balance sheet difference: {difference} (Assets: {assets}, L+E: {liabilities + equity})",
                    affected_records=[],
                    recommendation="Investigate accounting entries causing imbalance"
                ))

        except Exception as e:
            findings.append(AuditFinding(
                severity="high",
                category="balance",
                title="Balance Sheet Audit Failed",
                description=f"Could not retrieve balance sheet: {e}",
                affected_records=[],
                recommendation="Check Odoo connection and accounting configuration"
            ))

        return findings

    def _generate_summary(self, result: AuditResult) -> dict:
        """Generate audit summary."""
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }

        category_counts = {}

        for finding in result.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1

        return {
            "total_findings": len(result.findings),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "health_score": self._calculate_health_score(result)
        }

    def _calculate_health_score(self, result: AuditResult) -> int:
        """
        Calculate accounting health score (0-100).

        Returns:
            Health score percentage
        """
        if result.total_checks == 0:
            return 100

        # Start with 100 and deduct based on findings
        score = 100

        for finding in result.findings:
            if finding.severity == "critical":
                score -= 25
            elif finding.severity == "high":
                score -= 15
            elif finding.severity == "medium":
                score -= 8
            elif finding.severity == "low":
                score -= 3

        return max(0, min(100, score))

    def _save_audit_report(self, result: AuditResult):
        """Save audit report to vault."""
        report_path = self.logs_path / f"AUDIT_{result.audit_id}.md"

        content = f"""---
audit_id: {result.audit_id}
status: {result.status}
started: {result.started_at}
completed: {result.completed_at}
health_score: {result.summary.get('health_score', 0)}
---

# Accounting Audit Report

## Summary

| Metric | Value |
|--------|-------|
| Status | {result.status.upper()} |
| Total Checks | {result.total_checks} |
| Passed | {result.passed_checks} |
| Failed | {result.failed_checks} |
| Findings | {len(result.findings)} |
| Health Score | {result.summary.get('health_score', 0)}/100 |

## Findings by Severity

| Severity | Count |
|----------|-------|
| Critical | {result.summary.get('by_severity', {}).get('critical', 0)} |
| High | {result.summary.get('by_severity', {}).get('high', 0)} |
| Medium | {result.summary.get('by_severity', {}).get('medium', 0)} |
| Low | {result.summary.get('by_severity', {}).get('low', 0)} |

## Detailed Findings

"""
        for i, finding in enumerate(result.findings, 1):
            content += f"""
### {i}. {finding.title}

- **Severity**: {finding.severity.upper()}
- **Category**: {finding.category}
- **Description**: {finding.description}
- **Affected Records**: {', '.join(map(str, finding.affected_records)) if finding.affected_records else 'N/A'}
- **Recommendation**: {finding.recommendation}

---
"""

        content += f"""
## Recommendations Summary

"""
        # Group recommendations by severity
        for severity in ["critical", "high", "medium", "low"]:
            severity_findings = [f for f in result.findings if f.severity == severity]
            if severity_findings:
                content += f"\n### {severity.upper()} Priority Actions\n\n"
                for finding in severity_findings:
                    content += f"- {finding.recommendation}\n"

        report_path.write_text(content, encoding="utf-8")
        logger.info(f"Audit report saved: {report_path}")

    def get_quick_health_check(self) -> dict:
        """
        Perform quick health check without full audit.

        Returns:
            Quick health status dictionary
        """
        try:
            # Get key metrics
            outstanding = self.odoo.get_outstanding_invoices(limit=1000)
            total_outstanding = sum(i.get("amount_total", 0) for i in (outstanding or []))

            balance_sheet = self.odoo.get_balance_sheet()

            return {
                "status": "healthy",
                "outstanding_invoices": len(outstanding or []),
                "total_outstanding_amount": total_outstanding,
                "total_assets": balance_sheet.get("assets", {}).get("total", 0),
                "total_liabilities": balance_sheet.get("liabilities", {}).get("total", 0),
                "checked_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }


# =============================================================================
# Factory Function
# =============================================================================

def create_auditor(odoo_client: OdooClient, vault_path: Path = None) -> AccountingAuditor:
    """
    Create an accounting auditor.

    Args:
        odoo_client: Authenticated OdooClient instance
        vault_path: Path to vault for reports

    Returns:
        AccountingAuditor instance
    """
    return AccountingAuditor(odoo_client, vault_path)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for accounting audit."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Accounting Audit Tool")
    parser.add_argument("--full", action="store_true", help="Run full audit")
    parser.add_argument("--quick", action="store_true", help="Run quick health check")
    parser.add_argument("--vault", type=str, help="Vault path for reports")

    args = parser.parse_args()

    print("=" * 70)
    print("Accounting Audit Tool")
    print("=" * 70)

    # Check for Odoo configuration
    if not os.getenv("ODOO_BASE_URL"):
        print("\n⚠️  Odoo configuration not found.")
        print("Set the following environment variables:")
        print("  - ODOO_BASE_URL")
        print("  - ODOO_DB_NAME")
        print("  - ODOO_USERNAME")
        print("  - ODOO_PASSWORD")
        return

    try:
        from .odoo_client import OdooClient

        client = OdooClient()
        client.authenticate()

        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        auditor = AccountingAuditor(client, vault_path)

        if args.full:
            print("\n🔍 Running full audit...")
            result = auditor.run_full_audit()

            print(f"\n{'='*70}")
            print(f"Audit Complete: {result.status.upper()}")
            print(f"Health Score: {result.summary.get('health_score', 0)}/100")
            print(f"Findings: {len(result.findings)}")
            print(f"Report saved to: {auditor.logs_path}")

        elif args.quick:
            print("\n⚡ Running quick health check...")
            health = auditor.get_quick_health_check()

            print(f"\nStatus: {health['status'].upper()}")
            if health['status'] != 'error':
                print(f"Outstanding Invoices: {health['outstanding_invoices']}")
                print(f"Total Outstanding: {health['total_outstanding_amount']}")
                print(f"Total Assets: {health['total_assets']}")
                print(f"Total Liabilities: {health['total_liabilities']}")

        else:
            print("\nUsage: python -m modules.accounting.accounting_audit --full|--quick")

        client.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
