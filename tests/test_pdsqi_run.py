"""Running PDSQI-9 over the notes the rubric already scored.

The instrument itself is held to what was published in `test_pdsqi.py`. These
tests hold the machinery around it: that the rows can never be averaged into the
rubric's table, that a note is presented to the judge the same way every time,
and that an attribute nobody answered stays a gap rather than becoming a zero.
"""

from __future__ import annotations

import json

from tnb import judge, report, results
from tnb.scoring import pdsqi, pdsqi_run
from tnb.scoring.run import Candidate

NOTE = {
    "subjective": "Client reports rising anxiety before exams.",
    "objective": "Engaged, spoke at length, no distress observed.",
    "assessment": "Anxiety consistent with earlier sessions.",
    "plan": "Breathing practice, review in one week.",
}
TRANSCRIPT = "T: How was the week?\nC: The exam is on my mind."


def _judge_config(**overrides) -> judge.JudgeConfig:
    """A config that names no real project -- nothing here reaches a network."""
    base = {
        "project": "a-project",
        "location": "us-west4",
        "credentials_path": "secrets/none.json",
    }
    return judge.JudgeConfig(**{**base, **overrides})


def _candidate(**overrides) -> Candidate:
    base = {
        "provider": "einfra",
        "system_id": "a-model",
        "system_type": "model",
        "system_label": "a-model",
        "session_id": "s1",
        "note": dict(NOTE),
        "conversation": TRANSCRIPT,
    }
    return Candidate(**{**base, **overrides})


class _Judge:
    """Answers every question, refusing the nth if asked to."""

    def __init__(self, config, *, refuse_at: int | None = None, answer: str = "4") -> None:
        self.config = config
        self._refuse_at = refuse_at
        self._answer = answer
        self.prompts: list[str] = []

    def count_tokens(self, prompt: str) -> int:
        return len(prompt) // 4

    def ask(self, prompt: str):
        self.prompts.append(prompt)
        if len(self.prompts) == self._refuse_at:
            return judge.Answer(text="", ok=False, error="HTTP429: rate limited")
        # The binary attribute is asked last and wants a word, not a digit.
        text = "No" if "Yes or No" in prompt else self._answer
        return judge.Answer(text=text, ok=True, output_tokens=1)


# --- how a note is put to the judge -----------------------------------------


def test_the_note_is_rendered_in_the_instruments_order_not_the_dictionarys():
    """`organized` is one of the eight attributes.

    A note parsed out of a model's reply carries whatever order that model
    wrote in, so rendering in dictionary order would let the judge rate the
    order our parser happened to see and call it the model's organisation.
    """
    forwards = pdsqi.render_note(NOTE)
    backwards = pdsqi.render_note({key: NOTE[key] for key in reversed(list(NOTE))})

    assert forwards == backwards
    assert forwards.index("Subjective") < forwards.index("Objective")
    assert forwards.index("Assessment") < forwards.index("Plan")


def test_a_missing_section_is_shown_as_empty_rather_than_left_out():
    """A model that wrote no plan and was shown three headings would look
    tidier for the omission, on an instrument that asks about thoroughness."""
    rendered = pdsqi.render_note({"subjective": "Only this."})

    for heading in ("Subjective:", "Objective:", "Assessment:", "Plan:"):
        assert heading in rendered


def test_the_rendering_is_part_of_the_prompt_and_therefore_of_the_version():
    """Not a test of behaviour but of a claim: if `render_note` changes, every
    cached answer was given about a different text, and the version has to move
    with it. This fails loudly the day the rendering is edited."""
    assert pdsqi.render_note(NOTE) == (
        "Subjective: Client reports rising anxiety before exams.\n\n"
        "Objective: Engaged, spoke at length, no distress observed.\n\n"
        "Assessment: Anxiety consistent with earlier sessions.\n\n"
        "Plan: Breathing practice, review in one week."
    )
    assert pdsqi.JUDGE_PROMPT_VERSION == "pdsqi9-note-v1"


# --- what the rows may and may not be combined with -------------------------


def test_these_rows_can_never_share_a_table_with_the_rubrics():
    """Two of the six comparability keys differ, not one.

    Coverage of a 23-item checklist and quality on a validated instrument are
    two measurements of the same note. A table holding both invites a reader to
    average them into a third that nobody defined.
    """
    from tnb.scoring import run as rubric_run
    from tnb.scoring import tneval

    scored = pdsqi_run.NoteResult(
        candidate=_candidate(),
        scored={key: 4.0 for key in pdsqi.ATTRIBUTE_KEYS},
    )
    mine = pdsqi_run.to_rows([scored], judge_model="a-judge")[0]

    rubric_note = rubric_run.NoteResult(candidate=_candidate(), scores=tneval.Scores())
    theirs = rubric_run.to_rows([rubric_note], judge_model="a-judge")[0]

    differ = [
        key
        for key in results.COMPARABILITY_KEYS
        if getattr(mine, key, None) != getattr(theirs, key, None)
    ]
    assert set(differ) == {"track", "judge_prompt_version"}


