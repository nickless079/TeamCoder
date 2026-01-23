"""Grammar checking utilities for generated code.

This module wraps pyflakes analysis and optionally uses an LLM-based
`BaseAgent` instance to automatically fix code that fails static checks.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
	from pyflakes.api import check as pyflakes_check  # type: ignore[import]
	from pyflakes.reporter import Reporter  # type: ignore[import]
except ImportError as exc:  # pragma: no cover - handled at runtime
	pyflakes_check = None
	Reporter = None
	_PYFLAKES_IMPORT_ERROR = exc
else:
	_PYFLAKES_IMPORT_ERROR = None

from agents.BaseAgent import BaseAgent


@dataclass
class GrammarIssue:
	"""Represents a single diagnostic produced by pyflakes."""

	line: Optional[int]
	column: Optional[int]
	message: str
	raw: str


@dataclass
class GrammarCheckResult:
	"""Result structure returned by :class:`GrammarChecker`."""

	success: bool
	code: str
	issues: List[GrammarIssue] = field(default_factory=list)
	fixed: bool = False
	attempts: int = 0
	report: str = ""
	history: List[Dict[str, Any]] = field(default_factory=list)


class GrammarChecker:
	"""Run pyflakes on code strings and optionally fix issues via an LLM agent."""

	def __init__(
		self,
		fixer_agent: Optional[BaseAgent],
		verbose: int = 0,
		max_fix_attempts: int = 2,
	) -> None:
		self.fixer_agent = fixer_agent
		self.verbose = verbose
		self.max_fix_attempts = max(0, max_fix_attempts)

	def ensure_clean(
		self,
		code: str,
		context: Optional[Dict[str, Any]] = None,
	) -> GrammarCheckResult:
		"""Run pyflakes and attempt automatic fixes when issues are found.

		Args:
			code: Source code to analyse.
			context: Optional context (problem description, test cases, etc.)
					 that will be forwarded to the fixer agent.

		Returns:
			GrammarCheckResult describing the final status.
		"""

		context = context or {}
		current_code = code
		history: List[Dict[str, Any]] = []

		for attempt in range(self.max_fix_attempts + 1):
			diagnostics = self._run_pyflakes(current_code)

			if not diagnostics["issues"]:
				if self.verbose >= 1:
					print("[GrammarChecker] pyflakes found no issues.")
				return GrammarCheckResult(
					success=True,
					code=current_code,
					issues=[],
					fixed=attempt > 0,
					attempts=attempt,
					report=diagnostics["report"],
					history=history,
				)

			if attempt >= self.max_fix_attempts or self.fixer_agent is None:
				if self.verbose >= 1:
					print("[GrammarChecker] Unable to resolve pyflakes issues.")
				return GrammarCheckResult(
					success=False,
					code=current_code,
					issues=diagnostics["issues"],
					fixed=False,
					attempts=attempt,
					report=diagnostics["report"],
					history=history,
				)

			if self.verbose >= 1:
				print(
					f"[GrammarChecker] Attempting auto-fix via LLM (attempt {attempt + 1})."
				)

			fix_context = {
				"report": diagnostics["report"],
				"issues": diagnostics["issues"],
			}
			fix_context.update(context)

			new_code, agent_payload = self._request_fix(current_code, fix_context)
			history.append(agent_payload)

			if not new_code or new_code.strip() == current_code.strip():
				if self.verbose >= 1:
					print("[GrammarChecker] Fix attempt returned empty or unchanged code.")
				return GrammarCheckResult(
					success=False,
					code=current_code,
					issues=diagnostics["issues"],
					fixed=False,
					attempts=attempt + 1,
					report=diagnostics["report"],
					history=history,
				)

			current_code = new_code

		# Should not reach here due to return inside loop, but keep fallback
		return GrammarCheckResult(
			success=False,
			code=current_code,
			issues=[],
			fixed=False,
			attempts=self.max_fix_attempts,
			report="",
			history=history,
		)

	def _run_pyflakes(self, code: str) -> Dict[str, Any]:
		"""Execute pyflakes on code and collect diagnostics."""

		if pyflakes_check is None or Reporter is None:
			raise RuntimeError(
				"pyflakes is required for GrammarChecker. Please install the dependency."
			) from _PYFLAKES_IMPORT_ERROR

		output = io.StringIO()
		errors = io.StringIO()
		reporter = Reporter(output, errors)
		try:
			pyflakes_check(code, filename="<generated>", reporter=reporter)
		except Exception as exc:  # pragma: no cover - pyflakes should not raise
			if self.verbose >= 1:
				print(f"[GrammarChecker] pyflakes raised an exception: {exc}")
			return {
				"issues": [
					GrammarIssue(line=None, column=None, message=str(exc), raw=str(exc))
				],
				"report": str(exc),
			}

		combined = f"{output.getvalue()}{errors.getvalue()}".strip()
		issues = self._parse_pyflakes_output(combined)

		return {
			"issues": issues,
			"report": combined,
		}

	@staticmethod
	def _parse_pyflakes_output(report: str) -> List[GrammarIssue]:
		"""Convert pyflakes textual output into structured diagnostics."""

		if not report:
			return []

		issues: List[GrammarIssue] = []
		for line in report.splitlines():
			stripped = line.strip()
			if not stripped:
				continue

			match = re.match(r"[^:]+:(\d+)(?::(\d+))?\s*(.*)", stripped)
			if match:
				line_no = int(match.group(1))
				col_no = int(match.group(2)) if match.group(2) else None
				message = match.group(3).strip()
			else:
				line_no = None
				col_no = None
				message = stripped

			issues.append(
				GrammarIssue(
					line=line_no,
					column=col_no,
					message=message,
					raw=stripped,
				)
			)

		return issues

	def _request_fix(
		self,
		code: str,
		context: Dict[str, Any],
	) -> Tuple[Optional[str], Dict[str, Any]]:
		"""Ask the fixer agent to repair code according to pyflakes report."""

		if self.fixer_agent is None:
			return None, {"attempt": "skipped", "reason": "no fixer agent"}

		session_id = self.fixer_agent.start_new_session()
		prompt = self._build_fix_prompt(code, context)
		messages = [
			{
				"role": "system",
				"content": (
					"You are an expert Python engineer. Your job is to produce code "
					"that passes pyflakes static analysis while preserving intent."
				),
			},
			{"role": "user", "content": prompt},
		]

		try:
			response = self.fixer_agent._call_model(
				messages,
				session_id=session_id,
				include_history=False,
			)
		except Exception as exc:  # pragma: no cover - depends on external LLM
			if self.verbose >= 1:
				print(f"[GrammarChecker] Fixer agent failed: {exc}")
			return None, {"attempt": "error", "error": str(exc)}

		extracted = self._extract_code(response)
		return extracted, {
			"attempt": "fix",
			"session_id": session_id,
			"response": response,
			"extracted": extracted,
		}

	def _build_fix_prompt(self, code: str, context: Dict[str, Any]) -> str:
		"""Create a detailed prompt for the fixer agent."""

		report = context.get("report", "")
		problem_description = context.get("problem_description", "")
		extra = []

		if problem_description:
			extra.append("## Problem Description\n" + problem_description.strip())

		if test_cases := context.get("test_cases"):
			formatted_cases = "\n".join(str(tc) for tc in test_cases)[:1500]
			extra.append("## Relevant Test Cases\n" + formatted_cases)

		extra_block = "\n\n".join(extra)

		prompt = f"""
The current Python code must pass pyflakes static analysis. Pyflakes reported
the following diagnostics:

{report or 'No textual report available.'}

{extra_block}

Please review the original code and provide a corrected version that resolves
all diagnostics while preserving the intended behaviour. Return the full,
standalone Python code inside <FIXED_CODE>...</FIXED_CODE> tags,if the code is repeate some sentences,you just delete the repeative senteces.

<ORIGINAL_CODE>
{code}
</ORIGINAL_CODE>
"""

		return prompt.strip()

	@staticmethod
	def _extract_code(response: str) -> Optional[str]:
		"""Extract code from agent response using FIXED_CODE or code fences."""

		if not response:
			return None

		fixed_match = re.search(r"<FIXED_CODE>(.*?)</FIXED_CODE>", response, re.DOTALL)
		if fixed_match:
			return fixed_match.group(1).strip()

        
		fence_match = re.search(r"```(?:python)?\s*(.*?)```", response, re.DOTALL)
		if fence_match:
			return fence_match.group(1).strip()

        
		# Fallback to raw response if it looks like code (contains def/class)
		if "def " in response or "class " in response:
			return response.strip()

		return None
