"""Check the copied prompts against the repositories they were copied from.

The offline test pins a sha256, which proves the text has not been edited *here*.
It cannot notice that upstream changed its prompt — and if TN-Eval or iCARE
reword theirs, our numbers stop meaning what the paper's numbers mean. This is
the online half of that check, kept out of the test suite because ``make test``
is offline on purpose.

Run it with ``tnb prompts --verify``.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass

import httpx

from tnb.scoring import tneval as judge_prompts
from tnb.tasks import icare, soap

SOAP_SOURCE_URL = (
    "https://raw.githubusercontent.com/amazon-science/TN-Eval/main/src/generate_soap_note.py"
)
ICARE_SOURCE_URL = "https://raw.githubusercontent.com/proadhikary/iCARE/main/Baselines.py"
JUDGE_SOURCE_URL = (
    "https://raw.githubusercontent.com/amazon-science/TN-Eval/main/src/"
    "run_metrics_reference_free.py"
)
RUBRIC_SOURCE_URL = "https://raw.githubusercontent.com/amazon-science/TN-Eval/main/src/constant.py"

#: Our constant name -> theirs.
JUDGE_PROMPTS = {
    "PROMPT_COMPLETENESS": "rubric_prompt_completeness",
    "PROMPT_CONCISENESS": "rubric_prompt_conciseness",
    "PROMPT_LIKERT_COMPLETENESS": "rubric_prompt_likert_completeness",
    "PROMPT_LIKERT_CONCISENESS": "rubric_prompt_likert_conciseness",
    "PROMPT_LIKERT_FAITHFULNESS": "rubric_prompt_likert_faithfulness",
}


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _fetch(url: str, timeout: float) -> str:
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text


def _evaluate(node: ast.AST):
    """Evaluate a literal, including TN-Eval's ``\"\"\"...\"\"\".strip()`` idiom."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "strip"
        and not node.args
    ):
        inner = _evaluate(node.func.value)
        return inner.strip() if isinstance(inner, str) else None
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _literal(source: str, name: str):
    """Read one module-level constant without executing the file."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
            return _evaluate(node.value)
    return None


def check_soap(timeout: float = 30.0) -> Check:
    """Compare our copy of the SOAP template with TN-Eval's, byte for byte."""
    upstream = _literal(_fetch(SOAP_SOURCE_URL, timeout), "PROMPT_TEMPLATE_SOAP")
    if upstream is None:
        return Check("soap template", False, "PROMPT_TEMPLATE_SOAP not found upstream")

    digest = hashlib.sha256(upstream.encode()).hexdigest()
    if digest != soap.UPSTREAM_SHA256:
        return Check(
            "soap template",
            False,
            f"upstream is now {digest[:12]}, we pin {soap.UPSTREAM_SHA256[:12]}",
        )
    return Check("soap template", True, f"sha256 {digest[:12]} unchanged")


def check_icare(timeout: float = 30.0) -> Check:
    """Check iCARE still wraps its instructions in the sentences we reproduce.

    The 17 instructions themselves are fetched at run time, so they cannot
    drift unnoticed; only this wrapper lives in our source.
    """
    source = _fetch(ICARE_SOURCE_URL, timeout)
    missing = [
        label
        for label, fragment in (
            ("prefix", icare.PREFIX),
            ("nil clause", icare.NIL_CLAUSE),
            ("dialog marker", icare.DIALOG_MARKER),
            ("response marker", icare.RESPONSE_MARKER),
            ("therapist marker", icare.THERAPIST_MARKER),
            ("patient marker", icare.PATIENT_MARKER),
        )
        if fragment not in source
    ]
    if missing:
        return Check("icare wrapper", False, f"no longer in Baselines.py: {', '.join(missing)}")
    return Check("icare wrapper", True, "all six fragments still present in Baselines.py")


def check_judge(timeout: float = 30.0) -> Check:
    """Compare our copies of the five scoring prompts with TN-Eval's."""
    source = _fetch(JUDGE_SOURCE_URL, timeout)
    drifted = []
    for ours, theirs in JUDGE_PROMPTS.items():
        upstream = _literal(source, theirs)
        if not isinstance(upstream, str):
            drifted.append(f"{theirs} not found upstream")
            continue
        digest = hashlib.sha256(upstream.encode()).hexdigest()
        if digest != judge_prompts.UPSTREAM_SHA256[ours]:
            drifted.append(f"{theirs} changed")

    if drifted:
        return Check("judge prompts", False, "; ".join(drifted))
    return Check("judge prompts", True, f"all {len(JUDGE_PROMPTS)} unchanged")


def check_rubric(timeout: float = 30.0) -> Check:
    """Compare our 23 completeness criteria with TN-Eval's, wording included.

    A reworded criterion is a different question to the judge, so this is not a
    count check: every key and every sentence has to match.
    """
    upstream = _literal(_fetch(RUBRIC_SOURCE_URL, timeout), "CHECKBOX_MAPPING")
    if not isinstance(upstream, dict):
        return Check("rubric", False, "CHECKBOX_MAPPING not found upstream")
    if upstream != judge_prompts.CHECKBOX_MAPPING:
        added = sorted(set(upstream) - set(judge_prompts.CHECKBOX_MAPPING))
        removed = sorted(set(judge_prompts.CHECKBOX_MAPPING) - set(upstream))
        reworded = sorted(
            key
            for key in set(upstream) & set(judge_prompts.CHECKBOX_MAPPING)
            if upstream[key] != judge_prompts.CHECKBOX_MAPPING[key]
        )
        return Check(
            "rubric",
            False,
            f"added {added or '-'}, removed {removed or '-'}, reworded {reworded or '-'}",
        )
    return Check("rubric", True, f"all {len(upstream)} criteria unchanged")


def check_all(timeout: float = 30.0) -> list[Check]:
    return [
        check_soap(timeout),
        check_icare(timeout),
        check_judge(timeout),
        check_rubric(timeout),
    ]
