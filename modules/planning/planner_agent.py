#!/usr/bin/env python3
r"""
Planner Agent - Intelligent Task Planning and Prioritization

Analyzes tasks and generates optimized execution plans:
- Task analysis and classification
- Priority assignment
- Resource allocation
- Plan generation
- Dependency management

Usage:
    from modules.planning.planner_agent import PlannerAgent

    planner = PlannerAgent(vault_path)
    plan = planner.generate_plan(task)
"""

import json
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


class TaskCategory(Enum):
    """Task categories."""
    COMMUNICATION = "communication"
    ACCOUNTING = "accounting"
    MARKETING = "marketing"
    ADMIN = "admin"
    CRM = "crm"
    GENERAL = "general"


class UrgencyLevel(Enum):
    """Task urgency levels."""
    IMMEDIATE = "immediate"
    TODAY = "today"
    THIS_WEEK = "this_week"
    FLEXIBLE = "flexible"


@dataclass
class TaskAnalysis:
    """Result of task analysis."""
    task_id: str
    category: str
    urgency: str
    complexity: str  # low, medium, high
    estimated_duration: int  # minutes
    required_skills: list
    dependencies: list
    risks: list
    confidence: float  # 0-1
    analysis_notes: str = ""


@dataclass
class PlanStep:
    """Single step in an execution plan."""
    step: int
    action: str
    description: str
    estimated_duration: int = 5
    critical: bool = True
    requires_approval: bool = False
    dependencies: list = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ExecutionPlan:
    """Complete execution plan for a task."""
    plan_id: str
    task_id: str
    task_title: str
    created_at: str
    steps: list
    total_estimated_duration: int
    required_skills: list
    priority: str
    category: str
    analysis: dict = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class PlannerAgent:
    """
    AI Planner Agent.

    Analyzes tasks and generates optimized execution plans using
    rule-based intelligence (can be extended with LLM integration).
    """

    def __init__(self, vault_path: Path = None):
        """
        Initialize planner agent.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.needs_action = self.vault_path / "Needs_Action"
        self.plans_folder = self.vault_path / "Plans"
        self.logs_folder = self.vault_path / "Logs"

        # Create folders
        for folder in [self.plans_folder, self.logs_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        # Plan templates by category
        self._plan_templates = self._load_plan_templates()

        # Priority keywords
        self._priority_keywords = {
            "critical": ["urgent", "emergency", "asap", "critical", "immediate", "deadline"],
            "high": ["important", "priority", "soon", "today", "rush"],
            "medium": ["normal", "standard", "regular"],
            "low": ["when possible", "sometime", "low priority", "backlog"]
        }

        logger.info(f"PlannerAgent initialized at {self.vault_path}")

    def _load_plan_templates(self) -> dict:
        """Load plan templates by task category."""
        return {
            TaskCategory.COMMUNICATION.value: [
                {"step": 1, "action": "read_email", "description": "Read and understand message", "estimated_duration": 2},
                {"step": 2, "action": "classify_intent", "description": "Classify sender intent", "estimated_duration": 1},
                {"step": 3, "action": "draft_response", "description": "Generate response draft", "estimated_duration": 5},
                {"step": 4, "action": "submit_for_approval", "description": "Submit for human approval", "estimated_duration": 1, "requires_approval": True},
            ],
            TaskCategory.ACCOUNTING.value: [
                {"step": 1, "action": "extract_invoice_data", "description": "Extract invoice details", "estimated_duration": 3},
                {"step": 2, "action": "validate_invoice", "description": "Validate data accuracy", "estimated_duration": 2},
                {"step": 3, "action": "create_invoice", "description": "Create invoice in system", "estimated_duration": 5},
                {"step": 4, "action": "submit_for_approval", "description": "Submit for approval", "estimated_duration": 1, "requires_approval": True},
            ],
            TaskCategory.MARKETING.value: [
                {"step": 1, "action": "generate_content", "description": "Generate social media content", "estimated_duration": 10},
                {"step": 2, "action": "add_hashtags", "description": "Add relevant hashtags", "estimated_duration": 2},
                {"step": 3, "action": "schedule_post", "description": "Schedule for optimal time", "estimated_duration": 2},
                {"step": 4, "action": "submit_for_approval", "description": "Submit for approval", "estimated_duration": 1, "requires_approval": True},
            ],
            TaskCategory.CRM.value: [
                {"step": 1, "action": "classify_lead", "description": "Classify lead quality", "estimated_duration": 2},
                {"step": 2, "action": "create_crm_entry", "description": "Create CRM record", "estimated_duration": 3},
                {"step": 3, "action": "generate_proposal", "description": "Generate proposal", "estimated_duration": 10},
                {"step": 4, "action": "create_invoice", "description": "Create invoice if applicable", "estimated_duration": 5},
                {"step": 5, "action": "send_followup", "description": "Send follow-up message", "estimated_duration": 3},
            ],
            TaskCategory.ADMIN.value: [
                {"step": 1, "action": "analyze_task", "description": "Analyze task requirements", "estimated_duration": 3},
                {"step": 2, "action": "execute_action", "description": "Execute required action", "estimated_duration": 10},
                {"step": 3, "action": "document_result", "description": "Document completion", "estimated_duration": 2},
            ],
            TaskCategory.GENERAL.value: [
                {"step": 1, "action": "analyze_task", "description": "Analyze task requirements", "estimated_duration": 3},
                {"step": 2, "action": "determine_action", "description": "Determine appropriate action", "estimated_duration": 2},
                {"step": 3, "action": "execute_action", "description": "Execute the action", "estimated_duration": 10},
                {"step": 4, "action": "document_result", "description": "Document the result", "estimated_duration": 2},
            ]
        }

    def analyze_task(self, task: dict) -> TaskAnalysis:
        """
        Analyze a task and extract metadata.

        Args:
            task: Task dictionary

        Returns:
            TaskAnalysis object
        """
        task_id = task.get("task_id", "unknown")
        title = task.get("title", "")
        description = task.get("description", "")
        content = task.get("metadata", {}).get("content", "")

        # Combine text for analysis
        full_text = f"{title} {description} {content}".lower()

        # Determine category
        category = self._determine_category(full_text, task)

        # Determine urgency
        urgency = self._determine_urgency(full_text, task)

        # Determine complexity
        complexity = self._determine_complexity(full_text, task)

        # Estimate duration
        duration = self._estimate_duration(category, complexity)

        # Determine required skills
        skills = self._determine_required_skills(category)

        # Identify dependencies
        dependencies = self._identify_dependencies(task)

        # Identify risks
        risks = self._identify_risks(full_text, task)

        # Calculate confidence
        confidence = self._calculate_confidence(category, complexity)

        analysis = TaskAnalysis(
            task_id=task_id,
            category=category.value if isinstance(category, TaskCategory) else category,
            urgency=urgency.value if isinstance(urgency, UrgencyLevel) else urgency,
            complexity=complexity,
            estimated_duration=duration,
            required_skills=skills,
            dependencies=dependencies,
            risks=risks,
            confidence=confidence,
            analysis_notes=f"Analyzed at {datetime.now().isoformat()}"
        )

        logger.info(f"Analyzed task {task_id}: category={analysis.category}, urgency={analysis.urgency}")
        return analysis

    def _determine_category(self, text: str, task: dict) -> TaskCategory:
        """Determine task category from content."""
        # Check task type from metadata
        task_type = task.get("task_type", "")

        if task_type == "email" or any(w in text for w in ["email", "reply", "respond", "message"]):
            return TaskCategory.COMMUNICATION

        if task_type == "whatsapp" or any(w in text for w in ["whatsapp", "chat", "message"]):
            return TaskCategory.COMMUNICATION

        if task_type == "invoice" or any(w in text for w in ["invoice", "payment", "bill", "receipt", "accounting"]):
            return TaskCategory.ACCOUNTING

        if task_type == "social" or any(w in text for w in ["post", "social", "facebook", "instagram", "twitter", "content"]):
            return TaskCategory.MARKETING

        if task_type == "lead" or any(w in text for w in ["lead", "customer", "client", "crm", "prospect"]):
            return TaskCategory.CRM

        return TaskCategory.GENERAL

    def _determine_urgency(self, text: str, task: dict) -> UrgencyLevel:
        """Determine task urgency from content."""
        # Check explicit priority
        priority = task.get("priority", "").lower()

        if priority == "critical":
            return UrgencyLevel.IMMEDIATE
        if priority == "high":
            return UrgencyLevel.TODAY

        # Check keywords
        for keyword in self._priority_keywords["immediate"]:
            if keyword in text:
                return UrgencyLevel.IMMEDIATE

        for keyword in self._priority_keywords["high"]:
            if keyword in text:
                return UrgencyLevel.TODAY

        for keyword in self._priority_keywords["medium"]:
            if keyword in text:
                return UrgencyLevel.THIS_WEEK

        return UrgencyLevel.FLEXIBLE

    def _determine_complexity(self, text: str, task: dict) -> str:
        """Determine task complexity."""
        # Count indicators of complexity
        complexity_score = 0

        # Long content suggests complexity
        if len(text) > 1000:
            complexity_score += 1
        if len(text) > 5000:
            complexity_score += 1

        # Multiple topics
        if text.count("\n") > 10:
            complexity_score += 1

        # Technical terms
        technical_terms = ["api", "integration", "database", "server", "deployment", "configuration"]
        if any(term in text for term in technical_terms):
            complexity_score += 1

        # Financial amounts
        if "$" in text or "USD" in text:
            complexity_score += 1

        if complexity_score >= 3:
            return "high"
        elif complexity_score >= 1:
            return "medium"
        return "low"

    def _estimate_duration(self, category: TaskCategory, complexity: str) -> int:
        """Estimate task duration in minutes."""
        base_durations = {
            TaskCategory.COMMUNICATION.value: 10,
            TaskCategory.ACCOUNTING.value: 15,
            TaskCategory.MARKETING.value: 20,
            TaskCategory.CRM.value: 25,
            TaskCategory.ADMIN.value: 15,
            TaskCategory.GENERAL.value: 15
        }

        base = base_durations.get(category.value if isinstance(category, TaskCategory) else category, 15)

        complexity_multiplier = {
            "low": 1.0,
            "medium": 1.5,
            "high": 2.0
        }

        return int(base * complexity_multiplier.get(complexity, 1.0))

    def _determine_required_skills(self, category: TaskCategory) -> list:
        """Determine skills required for a category."""
        skill_map = {
            TaskCategory.COMMUNICATION: ["communication", "language"],
            TaskCategory.ACCOUNTING: ["accounting", "finance"],
            TaskCategory.MARKETING: ["marketing", "content_creation"],
            TaskCategory.CRM: ["sales", "communication", "accounting"],
            TaskCategory.ADMIN: ["organization", "documentation"],
            TaskCategory.GENERAL: ["planning", "problem_solving"]
        }

        return skill_map.get(category, ["planning"])

    def _identify_dependencies(self, task: dict) -> list:
        """Identify task dependencies."""
        dependencies = []

        # Check for references to other tasks
        metadata = task.get("metadata", {})
        content = metadata.get("content", "")

        if "reply to" in content.lower() or "in response to" in content.lower():
            dependencies.append("original_message")

        if "after approval" in content.lower():
            dependencies.append("human_approval")

        if "pending" in content.lower() and "payment" in content.lower():
            dependencies.append("payment_confirmation")

        return dependencies

    def _identify_risks(self, text: str, task: dict) -> list:
        """Identify potential risks."""
        risks = []

        # Financial risks
        if any(w in text for w in ["payment", "invoice", "money", "$"]):
            risks.append("financial_transaction")

        # Legal/compliance risks
        if any(w in text for w in ["contract", "legal", "agreement", "terms"]):
            risks.append("legal_review_required")

        # Customer-facing risks
        if any(w in text for w in ["customer", "client", "external"]):
            risks.append("customer_facing")

        # Sensitive data
        if any(w in text for w in ["password", "confidential", "private", "secret"]):
            risks.append("sensitive_data")

        return risks

    def _calculate_confidence(self, category: TaskCategory, complexity: str) -> float:
        """Calculate confidence in the analysis."""
        base_confidence = 0.8

        # Reduce confidence for high complexity
        if complexity == "high":
            base_confidence -= 0.2
        elif complexity == "medium":
            base_confidence -= 0.1

        # Category-specific confidence
        if category in [TaskCategory.GENERAL, TaskCategory.ADMIN]:
            base_confidence -= 0.1  # Less specific categories have lower confidence

        return max(0.3, min(1.0, base_confidence))

    def generate_plan(self, task: dict, analysis: TaskAnalysis = None) -> ExecutionPlan:
        """
        Generate an execution plan for a task.

        Args:
            task: Task dictionary
            analysis: Optional pre-computed analysis

        Returns:
            ExecutionPlan object
        """
        # Analyze if not provided
        if analysis is None:
            analysis = self.analyze_task(task)

        plan_id = f"PLAN_{task.get('task_id', 'unknown')}_{datetime.now().strftime('%H%M%S')}"

        # Get template steps for category
        category = analysis.category
        template_steps = self._plan_templates.get(category, self._plan_templates[TaskCategory.GENERAL.value])

        # Customize steps based on analysis
        steps = self._customize_steps(template_steps, task, analysis)

        # Calculate total duration
        total_duration = sum(step.get("estimated_duration", 5) for step in steps)

        plan = ExecutionPlan(
            plan_id=plan_id,
            task_id=task.get("task_id", "unknown"),
            task_title=task.get("title", "Untitled"),
            created_at=datetime.now().isoformat(),
            steps=steps,
            total_estimated_duration=total_duration,
            required_skills=analysis.required_skills,
            priority=task.get("priority", "medium"),
            category=category,
            analysis=asdict(analysis),
            metadata={
                "urgency": analysis.urgency,
                "complexity": analysis.complexity,
                "risks": analysis.risks
            }
        )

        logger.info(f"Generated plan {plan_id} with {len(steps)} steps")
        return plan

    def _customize_steps(
        self,
        template_steps: list,
        task: dict,
        analysis: TaskAnalysis
    ) -> list:
        """Customize template steps for specific task."""
        steps = []

        for i, template_step in enumerate(template_steps):
            step = PlanStep(
                step=template_step.get("step", i + 1),
                action=template_step.get("action", "unknown"),
                description=template_step.get("description", ""),
                estimated_duration=template_step.get("estimated_duration", 5),
                critical=template_step.get("critical", True),
                requires_approval=template_step.get("requires_approval", False),
                dependencies=template_step.get("dependencies", [])
            )

            # Add approval requirement for risky tasks
            if analysis.risks and step.action in ["create_invoice", "send_followup", "draft_response"]:
                step.requires_approval = True

            steps.append(asdict(step))

        return steps

    def prioritize_tasks(self, tasks: list) -> list:
        """
        Prioritize a list of tasks.

        Args:
            tasks: List of task dictionaries

        Returns:
            List of tasks sorted by priority
        """
        scored_tasks = []

        for task in tasks:
            analysis = self.analyze_task(task)

            # Calculate priority score
            score = 0

            # Urgency scoring
            urgency_scores = {
                UrgencyLevel.IMMEDIATE.value: 100,
                UrgencyLevel.TODAY.value: 75,
                UrgencyLevel.THIS_WEEK.value: 50,
                UrgencyLevel.FLEXIBLE.value: 25
            }
            score += urgency_scores.get(analysis.urgency, 25)

            # Risk scoring
            score += len(analysis.risks) * 10

            # Confidence bonus
            score += analysis.confidence * 10

            scored_tasks.append({
                "task": task,
                "analysis": analysis,
                "score": score
            })

        # Sort by score descending
        scored_tasks.sort(key=lambda x: x["score"], reverse=True)

        return [item["task"] for item in scored_tasks]

    def save_plan(self, plan: ExecutionPlan) -> Path:
        """
        Save plan to vault.

        Args:
            plan: Plan to save

        Returns:
            Path to saved file
        """
        filepath = self.plans_folder / f"{plan.plan_id}.md"

        content = f"""---