def test_the_page_knows_how_to_draw_the_track_it_was_given():
    """A track `results` accepts and `report` cannot draw is a row that lands in
    the file and never appears anywhere."""
    assert results.TRACK_PDSQI in results.TRACKS
    for table in (
        report.COLUMNS,
        report.MEASURE_TABLES,
        report.RANKING_MEASURES,
        report.JUDGE_MEASURES,
        report.TRACK_TITLES,
        report.TRACK_SWITCH_LABELS,
        report.TRACK_BLURBS,
        report.TRACK_DESIGN,
    ):
        assert results.TRACK_PDSQI in table


def test_the_columns_are_the_instruments_own_eight_and_nothing_averaged():
    keys = [key for key, _ in report.COLUMNS[results.TRACK_PDSQI]]

    assert keys == list(pdsqi.ATTRIBUTE_KEYS)
    assert report.RANKING_MEASURES[results.TRACK_PDSQI] is None, (
        "the instrument's authors report the attributes separately"
    )


def test_the_track_is_labelled_as_having_no_human_anchor_for_these_notes():
    """PDSQI-9 publishes a ceiling and not a calibration, and the difference is
    the whole reason the distinction is on the page: nobody has rated *these*
    notes on this instrument."""
    design = report.TRACK_DESIGN[results.TRACK_PDSQI]

    assert design["calibrated"] is False
    assert "0.575" in design["calibration"]
    assert "No human has rated these notes" in design["calibration"]


# --- an absence is never a measurement --------------------------------------


def test_an_attribute_the_judge_refused_is_named_and_the_note_is_partial(tmp_path):
    result = pdsqi_run.score_note(
        _candidate(),
        _Judge(_judge_config(), refuse_at=2),
        judge.Spend(limit_usd=0.0),
        cache_root=tmp_path,
    )

    assert result.failed == 1
    assert len(result.missing) == 1
    assert result.is_complete is False
    assert all(value > 0 for value in result.scored.values()), "nothing was zeroed"


def test_a_partial_note_is_left_out_of_the_mean_rather_than_averaged_over_seven():
    """A judge runs out of room on the long, dense notes, so the attribute that
    goes missing is not evenly distributed. Dropping it from a denominator
    flatters exactly the notes that lost one."""
    complete = pdsqi_run.NoteResult(
        candidate=_candidate(),
        scored={key: 5.0 for key in pdsqi.ATTRIBUTE_KEYS},
    )
    partial = pdsqi_run.NoteResult(
        candidate=_candidate(session_id="s2"),
        scored={key: 1.0 for key in pdsqi.ATTRIBUTE_KEYS if key != "useful"},
        missing=["useful"],
    )

    aggregate = pdsqi_run.SystemAggregate(notes=[complete, partial])
    metrics = aggregate.metrics()

    assert aggregate.n_partial == 1
    assert metrics.headline["useful"] == 5.0, "the complete note only"
    assert metrics.headline["accurate"] == 5.0, "and not 3.0, which is both notes"


def test_without_a_transcript_the_two_it_needs_are_absent_and_not_zero(tmp_path):
    """The six note-only attributes are the only ones a confidential session
    can be rated on, and a row that scored the other two zero would report a
    fabrication rather than a restriction."""
    client = _Judge(_judge_config())
    result = pdsqi_run.score_note(
        _candidate(),
        client,
        judge.Spend(limit_usd=0.0),
        cache_root=tmp_path,
        with_transcript=False,
    )

    assert result.asked == len(pdsqi.NOTE_ONLY_KEYS)
    assert result.is_complete, "six of six is complete when six were asked"
    assert set(result.scored) == set(pdsqi.NOTE_ONLY_KEYS)
    for key in pdsqi.NEEDS_TRANSCRIPT_KEYS:
        assert key not in result.scored
        assert key not in result.missing, "never asked is not the same as unanswered"

    assert not any(TRANSCRIPT in prompt for prompt in client.prompts)


