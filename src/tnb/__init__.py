"""therapy-note-bench: a reproducible benchmark of LLM-generated psychotherapy notes."""

#: Part of every row's comparability key, so this is not a release number: it is
#: the statement "these measures mean what they meant last time". Bump it
#: whenever a measure's definition changes, even if no interface does, and the
#: leaderboard starts a new table rather than mixing the two.
#:
#: 0.2.0 -- four measures changed meaning:
#:
#: - `rouge_l` compares field values over the sections the expert answered,
#:   not the whole rendered note. Both sides used to share our 17 field labels
#:   and every `Nil` the expert wrote, so a note with nothing in it scored
#:   0.379. It now scores 0.000.
#: - `temporal` became `temporal_past` and `temporal_next`. One column averaged
#:   a thing every model does with a thing almost none of them does, weighted
#:   3:1 towards the easy half by how often the experts answered each section.
#: - "the expert answered this field" is structural: a value that spells
#:   "nothing to report" out one sub-question at a time is empty, however many
#:   words it takes.
#: - `conciseness` is not published when the note text is unavailable, because
#:   then its denominator is unknown rather than equal to whatever arrived.
#: 0.3.0 -- a composite "Nil" is empty however it is punctuated. `is_filled`
#: split a composite answer on newlines and semicolons but not commas, and
#: matched the empty markers exactly, so "Nil" was empty and "Nil." was not.
#: `deepseek-v4-flash-thinking` wrote `Date: Nil, Place: Nil, Time: Nil` into
#: *what happens next* in the only two sessions that carried its Looks-forward
#: score, published as 0.1818 where the answer is 0.0909.
#:
#: 0.4.0 -- a list marker is no longer a sentence. `1. ` ends in a full stop
#: followed by a space, so a numbered plan was cut into pieces that were bare
#: numerals, each one a question the judge was asked and a numeral cannot pass:
#: a certain No in the numerator and a certain +1 in the denominator of
#: `conciseness`. It was 65% of `qwen3.5-122b`'s conciseness failures and 0% for
#: the models that write prose, so the column was partly measuring markdown.
__version__ = "0.4.0"
