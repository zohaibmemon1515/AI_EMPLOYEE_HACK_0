#!/usr/bin/env python3
r"""
Invoice Sync Module - Bi-directional Invoice Synchronization

Provides invoice synchronization capabilities:
- Sync invoices from external sources to Odoo
- Export invoices from Odoo to external systems
- Track sync status and history
- Handle sync conflicts
- Generate sync reports

Usage:
    from modules.accounting.invoice_sync import InvoiceSync

    sync = InvoiceSync(odoo_client, vault_path)
    sync.import_invoices_from_folder()
    sync.export_pending_invoices()
"""

import json
import logging
import shutil
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict

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
class SyncResult:
    """Result of a sync operation."""
    sync_id: str
    operation: str  # import, export
    started_at: str
    completed_at: str
    status: str  # success, partial, failed
    total_items: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class InvoiceData:
    """Invoice data for sync."""
    reference: str
    partner_name: str
    partner_email: str = ""
    invoice_date: str = ""
    due_date: str = ""
    lines: list = None
    total_amount: float = 0.0
    currency: str = "USD"
    notes: str = ""
    external_id: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.lines is None:
            self.lines = []
        if self.metadata is None:
            self.metadata = {}


class InvoiceSync:
    """
    Invoice Synchronization System.

    Handles bi-directional sync of invoices between:
    - Odoo ERP
    - Local file system (Markdown files)
    - External APIs (when configured)
    """

    def __init__(
        self,
        odoo_client: OdooClient,
        vault_path: Path = None,
        sync_folder: str = "Invoice_Sync"
    ):
        """
        Initialize invoice sync.

        Args:
            odoo_client: Authenticated OdooClient instance
            vault_path: Path to Obsidian vault
            sync_folder: Name of sync folder within vault
        """
        self.odoo = odoo_client
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.sync_folder = self.vault_path / sync_folder

        # Create sync subfolders
        self.incoming_folder = self.sync_folder / "Incoming"
        self.processed_folder = self.sync_folder / "Processed"
        self.failed_folder = self.sync_folder / "Failed"
        self.export_folder = self.sync_folder / "Export"

        for folder in [
            self.sync_folder,
            self.incoming_folder,
            self.processed_folder,
            self.failed_folder,
            self.export_folder
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        # Sync state
        self.sync_history_path = self.sync_folder / "sync_history.json"
        self._load_sync_history()

        logger.info(f"InvoiceSync initialized at {self.sync_folder}")

    def _load_sync_history(self):
        """Load sync history from file."""
        if self.sync_history_path.exists():
            try:
                data = json.loads(self.sync_history_path.read_text())
                self.sync_history = data.get("history", [])
                self.last_sync = data.get("last_sync")
            except Exception as e:
                logger.warning(f"Could not load sync history: {e}")
                self.sync_history = []
                self.last_sync = None
        else:
            self.sync_history = []
            self.last_sync = None

    def _save_sync_history(self):
        """Save sync history to file."""
        data = {
            "history": self.sync_history[-100:],  # Keep last 100 syncs
            "last_sync": self.last_sync,
            "updated_at": datetime.now().isoformat()
        }
        self.sync_history_path.write_text(json.dumps(data, indent=2))

    def _record_sync(self, result: SyncResult):
        """Record sync operation in history."""
        self.sync_history.append({
            "sync_id": result.sync_id,
            "operation": result.operation,
            "status": result.status,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "stats": {
                "total": result.total_items,
                "successful": result.successful,
                "failed": result.failed,
                "skipped": result.skipped
            }
        })
        self.last_sync = datetime.now().isoformat()
        self._save_sync_history()

    # =========================================================================
    # Import Operations
    # =========================================================================

    def import_invoices_from_folder(self) -> SyncResult:
        """
        Import invoices from Incoming folder.

        Looks for Markdown files with invoice data and creates
        corresponding invoices in Odoo.

        Returns:
            SyncResult with import statistics
        """
        sync_id = f"IMPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now().isoformat()

        logger.info(f"Starting invoice import: {sync_id}")

        result = SyncResult(
            sync_id=sync_id,
            operation="import",
            started_at=started_at,
            completed_at=""
        )

        # Find all invoice files
        invoice_files = list(self.incoming_folder.glob("*.md"))
        result.total_items = len(invoice_files)

        if not invoice_files:
            logger.info("No invoice files to import")
            result.status = "success"
            result.completed_at = datetime.now().isoformat()
            self._record_sync(result)
            return result

        for filepath in invoice_files:
            try:
                logger.info(f"Processing: {filepath.name}")

                # Parse invoice file
                invoice_data = self._parse_invoice_file(filepath)

                if not invoice_data:
                    result.skipped += 1
                    result.errors.append(f"Could not parse: {filepath.name}")
                    continue

                # Find or create partner
                partner_id = self._find_or_create_partner(invoice_data)

                if not partner_id:
                    result.failed += 1
                    result.errors.append(f"Could not create partner for: {filepath.name}")
                    continue

                # Create invoice lines
                lines = self._prepare_invoice_lines(invoice_data)

                # Create invoice in Odoo
                invoice_id = self.odoo.create_invoice(
                    partner_id=partner_id,
                    invoice_type="out_invoice",
                    lines=lines,
                    invoice_date=invoice_data.invoice_date or datetime.now().strftime("%Y-%m-%d"),
                    narration=invoice_data.notes
                )

                if invoice_id:
                    # Validate invoice
                    self.odoo.validate_invoice(invoice_id)

                    # Move file to processed
                    shutil.move(
                        str(filepath),
                        str(self.processed_folder / filepath.name)
                    )

                    result.successful += 1
                    logger.info(f"Created invoice {invoice_id} from {filepath.name}")
                else:
                    result.failed += 1
                    result.errors.append(f"Failed to create invoice: {filepath.name}")

            except Exception as e:
                logger.error(f"Error processing {filepath.name}: {e}")
                result.failed += 1
                result.errors.append(f"{filepath.name}: {str(e)}")

                # Move to failed folder
                try:
                    shutil.move(str(filepath), str(self.failed_folder / filepath.name))
                except:
                    pass

        result.completed_at = datetime.now().isoformat()
        result.status = "success" if result.failed == 0 else ("partial" if result.successful > 0 else "failed")

        self._record_sync(result)
        logger.info(f"Import complete: {result.successful}/{result.total_items} successful")

        return result

    def _parse_invoice_file(self, filepath: Path) -> Optional[InvoiceData]:
        """
        Parse invoice Markdown file.

        Expected format:
        ---
        reference: INV-001
        partner_name: Acme Corp
        partner_email: billing@acme.com
        invoice_date: 2024-01-15
        due_date: 2024-02-15
        total_amount: 1500.00
        currency: USD
        ---

        ## Line Items

        | Description | Quantity | Unit Price |
        |-------------|----------|------------|
        | Service A   | 10       | 100.00     |
        | Service B   | 5        | 100.00     |

        Args:
            filepath: Path to invoice file

        Returns:
            InvoiceData object or None
        """
        try:
            content = filepath.read_text(encoding="utf-8")

            # Extract frontmatter
            frontmatter = {}
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm_text = parts[1]
                    for line in fm_text.strip().split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            frontmatter[key.strip()] = value.strip()

            # Extract required fields
            reference = frontmatter.get("reference", filepath.stem)
            partner_name = frontmatter.get("partner_name", "")
            partner_email = frontmatter.get("partner_email", "")

            if not partner_name:
                logger.warning(f"No partner name in {filepath.name}")
                return None

            # Parse line items from markdown table
            lines = self._parse_line_items(content)

            # Calculate total if not provided
            total_amount = float(frontmatter.get("total_amount", 0))
            if total_amount == 0 and lines:
                total_amount = sum(
                    line.get("quantity", 1) * line.get("price_unit", 0)
                    for line in lines
                )

            return InvoiceData(
                reference=reference,
                partner_name=partner_name,
                partner_email=partner_email,
                invoice_date=frontmatter.get("invoice_date", ""),
                due_date=frontmatter.get("due_date", ""),
                lines=lines,
                total_amount=total_amount,
                currency=frontmatter.get("currency", "USD"),
                notes=frontmatter.get("notes", ""),
                external_id=frontmatter.get("external_id", ""),
                metadata={"source_file": filepath.name}
            )

        except Exception as e:
            logger.error(f"Error parsing {filepath.name}: {e}")
            return None

    def _parse_line_items(self, content: str) -> list:
        """Parse line items from markdown table."""
        lines = []

        # Look for markdown table
        table_match = re.search(
            r'\|\s*Description\s*\|\s*Quantity\s*\|\s*Unit Price\s*\|.*?\n\|[-| ]+\|.*?(?=\n\n|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if table_match:
            table_text = table_match.group(0)
            rows = table_text.strip().split("\n")[2:]  # Skip header and separator

            for row in rows:
                cells = [c.strip() for c in row.split("|") if c.strip()]
                if len(cells) >= 3:
                    try:
                        lines.append({
                            "name": cells[0],
                            "quantity": float(cells[1]) if cells[1] else 1,
                            "price_unit": float(cells[2].replace("$", "").replace(",", "")) if cells[2] else 0
                        })
                    except ValueError:
                        pass

        return lines

    def _find_or_create_partner(self, invoice_data: InvoiceData) -> Optional[int]:
        """
        Find existing partner or create new one.

        Args:
            invoice_data: Invoice data with partner info

        Returns:
            Partner ID or None
        """
        # Try to find by email
        if invoice_data.partner_email:
            partners = self.odoo.get_partners(
                domain=[("email", "=", invoice_data.partner_email)],
                limit=1
            )
            if partners:
                partner_id = partners[0]["id"]
                logger.info(f"Found existing partner: {partner_id}")
                return partner_id

        # Try to find by name
        partners = self.odoo.get_partners(
            domain=[("name", "=ilike", invoice_data.partner_name)],
            limit=1
        )
        if partners:
            partner_id = partners[0]["id"]
            logger.info(f"Found existing partner by name: {partner_id}")
            return partner_id

        # Create new partner
        partner_id = self.odoo.create_partner(
            name=invoice_data.partner_name,
            email=invoice_data.partner_email or "",
            is_customer=True
        )

        if partner_id:
            logger.info(f"Created new partner: {partner_id}")
            return partner_id

        return None

    def _prepare_invoice_lines(self, invoice_data: InvoiceData) -> list:
        """Prepare invoice lines for Odoo."""
        lines = []

        if invoice_data.lines:
            for line in invoice_data.lines:
                lines.append({
                    "name": line.get("name", "Service"),
                    "quantity": line.get("quantity", 1),
                    "price_unit": line.get("price_unit", 0)
                })
        else:
            # Single line for total amount
            lines.append({
                "name": invoice_data.reference or "Invoice",
                "quantity": 1,
                "price_unit": invoice_data.total_amount
            })

        return lines

    # =========================================================================
    # Export Operations
    # =========================================================================

    def export_pending_invoices(self) -> SyncResult:
        """
        Export pending invoices from Odoo to Export folder.

        Returns:
            SyncResult with export statistics
        """
        sync_id = f"EXPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now().isoformat()

        logger.info(f"Starting invoice export: {sync_id}")

        result = SyncResult(
            sync_id=sync_id,
            operation="export",
            started_at=started_at,
            completed_at=""
        )

        # Get recent invoices
        invoices = self.odoo.get_invoices(
            domain=[("state", "=", "posted")],
            limit=100,
            fields=["id", "name", "partner_id", "invoice_date", "amount_total", "state"]
        )

        result.total_items = len(invoices or [])

        if not invoices:
            logger.info("No invoices to export")
            result.status = "success"
            result.completed_at = datetime.now().isoformat()
            self._record_sync(result)
            return result

        for invoice in (invoices or []):
            try:
                # Check if already exported
                export_marker = self.export_folder / f".exported_{invoice['id']}"
                if export_marker.exists():
                    result.skipped += 1
                    continue

                # Get partner info
                partner_id = invoice.get("partner_id", [None])[0] if isinstance(invoice.get("partner_id"), list) else invoice.get("partner_id")
                partner = None
                if partner_id:
                    partners = self.odoo.get_partners(
                        domain=[("id", "=", partner_id)],
                        limit=1
                    )
                    if partners:
                        partner = partners[0]

                # Get invoice lines
                lines = self.odoo.get_invoice_lines(invoice["id"])

                # Create markdown file
                filepath = self.export_folder / f"INVOICE_{invoice['name']}.md"
                content = self._generate_invoice_markdown(invoice, partner, lines)
                filepath.write_text(content, encoding="utf-8")

                # Create export marker
                export_marker.write_text(
                    json.dumps({
                        "exported_at": datetime.now().isoformat(),
                        "invoice_id": invoice["id"]
                    })
                )

                result.successful += 1
                logger.info(f"Exported invoice {invoice['name']}")

            except Exception as e:
                logger.error(f"Error exporting invoice {invoice.get('name', 'unknown')}: {e}")
                result.failed += 1
                result.errors.append(f"Invoice {invoice.get('id', 'unknown')}: {str(e)}")

        result.completed_at = datetime.now().isoformat()
        result.status = "success" if result.failed == 0 else ("partial" if result.successful > 0 else "failed")

        self._record_sync(result)
        logger.info(f"Export complete: {result.successful}/{result.total_items} successful")

        return result

    def _generate_invoice_markdown(
        self,
        invoice: dict,
        partner: Optional[dict],
        lines: list
    ) -> str:
        """Generate markdown representation of invoice."""
        partner_name = partner.get("name", "Unknown") if partner else "Unknown"
        partner_email = partner.get("email", "") if partner else ""

        content = f"""---
reference: {invoice.get('name', 'N/A')}
partner_name: {partner_name}
partner_email: {partner_email}
invoice_date: {invoice.get('invoice_date', '')}
due_date: {invoice.get('invoice_date_due', '')}
total_amount: {invoice.get('amount_total', 0)}
currency: USD
state: {invoice.get('state', 'draft')}
odoo_id: {invoice.get('id', '')}
---

# Invoice: {invoice.get('name', 'N/A')}

## Partner Information

- **Name**: {partner_name}
- **Email**: {partner_email or 'N/A'}

## Invoice Details

| Field | Value |
|-------|-------|
| Invoice Date | {invoice.get('invoice_date', 'N/A')} |
| Due Date | {invoice.get('invoice_date_due', 'N/A')} |
| Total Amount | {invoice.get('amount_total', 0)} |
| Status | {invoice.get('state', 'draft')} |

## Line Items

| Description | Quantity | Unit Price | Total |
|-------------|----------|------------|-------|
"""
        for line in lines:
            name = line.get("name", "N/A")
            qty = line.get("quantity", 1)
            price = line.get("price_unit", 0)
            total = qty * price
            content += f"| {name} | {qty} | {price} | {total} |\n"

        content += f"""

---
*Exported from Odoo on {datetime.now().isoformat()}*
"""
        return content

    # =========================================================================
    # Sync Status and Reporting
    # =========================================================================

    def get_sync_status(self) -> dict:
        """
        Get current sync status.

        Returns:
            Status dictionary with sync statistics
        """
        # Count files in each folder
        incoming_count = len(list(self.incoming_folder.glob("*.md")))
        processed_count = len(list(self.processed_folder.glob("*.md")))
        failed_count = len(list(self.failed_folder.glob("*.md")))
        export_count = len(list(self.export_folder.glob("*.md")))

        return {
            "last_sync": self.last_sync,
            "total_syncs": len(self.sync_history),
            "folders": {
                "incoming": incoming_count,
                "processed": processed_count,
                "failed": failed_count,
                "export": export_count
            },
            "recent_syncs": self.sync_history[-5:]
        }

    def get_sync_report(self, sync_id: str = None) -> Optional[dict]:
        """
        Get detailed sync report.

        Args:
            sync_id: Specific sync ID to retrieve

        Returns:
            Sync report dictionary or None
        """
        if sync_id:
            for sync in self.sync_history:
                if sync.get("sync_id") == sync_id:
                    return sync
            return None

        # Return latest sync
        return self.sync_history[-1] if self.sync_history else None

    def cleanup_old_files(self, days: int = 30) -> int:
        """
        Clean up old processed files.

        Args:
            days: Keep files newer than this many days

        Returns:
            Number of files cleaned up
        """
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0

        for folder in [self.processed_folder, self.failed_folder]:
            for filepath in folder.glob("*.md"):
                try:
                    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if mtime < cutoff:
                        filepath.unlink()
                        cleaned += 1
                except Exception as e:
                    logger.warning(f"Could not process {filepath}: {e}")

        logger.info(f"Cleaned up {cleaned} old files")
        return cleaned


# =============================================================================
# Factory Function
# =============================================================================

def create_invoice_sync(
    odoo_client: OdooClient,
    vault_path: Path = None
) -> InvoiceSync:
    """
    Create an invoice sync instance.

    Args:
        odoo_client: Authenticated OdooClient instance
        vault_path: Path to vault

    Returns:
        InvoiceSync instance
    """
    return InvoiceSync(odoo_client, vault_path)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for invoice sync."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Invoice Sync Tool")
    parser.add_argument("--import", dest="do_import", action="store_true", help="Import invoices")
    parser.add_argument("--export", dest="do_export", action="store_true", help="Export invoices")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--cleanup", type=int, help="Clean up files older than N days")
    parser.add_argument("--vault", type=str, help="Vault path")

    args = parser.parse_args()

    print("=" * 70)
    print("Invoice Sync Tool")
    print("=" * 70)

    # Check for Odoo configuration
    if not os.getenv("ODOO_BASE_URL"):
        print("\n⚠️  Odoo configuration not found.")
        print("Set environment variables: ODOO_BASE_URL, ODOO_DB_NAME, etc.")
        return

    try:
        from .odoo_client import OdooClient

        client = OdooClient()
        client.authenticate()

        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        sync = InvoiceSync(client, vault_path)

        if args.do_import:
            print("\n📥 Importing invoices from Incoming folder...")
            result = sync.import_invoices_from_folder()
            print(f"\n{'='*70}")
            print(f"Import Complete: {result.status.upper()}")
            print(f"Successful: {result.successful}")
            print(f"Failed: {result.failed}")
            print(f"Skipped: {result.skipped}")

        elif args.do_export:
            print("\n📤 Exporting invoices to Export folder...")
            result = sync.export_pending_invoices()
            print(f"\n{'='*70}")
            print(f"Export Complete: {result.status.upper()}")
            print(f"Successful: {result.successful}")
            print(f"Failed: {result.failed}")
            print(f"Skipped: {result.skipped}")

        elif args.cleanup:
            print(f"\n🧹 Cleaning up files older than {args.cleanup} days...")
            cleaned = sync.cleanup_old_files(args.cleanup)
            print(f"Cleaned up {cleaned} files")

        else:
            print("\n📊 Sync Status:")
            status = sync.get_sync_status()
            print(f"  Last Sync: {status.get('last_sync', 'Never')}")
            print(f"  Total Syncs: {status.get('total_syncs', 0)}")
            print(f"  Folders:")
            print(f"    - Incoming: {status['folders']['incoming']}")
            print(f"    - Processed: {status['folders']['processed']}")
            print(f"    - Failed: {status['folders']['failed']}")
            print(f"    - Export: {status['folders']['export']}")

        client.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
