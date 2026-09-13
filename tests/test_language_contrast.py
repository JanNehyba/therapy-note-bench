"""The paired EN/CS comparison, on the synthetic content pair.

The demo store holds every profile in both languages over one shared content
pair, so the contrast can be exercised end to end without a single real Czech
case. What is pinned: two manifests that differ in anything but language are
refused; a pair is joined on translation_group and its client groups must
agree; a metric incomplete on one side is reported as not comparable and never
as a value; the public form carries no free text.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from therapy_note_eval import contrast, controls, report
from therapy_note_eval.cli import main
from therapy_note_eval.privacy import LABEL
from therapy_note_eval.schema import ValidationError
from therapy_note_eval.storage import Store

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace():
    # Same shape as tests/test_gen2.py: Store refuses a root that is not under
    # local/ and gitignored, so tmp_path cannot be used.
    path = REPO / "local" / ("gen2-test-" + uuid.uuid4().hex)
    path.mkdir(parents=True, mode=0o777)
    return path


def _pair(store: Store, profile: str) -> tuple[str, str]:
    manifests = report.load_workspace(store)["manifests"]
    by_language = {
        m.spec.language: key for key, m in manifests.items() if m.spec.profile == profile
    }
    return by_language["en"], by_language["cs"]


def test_the_demo_pair_contrasts_end_to_end(workspace):
    store = Store(workspace)
    controls.demo(store)
    left, right = _pair(store, "continuity")
    found = contrast.language_contrast(store, left, right)

    assert found["left"]["language"] == "en" and found["right"]["language"] == "cs"
    assert found["left"]["cases"] == found["right"]["cases"] == 1
    assert {"spec", "judge", "bank_author", "extractor"} <= set(found["compared_on"])
    assert not {"cases", "banks", "corpus", "origin"} & set(found["compared_on"])
    assert found["left"]["required_headings"] == found["right"]["required_headings"] == 0
    assert found["bank_comparability"]["left_information"] > 0
    assert found["systems"], "the shared generator has no compared metrics"
    for system, metrics in found["systems"].items():
        for metric, entry in metrics.items():
            if "not_comparable" in entry:
                assert entry["not_comparable"], (system, metric)
                continue
            # One client on each side: a difference and no interval, never a
            # fabricated one.
            assert entry["shared_cases"] == 1, (system, metric)
            assert entry["left_only"] == entry["right_only"] == 0
            assert entry["ci95"] is None, (system, metric)
    assert found["left_only_systems"] == found["right_only_systems"] == []


def test_two_manifests_in_one_language_are_refused(workspace):
    store = Store(workspace)
    controls.demo(store)
    left, _ = _pair(store, "continuity")
    with pytest.raises(ValidationError, match="same language"):
        contrast.language_contrast(store, left, left)


def test_manifests_that_differ_beyond_language_are_refused(workspace):
    """A different profile is a different instrument, not a different language."""
    store = Store(workspace)
    controls.demo(store)
    left, _ = _pair(store, "continuity")
    _, right = _pair(store, "supervision")
    with pytest.raises(ValidationError, match="beyond language"):
        contrast.language_contrast(store, left, right)


def test_a_metric_incomplete_on_one_side_is_named_not_averaged(workspace, monkeypatch):
    """The rule the report applies per cohort holds per pair here.

    The demo answers everything, so an incomplete side is made by hiding the
    right side's measured case from the contrast. Every metric must then come
    back as not comparable, never as the left value or as a difference over
    whatever remains.
    """
    store = Store(workspace)
    controls.demo(store)
    left, right = _pair(store, "continuity")
    original = report.measured_by_system

    def hide_right(store, key, manifest, found):
        by_system, identities, generated = original(store, key, manifest, found)
        if key == right:
            by_system = {system: {} for system in by_system}
        return by_system, identities, generated

    monkeypatch.setattr(report, "measured_by_system", hide_right)
    found = contrast.language_contrast(store, left, right)
    assert found["systems"]
    for system, metrics in found["systems"].items():
        for metric, entry in metrics.items():
            assert "right" in entry["not_comparable"], (system, metric)
            assert entry["complete_right"] is False
            assert "mean" not in entry and "ci95" not in entry
    for metrics in contrast.public_contrast(found)["systems"].values():
        for entry in metrics.values():
            assert entry["not_comparable"] is True and entry["complete_right"] is False


def test_the_public_form_carries_no_free_text(workspace):
    store = Store(workspace)
    controls.demo(store)
    left, right = _pair(store, "continuity")
    found = contrast.language_contrast(store, left, right)
    public = contrast.public_contrast(found)

    def leaves(value):
        if isinstance(value, dict):
            for k, v in value.items():
                yield k
                yield from leaves(v)
        elif isinstance(value, list):
            for v in value:
                yield from leaves(v)
        else:
            yield value

    for leaf in leaves(public):
        if isinstance(leaf, str):
            assert LABEL.fullmatch(leaf), leaf
    assert "interpretation" not in public and "note" not in public["bank_comparability"]


def test_the_cli_writes_a_private_and_a_public_contrast(workspace, capsys):
    assert main(["--workspace", str(workspace), "demo"]) == 0
    capsys.readouterr()
    left, right = _pair(Store(workspace), "continuity")
    assert main(["--workspace", str(workspace), "contrast", "--left", left, "--right", right]) == 0
    out = json.loads(capsys.readouterr().out)
    private, public = Path(out["contrast"]), Path(out["public_contrast"])
    assert private.parent.name == "contrasts" and public.parent.name == "public_contrasts"
    assert private.is_relative_to(workspace) and public.is_relative_to(workspace)
    stored = json.loads(public.read_text(encoding="utf-8"))
    assert stored == out["public"]
    assert "interpretation" not in stored and "pairing" not in stored
    assert "interpretation" in json.loads(private.read_text(encoding="utf-8"))