plan_id: {plan.plan_id}
task_id: {plan.task_id}
task_title: {plan.task_title}
created_at: {plan.created_at}
priority: {plan.priority}
category: {plan.category}
total_duration: {plan.total_estimated_duration} minutes
---

# Execution Plan: {plan.plan_id}

## Task
**{plan.task_title}** ({plan.task_id})

## Analysis

| Attribute | Value |
|-----------|-------|
| Category | {plan.category} |
| Priority | {plan.priority} |
| Urgency | {plan.metadata.get('urgency', 'N/A')} |
| Complexity | {plan.metadata.get('complexity', 'N/A')} |
| Estimated Duration | {plan.total_estimated_duration} minutes |

## Required Skills
{', '.join(plan.required_skills)}

## Execution Steps

| Step | Action | Description | Duration | Approval |
|------|--------|-------------|----------|----------|
"""
        for step in plan.steps:
            approval = "✓" if step.get("requires_approval") else ""
            content += f"| {step['step']} | {step['action']} | {step['description']} | {step['estimated_duration']}min | {approval} |\n"

        content += f"""
## Risks
{', '.join(plan.metadata.get('risks', ['None identified'])) if plan.metadata.get('risks') else 'None identified'}

---
*Plan generated by AI Employee Planner Agent*
"""
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved plan to {filepath}")
        return filepath

    def get_pending_tasks(self) -> list:
        """
        Get all pending tasks from vault.

        Returns:
            List of task dictionaries
        """
        tasks = []

        if not self.needs_action.exists():
            return tasks

        for filepath in self.needs_action.glob("*.md"):
            task = self._parse_task_file(filepath)
            if task:
                tasks.append(task)

        return tasks

    def _parse_task_file(self, filepath: Path) -> Optional[dict]:
        """Parse a task file into a task dictionary."""
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

            # Determine task type
            filename = filepath.name
            task_type = "general"
            if filename.startswith("EMAIL_"):
                task_type = "email"
            elif filename.startswith("WHATSAPP_"):
                task_type = "whatsapp"
            elif filename.startswith("LEAD_"):
                task_type = "lead"
            elif filename.startswith("INVOICE_"):
                task_type = "invoice"

            return {
                "task_id": f"TASK_{filepath.stem}",
                "title": frontmatter.get("subject", frontmatter.get("title", filepath.stem)),
                "description": content[:500],
                "priority": frontmatter.get("priority", "medium"),
                "task_type": task_type,
                "source": frontmatter.get("from", ""),
                "source_file": str(filepath),
                "metadata": {
                    "frontmatter": frontmatter,
                    "content": content
                }
            }

        except Exception as e:
            logger.error(f"Failed to parse task file {filepath}: {e}")
            return None


# =============================================================================
# Factory Function
# =============================================================================

def create_planner(vault_path: Path = None) -> PlannerAgent:
    """
    Create a planner agent.

    Args:
        vault_path: Path to vault

    Returns:
        PlannerAgent instance
    """
    return PlannerAgent(vault_path)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for planner agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Planner Agent")
    parser.add_argument("--vault", type=str, help="Vault path")
    parser.add_argument("--analyze", type=str, help="Analyze specific task file")
    parser.add_argument("--plan", type=str, help="Generate plan for task file")
    parser.add_argument("--prioritize", action="store_true", help="Prioritize all pending tasks")
    parser.add_argument("--list", action="store_true", help="List pending tasks")

    args = parser.parse_args()

    print("=" * 70)
    print("Planner Agent")
    print("=" * 70)

    try:
        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        planner = PlannerAgent(vault_path)

        if args.list:
            tasks = planner.get_pending_tasks()
            print(f"\n📋 Pending Tasks ({len(tasks)}):")
            for task in tasks[:10]:
                print(f"   - {task['task_id']}: {task['title'][:50]}...")
            if len(tasks) > 10:
                print(f"   ... and {len(tasks) - 10} more")

        elif args.analyze:
            task_file = Path(args.analyze)
            if task_file.exists():
                task = planner._parse_task_file(task_file)
                if task:
                    analysis = planner.analyze_task(task)
                    print(f"\n🔍 Task Analysis:")
                    print(f"   Category: {analysis.category}")
                    print(f"   Urgency: {analysis.urgency}")
                    print(f"   Complexity: {analysis.complexity}")
                    print(f"   Duration: {analysis.estimated_duration} min")
                    print(f"   Skills: {', '.join(analysis.required_skills)}")
                    print(f"   Confidence: {analysis.confidence:.0%}")

        elif args.plan:
            task_file = Path(args.plan)
            if task_file.exists():
                task = planner._parse_task_file(task_file)
                if task:
                    plan = planner.generate_plan(task)
                    filepath = planner.save_plan(plan)
                    print(f"\n📋 Generated Plan:")
                    print(f"   Plan ID: {plan.plan_id}")
                    print(f"   Steps: {len(plan.steps)}")
                    print(f"   Duration: {plan.total_estimated_duration} min")
                    print(f"   Saved to: {filepath}")

        elif args.prioritize:
            tasks = planner.get_pending_tasks()
            if tasks:
                prioritized = planner.prioritize_tasks(tasks)
                print(f"\n📊 Prioritized Tasks:")
                for i, task in enumerate(prioritized[:10], 1):
                    print(f"   {i}. {task['task_id']}: {task['title'][:50]}...")

        else:
            print("\nUsage: python -m modules.planning.planner_agent --list|--analyze|--plan|--prioritize")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