def test_a_column_is_dropped_rather_than_averaged_over_the_notes_that_have_it():
    """If one note of two lacks an attribute, the mean of the other one is not
    that system's score on it -- it is a mean over a subset chosen by the judge
    rather than by us."""
    both = pdsqi_run.SystemAggregate(
        notes=[
            pdsqi_run.NoteResult(
                candidate=_candidate(),
                scored={key: 4.0 for key in pdsqi.NOTE_ONLY_KEYS},
            ),
            pdsqi_run.NoteResult(
                candidate=_candidate(session_id="s2"),
                scored={key: 2.0 for key in pdsqi.ATTRIBUTE_KEYS},
            ),
        ]
    )

    headline = both.metrics().headline

    assert "accurate" not in headline, "one note of the two was never asked it"
    assert headline["useful"] == 3.0, "both notes were"


# --- publishing what is already answered ------------------------------------


def test_from_cache_checks_what_the_judge_was_asked(tmp_path):
    """A re-generated note must not be published carrying the judgement of the
    text it replaced. `score_note` has checked this since the digest was added;
    the path that publishes without asking anything has to check it too."""
    client = _Judge(_judge_config())
    candidate = _candidate()
    pdsqi_run.score_note(candidate, client, judge.Spend(limit_usd=0.0), cache_root=tmp_path)

    assert pdsqi_run.from_cache([candidate], client, cache_root=tmp_path), "the note as answered"

    rewritten = _candidate(note={**NOTE, "plan": "Something else entirely."})
    assert pdsqi_run.from_cache([rewritten], client, cache_root=tmp_path) == []


def test_from_cache_counts_an_unanswered_attribute_as_partial(tmp_path):
    """No threshold, unlike the rubric's sixty questions: one missing attribute
    of eight is an eighth of the instrument, and a mean over the other seven is
    a different measurement under the same heading."""
    candidate = _candidate()
    client = _Judge(_judge_config(), refuse_at=3)
    pdsqi_run.score_note(candidate, client, judge.Spend(limit_usd=0.0), cache_root=tmp_path)

    from_cache = pdsqi_run.from_cache([candidate], client, cache_root=tmp_path)

    assert len(from_cache) == 1
    assert from_cache[0].is_complete is False
    assert len(from_cache[0].missing) == 1
    assert pdsqi_run.SystemAggregate(notes=from_cache).metrics().headline == {}


def test_a_refused_call_leaves_a_record_that_is_not_read_back_as_an_answer(tmp_path):
    candidate = _candidate()
    spend = judge.Spend(limit_usd=0.0)
    pdsqi_run.score_note(
        candidate, _Judge(_judge_config(), refuse_at=2), spend, cache_root=tmp_path
    )

    written = [json.loads(p.read_text(encoding="utf-8")) for p in tmp_path.rglob("*.json")]
    refused = [record for record in written if not record["ok"]]
    assert len(refused) == 1
    assert refused[0]["error"] == "HTTP429: rate limited"

    second = pdsqi_run.score_note(candidate, _Judge(_judge_config()), spend, cache_root=tmp_path)
    assert second.cached == len(pdsqi.ATTRIBUTES) - 1
    assert second.asked == 1
    assert second.is_complete


# --- what a row says about the systems it names ------------------------------


def test_a_row_carries_the_ceiling_it_has_to_be_read_against():
    row = pdsqi_run.to_rows(
        [
            pdsqi_run.NoteResult(
                candidate=_candidate(),
                scored={key: 4.0 for key in pdsqi.ATTRIBUTE_KEYS},
            )
        ],
        judge_model="a-judge",
    )[0]

    assert "0.575" in row.metrics_note
    assert "no human has rated these notes" in row.metrics_note.lower()


def test_a_session_the_endpoint_refused_is_not_charged_to_the_model():
    """The same rule as the rubric track, for the same reason: a note e-INFRA
    never answered for is not a note the model failed to write."""
    scored = pdsqi_run.NoteResult(
        candidate=_candidate(),
        scored={key: 4.0 for key in pdsqi.ATTRIBUTE_KEYS},
    )
    unreached = results.Unreached(
        sessions=2,
        reasons={"HTTP429: rate limited": 2},
        failure_reasons={},
    )

    row = pdsqi_run.to_rows(
        [scored],
        judge_model="a-judge",
        n_generated={("einfra", "a-model"): 1},
        n_attempted=3,
        n_unreached={("einfra", "a-model"): unreached},
    )[0]

    assert row.n_sessions_attempted == 3
    assert row.n_sessions_generated == 1
    assert row.n_failed == 0, "two missing notes, both of them the endpoint's"
    assert row.unreached_reasons == {"HTTP429: rate limited": 2}
