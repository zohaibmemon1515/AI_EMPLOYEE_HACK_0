#!/usr/bin/env python3
r"""
Odoo ERP Client - JSON-RPC API Integration

Provides comprehensive integration with Odoo Community Edition for accounting operations:
- Authentication via JSON-RPC
- Invoice creation and management
- Payment recording
- Financial data retrieval
- Customer/vendor management

Usage:
    from modules.accounting.odoo_client import OdooClient

    client = OdooClient(
        base_url="http://localhost:8069",
        db="odoo_db",
        username="admin",
        password="admin_password"
    )
    client.authenticate()
    invoices = client.get_invoices(limit=10)
"""

import json
import logging
import os
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path

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


class OdooRPCError(Exception):
    """Custom exception for Odoo RPC errors."""
    pass


class OdooAuthenticationError(Exception):
    """Custom exception for Odoo authentication errors."""
    pass


class OdooClient:
    """
    Odoo ERP Client using JSON-RPC API.

    Supports Odoo Community Edition 14.0+ with full accounting integration.
    """

    def __init__(
        self,
        base_url: str = None,
        db_name: str = None,
        username: str = None,
        password: str = None,
        api_key: str = None,
    ):
        """
        Initialize Odoo client.

        Args:
            base_url: Odoo server URL (e.g., http://localhost:8069)
            db_name: Database name
            username: Odoo username
            password: Odoo password
            api_key: Optional Odoo API key (for Odoo.sh or cloud)
        """
        # Load from environment if not provided
        self.base_url = base_url or os.getenv("ODOO_BASE_URL", "http://localhost:8069")
        self.db_name = db_name or os.getenv("ODOO_DB_NAME", "odoo")
        self.username = username or os.getenv("ODOO_USERNAME", "admin")
        self.password = password or os.getenv("ODOO_PASSWORD", "")
        self.api_key = api_key or os.getenv("ODOO_API_KEY", "")

        # Session state
        self._uid: Optional[int] = None
        self._session: requests.Session = requests.Session()
        self._authenticated: bool = False
        self._auth_expiry: Optional[datetime] = None

        # Cache for model information
        self._model_cache: dict = {}

        # Validate configuration
        self._validate_config()

        logger.info(f"OdooClient initialized for {self.base_url}/{self.db_name}")

    def _validate_config(self):
        """Validate configuration parameters."""
        if not self.base_url:
            raise ValueError("Odoo base URL is required")
        if not self.db_name:
            raise ValueError("Odoo database name is required")
        if not self.username:
            raise ValueError("Odoo username is required")
        if not self.password and not self.api_key:
            raise ValueError("Odoo password or API key is required")

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated and session is valid."""
        if not self._authenticated:
            return False
        if self._auth_expiry and datetime.now() > self._auth_expiry:
            self._authenticated = False
            return False
        return True

    @property
    def uid(self) -> Optional[int]:
        """Get current user ID."""
        return self._uid

    def authenticate(self) -> bool:
        """
        Authenticate with Odoo server.

        Returns:
            True if authentication successful

        Raises:
            OdooAuthenticationError: If authentication fails
        """
        try:
            # Use common.authenticate for Odoo 14+
            endpoint = f"{self.base_url}/jsonrpc"

            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "common",
                    "method": "authenticate",
                    "args": [
                        self.db_name,
                        self.username,
                        self.password,
                        {}
                    ]
                },
                "id": self._generate_request_id()
            }

            response = self._session.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                error = result["error"]
                raise OdooAuthenticationError(
                    f"Authentication failed: {error.get('data', {}).get('message', error.get('message', 'Unknown error'))}"
                )

            if "result" in result:
                self._uid = result["result"]
                if self._uid:
                    self._authenticated = True
                    # Session valid for 24 hours
                    self._auth_expiry = datetime.now() + timedelta(hours=24)
                    logger.info(f"Authenticated successfully as user {self._uid}")
                    return True
                else:
                    raise OdooAuthenticationError("Authentication returned null UID")

            raise OdooAuthenticationError("Invalid response from Odoo server")

        except requests.RequestException as e:
            raise OdooAuthenticationError(f"Connection failed: {e}")

    def _generate_request_id(self) -> str:
        """Generate unique request ID for JSON-RPC."""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{timestamp}-{os.urandom(8).hex()}".encode()).hexdigest()[:16]

    def _execute(
        self,
        model: str,
        method: str,
        args: list = None,
        kwargs: dict = None,
        retry: bool = True
    ) -> Any:
        """
        Execute a method on an Odoo model.

        Args:
            model: Odoo model name (e.g., 'account.move')
            method: Method to call (e.g., 'search_read')
            args: Positional arguments
            kwargs: Keyword arguments
            retry: Whether to retry on authentication failure

        Returns:
            Method result

        Raises:
            OdooRPCError: If RPC call fails
        """
        if not self.is_authenticated:
            if retry:
                logger.info("Not authenticated, attempting to authenticate...")
                self.authenticate()
            else:
                raise OdooRPCError("Not authenticated")

        endpoint = f"{self.base_url}/jsonrpc"

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.db_name,
                    self._uid,
                    self.password,
                    model,
                    method,
                    args or [],
                    kwargs or {}
                ]
            },
            "id": self._generate_request_id()
        }

        try:
            response = self._session.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                error = result["error"]
                error_msg = error.get('data', {}).get('message', error.get('message', 'Unknown error'))

                # Handle authentication expiry
                if "AccessError" in error_msg or "SessionExpired" in error_msg:
                    self._authenticated = False
                    if retry:
                        logger.info("Session expired, re-authenticating...")
                        self.authenticate()
                        return self._execute(model, method, args, kwargs, retry=False)

                raise OdooRPCError(f"RPC error: {error_msg}")

            return result.get("result")

        except requests.RequestException as e:
            raise OdooRPCError(f"Connection failed: {e}")

    # =========================================================================
    # Invoice Operations
    # =========================================================================

    def create_invoice(
        self,
        partner_id: int,
        invoice_type: str = "out_invoice",
        lines: list = None,
        invoice_date: str = None,
        payment_term_id: int = None,
        narration: str = None,
    ) -> int:
        """
        Create a new customer invoice.

        Args:
            partner_id: Customer/partner ID
            invoice_type: Type (out_invoice, out_refund, in_invoice, in_refund)
            lines: Invoice line items [{product_id, quantity, price_unit, ...}]
            invoice_date: Invoice date (YYYY-MM-DD)
            payment_term_id: Payment term ID
            narration: Additional notes

        Returns:
            Invoice ID
        """
        invoice_vals = {
            "move_type": invoice_type,
            "partner_id": partner_id,
            "invoice_date": invoice_date or datetime.now().strftime("%Y-%m-%d"),
        }

        if payment_term_id:
            invoice_vals["invoice_payment_term_id"] = payment_term_id

        if narration:
            invoice_vals["narration"] = narration

        # Create invoice
        invoice_id = self._execute(
            "account.move",
            "create",
            [invoice_vals]
        )

        # Add invoice lines
        if lines:
            line_vals = []
            for line in lines:
                line_vals.append((0, 0, {
                    "product_id": line.get("product_id"),
                    "name": line.get("name", line.get("product_id")),
                    "quantity": line.get("quantity", 1),
                    "price_unit": line.get("price_unit", 0),
                    "account_id": line.get("account_id"),
                    "tax_ids": line.get("tax_ids", []),
                }))

            self._execute(
                "account.move",
                "write",
                [invoice_id],
                {"invoice_line_ids": line_vals}
            )

        logger.info(f"Created invoice {invoice_id} for partner {partner_id}")
        return invoice_id

    def get_invoices(
        self,
        domain: list = None,
        limit: int = 100,
        offset: int = 0,
        fields: list = None,
        order: str = "invoice_date desc"
    ) -> list:
        """
        Retrieve invoices with optional filtering.

        Args:
            domain: Odoo domain filter
            limit: Maximum records to return
            offset: Record offset
            fields: Specific fields to retrieve
            order: Sort order

        Returns:
            List of invoice records
        """
        default_fields = [
            "id", "name", "move_type", "partner_id", "invoice_date",
            "invoice_date_due", "amount_total", "amount_untaxed",
            "amount_tax", "state", "payment_state", "currency_id"
        ]

        search_domain = domain or []

        invoices = self._execute(
            "account.move",
            "search_read",
            [],
            {
                "domain": search_domain,
                "fields": fields or default_fields,
                "limit": limit,
                "offset": offset,
                "order": order
            }
        )

        return invoices or []

    def get_invoice(self, invoice_id: int, fields: list = None) -> Optional[dict]:
        """
        Get single invoice by ID.

        Args:
            invoice_id: Invoice ID
            fields: Specific fields to retrieve

        Returns:
            Invoice record or None
        """
        invoices = self.get_invoices(
            domain=[("id", "=", invoice_id)],
            limit=1,
            fields=fields
        )
        return invoices[0] if invoices else None

    def update_invoice(self, invoice_id: int, values: dict) -> bool:
        """
        Update invoice fields.

        Args:
            invoice_id: Invoice ID
            values: Fields to update

        Returns:
            True if successful
        """
        result = self._execute(
            "account.move",
            "write",
            [invoice_id],
            values
        )
        return result is True

    def validate_invoice(self, invoice_id: int) -> bool:
        """
        Post/validate an invoice.

        Args:
            invoice_id: Invoice ID

        Returns:
            True if successful
        """
        try:
            self._execute(
                "account.move",
                "action_post",
                [invoice_id]
            )
            logger.info(f"Validated invoice {invoice_id}")
            return True
        except OdooRPCError as e:
            logger.error(f"Failed to validate invoice {invoice_id}: {e}")
            return False

    def cancel_invoice(self, invoice_id: int) -> bool:
        """
        Cancel an invoice.

        Args:
            invoice_id: Invoice ID

        Returns:
            True if successful
        """
        try:
            self._execute(
                "account.move",
                "button_cancel",
                [invoice_id]
            )
            logger.info(f"Cancelled invoice {invoice_id}")
            return True
        except OdooRPCError as e:
            logger.error(f"Failed to cancel invoice {invoice_id}: {e}")
            return False

    def get_invoice_lines(self, invoice_id: int) -> list:
        """
        Get invoice line items.

        Args:
            invoice_id: Invoice ID

        Returns:
            List of invoice lines
        """
        lines = self._execute(
            "account.move.line",
            "search_read",
            [],
            {
                "domain": [("move_id", "=", invoice_id)],
                "fields": [
                    "id", "product_id", "name", "quantity", "price_unit",
                    "price_subtotal", "price_total", "tax_ids", "account_id"
                ]
            }
        )
        return lines or []

    # =========================================================================
    # Payment Operations
    # =========================================================================

    def register_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_date: str = None,
        payment_method: str = "manual",
        payment_reference: str = None,
    ) -> int:
        """
        Register a payment for an invoice.

        Args:
            invoice_id: Invoice ID
            amount: Payment amount
            payment_date: Payment date
            payment_method: Payment method name
            payment_reference: Payment reference/note

        Returns:
            Payment ID
        """
        # Create payment wizard values
        payment_vals = {
            "amount": amount,
            "payment_date": payment_date or datetime.now().strftime("%Y-%m-%d"),
            "payment_reference": payment_reference or "",
        }

        # Get payment method
        if payment_method:
            methods = self._execute(
                "account.payment.method",
                "search_read",
                [],
                {
                    "domain": [("name", "=", payment_method)],
                    "fields": ["id"],
                    "limit": 1
                }
            )
            if methods:
                payment_vals["payment_method_id"] = methods[0]["id"]

        # Create payment through wizard
        try:
            # For Odoo 14+, use account.move.reversal or direct payment creation
            payment_id = self._execute(
                "account.payment",
                "create",
                [{
                    "amount": amount,
                    "payment_date": payment_vals["payment_date"],
                    "ref": payment_vals["payment_reference"],
                    "partner_type": "customer",
                    "partner_id": self.get_invoice(invoice_id).get("partner_id", []) if isinstance(self.get_invoice(invoice_id), dict) else None,
                    "payment_type": "inbound",
                    "move_id": invoice_id,
                }]
            )

            if payment_id:
                self._execute("account.payment", "action_post", [payment_id])
                logger.info(f"Registered payment {payment_id} for invoice {invoice_id}")
                return payment_id

        except OdooRPCError as e:
            logger.error(f"Failed to register payment: {e}")
            # Fallback: manual reconciliation
            return self._manual_reconcile_payment(invoice_id, amount, payment_date)

        return 0

    def _manual_reconcile_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_date: str = None
    ) -> int:
        """Fallback manual payment reconciliation."""
        try:
            # Create account move for payment
            move_id = self._execute(
                "account.move",
                "create",
                [{
                    "move_type": "entry",
                    "date": payment_date or datetime.now().strftime("%Y-%m-%d"),
                    "ref": f"Payment for invoice {invoice_id}",
                    "line_ids": [
                        (0, 0, {
                            "account_id": self._get_receivable_account_id(),
                            "debit": amount,
                            "credit": 0,
                            "name": f"Payment received for invoice {invoice_id}"
                        }),
                        (0, 0, {
                            "account_id": self._get_bank_account_id(),
                            "debit": 0,
                            "credit": amount,
                            "name": f"Bank receipt for invoice {invoice_id}"
                        })
                    ]
                }]
            )
            logger.info(f"Created manual payment entry {move_id}")
            return move_id
        except Exception as e:
            logger.error(f"Manual reconciliation failed: {e}")
            return 0

    def _get_receivable_account_id(self) -> int:
        """Get default receivable account ID."""
        accounts = self._execute(
            "account.account",
            "search_read",
            [],
            {
                "domain": [("account_type", "=", "asset_receivable")],
                "fields": ["id"],
                "limit": 1
            }
        )
        return accounts[0]["id"] if accounts else 1

    def _get_bank_account_id(self) -> int:
        """Get default bank account ID."""
        accounts = self._execute(
            "account.account",
            "search_read",
            [],
            {
                "domain": [("account_type", "=", "asset_cash")],
                "fields": ["id"],
                "limit": 1
            }
        )
        return accounts[0]["id"] if accounts else 1

    def get_payments(
        self,
        domain: list = None,
        limit: int = 100
    ) -> list:
        """
        Retrieve payments.

        Args:
            domain: Odoo domain filter
            limit: Maximum records

        Returns:
            List of payment records
        """
        payments = self._execute(
            "account.payment",
            "search_read",
            [],
            {
                "domain": domain or [],
                "fields": [
                    "id", "name", "partner_id", "amount", "payment_date",
                    "payment_type", "state", "ref", "currency_id"
                ],
                "limit": limit
            }
        )
        return payments or []

    # =========================================================================
    # Partner (Customer/Vendor) Operations
    # =========================================================================

    def get_partners(
        self,
        domain: list = None,
        limit: int = 100,
        partner_type: str = None
    ) -> list:
        """
        Retrieve partners (customers/vendors).

        Args:
            domain: Odoo domain filter
            limit: Maximum records
            partner_type: Filter by type ('customer', 'supplier', 'both')

        Returns:
            List of partner records
        """
        search_domain = domain or []

        if partner_type:
            if partner_type == "customer":
                search_domain.append(("customer_rank", ">", 0))
            elif partner_type == "supplier":
                search_domain.append(("supplier_rank", ">", 0))

        partners = self._execute(
            "res.partner",
            "search_read",
            [],
            {
                "domain": search_domain,
                "fields": [
                    "id", "name", "email", "phone", "vat",
                    "customer_rank", "supplier_rank", "street", "city", "country_id"
                ],
                "limit": limit
            }
        )
        return partners or []

    def create_partner(
        self,
        name: str,
        email: str = None,
        phone: str = None,
        vat: str = None,
        is_customer: bool = True,
        is_supplier: bool = False,
        street: str = None,
        city: str = None,
        country_id: int = None,
    ) -> int:
        """
        Create a new partner.

        Args:
            name: Partner name
            email: Email address
            phone: Phone number
            vat: VAT number
            is_customer: Is a customer
            is_supplier: Is a supplier
            street: Street address
            city: City
            country_id: Country ID

        Returns:
            Partner ID
        """
        partner_vals = {
            "name": name,
            "email": email,
            "phone": phone,
            "vat": vat,
            "customer_rank": 1 if is_customer else 0,
            "supplier_rank": 1 if is_supplier else 0,
            "street": street,
            "city": city,
            "country_id": country_id,
        }

        partner_id = self._execute(
            "res.partner",
            "create",
            [partner_vals]
        )
        logger.info(f"Created partner {partner_id}: {name}")
        return partner_id

    # =========================================================================
    # Financial Reports
    # =========================================================================

    def get_balance_sheet(self, date: str = None) -> dict:
        """
        Get balance sheet summary.

        Args:
            date: Report date (YYYY-MM-DD)

        Returns:
            Balance sheet data
        """
        report_date = date or datetime.now().strftime("%Y-%m-%d")

        # Get asset accounts
        assets = self._execute(
            "account.account",
            "search_read",
            [],
            {
                "domain": [("account_type", "in", ["asset_fixed", "asset_current", "asset_non_current"])],
                "fields": ["id", "name", "code", "balance"]
            }
        )

        # Get liability accounts
        liabilities = self._execute(
            "account.account",
            "search_read",
            [],
            {
                "domain": [("account_type", "in", ["liability_current", "liability_non_current"])],
                "fields": ["id", "name", "code", "balance"]
            }
        )

        # Get equity accounts
        equity = self._execute(
            "account.account",
            "search_read",
            [],
            {
                "domain": [("account_type", "=", "equity")],
                "fields": ["id", "name", "code", "balance"]
            }
        )

        return {
            "date": report_date,
            "assets": {
                "total": sum(a.get("balance", 0) for a in (assets or [])),
                "accounts": assets or []
            },
            "liabilities": {
                "total": sum(l.get("balance", 0) for l in (liabilities or [])),
                "accounts": liabilities or []
            },
            "equity": {
                "total": sum(e.get("balance", 0) for e in (equity or [])),
                "accounts": equity or []
            }
        }

    def get_profit_loss(
        self,
        date_from: str = None,
        date_to: str = None
    ) -> dict:
        """
        Get profit and loss summary.

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            P&L data
        """
        if not date_from:
            date_from = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")

        # Get income accounts
        income = self._execute(
            "account.account",
            "search_read",
            [],
            {
                "domain": [("account_type", "=", "income")],
                "fields": ["id", "name", "code", "balance"]
            }
        )

        # Get expense accounts
        expenses = self._execute(
            "account.account",
            "search_read",
            [],
            {
                "domain": [("account_type", "=", "expense")],
                "fields": ["id", "name", "code", "balance"]
            }
        )

        total_income = sum(i.get("balance", 0) for i in (income or []))
        total_expenses = sum(e.get("balance", 0) for e in (expenses or []))

        return {
            "date_from": date_from,
            "date_to": date_to,
            "income": {
                "total": total_income,
                "accounts": income or []
            },
            "expenses": {
                "total": total_expenses,
                "accounts": expenses or []
            },
            "net_profit": total_income - total_expenses
        }

    def get_revenue_summary(
        self,
        period: str = "month",
        limit: int = 12
    ) -> dict:
        """
        Get revenue summary by period.

        Args:
            period: Period type (day, week, month, year)
            limit: Number of periods to include

        Returns:
            Revenue summary data
        """
        # Get invoices grouped by period
        invoices = self.get_invoices(
            domain=[
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("state", "=", "posted")
            ],
            limit=1000,
            fields=["id", "invoice_date", "amount_untaxed", "amount_total"]
        )

        # Group by period
        revenue_by_period = {}
        for invoice in (invoices or []):
            invoice_date = invoice.get("invoice_date", "")
            if not invoice_date:
                continue

            # Extract period key
            if period == "month":
                period_key = invoice_date[:7]  # YYYY-MM
            elif period == "year":
                period_key = invoice_date[:4]  # YYYY
            else:
                period_key = invoice_date

            if period_key not in revenue_by_period:
                revenue_by_period[period_key] = {
                    "revenue": 0,
                    "invoices": 0
                }

            revenue_by_period[period_key]["revenue"] += invoice.get("amount_untaxed", 0)
            revenue_by_period[period_key]["invoices"] += 1

        # Sort and limit
        sorted_periods = sorted(revenue_by_period.items(), reverse=True)[:limit]

        return {
            "period": period,
            "data": dict(sorted_periods)
        }

    def get_outstanding_invoices(
        self,
        partner_id: int = None,
        limit: int = 100
    ) -> list:
        """
        Get outstanding (unpaid) invoices.

        Args:
            partner_id: Filter by partner
            limit: Maximum records

        Returns:
            List of outstanding invoices
        """
        domain = [
            ("state", "=", "posted"),
            ("payment_state", "!=", "paid"),
            ("payment_state", "!=", "in_payment")
        ]

        if partner_id:
            domain.append(("partner_id", "=", partner_id))

        return self.get_invoices(domain=domain, limit=limit)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_model_fields(self, model: str) -> list:
        """
        Get fields for a model.

        Args:
            model: Model name

        Returns:
            List of field definitions
        """
        if model in self._model_cache:
            return self._model_cache[model]

        fields = self._execute(
            model,
            "fields_get",
            [],
            {}
        )

        self._model_cache[model] = fields
        return fields

    def search(
        self,
        model: str,
        domain: list,
        limit: int = 100,
        fields: list = None
    ) -> list:
        """
        Generic search method.

        Args:
            model: Model name
            domain: Odoo domain
            limit: Maximum records
            fields: Fields to retrieve

        Returns:
            List of records
        """
        return self._execute(
            model,
            "search_read",
            [],
            {
                "domain": domain,
                "fields": fields,
                "limit": limit
            }
        )

    def create(self, model: str, values: dict) -> int:
        """
        Generic create method.

        Args:
            model: Model name
            values: Record values

        Returns:
            Created record ID
        """
        return self._execute(model, "create", [values])

    def write(self, model: str, record_id: int, values: dict) -> bool:
        """
        Generic update method.

        Args:
            model: Model name
            record_id: Record ID
            values: Values to update

        Returns:
            True if successful
        """
        return self._execute(model, "write", [record_id], values)

    def unlink(self, model: str, record_ids: list) -> bool:
        """
        Generic delete method.

        Args:
            model: Model name
            record_ids: Record IDs to delete

        Returns:
            True if successful
        """
        return self._execute(model, "unlink", [record_ids])

    def close(self):
        """Close the session."""
        self._session.close()
        self._authenticated = False
        self._uid = None
        logger.info("OdooClient session closed")

    def __enter__(self):
        """Context manager entry."""
        self.authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# =============================================================================
# Factory Function
# =============================================================================

def create_odoo_client(
    base_url: str = None,
    db_name: str = None,
    username: str = None,
    password: str = None,
    api_key: str = None,
) -> OdooClient:
    """
    Create and authenticate an Odoo client.

    Args:
        base_url: Odoo server URL
        db_name: Database name
        username: Username
        password: Password
        api_key: API key (optional)

    Returns:
        Authenticated OdooClient instance
    """
    client = OdooClient(
        base_url=base_url,
        db_name=db_name,
        username=username,
        password=password,
        api_key=api_key
    )
    client.authenticate()
    return client


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for testing Odoo client."""
    import argparse

    parser = argparse.ArgumentParser(description="Odoo ERP Client")
    parser.add_argument("--url", type=str, help="Odoo URL")
    parser.add_argument("--db", type=str, help="Database name")
    parser.add_argument("--user", type=str, help="Username")
    parser.add_argument("--password", type=str, help="Password")
    parser.add_argument("--test", action="store_true", help="Run tests")

    args = parser.parse_args()

    print("=" * 70)
    print("Odoo ERP Client - Test Interface")
    print("=" * 70)

    try:
        client = OdooClient(
            base_url=args.url,
            db_name=args.db,
            username=args.user,
            password=args.password
        )

        if args.test:
            print("\n🔐 Authenticating...")
            if client.authenticate():
                print(f"✅ Authenticated as user {client.uid}")

                print("\n📊 Testing invoice retrieval...")
                invoices = client.get_invoices(limit=5)
                print(f"   Found {len(invoices)} invoices")

                print("\n👥 Testing partner retrieval...")
                partners = client.get_partners(limit=5)
                print(f"   Found {len(partners)} partners")

                print("\n💰 Testing balance sheet...")
                balance = client.get_balance_sheet()
                print(f"   Total Assets: {balance['assets']['total']}")
                print(f"   Total Liabilities: {balance['liabilities']['total']}")

                print("\n✅ All tests passed!")
            else:
                print("❌ Authentication failed")

        client.close()

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
