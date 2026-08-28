"""The Deepsy note prompts, read from the application rather than copied here.

**This file holds no prompt text, on purpose.** It used to: the three prompts
were generated into it verbatim, and this repository is public. They are the
Deepsy application's production prompts and its author asked for them not to be
published, which is the right call and is not a benchmark decision to make on
somebody's behalf.

So they are read from the application at run time instead. That is a stronger
version of this project's own invariant rather than a weaker one -- a prompt
reproduced by copying can drift from its source, and the test that used to guard
against that is now unnecessary because there is only one copy.

**Where it looks.** `TNB_DEEPSY_PROMPTS` if it is set, otherwise the
`monitor-notes` checkout beside this one. The Deepsy track cannot run without
it, and that is honest: a benchmark of a format it cannot read is not a
measurement of that format.

**Nothing is read at import.** `tnb.tasks` imports every task module to build
its registry, and a missing sibling checkout must not stop `tnb models` or the
English tracks from running. The load happens on first use, and what it raises
then names the directory it wanted.

Three of the eleven sections. `dekurz` and the questionnaires are out by
decision; `episode_summary` and `progress` read a previous note rather than a
transcript, and this benchmark scores single sessions. What is left that reads
only a transcript is six, and these three are the three with a SOAP counterpart
-- which is what makes the comparison a comparison of formats rather than of
tasks.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

#: Which sections this benchmark asks for, and the order they are asked in.
SECTION_FILES = ("data", "clinical_hypotheses", "plan")

#: Where the application's prompts live when nothing says otherwise: a
#: `monitor-notes` checkout beside this repository.
DEFAULT_ROOT = (
    Path(__file__).resolve().parents[4]
    / "monitor-notes"
    / "app"
    / "Config"
    / "TherapyNote"
    / "prompts"
)

ENV_VAR = "TNB_DEEPSY_PROMPTS"


class PromptsUnavailable(RuntimeError):
    """The Deepsy prompts are not on this machine.

    Raised rather than defaulted. A benchmark that quietly substituted a prompt
    of its own would still print a Deepsy column, and that column would be
    measuring something nobody asked for.
    """


def root() -> Path:
    return Path(os.environ.get(ENV_VAR) or DEFAULT_ROOT)


def available() -> bool:
    """Whether the track can run here. Used by tests to skip rather than fail."""
    return all((root() / f"{name}.yaml").is_file() for name in SECTION_FILES)


@cache
def _load() -> tuple[dict[str, str], dict[str, str], int, str]:
    import yaml

    where = root()
    if not available():
        raise PromptsUnavailable(
            f"The Deepsy prompts are not at {where}.\n"
            "They are the application's own and are not copied into this "
            f"repository. Check out `monitor-notes` beside it, or set {ENV_VAR} "
            "to the directory holding data.yaml, clinical_hypotheses.yaml and "
            "plan.yaml."
        )

    system: dict[str, str] = {}
    template: dict[str, str] = {}
    length: int | None = None
    fmt: str | None = None
    for name in SECTION_FILES:
        loaded = yaml.safe_load((where / f"{name}.yaml").read_text(encoding="utf-8"))
        section = loaded[name]
        system[name] = section["system_message"]
        template[name] = section["user_message_template"]
        settings = loaded.get("settings") or {}
        # `PromptLoader` takes the settings from the first section file and all
        # three of these declare the same. Checked rather than assumed: if they
        # ever differ, one of them is silently not the one being used.
        if length is None:
            length, fmt = settings.get("default_length"), settings.get("default_format")
        elif (settings.get("default_length"), settings.get("default_format")) != (length, fmt):
            raise PromptsUnavailable(
                f"{name}.yaml declares different settings from {SECTION_FILES[0]}.yaml. "
                "The application reads them from one file, so which one is in force "
                "is no longer obvious and this benchmark will not guess."
            )
    return system, template, int(length or 0), str(fmt or "")


def system(section: str) -> str:
    """The system message the application sends for one section."""
    return _load()[0][section]


def template(section: str) -> str:
    """The user-message template, placeholders unfilled."""
    return _load()[1][section]


def sections() -> tuple[str, ...]:
    """The sections that loaded, which is what `build_prompt` may be asked for."""
    return tuple(_load()[1])


def default_length() -> int:
    """The word limit the application sets. Part of the prompt, not our choice."""
    return _load()[2]


def default_format() -> str:
    return _load()[3]
