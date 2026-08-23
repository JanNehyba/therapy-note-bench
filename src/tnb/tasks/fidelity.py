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

from tnb.tasks import icare, soap

SOAP_SOURCE_URL = (
    "https://raw.githubusercontent.com/amazon-science/TN-Eval/main/src/generate_soap_note.py"
)
ICARE_SOURCE_URL = "https://raw.githubusercontent.com/proadhikary/iCARE/main/Baselines.py"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _fetch(url: str, timeout: float) -> str:
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text


def _literal(source: str, name: str) -> str | None:
    """Read one module-level string constant without executing the file."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
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


def check_all(timeout: float = 30.0) -> list[Check]:
    return [check_soap(timeout), check_icare(timeout)]
