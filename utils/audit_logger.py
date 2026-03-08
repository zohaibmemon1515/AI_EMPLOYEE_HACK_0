#!/usr/bin/env python3
r"""
Audit Logger - Comprehensive Action Logging System

Provides centralized logging for all AI Employee actions:
- Structured JSON logging
- Action categorization
- Performance tracking
- Audit trail generation
- Compliance reporting

Log Structure:
{
    "timestamp": "ISO 8601 datetime",
    "module": "module.submodule",
    "action": "action_name",
    "input": {...},
    "result": {...},
    "status": "success|failed|warning",
    "actor": "ai_employee|human|system",
    "duration_ms": 123
}

Usage:
    from utils.audit_logger import AuditLogger

    logger = AuditLogger(vault_path)
    logger.log_action("email", "send", {"to": "user@example.com"}, {"message_id": "123"})
"""

import json
import logging
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
from contextlib import contextmanager
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


class ActionStatus(Enum):
    """Action execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"


class ActorType(Enum):
    """Actor types for actions."""
    AI_EMPLOYEE = "ai_employee"
    HUMAN = "human"
    SYSTEM = "system"
    SCHEDULED = "scheduled"


@dataclass
class AuditLogEntry:
    """Single audit log entry."""
    timestamp: str
    module: str
    action: str
    input_data: dict
    result: dict
    status: str
    actor: str
    duration_ms: int = 0
    session_id: str = ""
    correlation_id: str = ""
    error: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.session_id:
            self.session_id = f"SESSION_{datetime.now().strftime('%Y%m%d')}"
        if not self.correlation_id:
            self.correlation_id = f"CORR_{int(time.time() * 1000)}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class AuditLogger:
    """
    Comprehensive Audit Logger.

    Provides centralized logging for all AI Employee actions with:
    - Structured JSON logging
    - Daily log rotation
    - Thread-safe operations
    - Query capabilities
    - Export functionality
    """

    def __init__(
        self,
        vault_path: Path = None,
        retention_days: int = 90,
        async_write: bool = True
    ):
        """
        Initialize audit logger.

        Args:
            vault_path: Path to Obsidian vault
            retention_days: Days to retain logs
            async_write: Use async file writing
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.logs_folder = self.vault_path / "Logs"
        self.retention_days = retention_days
        self.async_write = async_write

        # Create logs folder
        self.logs_folder.mkdir(parents=True, exist_ok=True)

        # Thread safety
        self._lock = threading.Lock()
        self._write_queue = []
        self._writer_thread = None
        self._stop_writer = False

        # Session tracking
        self._session_id = f"SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._correlation_counter = 0

        # Start async writer if enabled
        if async_write:
            self._start_writer_thread()

        logger.info(f"AuditLogger initialized at {self.logs_folder}")

    def _start_writer_thread(self):
        """Start background log writer thread."""
        def writer_loop():
            while not self._stop_writer:
                if self._write_queue:
                    with self._lock:
                        batch = self._write_queue[:10]  # Batch write
                        self._write_queue = self._write_queue[10:]
                    self._write_batch(batch)
                time.sleep(1)

        self._writer_thread = threading.Thread(target=writer_loop, daemon=True)
        self._writer_thread.start()

    def _stop_writer_thread(self):
        """Stop background writer thread."""
        self._stop_writer = True
        if self._writer_thread:
            self._writer_thread.join(timeout=5)
            # Write remaining logs
            if self._write_queue:
                with self._lock:
                    self._write_batch(self._write_queue)
                self._write_queue = []

    def _get_correlation_id(self) -> str:
        """Generate unique correlation ID."""
        self._correlation_counter += 1
        return f"CORR_{int(time.time() * 1000)}_{self._correlation_counter}"

    def _get_log_file(self, date: datetime = None) -> Path:
        """Get log file path for a date."""
        if date is None:
            date = datetime.now()
        return self.logs_folder / f"{date.strftime('%Y-%m-%d')}.json"

    def _write_batch(self, entries: list):
        """Write a batch of log entries."""
        if not entries:
            return

        # Group entries by date
        entries_by_date = {}
        for entry in entries:
            try:
                date_str = entry.get("timestamp", "")[:10]
                if date_str not in entries_by_date:
                    entries_by_date[date_str] = []
                entries_by_date[date_str].append(entry)
            except:
                pass

        # Write to respective files
        for date_str, date_entries in entries_by_date.items():
            try:
                log_file = self.logs_folder / f"{date_str}.json"

                # Load existing entries
                existing = []
                if log_file.exists():
                    try:
                        existing = json.loads(log_file.read_text())
                    except:
                        existing = []

                # Append new entries
                existing.extend(date_entries)

                # Write back
                log_file.write_text(json.dumps(existing, indent=2))

            except Exception as e:
                logger.error(f"Failed to write log batch: {e}")

    def log_action(
        self,
        module: str,
        action: str,
        input_data: dict = None,
        result: dict = None,
        status: ActionStatus = ActionStatus.SUCCESS,
        actor: ActorType = ActorType.AI_EMPLOYEE,
        error: str = "",
        metadata: dict = None,
        correlation_id: str = None
    ) -> str:
        """
        Log an action.

        Args:
            module: Module name (e.g., "skills.communication")
            action: Action name (e.g., "send_email")
            input_data: Input parameters
            result: Action result
            status: Action status
            actor: Who performed the action
            error: Error message if failed
            metadata: Additional metadata
            correlation_id: Correlation ID for tracing

        Returns:
            Correlation ID
        """
        entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            module=module,
            action=action,
            input_data=input_data or {},
            result=result or {},
            status=status.value,
            actor=actor.value,
            error=error,
            metadata=metadata or {},
            session_id=self._session_id,
            correlation_id=correlation_id or self._get_correlation_id()
        )

        if self.async_write:
            with self._lock:
                self._write_queue.append(entry.to_dict())
        else:
            self._write_batch([entry.to_dict()])

        return entry.correlation_id

    @contextmanager
    def log_context(self, module: str, action: str, actor: ActorType = ActorType.AI_EMPLOYEE):
        """
        Context manager for logging action with timing.

        Usage:
            with logger.log_context("skills", "send_email") as ctx:
                # Do work
                ctx.result = {"message_id": "123"}

        Args:
            module: Module name
            action: Action name
            actor: Actor type

        Yields:
            LogContext object
        """
        start_time = time.time()
        correlation_id = self._get_correlation_id()

        class LogContext:
            def __init__(self):
                self.input_data = {}
                self.result = {}
                self.status = ActionStatus.SUCCESS
                self.error = ""
                self.metadata = {}

        ctx = LogContext()
        try:
            yield ctx
        except Exception as e:
            ctx.status = ActionStatus.FAILED
            ctx.error = str(e)
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)

            entry = AuditLogEntry(
                timestamp=datetime.now().isoformat(),
                module=module,
                action=action,
                input_data=ctx.input_data,
                result=ctx.result,
                status=ctx.status.value,
                actor=actor.value,
                duration_ms=duration_ms,
                error=ctx.error,
                metadata=ctx.metadata,
                session_id=self._session_id,
                correlation_id=correlation_id
            )

            if self.async_write:
                with self._lock:
                    self._write_queue.append(entry.to_dict())
            else:
                self._write_batch([entry.to_dict()])

    def query_logs(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        module: str = None,
        action: str = None,
        status: ActionStatus = None,
        actor: ActorType = None,
        limit: int = 100
    ) -> list:
        """
        Query audit logs.

        Args:
            start_date: Start date filter
            end_date: End date filter
            module: Module filter
            action: Action filter
            status: Status filter
            actor: Actor filter
            limit: Maximum results

        Returns:
            List of matching log entries
        """
        results = []

        # Determine date range
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        # Scan log files
        current_date = start_date
        while current_date <= end_date and len(results) < limit:
            log_file = self._get_log_file(current_date)

            if log_file.exists():
                try:
                    data = json.loads(log_file.read_text())

                    for entry in reversed(data):  # Most recent first
                        # Apply filters
                        if module and entry.get("module", "") != module:
                            continue
                        if action and entry.get("action", "") != action:
                            continue
                        if status and entry.get("status", "") != status.value:
                            continue
                        if actor and entry.get("actor", "") != actor.value:
                            continue

                        results.append(entry)

                        if len(results) >= limit:
                            break

                except Exception as e:
                    logger.debug(f"Error reading log {log_file}: {e}")

            current_date += timedelta(days=1)

        return results

    def get_action_summary(
        self,
        date: datetime = None
    ) -> dict:
        """
        Get summary of actions for a date.

        Args:
            date: Date to summarize

        Returns:
            Summary dictionary
        """
        if date is None:
            date = datetime.now()

        logs = self.query_logs(
            start_date=date,
            end_date=date,
            limit=10000
        )

        summary = {
            "date": date.strftime("%Y-%m-%d"),
            "total_actions": len(logs),
            "by_status": {},
            "by_module": {},
            "by_actor": {},
            "errors": [],
            "avg_duration_ms": 0
        }

        total_duration = 0
        duration_count = 0

        for entry in logs:
            # Count by status
            status = entry.get("status", "unknown")
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

            # Count by module
            module = entry.get("module", "unknown")
            summary["by_module"][module] = summary["by_module"].get(module, 0) + 1

            # Count by actor
            actor = entry.get("actor", "unknown")
            summary["by_actor"][actor] = summary["by_actor"].get(actor, 0) + 1

            # Track errors
            if entry.get("status") == "failed":
                summary["errors"].append({
                    "module": entry.get("module"),
                    "action": entry.get("action"),
                    "error": entry.get("error")
                })

            # Track duration
            duration = entry.get("duration_ms", 0)
            if duration > 0:
                total_duration += duration
                duration_count += 1

        if duration_count > 0:
            summary["avg_duration_ms"] = round(total_duration / duration_count, 1)

        return summary

    def export_logs(
        self,
        output_path: Path,
        start_date: datetime = None,
        end_date: datetime = None,
        format: str = "json"
    ) -> Path:
        """
        Export logs to file.

        Args:
            output_path: Output file path
            start_date: Start date
            end_date: End date
            format: Export format (json, csv)

        Returns:
            Path to exported file
        """
        logs = self.query_logs(
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )

        if format == "json":
            output_path.write_text(json.dumps(logs, indent=2))
        elif format == "csv":
            import csv
            if logs:
                with open(output_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                    writer.writeheader()
                    writer.writerows(logs)

        logger.info(f"Exported {len(logs)} logs to {output_path}")
        return output_path

    def cleanup_old_logs(self):
        """Remove logs older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = 0

        for log_file in self.logs_folder.glob("*.json"):
            try:
                # Extract date from filename
                date_str = log_file.stem  # YYYY-MM-DD
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff:
                    log_file.unlink()
                    removed += 1
            except:
                pass

        logger.info(f"Cleaned up {removed} old log files")
        return removed

    def close(self):
        """Close logger and flush remaining logs."""
        self._stop_writer_thread()
        logger.info("AuditLogger closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# =============================================================================
# Factory Function
# =============================================================================

def create_audit_logger(
    vault_path: Path = None,
    retention_days: int = 90
) -> AuditLogger:
    """
    Create an audit logger.

    Args:
        vault_path: Path to vault
        retention_days: Log retention period

    Returns:
        AuditLogger instance
    """
    return AuditLogger(vault_path, retention_days)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for audit logger."""
    import argparse

    parser = argparse.ArgumentParser(description="Audit Logger")
    parser.add_argument("--vault", type=str, help="Vault path")
    parser.add_argument("--summary", action="store_true", help="Show today's summary")
    parser.add_argument("--query", type=str, help="Query logs by module")
    parser.add_argument("--export", type=str, help="Export logs to file")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old logs")

    args = parser.parse_args()

    print("=" * 70)
    print("Audit Logger")
    print("=" * 70)

    try:
        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        log_path = vault_path / "Logs"

        if not log_path.exists():
            print(f"\n⚠️  Logs folder not found: {log_path}")
            return

        logger = AuditLogger(vault_path, async_write=False)

        if args.summary:
            summary = logger.get_action_summary()
            print(f"\n📊 Today's Summary ({summary['date']}):")
            print(f"   Total Actions: {summary['total_actions']}")
            print(f"   By Status: {summary['by_status']}")
            print(f"   By Module: {summary['by_module']}")
            print(f"   Avg Duration: {summary['avg_duration_ms']}ms")
            if summary['errors']:
                print(f"   Errors: {len(summary['errors'])}")

        elif args.query:
            logs = logger.query_logs(module=args.query, limit=20)
            print(f"\n📋 Recent '{args.query}' actions:")
            for entry in logs[:10]:
                print(f"   - {entry.get('timestamp', '')[:19]}: {entry.get('action')} ({entry.get('status')})")

        elif args.export:
            output_path = Path(args.export)
            logger.export_logs(output_path)
            print(f"\n✅ Exported logs to {output_path}")

        elif args.cleanup:
            removed = logger.cleanup_old_logs()
            print(f"\n🧹 Cleaned up {removed} old log files")

        else:
            # Show recent activity
            logs = logger.query_logs(limit=10)
            print(f"\n📋 Recent Activity:")
            for entry in logs:
                print(f"   - {entry.get('timestamp', '')[:19]}: {entry.get('module')}.{entry.get('action')} ({entry.get('status')})")

        logger.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
