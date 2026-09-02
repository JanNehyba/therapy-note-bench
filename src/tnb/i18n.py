"""Czech beside the English, for the two published pages.

English is the source. Every string a reader sees is authored once, in English,
where it belongs -- in a template, in a scorer's measure table, in ``report.py``
-- and this module is a lookup beside it. Nothing here is a second copy of the
page: a key with no entry draws its English, so the pages cannot break by being
half-translated, and a translation that falls behind shows as English rather
than as a blank.

Three kinds of key share one dictionary, and they cannot collide:

``page.*``
    Prose that is HTML in a template, marked there with ``data-t``. Keyed by an
    id rather than by its own text, because a paragraph carrying three links is
    not a good dictionary key.

a sentence with ``{0}`` in it
    A sentence written in the page script, marked there with the ``T`` tagged
    template. The holes are numbered so Czech may reorder them -- it has to, and
    it may also ignore one: English picks between "is" and "are" where Czech
    agrees three ways, so the Czech sentence is written to need no such word and
    simply never mentions that hole.

any other sentence
    A string out of the payload -- a column heading, a caveat, a track title, a
    blurb. Keyed by the English itself, so the dictionary reads as a translation
    memory and no key has to be invented for a sentence that already exists.

Keys are whitespace-normalised on both sides. A sentence in a template literal
carries the template's indentation with it, and a dictionary that had to
reproduce that would break the first time somebody re-indented a function.

The words this file has settled on, so two panels do not name one thing twice:

===================  ============================================
note (of a session)  zápis
session              sezení
transcript           přepis
judge                hodnotitel; *judge model* is *hodnoticí model*
rubric               rubrika
track                větev
harness              harness -- a version label, left as it is
provider             poskytovatel
expert note          expertní zápis
completeness         úplnost
conciseness          stručnost
faithfulness         věrnost
band / rank          pásmo / příčka
===================  ============================================

Numbers keep the decimal point they have in the tables. A page that wrote 0.18
in a column and 0,18 in the sentence under it would be asking the reader to
believe they are the same number.

``tests/test_i18n.py`` holds this file to the pages: every ``data-t`` id, every
tagged sentence and every payload string a page draws must be answered here.
"""

from __future__ import annotations

#: The language the pages open in, and the language every key is written in.
DEFAULT_LANG = "en"

#: Offered by the switch, in the order it draws them.
LANGUAGES = ("en", "cs")


def norm(text: str) -> str:
    """A key with its wrapping taken out, exactly as the page does it."""
    return " ".join(str(text).split())


#: Prose that is HTML in a template, keyed by the id its ``data-t`` names.
_STATIC = {
    "page.title": "therapy-note-bench — žebříček",
    "page.sub": (
        "Zápisy z psychoterapeutických sezení psané jazykovými modely, hodnocené třemi "
        "publikovanými nástroji — rubrikou SOAP z TN-Eval, PDSQI-9 a 17 oddíly z iCARE — "
        "a přeměřované, jak se modely mění. "
        '<a href="https://github.com/JanNehyba/therapy-note-bench">Kód a všechna skóre na '
        "GitHubu</a>; korpusy se stahují z vlastních zdrojů a tady se dál nešíří."
    ),
    "page.methods-link": (
        '<a href="methods.html">Jak se to měřilo →</a> '
        "Definice každého sloupce, který hodnotitel a jak těsně se shoduje se dvěma terapeuty, "
        "jak daleko od sebe jsou oba hodnotitelé, co jsou ty dva korpusy a odkud pocházejí, "
        "a které řádky se už nekreslí."
    ),
    "page.brief-link": (
        '<a href="brief.html">Jak číst tyto výsledky →</a> '
        "Čtyři tvrzení, která tabulky unesou, a čtyři, která ne, i se souborem, ze kterého "
        "každé číslo pochází."
    ),
    "page.foot.data": (
        'Vykreslená čísla jsou v souboru <a href="leaderboard.json">leaderboard.json</a>; '
        "každý běh, který za nimi stojí, je v <code>results/rows.jsonl</code> "
        "v repozitáři. Běhy, které jsou změřené a nepublikují se, jdou do souboru "
        "mimo něj."
    ),
    "page.foot.author": (
        "Tento benchmark spravuje Jan Nehyba. Opravy a sporná čísla: "
        '<a href="https://github.com/JanNehyba/therapy-note-bench/issues">založte issue</a>.'
    ),
    "scored up to <code>{0}</code>": "obodováno nejpozději <code>{0}</code>",
    "page.foot.notes": (
        "<strong>Zápisy</strong> počítají, kolik zápisů dokázal protokol vůbec přečíst. Model, "
        "který napíše dobrý zápis ve špatném tvaru, přichází o zápisy kvůli formátu, ne kvůli "
        "obsahu — přečtěte si ten počet dřív, než začnete srovnávat skóre."
    ),
    "page.foot.provider": (
        "Předposlední sloupec je <strong>poskytovatel</strong>, který model obsluhoval. Totéž "
        "id modelu u dvou poskytovatelů může znamenat dvě různá sestavení — jiná kvantizace, "
        "jiné "
        "váhy, jiný systémový prompt — proto jsou to tady vždy dva řádky, nikdy jeden."
    ),
    "page.foot.comparability": (
        "Řádky se srovnávají jedině tehdy, když se shodují ve všech šesti: větev, verze "
        "harnessu, verze promptu, hodnoticí model, verze hodnoticího promptu a "
        "<strong>nastavení, ve kterém hodnotitel běžel</strong> — proto je hodnotitel "
        "přepínačem nahoře a ne sloupcem tady. Co bylo z tabulek staženo a proč, stojí "
        '<a href="methods.html#withdrawn">na stránce o metodě</a>.'
    ),
    "page.foot.background": (
        "<strong>Pozadí.</strong> "
        '<a href="datasets.md">Datové sady</a> — odkud každá pochází, jakou licenci publikuje '
        "(žádná ze tří) a jaké pasti v nich jsou; "
        '<a href="methodology.md">metoda</a>; '
        '<a href="limitations.md">co výsledek nesmí tvrdit</a>; '
        '<a href="landscape.md">co v oboru existuje a co ne</a>; '
        '<a href="models-snapshot.md">co měl endpoint kdy nasazené</a>.'
    ),
}


#: Sentences written in the page script, keyed by their English with numbered
#: holes. Read the module docstring for why a hole may go unused.
_SENTENCES = {
    # -- the order and the groups -------------------------------------------
    "Place": "Místo",
    "Group": "Skupina",
    "Place by column": "Místo po sloupcích",
    "checked against people": "ověřeno proti lidem",
    "mean place {0}": "průměrné místo {0}",
    "not placed: {0}": "bez místa: {0}",
    "Not placed: {0} not measured for this row.": "Bez místa: {0} u tohoto řádku neměřeno.",
    "Outside the compared population: a column is missing under one of the two judges.": (
        "Mimo porovnávanou populaci: u jednoho ze dvou hodnotitelů chybí sloupec."
    ),
    "Place in this table's order: the mean of the row's places over the instrument's columns,"
    " every column counting once. Ties share a place.": (
        "Místo v pořadí této tabulky: průměr míst řádku přes sloupce nástroje, každý sloupec "
        "počítá jednou. Remízy sdílejí místo."
    ),
    "What the evidence separates: a system stands above another only when it is at least as good"
    " on every column under both judges in {0} of the resampled conversations. Systems no tested"
    " comparison separates share a group.": (
        "Co důkazy oddělí: systém stojí nad jiným jen tehdy, když je aspoň tak dobrý v každém "
        "sloupci u obou hodnotitelů v {0} převzorkovaných rozhovorů. Systémy, které žádné "
        "otestované porovnání neoddělí, sdílejí skupinu."
    ),
    "Mean place {0}, which is where this row's place of {1} comes from. Ties share a place.": (
        "Průměrné místo {0}, z něhož vychází místo {1} tohoto řádku. Remízy sdílejí místo."
    ),
    "No place: {0} was not measured for this row, and a mean over fewer columns would be a"
    " different quantity.": (
        "Bez místa: {0} nebylo u tohoto řádku měřeno a průměr přes méně sloupců by byl jiná "
        "veličina."
    ),
    "Ordered by <strong>mean place</strong> over the {0} columns of this instrument, every column"
    " counting once &mdash; a convention, not a measurement: the columns do not predict each"
    " other. Under the other weightings tried (each column counted twice, and the reference rows"
    " removed) first place is held by {1}; at most {2} of {3} systems change place and none by"
    ' more than {4} (<a href="methods.html#ordering">how the order was built</a>). Ties share a'
    " place.": (
        "Seřazeno podle <strong>průměrného místa</strong> přes {0} sloupců tohoto nástroje, "
        "každý sloupec počítá jednou &mdash; konvence, ne měření: sloupce se navzájem "
        "nepředpovídají. Při ostatních vyzkoušených vahách (každý sloupec počítán dvakrát a "
        "odebrané referenční řádky) drží první místo {1}; místo změní nejvýš {2} z {3} systémů "
        'a žádný o víc než {4} (<a href="methods.html#ordering">jak pořadí vzniklo</a>). '
        "Remízy sdílejí místo."
    ),
    "<strong>Group</strong> is what the evidence separates: a system stands above another only"
    " when it is at least as good on every column under both judges in {0} of {1} resampled"
    " conversations. {2} group(s) for {3} systems; {4} of them beaten by no tested comparison"
    ' (<a href="methods.html#groups">how the comparisons were tested</a>).': (
        "<strong>Skupina</strong> je to, co důkazy oddělí: systém stojí nad jiným jen tehdy, když "
        "je aspoň tak dobrý v každém sloupci u obou hodnotitelů v {0} z {1} převzorkování "
        "rozhovorů. {2} skupin pro {3} systémů; {4} z nich neporazí žádné otestované porovnání "
        '(<a href="methods.html#groups">jak se porovnání testovala</a>).'
    ),
    "<strong>Which of these the evidence separates has not been tested for this table.</strong>"
    " Read adjacent places as an order, not as a result.": (
        "<strong>Které z nich důkazy oddělí, nebylo u této tabulky testováno.</strong> Čtěte "
        "sousední místa jako pořadí, ne jako výsledek."
    ),
    "<strong>No column of this table has been checked against people</strong>: nobody has rated"
    " these notes on this instrument.": (
        "<strong>Žádný sloupec této tabulky nebyl ověřen proti lidem</strong>: tyto zápisy na "
        "tomto nástroji nikdo nehodnotil."
    ),
    "Only one column here is checked against people: <strong>{0}</strong>. The judge and a"
    " trained therapist agree on it at <strong>{1}</strong> where two therapists reach"
    " <strong>{2}</strong> ({3}); on the 1&#8211;5 ratings TN-Eval published beside that rubric,"
    " those two therapists reach only {4} ({5}). Both are computed here from TN-Eval's own"
    ' annotations over {6} notes; <a href="methods.html#calibration">how this was measured</a>.'
    " It counts once in the order above, like every other column.{7}": (
        "Proti lidem je tu ověřený jediný sloupec: <strong>{0}</strong>. Hodnotitel a školený "
        "terapeut se na něm shodnou na <strong>{1}</strong> tam, kde se dva terapeuti shodnou na "
        "<strong>{2}</strong> ({3}); na hodnoceních 1&#8211;5, která TN-Eval zveřejnil vedle té "
        "rubriky, dosáhnou titíž dva terapeuti jen {4} ({5}). Obojí je spočítané zde z anotací "
        'TN-Evalu přes {6} zápisů; <a href="methods.html#calibration">jak se to měřilo</a>. '
        "V pořadí výše počítá jednou, jako každý jiný sloupec.{7}"
    ),
    "Only one column here has a human anchor at all: <strong>{0}</strong>. <strong>This judge's"
    " agreement with the two therapists is not published here</strong>, so the figure that"
    " belongs in this sentence is missing rather than borrowed from another judge. It counts"
    " once in the order above, like every other column.": (
        "Lidskou kotvu tu má vůbec jediný sloupec: <strong>{0}</strong>. <strong>Shoda tohoto "
        "hodnotitele s oběma terapeuty tu není publikovaná</strong>, takže číslo, které do této "
        "věty patří, chybí — místo aby se půjčilo od jiného hodnotitele. V pořadí výše počítá "
        "jednou, jako každý jiný sloupec."
    ),
    "On the order itself the two judges agree at Spearman {0}: {1} of {2} systems hold a"
    " different place under the other judge.": (
        "Na samotném pořadí se oba hodnotitelé shodnou při Spearmanově {0}: {1} z {2} systémů má "
        "u druhého hodnotitele jiné místo."
    ),
    # -- the methods page: how the order was built ------------------------------
    "Every table is ordered the same way. On each column of its instrument every system is"
    " placed 1st, 2nd, &hellip; at the precision the table prints, so two rows that print the"
    " same figure share a place; the places are averaged with every column counting once; and"
    " the rows are ordered by that mean, ties sharing a place. That equal weight is the one"
    " convention the order embeds. The rows below recompute the order with each column counted"
    " twice and with the reference rows removed, and say who is first under each, how many"
    " systems change place, the furthest any moves, and Spearman against the equal-weight"
    " order.": (
        "Každá tabulka je seřazená stejně. Na každém sloupci svého nástroje je každý systém "
        "umístěn jako 1., 2., &hellip; na přesnosti, kterou tabulka tiskne, takže dva řádky se "
        "stejnou vytištěnou hodnotou sdílejí místo; místa se průměrují, každý sloupec počítá "
        "jednou; a řádky se řadí podle toho průměru, remízy sdílejí místo. Ta stejná váha je "
        "jediná konvence, kterou pořadí nese. Řádky níže pořadí přepočítávají s každým sloupcem "
        "počítaným dvakrát a s odebranými referenčními řádky a říkají, kdo je při každé variantě "
        "první, kolik systémů změní místo, o kolik nejvýš se některý posune a Spearmanovu "
        "korelaci proti pořadí se stejnými vahami."
    ),
    "No ordered table yet.": "Zatím žádná seřazená tabulka.",
    "every column once": "každý sloupec jednou",
    "reference rows removed ({0})": "odebrané referenční řádky ({0})",
    "{0} counted twice": "{0} počítáno dvakrát",
    "{0} pair(s) reversed": "{0} dvojic prohozeno",
    "{0} systems placed over {1} columns{2}.": "{0} systémů umístěno přes {1} sloupců{2}.",
    "Weighting": "Váhy",
    "First": "První",
    "Second": "Druhý",
    "Moved": "Posunuto",
    "Furthest": "Nejdál",
    "The two judges' orders on this track agree at Spearman <strong>{0}</strong> over {1}"
    " systems; {2} hold a different place under the other judge{3}.": (
        "Pořadí obou hodnotitelů na této trati se shodují při Spearmanově <strong>{0}</strong> "
        "přes {1} systémů; {2} z nich má u druhého hodnotitele jiné místo{3}."
    ),
    "<code>{0}</code> furthest ({1} under <code>{2}</code>, {3} under <code>{4}</code>)": (
        "<code>{0}</code> nejdál ({1} u <code>{2}</code>, {3} u <code>{4}</code>)"
    ),
    # -- the methods page: which comparisons survive ------------------------------
    "A system beats another outright when it is at least as good on every column of one"
    " instrument under both judges and strictly better somewhere. Each such claim is tested"
    " whole: every (judge, column) pair is a leg, and all legs are resampled together over the"
    " conversations both systems were scored on, paired. The claim holds in a draw when the"
    " winner is at least as good on every leg and ahead on one; it is kept when it holds in the"
    " stated share of draws. What survives is layered into the Group column: group 1 is beaten"
    " by no kept claim, group 2 only by group 1, and nothing breaks a tie.": (
        "Systém porazí jiný na plné čáře, když je aspoň tak dobrý v každém sloupci jednoho "
        "nástroje u obou hodnotitelů a někde přísně lepší. Každé takové tvrzení se testuje celé: "
        "každá dvojice (hodnotitel, sloupec) je jedna noha a všechny nohy se převzorkují "
        "společně přes rozhovory, na nichž byly oba systémy obodovány, párově. Tvrzení v jednom "
        "tahu drží, když je vítěz aspoň tak dobrý na každé noze a na jedné napřed; ponechá se, "
        "když drží v uvedeném podílu tahů. Co přežije, se navrství do sloupce Skupina: skupinu 1 "
        "neporazí žádné ponechané tvrzení, skupinu 2 jen skupina 1, a remízy nic nerozřazuje."
    ),
    "No comparison has been tested yet.": "Zatím nebylo otestováno žádné porovnání.",
    "{0} claim(s) on the stored means, {1} tested over {2} draws each; {3}; {4} untestable.": (
        "{0} tvrzení na uložených průměrech, {1} otestováno, každé přes {2} tahů; {3}; "
        "{4} netestovatelných."
    ),
    "{0} hold at {1}": "{0} drží při {1}",
    "Groups: {0}": "Skupiny: {0}",
    "kept": "drží",
    "not kept": "nedrží",
    "Winner": "Vítěz",
    "Loser": "Poražený",
    "Shared": "Sdíleno",
    "Holds in": "Drží v",
    "At {0}": "Při {0}",
    "Thinnest leg": "Nejtenčí noha",
    "Completeness alone": "Jen úplnost",
    "Untestable: {0}.": "Netestovatelné: {0}.",
    # -- one row, opened ----------------------------------------------------
    "{0} of this system's notes are still being judged.": (
        "U tohoto systému se ještě hodnotí {0} z jeho zápisů."
    ),
    "The scores above rest on <strong>{0}</strong> of the {1} notes the judge started: {2} came"
    " back with part of the protocol unanswered and {3} left out rather than averaged over a"
    " smaller denominator.": (
        "Skóre výše stojí na <strong>{0}</strong> z {1} zápisů, které hodnotitel začal hodnotit: "
        "u {2} z nich se část protokolu vrátila nezodpovězená, a ty jsou vynechány, místo aby se "
        "průměrovaly přes menší jmenovatel."
    ),
    "is": "je",
    "are": "jsou",
    "The scores above rest on all {0} notes the judge finished.": (
        "Skóre výše stojí na všech {0} zápisech, které hodnotitel dokončil."
    ),
    "{0} note(s) the protocol could not read": "Zápisy, které protokol nedokázal přečíst: {0}",
    "{0} note(s) missing, with no recorded reason.": (
        "Chybějící zápisy bez zaznamenaného důvodu: {0}."
    ),
    "{0} call(s) this harness cut off": "Volání, která uťal tento harness: {0}",
    "{0} call(s) unanswered or cut off": "Volání nezodpovězená nebo uťatá: {0}",
    "{0} call(s) the endpoint never answered": "Volání, která endpoint nikdy nezodpověděl: {0}",
    "Not the model's doing, and not counted against it.": (
        "Není to vina modelu a nepočítá se mu to k tíži."
    ),
    "A rate limit, a backend error or a timeout; re-running the generation fills those in.": (
        "Rate limit, chyba backendu nebo timeout; opakované generování je doplní."
    ),
    "Where the reason is a token ceiling it is ours: the call had already had its one"
    " escalation, and past that we stopped it.": (
        "Tam, kde je důvodem strop tokenů, je to naše věc: volání už mělo svou jedinou eskalaci "
        "a za ní jsme ho zastavili."
    ),
    "Generated with <strong>{0}</strong>.": "Vygenerováno s nastavením <strong>{0}</strong>.",
    "Generation settings were not recorded for this row.": (
        "U tohoto řádku nebylo nastavení generování zaznamenáno."
    ),
    "By section": "Po oddílech",
    "Section": "Oddíl",
    "These sections will not average to the figure in the row above, and the gap is the {0}"
    " part-answered {1}: the row's figure averages each note's own sections first, while a"
    " section here averages the notes that have it. A note missing one section counts in one and"
    " not the other. Rows with no part-answered notes agree exactly.": (
        "Tyto oddíly se nezprůměrují na číslo v řádku výše a ten rozdíl dělají zápisy "
        "zodpovězené jen zčásti — je jich {0}: číslo v řádku průměruje nejdřív oddíly každého "
        "zápisu zvlášť, kdežto oddíl tady průměruje ty zápisy, které ho mají. Zápis, kterému "
        "jeden oddíl chybí, se počítá do jednoho, a do druhého ne. Řádky bez částečně "
        "zodpovězených zápisů souhlasí přesně."
    ),
    "note": "zápis",
    "notes": "zápisy",
    "TRACE dimensions": "Dimenze TRACE",
    "Rubric criteria": "Kritéria rubriky",
    "Source: {0}": "Zdroj: {0}",
    "Wrote <strong>{0}</strong> of the {1} notes the protocol asked for — the same as every"
    " other row in this table, which is why there is no Notes column.": (
        "Napsal <strong>{0}</strong> z {1} zápisů, které protokol žádal — stejně jako každý "
        "další řádek v této tabulce, a proto tu není sloupec Zápisy."
    ),
    "Nothing to break down yet — this row has no scores.": (
        "Zatím není co rozebírat — tento řádek nemá žádná skóre."
    ),
    # -- a table nobody has judged yet ---------------------------------------
    "notes written {0}": "napsané zápisy {0}",
    "waiting for the judge": "čeká na hodnotitele",
    "{0} system(s) have written their notes; nothing has been scored yet, so there is nothing to"
    " rank. The count is what has been measured — how many notes each one produced that the"
    " protocol could read.": (
        "Počet systémů, které už napsaly své zápisy: {0}. Nic zatím nebylo obodováno, takže "
        "není co řadit. Změřený je zatím jen ten počet — kolik zápisů každý z nich vytvořil tak, "
        "aby je protokol dokázal přečíst."
    ),
    # -- the rows that are not models under test -----------------------------
    'the row marked <span class="chip">{0}</span> is a <strong>note a human clinician'
    " wrote</strong>, scored by the identical protocol": (
        'řádek označený <span class="chip">{0}</span> je <strong>zápis, který napsal člověk — '
        "klinik</strong>, obodovaný týmž protokolem"
    ),
    'rows marked <span class="chip">{0}</span> are the <strong>source paper&rsquo;s own'
    " systems</strong>, scored here so this table can be read against theirs": (
        'řádky označené <span class="chip">{0}</span> jsou <strong>vlastní systémy zdrojového '
        "článku</strong>, obodované tady, aby se tato tabulka dala číst proti té jejich"
    ),
    "Not every row is a model under test: {0}. Both are scored by the identical protocol, which"
    " is why they sit in the ranking. A human note placing low is a fact about the measure, not"
    " about the clinician.": (
        "Ne každý řádek je testovaný model: {0}. Obojí je bodováno týmž protokolem, proto stojí "
        "v pořadí. Nízko umístěný lidský zápis vypovídá o měřítku, ne o klinikovi."
    ),
    # Both keep their spaces: a key is trimmed on the way in and a value is not,
    # so a joiner has to carry its own. Czech puts no comma before "a".
    ", and": " a ",
    "and": " a ",
    # -- what instrument this table is ---------------------------------------
    "judge <code>{0}</code>{1}": "hodnotitel <code>{0}</code>{1}",
    "judge prompt {0}": "hodnoticí prompt {0}",
    "judge prompts {0}": "hodnoticí prompty {0}",
    "<strong>older harness</strong>, columns may differ from the tables above": (
        "<strong>starší harness</strong>, sloupce se mohou lišit od tabulek výše"
    ),
    "not yet judged": "zatím neohodnoceno",
    "The instrument these rows share:": "Nástroj, kterým byly tyto řádky změřeny:",
    "harness <code>{0}</code>": "harness <code>{0}</code>",
    "prompt <code>{0}</code>": "prompt <code>{0}</code>",
    # -- the grid itself ------------------------------------------------------
    "References": "Literatura",
    "How to cite this benchmark": "Jak citovat tento benchmark",
    "A number quoted from these tables is a number from one judge at one setting &mdash; cite the"
    " version, not just the link.": (
        "Číslo citované z těchto tabulek je číslo od jednoho hodnotitele v jednom nastavení "
        "&mdash; citujte verzi, ne jen odkaz."
    ),
    "generation coverage": "pokrytí generování",
    "measures redefined in <code>{0}</code>": "míry předefinovány ve verzi <code>{0}</code>",
    "judge settings not recorded": "nastavení hodnotitele nezaznamenáno",
    "questions rewritten in <code>{0}</code>": "otázky přepsány ve verzi <code>{0}</code>",
    "judge tried during calibration, not on the panel": (
        "hodnotitel vyzkoušen při kalibraci, není v panelu"
    ),
    "; ": "; ",
    "These rows were measured under an instrument the current tables cannot be compared with."
    " All of them remain in <code>results/rows.jsonl</code>.": (
        "Tyto řádky byly změřeny nástrojem, se kterým se současné tabulky srovnávat nedají. "
        "Všechny zůstávají v <code>results/rows.jsonl</code>."
    ),
    "Rows": "Řádků",
    "Harness": "Harness",
    "Reason": "Důvod",
    "The summary below is in English: it is assembled from the numbers it reports.": (
        "Souhrn níže je v angličtině: skládá se z čísel, o kterých mluví."
    ),
    "And the two against each other.": "A ti dva proti sobě.",
    "System": "Systém",
    "Median words in this model’s notes. Completeness counts coverage, so a longer note covers"
    " more.": (
        "Medián počtu slov v zápisech tohoto modelu. Úplnost počítá pokrytí, takže delší zápis "
        "pokryje víc."
    ),
    "Words": "Slova",
    "Notes": "Zápisy",
    # The column counted notes the figures do not rest on: 50 of 50 written,
    # and an average computed from 44 of them. Czech uses the same three
    # sentences the English does, in the same place.
    "Notes written of notes asked for, and where they differ, how many of them the figures in"
    " this row rest on.": (
        "Napsané zápisy z vyžádaných, a kde se to liší, na kolika z nich stojí čísla v tomto řádku."
    ),
    "{0} behind the score": "za skóre stojí {0}",
    "{0} note(s) came back with part of the protocol unanswered and are left out of the figures"
    " rather than averaged over a smaller denominator. The row's detail says which.": (
        "{0} zápisů se vrátilo s částí protokolu nezodpovězenou; do čísel se nezapočítávají, "
        "místo aby se průměrovaly přes menší jmenovatel. Detail řádku říká které."
    ),
    "{0} judged": "ohodnoceno {0}",
    "settings": "nastavení",
    # "in the panel below" was true until the eight panels moved to the methods
    # page, and then it pointed a reader at a panel that is not there -- from
    # inside a tooltip a phone cannot open, at that.
    "scored by a judge from the same vendor, whose self-preference is measured on the methods"
    " page": (
        "obodováno hodnotitelem od téhož dodavatele; jak moc nadržuje sám sobě, je změřeno "
        "na stránce s metodikou"
    ),
    "judge's own {0}": "stejný dodavatel jako hodnotitel: {0}",
    # -- the sentences under the grid ----------------------------------------
    "Reference group — the {0} systems neither judge's vendor wrote: {1}.": (
        "Referenční skupina — {0} systémů, které nenapsal dodavatel ani jednoho z hodnotitelů: {1}."
    ),
    "{0} are in it under a name their model family does not share, and pull the answer toward"
    " zero.": (
        "{0} v ní jsou pod jménem, které jejich rodina modelů nesdílí, a táhnou odpověď k nule."
    ),
    # The size of that lead, and what it does when the notes are resampled.
    # Under one of the two published judges it does not clear zero, and at two
    # decimal places the two cases print the same sentence.
    "Resampling the {0} notes puts that lead at <strong>{1}</strong> ({2} to {3}).": (
        "Po převzorkování {0} zápisů je ten náskok <strong>{1}</strong> ({2} až {3})."
    ),
    "<strong>That lead is {0} ({1} to {2} when the {3} notes are resampled), so under this judge"
    " it does not clear zero.</strong> It stays the only column with a human anchor at all"
    " &mdash; but on this judge's table, being closer to a therapist than they are to each"
    " other is not something these notes establish.": (
        "<strong>Ten náskok je {0} ({1} až {2} při převzorkování {3} zápisů), takže u tohoto "
        "hodnotitele nepřekročí nulu.</strong> Zůstává jediným sloupcem s jakýmkoli lidským "
        "ukotvením &mdash; ale v tabulce tohoto hodnotitele není to, že by byl "
        "blíž terapeutovi než oni sobě navzájem, něco, co by tyto zápisy prokázaly."
    ),
    # What the endpoints served the last time anyone asked. A row nobody can
    # ask again and a model nobody has asked yet are two different silences,
    # and both were left to inference.
    "withdrawn": "staženo",
    "The endpoint no longer served this model when it was last asked, on {0}. Its figures are"
    " final &mdash; it cannot be asked again, re-scored, or measured on a column added later"
    " &mdash; and they are kept and counted like every other row, because the measurements were"
    " made.": (
        "Endpoint tento model už nenabízel, když se ho někdo naposledy ptal, {0}. Jeho čísla "
        "jsou konečná &mdash; nejde se ho zeptat znovu, přebodovat ho ani ho změřit na sloupci, "
        "který přibude později &mdash; a zůstávají tu a počítají se jako u každého jiného "
        "řádku, protože ta měření proběhla."
    ),
    "<strong>{0}</strong> is drawn here and was not served when the endpoints were last asked, on"
    " {1}. Its figures are final rather than stale: the measurement was made, it counts in every"
    " comparison on this page, and it is kept so that a model withdrawn from an endpoint does not"
    " quietly leave the record.": (
        "<strong>{0}</strong> se tu kreslí a při posledním dotazu na endpointy, {1}, už nabízen "
        "nebyl. Jeho čísla nejsou zastaralá, ale konečná: to měření proběhlo, počítá se do "
        "každého porovnání na této stránce a řádek tu zůstává proto, aby model stažený "
        "z endpointu tiše nezmizel ze záznamu."
    ),
    "<strong>{0}</strong> was served on {1} and has never been asked to write a note, so its"
    " absence from these tables is a question nobody put, not a result.": (
        "<strong>{0}</strong> byl {1} nabízen a nikdy nebyl požádán, aby napsal zápis — jeho "
        "nepřítomnost v těchto tabulkách je tedy nepoložená otázka, ne výsledek."
    ),
    "{0} could not be asked, so nothing here is said about the models it serves.": (
        "{0} se zeptat nešlo, takže se tu o modelech, které nabízí, neříká nic."
    ),
    # The methods page's own table of the comparisons the band edges rest on.
    "Comparisons the band boundary turns on": "Porovnání, na kterých hranice pásma stojí",
    "Comparison": "Porovnání",
    "Beats in": "Poráží v",
    "From the cut": "Od řezu",
    "Rows it would move": "Kolik řádků by posunulo",
    "over": "nad",
    "none": "žádné",
    "Two systems are separated when one beats the other in at least {0} of resamples. That"
    " fraction is estimated from {1} draws and carries a standard error of <strong>{2}</strong>,"
    " so a comparison landing within a few of those is one the threshold decided rather than the"
    " evidence. {3} of the {4} comparisons that can decide a band are inside {5} of them.": (
        "Dva systémy se rozliší, když jeden poráží druhý aspoň v {0} převzorkování. Ten podíl je "
        "odhadnutý z {1} tahů a nese vlastní směrodatnou chybu <strong>{2}</strong>, takže "
        "porovnání, které padne do několika takových chyb od prahu, rozhodl práh, ne důkaz. "
        "{3} ze {4} porovnání, která můžou o pásmu rozhodnout, leží uvnitř {5} z nich."
    ),
    "Provider": "Poskytovatel",
    # The one instrument label with no Czech. The blurb directly above the
    # table already calls it "rubrika TN-Eval"; the column group tag and the
    # Beats-outright header printed the English six times beside it.
    "TN-Eval rubric": "rubrika TN-Eval",
    # A proper name, so it does not change -- but it is drawn on the Czech
    # page and the dictionary is the record of what was considered. Without
    # the entry the check cannot tell "left in English on purpose" from
    # "nobody looked".
    "iCARE": "iCARE",
    "The endpoint that served the model. The same id on two endpoints can be two different"
    " builds.": (
        "Endpoint, který model obsloužil. Totéž id na dvou endpointech mohou být dvě různá "
        "sestavení."
    ),
    "Marks": "Značky",
    "Conditions this row did not share with the others, and whether its judge shares a vendor"
    " with it.": (
        "Podmínky, které tenhle řádek nesdílel s ostatními, a jestli jeho hodnotitel sdílí "
        "dodavatele s ním."
    ),
    # The half a tooltip had no room for, in the legend under the table: what
    # the two badges in the Marks column mean, and that the heading does not
    # sort. It is the other column with no arrow on it.
    "A row marked ≠ settings ran under conditions the rest of the table did not, and the"
    " settings themselves are in the row's own detail, one tap below it. A row marked judge's"
    " own was scored by a judge from the same vendor as the model it graded; how much that is"
    " worth is measured on the methods page. {0} heading carries no ↕ and does not"
    " sort: these are labels, not an order.": (
        "Řádek se značkou ≠ nastavení běžel za podmínek, které zbytek tabulky neměl, a samotné "
        "nastavení je v detailu toho řádku, jedno klepnutí pod ním. Řádek se značkou "
        "stejný dodavatel jako hodnotitel znamená, že řádek obodoval hodnotitel od téhož "
        "dodavatele, jako je model, který "
        "známkoval; kolik to vydá, je změřeno na stránce s metodikou. {0} záhlaví ↕ a neřadí se "
        "podle něj: jsou to štítky, ne pořadí."
    ),
    # Only the tables with a ranking column have a Band heading to point at.
    # The iCARE tables do not, and the analogy sent a reader looking for it.
    "This": "U tohoto není",
    "Effort": "Úsilí",
    "A model that takes a reasoning-effort setting carries it beside its name. It is the effort"
    " the note was written at, not a score, and a model with no badge has no such control — which"
    " is not the same as one set to low.": (
        "Model, který má nastavitelné úsilí na uvažování, ho nese vedle svého jména. Je to úsilí, "
        "se kterým byl zápis napsán, ne skóre, a model bez značky takové nastavení nemá — což "
        "není totéž jako mít ho na nízké."
    ),
    "reasoning effort the note was written at": "úsilí na uvažování, se kterým byl zápis napsán",
    "judge cannot be checked against people": "hodnotitele nelze ověřit proti lidem",
    "both": "oba",
    "Keep this judge's figures and add, beside each one, how far the other judge was from it."
    " Nothing is averaged: the second number is the other judge's own score, written as a"
    " distance.": (
        "Ponechá čísla tohoto hodnotitele a k každému připíše, jak daleko od něj byl ten "
        "druhý. Nic se neprůměruje: to druhé číslo je vlastní skóre druhého hodnotitele, "
        "napsané jako vzdálenost."
    ),
    # The same thing, above the cells it applies to and only while they carry a
    # second figure. The button explained itself in a `title=`, so tapping it on
    # a phone sprinkled a triangle and a number into every one of seventeen
    # columns with nothing anywhere saying what they were.
    "Every figure now carries a second one: how far <code>{0}</code> was from this judge on the"
    " same row. Nothing is averaged — ▴ is the other judge scoring it higher and ▾ lower, and"
    " the number is the distance between the two.": (
        "Každé číslo teď nese ještě druhé: jak daleko od tohoto hodnotitele byl na témž řádku "
        "<code>{0}</code>. Nic se neprůměruje — ▴ znamená, že druhý hodnotitel dal víc, ▾ že "
        "míň, a to číslo je vzdálenost mezi nimi."
    ),
    "<strong>Sources:</strong> {0} — every prompt and rubric here is reproduced verbatim"
    ' from them. <a href="methods.html#licences">What each is used for, and on what terms</a>:'
    " three of them publish no licence at all, and a fourth shows only a badge.": (
        "<strong>Zdroje:</strong> {0} — každý zdejší prompt i rubrika jsou z nich "
        'převzaté doslova. <a href="methods.html#licences">K čemu se každý používá a za '
        "jakých podmínek</a>: tři z nich nezveřejňují žádnou licenci a čtvrtý ukazuje jen "
        "odznak."
    ),
    "The instrument is reproduced verbatim, anchors included, so a score here answers the"
    " published question and not a rewritten one.": (
        "Nástroj je převzatý doslova včetně kotev, takže zdejší skóre odpovídá na "
        "publikovanou otázku, ne na přepsanou."
    ),
    "the nine attributes and their anchors, eight of which are scored": (
        "devět atributů a jejich kotvy, z nichž osm se hodnotí"
    ),
    # -- what the corpus is and what a note is, above each table -------------
    "TN-Eval SOAP": "TN-Eval SOAP",
    "This track. A model reads a counselling transcript and writes a SOAP note; TN-Eval's"
    " published rubric then scores it. Named after the paper the prompt and the rubric are taken"
    " from.": (
        "Tato větev. Model si přečte přepis poradenského rozhovoru a napíše zápis SOAP; ten "
        "pak obodovala publikovaná rubrika TN-Evalu. Pojmenováno podle článku, ze kterého "
        "pochází prompt i rubrika."
    ),
    "The transcripts": "Přepisy",
    "AnnoMI: 133 publicly released motivational-interviewing sessions, transcribed and annotated"
    " by therapists. They are demonstration sessions, not recordings of clinical practice."
    " 50 are scored here.": (
        "AnnoMI: 133 veřejně vydaných motivačních rozhovorů, přepsaných a anotovaných terapeuty. "
        "Jsou to ukázková sezení, ne záznamy klinické praxe. Hodnotí se z nich 50."
    ),
    "SOAP note": "Zápis SOAP",
    "The standard clinical note format: subjective, objective, assessment, plan. Every model"
    " writes into the same four headings.": (
        "Standardní formát klinického zápisu: subjektivní, objektivní, hodnocení, plán. "
        "Všechny modely píší do týchž čtyř nadpisů."
    ),
    "PDSQI-9": "PDSQI-9",
    "A published instrument for rating how a clinical note is written, validated on real"
    " records with physicians doing the rating.": (
        "Publikovaný nástroj na hodnocení toho, jak je klinický zápis napsaný, ověřený na "
        "skutečné dokumentaci s lékaři jako hodnotiteli."
    ),
    "iCARE / iHOPE": "iCARE / iHOPE",
    "This track. A model fills in a 17-field clinical form from a counselling transcript, and"
    " its answers are compared with the form an expert clinician filled in from the same"
    " session. One project under two names: released as iCARE, renamed iHOPE in the preprint.": (
        "Tato větev. Model vyplní z přepisu poradenského rozhovoru klinický formulář o 17 "
        "polích a jeho odpovědi se porovnají s formulářem, který z téhož sezení vyplnil "
        "expertní klinik. Jeden projekt pod dvěma jmény: vydán jako iCARE, v preprintu "
        "přejmenován na iHOPE."
    ),
    "The sessions": "Sezení",
    "40 counselling demonstrations, each with one form an expert clinician filled in from it"
    " afterwards -- not the clinician who conducted it, who is not part of this corpus. That"
    " form is the answer key, not an entry.": (
        "40 ukázkových poradenských sezení, u každého jeden formulář, který z něj dodatečně "
        "vyplnil expertní klinik — ne ten, kdo sezení vedl; ten součástí korpusu není. Ten "
        "formulář je klíč k odpovědím, ne soutěžící."
    ),
    "The form": "Formulář",
    "17 fields to fill in rather than a note to write, so a blank field is a different thing"
    " from a short sentence.": (
        "17 políček k vyplnění místo zápisu k napsání, takže prázdné políčko je něco jiného "
        "než krátká věta."
    ),
    # No column ranks it, and the rows are alphabetical until the comparison
    # that could order them has been tested. Not "nothing to order them by":
    # that was said, and it was not true.
    # The other two reasons a track carries no ranking column. All three used
    # to be the sentence above, which is a statement about the iCARE paper and
    # was drawn under the Czech and PDSQI tables as well.
    "{0} · notes answered": "{0} · zodpovězených zápisů",
    "mean words per note": "průměrný počet slov na zápis",
    # -- what a note here is scored against -----------------------------------
    "the human note competes": "lidský zápis soutěží",
    "the human note is the answer key": "lidský zápis je vzorem",
    "judge checked against people": "hodnotitel ověřen proti lidem",
    "Scored against": "Hodnoceno proti",
    "Where the human note sits": "Kde stojí lidský zápis",
    "Can the judge be checked?": "Lze hodnotitele ověřit?",
    # -- the switch, the footer, the empty page -------------------------------
    "Track": "Větev",
    "Judge": "Hodnotitel",
    "older harness": "starší harness",
    "Every score in these tables is generated from <code>results/{0}</code>, which is"
    " append-only: a re-run adds rows beside the old ones rather than replacing them, and what"
    " is drawn here is the newest of each. Two things beside them are not from that file: the"
    " Band column and its bootstrap, and the judge-against-therapist figures under the table,"
    " both computed from the judge's individual answers.": (
        "Každé skóre v těchto tabulkách je vygenerováno ze souboru <code>results/{0}</code>, do "
        "kterého se jen přidává: opakovaný běh přidá řádky vedle starých, místo aby je nahradil, "
        "a kreslí se tu z každého ten nejnovější. Dvě věci vedle nich z toho souboru nejsou: "
        "sloupec Pásmo i jeho bootstrap a čísla o shodě hodnotitele s terapeutem pod tabulkou — "
        "obojí se počítá z jednotlivých odpovědí hodnotitele."
    ),
    # Leading space, like the English fragment it replaces: it joins onto the
    # sentence before it and the key it is found by was trimmed.
    # The rank is named on the *measure*, not on the drawn table: the iCARE
    # rows are alphabetical, so "13. v této tabulce" sent a reader counting to a
    # row that holds somebody else.
    "— <code>{0}</code> furthest, {1}{2} on {3} under this judge and {4}{5} under that one": (
        " — nejdál <code>{0}</code>, {1}{2} na sloupci {3} u tohoto hodnotitele a {4}{5} "
        "u toho druhého"
    ),
    "<strong>The two judges agree on the shape of this ranking and not on its order.</strong> On"
    " {0}, {1} of {2} systems land somewhere else under <code>{3}</code>{4}{5}{6}": (
        "<strong>Oba hodnotitelé se shodnou na tvaru tohoto pořadí, ne na konkrétním sledu "
        "příček.</strong> Na sloupci {0} se pod hodnotitelem <code>{3}</code> umístí jinam {1} "
        "z {2} systémů{4}{5}{6}"
    ),
    "— so the top and the bottom are claims this table supports; adjacent places are not.": (
        " — blízko vrcholu a blízko dna jsou tvrzení, která tato tabulka unese; sousední místa ne."
    ),
    # Drawn instead of the clause above where the table has no ranking column,
    # because there it would contradict the sentence directly above it.
    "No runs yet": "Zatím žádný běh",
    "The first run will populate this page.": "První běh tuto stránku naplní.",
    # -- what a row is, when it is not a model --------------------------------
    "therapist": "terapeut",
    "reference model": "referenční model",
    "as published": "jak bylo publikováno",
    # -- Czech writes every ordinal `4.`; see `ordinal` in the helpers --------
    "{ordinal-suffix}": ".",
}


#: Strings that reach the pages inside ``docs/leaderboard.json``: track titles
#: and blurbs, what each track scores a note against, and every column's
#: heading, definition and caveat. Authored in the scorers and in ``report.py``,
#: where the number they describe is computed.
_PAYLOAD = {
    # PDSQI-9's own row note, drawn now that the instrument has a table of its
    # own; it sat on rows the merged table never showed.
    "PDSQI-9, adapted: see docs/landscape.md. Physicians agree with each other on this"
    " instrument at Krippendorff's alpha 0.575, which is the ceiling these columns are read"
    " against -- no human has rated these notes on it.": (
        "PDSQI-9, upravený: viz docs/landscape.md. Lékaři se na tomto nástroji mezi sebou "
        "shodují na Krippendorffově alfě 0.575, což je strop, proti němuž se tyto sloupce "
        "čtou — tyto zápisy na něm žádný člověk nehodnotil."
    ),
    # -- track titles and blurbs ---------------------------------------------
    "iCARE form on the iHOPE corpus · 17 sections per session": (
        "Formulář iCARE na korpusu iHOPE · 17 oddílů na sezení"
    ),
    # The two blurbs a merged table hides. `_merge_instruments` draws the rubric
    # and PDSQI-9 as one table with one blurb, so these are what a reader sees
    # when a run has only one of the two -- which is every run before the other
    # instrument has been asked.
    "Reference-free. 23 completeness criteria, conciseness scored sentence by sentence,"
    " faithfulness against the full transcript.": (
        "Bez referenčního zápisu. 23 kritérií úplnosti, stručnost bodovaná větu po větě, "
        "věrnost proti celému přepisu."
    ),
    "A published instrument asked about the same notes as the TN-Eval SOAP track: the SOAP notes"
    " written from the 50 AnnoMI conversations. Not a third corpus -- one corpus, two"
    " instruments, so the two tables can be read against each other. Eight attributes, reported"
    " separately and never averaged, because the instrument reports them that way and because"
    " one of the eight is a 0-1 column: a mean over it and seven 1-5 scales would be a number"
    " with no unit.": (
        "Publikovaný nástroj položený na tytéž zápisy jako větev TN-Eval SOAP: na zápisy SOAP "
        "napsané z 50 rozhovorů AnnoMI. Není to třetí korpus — jeden korpus, dva nástroje, aby "
        "se ty dvě tabulky daly číst proti sobě. Osm atributů, vykazovaných zvlášť a nikdy "
        "neprůměrovaných, protože je tak vykazuje sám nástroj a protože jeden z těch osmi je "
        "sloupec 0-1: průměr přes něj a přes sedm škál 1-5 by bylo číslo bez jednotky."
    ),
    "Automatic metrics and a TRACE judge side by side, because the source paper found they"
    " disagree. That disagreement is a result, not an error. iCARE and iHOPE are one project"
    " under two names: the code was released as iCARE in April 2025 and the preprint renamed it"
    " iHOPE in August 2026, sixteen months later. **PDSQI-9 has no columns here**, and that is"
    " deliberate rather than missing: it rates how a clinical note is written, and these are 17"
    " form fields rather than a written note. It runs on the SOAP notes, where it can be read"
    " against the rubric that scores the same text.": (
        "Automatické metriky a hodnotitel TRACE vedle sebe, protože zdrojový článek zjistil, že "
        "si odporují. Ten rozpor je výsledek, ne chyba. iCARE a iHOPE jsou jeden projekt pod "
        "dvěma jmény: kód vyšel jako iCARE v dubnu 2025 a preprint jej v srpnu 2026, o šestnáct "
        "měsíců později, přejmenoval na iHOPE. **PDSQI-9 tu nemá žádné sloupce**, a to záměrně, "
        "ne omylem: hodnotí, jak je klinický zápis napsán, a tohle je 17 polí formuláře, ne "
        "napsaný zápis. Běží na zápisech SOAP, kde se dá číst proti rubrice, která boduje týž "
        "text."
    ),
    "TN-Eval SOAP": "TN-Eval SOAP",
    "iCARE / iHOPE": "iCARE / iHOPE",
    # -- what a note is scored against ----------------------------------------
    "The transcript and a 23-item rubric. There is no gold note to copy, so any new model can be"
    " measured without anyone writing one.": (
        "Přepis a rubrika o 23 položkách. Není tu žádný zlatý zápis ke zkopírování, takže "
        "libovolný nový model lze změřit, aniž by ho někdo musel napsat."
    ),
    "The therapist's note is scored by the identical protocol and sits in the table as its own"
    " row. It is a competitor, not the answer key.": (
        "Terapeutův zápis je obodován týmž protokolem a stojí v tabulce jako vlastní řádek. Je "
        "to soutěžící, ne vzor."
    ),
    "TN-Eval released 150 notes that two therapists had already rated -- 50 written by a"
    " therapist, 50 by Llama 3.1 70B, 50 by Mistral Large V2. Every judge here answers those same"
    " questions about those same notes first, so how far it agrees with a person is a published"
    " number and not a hope.": (
        "TN-Eval zveřejnil 150 zápisů, které už dva terapeuti ohodnotili — 50 napsal terapeut, "
        "50 Llama 3.1 70B a 50 Mistral Large V2. Každý zdejší hodnotitel nejdřív odpoví na tytéž "
        "otázky o týchž zápisech, takže to, jak moc se shoduje s člověkem, je publikované číslo, "
        "a ne naděje."
    ),
    "An expert note written from the session by a clinician who was not in it. ROUGE-L and"
    " BERTScore measure how closely the model reproduced it; TRACE asks a judge to rate the note"
    " itself, the way the paper's experts did.": (
        "Expertní zápis, který ze sezení napsal klinik, jenž u něj nebyl. ROUGE-L a BERTScore "
        "měří, jak těsně jej model zreprodukoval; TRACE žádá hodnotitele, aby ohodnotil samotný "
        "zápis, tak jako to dělali experti v tom článku."
    ),
    # The one tick box on the leaderboard. It reaches the page through `tr()`
    # like everything else, but it is a constant rather than a tagged sentence,
    # so the scanner that finds untranslated text never looked at it and it
    # would have drawn in English on a Czech page the first time a row of that
    # type appeared.
    "Show numbers as published (different harness — never ranked with ours)": (
        "Ukázat čísla tak, jak byla publikována (jiný harness — nikdy se neřadí s našimi)"
    ),
    "The expert note is the answer key and never competes. In the source paper the experts"
    " compared models with each other -- a smaller Mistral was preferred over the model leading"
    " on the automatic metrics -- and the expert note was what those metrics measured against,"
    " not an entry.": (
        "Expertní zápis je vzor a nikdy nesoutěží. Ve zdrojovém článku experti srovnávali modely "
        "mezi sebou — menšímu Mistralu dali přednost před modelem, který vedl v automatických "
        "metrikách — a expertní zápis byl to, proti čemu se ty metriky měřily, ne soutěžící."
    ),
    "Not possible here. The authors' expert ratings are not in the public repository, so there is"
    " nothing to check this judge against. Two independent judges score every note instead, and"
    " where they disagree is the only control this track can have.": (
        "Tady to nejde. Expertní hodnocení autorů nejsou ve veřejném repozitáři, takže není proti "
        "čemu tohoto hodnotitele ověřit. Místo toho každý zápis boduje dvojice nezávislých "
        "hodnotitelů a to, kde se neshodnou, je jediná kontrola, kterou tato větev mít může."
    ),
    # -- the rubric's three columns -------------------------------------------
    "Completeness": "Úplnost",
    "completeness": "úplnost",
    "The equal-weighted mean of the note's four SOAP section fractions. Per section, the fraction"
    " of that section's criteria the judge found present.": (
        "Rovnoměrný průměr čtyř oddílových podílů zápisu podle SOAP. V rámci oddílu je to podíl "
        "kritérií daného oddílu, která hodnotitel našel přítomná."
    ),
    # Keyed by the *formatted* English: `report.column_meta` fills `{criteria}`
    # from the rubric before the caveat reaches the payload, so 23 is in the key
    # the same way "temperature 0, max tokens 4096" is further down this file.
    # The item count is interpolated in Python before the string reaches the
    # payload, so the key carries `23` and not a hole.
    "Counts coverage of a checklist, not judgement. All 23 rubric items are asked of every note,"
    " whatever the session was about, so an item the session never called for counts as absent"
    " exactly like one the note forgot. The figure is the equal-weighted mean of the note's four"
    " section fractions, not the fraction of all 23 items, so a four-item section counts as much"
    " as an eight-item one. This is the column the table is ordered by.": (
        "Počítá pokrytí seznamu položek, ne úsudek. Všech 23 položek rubriky se ptá u každého "
        "zápisu, ať bylo sezení o čemkoli, takže položka, kterou si sezení nikdy nevyžádalo, se "
        "počítá jako chybějící stejně jako ta, na kterou zápis zapomněl. To číslo je rovnoměrný "
        "průměr čtyř oddílových podílů zápisu, ne podíl ze všech 23 položek — čtyřpoložkový "
        "oddíl tedy váží stejně jako osmipoložkový. Podle tohoto sloupce je tabulka seřazena."
    ),
    # The computed half of that caveat, authored in the leaderboard's script
    # because its two figures are read off the table the sentence is printed
    # under. Kept here beside the caveat rather than with the other sentences:
    # a translator changing one of them has to see the other.
    "On the table above, the highest {0} is {1} out of a possible 1.00.": (
        "V tabulce výše je nejvyšší {0} {1} z možných 1.00."
    ),
    # The clinician's own figure rather than their row number: a row number is
    # read off the order the table happens to be drawn in, and stops being true
    # the moment a reader clicks a column heading.
    "On the table above, the highest {0} is {1} out of a possible 1.00, and the note a human"
    " clinician wrote scores {2} by the same rule.": (
        "V tabulce výše je nejvyšší {0} {1} z možných 1.00 a zápis, který napsal člověk-klinik, "
        "má podle téhož pravidla {2}."
    ),
    "Conciseness": "Stručnost",
    "Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is"
    " off-topic; it does not mean the note is short.": (
        "Podíl vět zápisu, které odpovídají aspoň jedné položce rubriky. 1.00 znamená, že nic "
        "není mimo téma; neznamená to, že je zápis krátký."
    ),
    "Not a length measure, despite the name: a note twice as long scores the same if every"
    " added sentence is on topic. It is also the measure most moved by the judge's own settings"
    " -- raising the thinking budget from 128 to 256 tokens shifted all nineteen systems and"
    " reordered sixteen of them. The higher budget is what the table above is scored at; it was"
    " the budget-128 rows it was compared against that are gone -- not in results/rows.jsonl in"
    " any revision and not re-derivable, see docs/limitations.md.": (
        "Navzdory jménu to není míra délky: dvakrát delší zápis dostane stejné skóre, pokud je "
        "každá přidaná věta k tématu. Je to také míra, kterou nejvíc hýbe vlastní nastavení "
        "hodnotitele — zvednutí rozpočtu na přemýšlení ze 128 na 256 tokenů posunulo všech "
        "devatenáct systémů a u šestnácti z nich změnilo pořadí. Vyšší rozpočet je ten, na kterém "
        "je obodovaná tabulka výše; chybí ta druhá polovina — řádky s rozpočtem 128, proti "
        "kterým se srovnávalo, nejsou v results/rows.jsonl v žádné revizi a nedají se odvodit, "
        "viz docs/limitations.md."
    ),
    "Faithfulness": "Věrnost",
    "Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies."
    " TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert"
    " scale.": (
        "Zda zápis odporuje přepisu, hodnoceno 1 až 5, kde 5 je bez nepřesností. Protokol "
        "TN-Eval nemá verzi této otázky založenou na kritériích, takže zůstává Likertovou "
        "škálou."
    ),
    "A different scale from the two columns beside it, and a weak one: TN-Eval published"
    " Krippendorff's alpha 0.18 between its two therapist annotators on this rating, and"
    " recomputing it here from their released annotations gives the same. Read it as a flag for"
    " gross invention, not as a ranking.": (
        "Jiná škála než u dvou sloupců vedle, a slabá: TN-Eval zveřejnil mezi svými dvěma "
        "terapeuty-anotátory na tomto hodnocení Krippendorffovu alfu 0.18 a přepočet zde "
        "z jejich zveřejněných anotací dává totéž. Čtěte to jako signál hrubého výmyslu, ne "
        "jako pořadí."
    ),
    # -- PDSQI-9 ---------------------------------------------------------------
    "Accurate": "Přesnost",
    "The note is true and free of incorrect information. PDSQI-9 item 2, rated 1 (not at all) to"
    " 5 (extremely).": (
        "Zápis je pravdivý a bez nesprávných informací. PDSQI-9, položka 2, hodnoceno 1 (vůbec) "
        "až 5 (zcela)."
    ),
    "The instrument was validated on multi-note clinical summaries from a corpus that excluded"
    " psychiatry, not on notes written from a single session. Its authors report Krippendorff's"
    " alpha 0.575 between trained physicians on that material -- a published ceiling, not a"
    " measurement of this judge on these notes.": (
        "Nástroj byl validován na klinických souhrnech z několika zápisů, z korpusu, který "
        "psychiatrii vylučoval, ne na zápisech z jednoho sezení. Jeho autoři uvádějí mezi "
        "školenými lékaři na tomto materiálu Krippendorffovu alfu 0.575 — je to publikovaný "
        "strop, ne měření tohoto hodnotitele na těchto zápisech."
    ),
    "{0} columns": "Sloupce {0}",
    "Thorough": "Důkladnost",
    "The note should thoroughly cover all critical patient issues. PDSQI-9 item 3, rated 1 (not"
    " at all) to 5 (extremely).": (
        "Zápis by měl důkladně pokrýt všechny kritické potíže pacienta. PDSQI-9, položka 3, "
        "hodnoceno 1 (vůbec) až 5 (zcela)."
    ),
    "Useful": "Užitečnost",
    "All the information is in there that is useful to the target provider/intended audience. The"
    " note is extremely relevant, providing valuable information and/or analysis. PDSQI-9 item 4,"
    " rated 1 (not at all) to 5 (extremely).": (
        "Zápis obsahuje všechny informace, které jsou užitečné cílovému poskytovateli péče / "
        "zamýšlenému "
        "čtenáři. Zápis je krajně relevantní a přináší cennou informaci a/nebo analýzu. "
        "PDSQI-9, položka 4, hodnoceno 1 (vůbec) až 5 (zcela)."
    ),
    "Organized": "Uspořádanost",
    "The note is well-formed and structured in a way that helps the reader understand the"
    " patient's clinical course. PDSQI-9 item 5, rated 1 (not at all) to 5 (extremely).": (
        "Zápis je dobře utvořený a strukturovaný tak, aby čtenáři pomohl porozumět klinickému "
        "průběhu u pacienta. PDSQI-9, položka 5, hodnoceno 1 (vůbec) až 5 (zcela)."
    ),
    "Comprehensible": "Srozumitelnost",
    "The note is clear, without ambiguity or sections that are difficult to understand. PDSQI-9"
    " item 6, rated 1 (not at all) to 5 (extremely).": (
        "Zápis je jasný, bez dvojznačností a bez pasáží, kterým je těžké porozumět. PDSQI-9, "
        "položka 6, hodnoceno 1 (vůbec) až 5 (zcela)."
    ),
    "Succinct": "Úspornost",
    "The note is brief, to the point, and without redundancy. PDSQI-9 item 7, rated 1 (not at"
    " all) to 5 (extremely).": (
        "Zápis je krátký, věcný a bez nadbytečností. PDSQI-9, položka 7, hodnoceno 1 (vůbec) až "
        "5 (zcela)."
    ),
    "Synthesized": "Syntéza",
    "The note reflects an understanding of the patient's status and ability to develop a plan of"
    " care. PDSQI-9 item 8, rated 1 (not at all) to 5 (extremely).": (
        "Zápis odráží porozumění stavu pacienta a schopnost vytvořit plán péče. PDSQI-9, "
        "položka 8, hodnoceno 1 (vůbec) až 5 (zcela)."
    ),
    "Free of stigmatizing language": "Bez stigmatizujícího jazyka",
    "The note is free of discrediting or exaggerated words, of judgment or labelling, and uses"
    " person-first language. PDSQI-9 item 9, answered yes or no and reported as the fraction of"
    " notes free of it.": (
        "Zápis je prostý znevažujících či přehnaných slov, soudů a nálepkování a mluví nejdřív "
        "o člověku. PDSQI-9, položka 9, odpověď ano/ne, vykázáno jako podíl zápisů, které jsou "
        "ho prosté."
    ),
    # -- the iCARE columns ------------------------------------------------------
    "ROUGE-L": "ROUGE-L",
    "Longest-common-subsequence overlap with the expert note, F-measure. Rewards using the same"
    " words in the same order.": (
        "Překryv s expertním zápisem podle nejdelší společné podposloupnosti, F-míra. Odměňuje "
        "užití týchž slov v témže pořadí."
    ),
    "Not the source paper's ROUGE-L and not comparable with their published table. Theirs"
    " compares the whole rendered note, which puts our own field labels and every Nil the"
    " expert wrote on both sides -- a note where the model wrote nothing at all scores 0.379 that"
    " way, above most real notes. This compares the field values of the sections the expert"
    " answered, where the same empty note scores 0.000, and every model's figure fell by about a"
    " third. It also cannot tell a good paraphrase from a wrong answer, and the source paper"
    " found it disagrees with what clinicians preferred.": (
        "Není to ROUGE-L ze zdrojového článku a s jejich publikovanou tabulkou to není "
        "srovnatelné. Ta jejich srovnává celý vykreslený zápis, což staví naše vlastní názvy "
        "polí a každé Nil, které expert napsal, na obě strany — zápis, do kterého model "
        "nenapsal vůbec nic, tak boduje 0.379, výš než většina skutečných zápisů. Tady se "
        "srovnávají hodnoty polí těch oddílů, které expert vyplnil; tentýž prázdný zápis tam "
        "boduje 0.000 a číslo každého modelu kleslo asi o třetinu. Metrika také neodliší dobrou "
        "parafrázi od špatné odpovědi a zdrojový článek zjistil, že si odporuje s tím, čemu "
        "dávali přednost kliničtí experti."
    ),
    "BERTScore": "BERTScore",
    "Embedding similarity to the expert note. Tolerates paraphrase.": (
        "Podobnost embeddingů s expertním zápisem. Snese parafrázi."
    ),
    "A fluent note about the wrong session still scores well.": (
        "Plynulý zápis o špatném sezení boduje pořád dobře."
    ),
    "TRACE": "TRACE",
    "Trustworthiness, relevance, accuracy, comprehensiveness and expression, each rated 1-5 by a"
    " judge and averaged.": (
        "Důvěryhodnost, relevance, přesnost, komplexnost a vyjadřování, každé hodnoceno "
        "hodnotitelem 1–5 a zprůměrováno."
    ),
    "A re-implementation with no human anchor: the authors never published their ratings, so"
    " unlike the TN-Eval track this number is not calibrated against anybody.": (
        "Reimplementace bez lidské kotvy: autoři svá hodnocení nikdy nezveřejnili, takže na "
        "rozdíl od větve TN-Eval není toto číslo zkalibrováno proti nikomu."
    ),
    "Looks back": "Ohlédnutí zpět",
    "Section 5 only -- what happened in the previous session. The fraction of the 34 sessions"
    " whose expert note answered it where the model did too.": (
        "Jen oddíl 5 — co se stalo na minulém sezení. Podíl z 34 sezení, jejichž expertní zápis "
        "na něj odpověděl, kde odpověděl i model."
    ),
    "Kept out of any average. Every model scores 0.97-1.00 here, so this column separates nobody"
    " -- it is shown because its twin does.": (
        "Drženo mimo jakýkoli průměr. Každý model tu boduje 0.97–1.00, takže tento sloupec "
        "nikoho neodliší — je vidět proto, že jeho dvojče ano."
    ),
    "Looks forward": "Výhled dopředu",
    "Section 17 only -- what happens at the next session. The fraction of the 11 sessions whose"
    " expert note answered it where the model did too.": (
        "Jen oddíl 17 — co bude na příštím sezení. Podíl z 11 sezení, jejichž expertní zápis na "
        "něj odpověděl, kde odpověděl i model."
    ),
    "This is where the source paper reports every model it tested failing, and ours do too: 0.00"
    " to 0.55. Reported apart from its twin because averaging the two turned 1.00 and 0.09 into"
    " 0.78 and hid exactly this.": (
        "Právě tady zdrojový článek hlásí selhání každého modelu, který testoval, a ty naše "
        "selhávají také: 0.00 až 0.55. Vykazuje se odděleně od svého dvojčete, protože průměr "
        "těch dvou udělal z 1.00 a 0.09 hodnotu 0.78 a zakryl přesně tohle."
    ),
    # -- row notes, settings, sections and failure reasons ---------------------
    "faithfulness is a Likert rating; TN-Eval measured weak human agreement on it -- see"
    " docs/limitations.md": (
        "věrnost je Likertovo hodnocení; TN-Eval na ní naměřil slabou shodu mezi lidmi — viz "
        "docs/limitations.md"
    ),
    "TRACE is a re-implementation with no human anchor -- the authors never published their"
    " ratings. See docs/limitations.md": (
        "TRACE je reimplementace bez lidské kotvy — autoři svá hodnocení nikdy nezveřejnili. "
        "Viz docs/limitations.md"
    ),
    "temperature 0, max tokens 4096": "teplota 0, max tokenů 4096",
    "temperature 0, max tokens 16384": "teplota 0, max tokenů 16384",
    "effort medium, temperature 1 (forced by the provider), max tokens 4096": (
        "úsilí medium, teplota 1 (vynuceno poskytovatelem), max tokenů 4096"
    ),
    "answer did not contain a SOAP dictionary": "odpověď neobsahovala slovník SOAP",
    "answer was not a note": "odpověď nebyla zápis",
    "empty content": "prázdná odpověď",
    "unreadable cache file": "nečitelný soubor v cache",
    "truncated at max_tokens=16384": "uťato na max_tokens=16384",
    "subjective": "subjektivní",
    "objective": "objektivní",
    "assessment": "hodnocení",
    "plan": "plán",
}


#: The methods page: its panels are the instrument, and every one of them is
#: prose this project wrote. What it *quotes* -- TN-Eval's prompt and rubric,
#: iCARE's field names -- is not here and is not translated: a Czech paraphrase
#: of an instruction would show a reader something no model was ever given.
_METHODS = {
    "methods.title": "therapy-note-bench — jak se to měřilo",
    "methods.h1": "Jak se to měřilo",
    "methods.sub": (
        'Nástroj, který stojí za <a href="index.html">žebříčkem</a>: který hodnotitel, ověřený '
        "proti komu, na kterých korpusech a v čem se ti dva hodnotitelé neshodnou. "
        '<a href="https://github.com/JanNehyba/therapy-note-bench">Zdroj a metoda</a>.'
    ),
    "methods.calibration.h2": "Kalibrace hodnotitele",
    "methods.calibration.pending": (
        "Než se kterémukoli zdejšímu číslu začne věřit, hodnotitel se obodová proti dvěma "
        "lidským anotátorům, které TN-Eval zveřejnil, a shoda se objeví tady — i když bude "
        "špatná. <strong>Zatím nezměřeno.</strong>"
    ),
    "methods.judges.summary": (
        "<strong>Proč zrovna tito dva hodnotitelé, a ne ty nejnovější modely</strong>"
    ),
    "methods.saturation.summary": "<strong>Zbývá vůbec co měřit?</strong>",
    "methods.ordering.summary": (
        "<strong>Jak je každá tabulka seřazená a co by udělaly jiné váhy</strong>"
    ),
    "methods.groups.summary": ("<strong>Která porovnání přežijí převzorkování rozhovorů</strong>"),
    "methods.saturation.figure": (
        "Jak velkou část rozsahu každé míry modely skutečně obsadí. Vlevo: jeden pruh na každé "
        "kritérium rubriky, od nejhoršího modelu k nejlepšímu, s vyznačeným terapeutem. Vpravo: "
        "totéž čtení TRACE, kde jeden pruh jsou všechny modely najednou. Kreslí "
        "<code>tools/figures.py</code> ze souborů jmenovaných v patičce obrázku. "
        "<strong>Obrázek sám je vysázený anglicky.</strong> V jeho legendě: "
        "<em>every model does it</em> = zvládají to všechny modely, "
        "<em>separates models</em> = rozlišuje modely, "
        "<em>partly</em> = zčásti, "
        "<em>nobody does it</em> = nezvládá to nikdo; a <em>% of the scale</em> je, "
        "jakou část rozsahu míry modely obsadí."
    ),
    "methods.protocol.summary": ("<strong>Co je tady zápis a proti čemu se hodnotí?</strong>"),
    "methods.design.summary": (
        "<strong>S čím každá větev zápis porovnává a jestli jde její hodnotitel ověřit</strong>"
    ),
    "methods.corpora.summary": (
        "<strong>Co jsou ty dva korpusy a jak velkou část formuláře experti vyplnili</strong>"
    ),
    "methods.licences.summary": ("<strong>Odkud pochází každý vstup a za jakých podmínek</strong>"),
    "methods.brief-link": (
        '<a href="brief.html">Jak číst tyto výsledky →</a> '
        "Čtyři tvrzení, která tabulky unesou, a čtyři, která ne, i se souborem, ze kterého "
        "každé číslo pochází."
    ),
    "methods.foot.columns": (
        "U <strong>věrnosti</strong> je lidská shoda téměř nulová — TN-Eval naměřil mezi "
        "školenými terapeuty Krippendorffovu alfu 0.18 — a <strong>TRACE</strong> je "
        "reimplementace <em>bez lidské kotvy</em>. Rozsah každého sloupce, co počítá a jak se "
        'nesmí číst, stojí pod jeho vlastní tabulkou na <a href="index.html">žebříčku</a>.'
    ),
    "methods.foot.provider": (
        "Štítek za názvem modelu je <strong>poskytovatel</strong>, který ho obsluhoval. Totéž "
        "id modelu u dvou poskytovatelů může znamenat dvě různá sestavení — jiná kvantizace, "
        "jiné "
        "váhy, jiný systémový prompt — proto jsou tam vždy dva řádky, nikdy jeden."
    ),
    "methods.foot.comparability": (
        "Řádky se srovnávají jedině tehdy, když se shodují ve všech šesti: větev, verze "
        "harnessu, verze promptu, hodnoticí model, verze hodnoticího promptu a "
        "<strong>nastavení, ve kterém hodnotitel běžel</strong>. Změněný hodnotitel — nebo "
        "hodnotitel s jiným rozpočtem na přemýšlení — zakládá novou tabulku, místo aby přepsal "
        "tuhle. Skupina, která jmenuje hodnotitele a neumí říct, jak byl nastaven, se stahuje: "
        "dva řádky, které oba nezaznamenávají nic, tím ještě nejsou týž nástroj."
    ),
    # -- the interval plot ---------------------------------------------------
    "{0}: {1} over the shared conversations (95% interval {2} to {3})": (
        "{0}: {1} přes sdílené rozhovory (95% interval {2} až {3})"
    ),
    "— the table shows {0}, over the {1} notes the judge finished": (
        " — tabulka ukazuje {0}, přes {1} zápisů, které hodnotitel dokončil"
    ),
    "Completeness with 95% bootstrap intervals, best first": (
        "Úplnost s 95% bootstrapovými intervaly, nejlepší první"
    ),
    # -- the saturation panel -------------------------------------------------
    "discriminating": "rozlišuje",
    "saturated": "nasyceno",
    "mixed": "smíšeně",
    "unreachable": "nedosažitelné",
    "still separates models": "modely od sebe stále odděluje",
    "every model already does this": "tohle už zvládne každý model",
    "partly, weakly": "zčásti, slabě",
    "nobody can, the therapist included": "nedokáže to nikdo, terapeuta nevyjímaje",
    "{0} ({1}) — {2}": "{0} ({1}) — {2}",
    "{0}: models {1} to {2} percent": "{0}: modely {1} až {2} procent",
    "{0}: models {1}–{2}%": "{0}: modely {1}–{2} %",
    ", therapist {0}%": ", terapeut {0} %",
    "— not separable": "— nerozlišitelné",
    "On this evidence <strong>every system is distinguishable from every other</strong> — the"
    " benchmark has not run out of resolution yet.": (
        "Na této evidenci je <strong>každý systém odlišitelný od každého jiného</strong> — "
        "benchmarku zatím nedošlo rozlišení."
    ),
    "Left out of this section because they are still being scored: {0}. Including a half-scored"
    " system would shrink the shared corpus for everyone else.": (
        "Z tohoto oddílu vynecháno, protože se to ještě boduje: {0}. Zahrnout napůl obodovaný "
        "systém by zmenšilo sdílený korpus všem ostatním."
    ),
    "<strong>These numbers are not the table's numbers, and they should not be.</strong> The"
    ' <a href="index.html">leaderboard table</a> averages each system'
    " over its own notes; this section averages every system"
    " over the <strong>{0} of {1}</strong> conversations they <em>all</em> have, because a"
    " paired comparison is only paired on a shared set. The set is smaller because {2}. Expect"
    " small differences from the table, and expect closely-matched systems to change places:"
    " that two orderings disagree over which {3} of {4} conversations you use is itself a"
    " result"
    " about how tightly packed these models are.": (
        "<strong>Tato čísla nejsou čísla z tabulky, a ani být nemají.</strong> "
        '<a href="index.html">Tabulka žebříčku</a> průměruje každý systém přes jeho vlastní '
        "zápisy; tento oddíl průměruje každý systém "
        "přes <strong>{0} z {1}</strong> rozhovorů, které mají <em>všechny</em>, protože "
        "párové srovnání je párové jen na sdílené množině. Ta množina je menší proto, že {2}. "
        "Očekávejte drobné rozdíly oproti tabulce a očekávejte, že si těsně vyrovnané systémy "
        "prohodí místa: to, že se dvě uspořádání neshodnou podle toho, kterých {3} z {4} "
        "rozhovorů použijete, je samo o sobě výsledek o tom, jak nahusto tyto modely stojí."
    ),
    "{0} was scored on {1} fewer": "{0} byl obodován o {1} méně",
    "{0}, and the other {1} on {2}": "{0}, a zbývajících {1} o {2}",
    "one each": "jeden každý",
    "no more than {0} each": "po nejvýš {0}",
    "Computed from <code>{0}</code>'s individual answers{1}.": (
        "Spočteno z jednotlivých odpovědí hodnotitele <code>{0}</code>{1}."
    ),
    "at {0}": " při nastavení {0}",
    "The cache also held answers at other settings; they are two instruments and were not mixed"
    " in.": (
        "Cache držela i odpovědi z jiných nastavení; jsou to dva nástroje a nebyly do sebe míchány."
    ),
    "A ranking always prints an order. This asks whether the evidence supports one. Both parts"
    " read the individual judgements rather than the averages. The intervals below are over the"
    " <strong>{0} conversations every system has a finished judgement for</strong>; the criterion"
    " table underneath is over every conversation each system was scored on, which is why its"
    " figures match the leaderboard's and these do not.": (
        "Žebříček vždycky vytiskne nějaké pořadí. Tady se ptáme, jestli ho evidence unese. Obě "
        "části čtou jednotlivé soudy, ne průměry. Intervaly níže jsou přes <strong>{0} "
        "rozhovorů, u kterých má dokončený soud každý systém</strong>; tabulka kritérií pod nimi "
        "je přes všechny rozhovory, na kterých byl každý systém obodován — proto její čísla "
        "sedí se žebříčkem a tato ne."
    ),
    "Completeness over the shared conversations, with the range the evidence supports": (
        "Úplnost přes sdílené rozhovory, s rozpětím, které evidence unese"
    ),
    "95% intervals from a paired bootstrap over conversations — the same resample scores every"
    " system, so a hard conversation counts as difficulty rather than disagreement. The dashed"
    " line is the therapist. Hover a bar for the table's figure beside this one.": (
        "95% intervaly z párového bootstrapu přes rozhovory — týž převzorek boduje každý systém, "
        "takže těžký rozhovor se počítá jako obtížnost, ne jako neshoda. Čárkovaná čára je "
        "terapeut. Najeďte na pruh a uvidíte vedle tohoto čísla i to z tabulky."
    ),
    "Ranked, with systems the evidence cannot separate grouped on one line. These are groups,"
    " not equivalence classes: being inseparable is not transitive, so the boundary between"
    " adjacent lines is a convention.": (
        "Seřazeno, přičemž systémy, které evidence neoddělí, stojí na jednom řádku. Jsou to "
        "skupiny, ne třídy ekvivalence: nerozlišitelnost není tranzitivní, takže hranice mezi "
        "sousedními řádky je konvence."
    ),
    "What each rubric criterion is still doing": "Co které kritérium rubriky ještě dělá",
    "The bar spans lowest to highest model; the grey tick is the therapist. A bar pinned right"
    " means every model already satisfies it. A bar pinned left where the therapist is pinned"
    " left too means the question has no answer in a counselling transcript — that is a fact"
    " about the corpus, not about the models.": (
        "Pruh sahá od nejnižšího modelu k nejvyššímu; šedá ryska je terapeut. Pruh přilepený "
        "vpravo znamená, že to už splní každý model. Pruh přilepený vlevo tam, kde je vlevo "
        "přilepený i terapeut, znamená, že ta otázka v poradenském přepisu nemá odpověď — a to "
        "je fakt o korpusu, ne o modelech."
    ),
    "Criterion": "Kritérium",
    "Models, worst to best": "Modely, od nejhoršího k nejlepšímu",
    # -- the corpora ----------------------------------------------------------
    "Both corpora are transcripts of published demonstration sessions, not of clinical"
    " practice. Sizes are of the splits this benchmark actually scores; lengths are in words of"
    " transcript, which is what a model has to read.": (
        "Oba korpusy jsou přepisy publikovaných ukázkových sezení, ne klinické praxe. "
        "Velikosti jsou velikosti těch částí, které tento benchmark opravdu boduje; délky jsou "
        "ve slovech přepisu, což je to, co musí model přečíst."
    ),
    "Sessions": "Sezení",
    "Words / session (range)": "Slov na sezení (rozsah)",
    "Turns (range)": "Replik (rozsah)",
    "Words in the expert note": "Slov v expertním zápise",
    "temporal": "časové",
    "How much of the iCARE form has an answer at all": (
        "Jak velká část formuláře iCARE má vůbec odpověď"
    ),
    "Across the expert notes, <strong>{0} of {1} fields ({2}%)</strong> say something; the rest"
    " are <code>Nil</code>. A published counselling video has no hospital id and no referring"
    " clinician, so several fields cannot be answered by anyone. On those, a model scores by"
    " staying quiet rather than by writing a good note — read the low rows as <em>no signal</em>,"
    " not as a hard test.": (
        "Napříč expertními zápisy něco říká <strong>{0} z {1} polí ({2} %)</strong>; zbytek je "
        "<code>Nil</code>. Publikované poradenské video nemá ID nemocnice ani odesílajícího "
        "lékaře, takže na několik polí nemůže odpovědět nikdo. Na těch model boduje tím, že mlčí, "
        "ne tím, že napíše dobrý zápis — nízké řádky čtěte jako <em>žádný signál</em>, ne jako "
        "těžkou zkoušku."
    ),
    "Filled by the expert": "Vyplněno expertem",
    "<strong>Contamination is not measured.</strong> Both corpora are public files on GitHub —"
    " the transcripts, the expert notes and the rubric — so any model here may have read them"
    " during training. A score earned from the transcript cannot be told apart from one recalled"
    " from it.": (
        "<strong>Kontaminace se tu neměří.</strong> Oba korpusy jsou veřejné soubory na "
        "GitHubu — přepisy, expertní zápisy i rubrika — takže kterýkoli zdejší model je mohl "
        "číst při trénování. Skóre získané z přepisu se nedá odlišit od skóre vybaveného "
        "z paměti."
    ),
    # -- licences -------------------------------------------------------------
    "Licence field, file tree and README checked for each source on 2026-08-24. <strong>Two of"
    " the six carry a licence; three publish none, and the sixth shows a badge with no LICENSE"
    " file behind it.</strong> Nothing here redistributes a corpus: every dataset is fetched from"
    " its origin when a run needs it, and this page shows field names and scores, never"
    " transcripts, notes, or somebody else's prompt.": (
        "U každého zdroje bylo 24. 8. 2026 ověřeno pole s licencí, strom souborů a README. "
        "<strong>Licenci nesou dva ze šesti; tři žádnou nezveřejňují a šestý ukazuje odznak, "
        "za kterým není soubor LICENSE.</strong> Nic tady korpus dál nešíří: každá datová sada "
        "se stahuje ze svého zdroje, až když ji běh potřebuje, a tato stránka ukazuje názvy "
        "polí a skóre, nikdy ne přepisy, zápisy nebo cizí prompt."
    ),
    # `Apache-2.0` and `CC BY 4.0` are identifiers and are the same in every
    # language; they are listed so the guard can see they were decided and
    # not forgotten.
    "Apache-2.0": "Apache-2.0",
    "none published": "žádná nezveřejněna",
    "MIT badge, no LICENSE file": "odznak MIT, žádný soubor LICENSE",
    "CC BY 4.0 (arXiv version)": "CC BY 4.0 (verze na arXivu)",
    "Source": "Zdroj",
    "Used for": "Použito na",
    "Licence": "Licence",
    # -- the protocol ---------------------------------------------------------
    # Written as a list rather than as a counted noun, because Czech takes a
    # different case for 2-4 than for 5 and up and this renders both: the
    # four-criterion section printed "plán — 4 kritérií", which is the
    # genitive where the nominative belongs.
    "{0} — {1} criteria": "{0} — kritérií: {1}",
    "A note here is a <strong>SOAP note</strong>: four sections, in this order. The descriptions"
    " are the ones the models are given, quoted from TN-Eval's own prompt.": (
        "Zápis je tu <strong>zápis SOAP</strong>: čtyři oddíly, v tomto pořadí. Popisy jsou ty, "
        "které dostávají modely, citované z vlastního promptu TN-Eval — a proto zůstávají "
        "anglicky."
    ),
    "Completeness is scored by asking the judge, once per item, whether that item is present in"
    " the matching section. These are TN-Eval's <strong>{0} criteria</strong>, reproduced"
    " verbatim — a note's figure is the equal-weighted mean of its section fractions, not the"
    " fraction of all {1} items; the per-criterion rates are in each row's detail.": (
        "Úplnost se boduje tak, že se hodnotitele u každé položky zvlášť zeptáme, jestli je ta "
        "položka v odpovídajícím oddílu. Tohle je <strong>{0} kritérií</strong> z TN-Eval, "
        "reprodukovaných doslova — číslo u zápisu je průměr podílů za jeho oddíly, každý se "
        "stejnou vahou, ne podíl ze všech {1} položek; míry po jednotlivých kritériích jsou "
        "v detailu každého řádku."
    ),
    "The other track: iCARE's 17 sections": "Ta druhá větev: 17 oddílů iCARE",
    "The iCARE note is not four paragraphs but a <strong>form</strong>. Each of these 17 fields"
    " is filled by its own model call, using an instruction written by clinicians at AIIMS"
    " Delhi, and the correct answer is <code>Nil</code> when the transcript does not say. The two"
    " marked sections ask what happened <em>last</em> time and what happens <em>next</em> time —"
    " the source paper reports that every model it tested failed on them, so they get their own"
    " column rather than being averaged away.": (
        "Zápis iCARE nejsou čtyři odstavce, ale <strong>formulář</strong>. Každé z těch 17 polí "
        "vyplňuje vlastní volání modelu podle instrukce, kterou napsali kliničtí lékaři z AIIMS "
        "Dillí, a správná odpověď je <code>Nil</code>, když to přepis neříká. Dva označené "
        "oddíly se ptají, co bylo <em>minule</em> a co bude <em>příště</em> — zdrojový článek "
        "hlásí, že na nich selhal každý model, který testoval, takže dostávají vlastní sloupec, "
        "místo aby se rozpustily v průměru."
    ),
    'The instructions themselves are fetched from <a href="https://github.com/proadhikary/iCARE">'
    "the iCARE repository</a> at run time and used unchanged; this page shows the field names"
    " only, because that repository publishes no licence.": (
        'Samotné instrukce se za běhu stahují z <a href="https://github.com/proadhikary/iCARE">'
        "repozitáře iCARE</a> a používají se beze změny; tato stránka ukazuje jen názvy polí, "
        "protože ten repozitář nepublikuje žádnou licenci."
    ),
    # -- similarity is not quality ---------------------------------------------
    "Two of the five iCARE columns measure how closely a model reproduced the clinician's"
    " wording. Here is what that misses — section <strong>{0}</strong> of session {1}, written by"
    " the clinician who saw it and by <code>{2}</code>, both verbatim.": (
        "Dva z pěti sloupců iCARE měří, jak těsně model zreprodukoval klinikovo znění. Tady je "
        "to, co jim uniká — oddíl <strong>{0}</strong> sezení {1}, napsaný klinikem, který ho "
        "viděl, a modelem <code>{2}</code>, obojí doslova."
    ),
    "The clinician wrote": "Klinik napsal",
    "{0} wrote": "{0} napsal",
    "ROUGE-L: <strong>{0}</strong> — near zero. {1}": (
        "ROUGE-L: <strong>{0}</strong> — skoro nula. {1}"
    ),
    # -- calibration ------------------------------------------------------------
    # The judge panel prints the same four by their raw key, underscores and
    # all; the calibration table above spells them with spaces. Both are drawn.
    "rubric_completeness": "úplnost podle rubriky",
    "likert_completeness": "úplnost na Likertově škále",
    "likert_conciseness": "stručnost na Likertově škále",
    "likert_faithfulness": "věrnost na Likertově škále",
    "rubric completeness": "úplnost podle rubriky",
    "likert completeness": "úplnost na Likertově škále",
    "likert conciseness": "stručnost na Likertově škále",
    "likert faithfulness": "věrnost na Likertově škále",
    "Cohen's kappa": "Cohenova kappa",
    "Spearman rho": "Spearmanovo rhó",
    "(alpha {0} against {1})": " (alfa {0} proti {1})",
    "The judge reproduces TN-Eval's central finding: criterion checklists agree far better than"
    " 1–5 scales{0}. That is why the ranking uses the rubric and the Likert columns carry a"
    " caveat.": (
        "Hodnotitel reprodukuje ústřední zjištění TN-Eval: seznamy kritérií se shodují mnohem "
        "lépe než škály 1–5{0}. Proto pořadí staví na rubrice a likertovské sloupce nesou "
        "výhradu."
    ),
    "The judge does <strong>not</strong> reproduce TN-Eval's finding that criterion checklists"
    " agree better than 1–5 scales{0}. Reported rather than explained away.": (
        "Hodnotitel <strong>nereprodukuje</strong> zjištění TN-Eval, že se seznamy kritérií "
        "shodují lépe než škály 1–5{0}. Uvedeno, ne zamlčeno."
    ),
    "The two instruments <strong>cannot be separated</strong> here{0}, so this run neither"
    " reproduces nor contradicts TN-Eval's finding. Reported as undecided rather than rounded"
    " into a verdict.": (
        "Ty dva nástroje tu <strong>nelze oddělit</strong>{0}, takže tento běh zjištění TN-Eval "
        "ani nereprodukuje, ani mu neodporuje. Vykázáno jako nerozhodnuté, ne zaokrouhleno na "
        "verdikt."
    ),
    "Judge <code>{0}</code> against the two therapists TN-Eval had rate the same {1} notes.": (
        "Hodnotitel <code>{0}</code> proti dvěma terapeutům, které nechal TN-Eval ohodnotit "
        "týchž {1} zápisů."
    ),
    "Measure": "Míra",
    "Statistic": "Statistika",
    "Judge vs therapist": "Hodnotitel vs. terapeut",
    "Therapist vs therapist": "Terapeut vs. terapeut",
    "Krippendorff's alpha, judge vs therapist": "Krippendorffova alfa, hodnotitel vs. terapeut",
    "Alpha, judge": "Alfa, hodnotitel",
    "Krippendorff's alpha, therapist vs therapist": "Krippendorffova alfa, terapeut vs. terapeut",
    "Alpha, therapists": "Alfa, terapeuti",
    "<strong>The right-hand column is the ceiling, not a target to beat.</strong> Two trained"
    " therapists disagree with each other about these notes; a judge that agrees with a therapist"
    " as often as the other therapist does has done as well as the task allows.": (
        "<strong>Pravý sloupec je strop, ne cíl, který se má překonat.</strong> Dva školení "
        "terapeuti se o těchto zápisech neshodnou mezi sebou; hodnotitel, který se s terapeutem "
        "shodne stejně často jako ten druhý terapeut, udělal maximum, co úloha dovoluje."
    ),
    "<strong>Why two statistics.</strong> Cohen's kappa suits a yes/no criterion and Spearman"
    " suits a 1–5 scale, so each measure is reported under the one a reader expects. Those two"
    " are different quantities and an inequality between them means nothing, so the comparison"
    " below is made on <strong>Krippendorff's alpha</strong> — defined for both, nominal for the"
    " rubric and ordinal for the scales, and the statistic TN-Eval used to reach the finding in"
    " the first place.": (
        "<strong>Proč dvě statistiky.</strong> Cohenova kappa sedí na kritérium ano/ne "
        "a Spearman na škálu 1–5, takže se každá míra vykazuje pod tou, kterou čtenář čeká. Jsou "
        "to dvě různé veličiny a nerovnost mezi nimi neznamená nic, takže srovnání níže stojí na "
        "<strong>Krippendorffově alfě</strong> — definované pro obojí, nominální pro rubriku "
        "a ordinální pro škály. Je to táž statistika, jakou k tomu zjištění došel sám TN-Eval."
    ),
    "Whose notes the judge was checked on": "Na čích zápisech byl hodnotitel ověřen",
    # -- the dominance rule, the grid's withheld rows, and the page's provenance --
    "Compared on the stored figures, not the printed ones: unlike the rank correlation above,"
    " where two scores that print the same are tied, rounding a narrow loss into a tie here"
    " would <em>let a claim through</em> rather than hold one back. So two rows printing the"
    " same number need not tie.": (
        "Porovnává se na uložených hodnotách, ne na vytištěných: na rozdíl od pořadové korelace "
        "výše, kde jsou dvě stejně vytištěná čísla shodná, by tady zaokrouhlení těsné prohry na "
        "shodu tvrzení <em>propustilo</em>, ne zadrželo. Dva řádky se stejně vytištěným číslem "
        "tedy nemusí být shodné."
    ),
    "{0} of {1} print the same number": "{0} z {1} tiskne totéž číslo",
    "related, in reverse": "souvisí, obráceně",
    "<strong>Not detected is not the same as absent.</strong> An interval that includes zero"
    " means a run this size could not see an effect, not that there is none — and the"
    " comparison is a vendor's three or four models against the systems neither of them"
    " wrote.": (
        "<strong>Nedetekováno není totéž co nepřítomno.</strong> Interval, který zahrnuje "
        "nulu, znamená, že běh této velikosti efekt neuviděl, ne že žádný není — a srovnávají "
        "se tři nebo čtyři modely jednoho dodavatele proti systémům, které nepsal ani jeden "
        "z nich."
    ),
    "The panels on this page are computed from {0} — the calibration and the bands from the"
    " judges' individual answers rather than from the rows, because an average cannot be"
    " resampled.": (
        "Panely na této stránce jsou spočítané z {0} — kalibrace a pásma z jednotlivých "
        "odpovědí hodnotitelů, ne z řádků, protože průměr se převzorkovat nedá."
    ),
    "Human ratings exist for {0} systems and no others: {1}. <strong>No human has read a note"
    " written by any of the models this benchmark generated</strong> — the rows above are"
    " TN-Eval's own released notes, which the leaderboard carries as dated reference rows. So the"
    " figure is measured on those and applied to every other row.": (
        "Lidská hodnocení existují pro {0} systémy a pro žádné jiné: {1}. <strong>Žádný člověk "
        "nečetl zápis od kteréhokoli z modelů, které tento benchmark vygeneroval</strong> — "
        "řádky výše jsou vlastní zveřejněné zápisy TN-Evalu, které žebříček vede jako datované "
        "referenční řádky. Číslo je tedy změřeno na nich a použito na všechny ostatní řádky."
    ),
    "Notes written by": "Zápisy napsal",
    "Therapists": "Terapeuti",
    "The judge does not agree with a person equally well on all of them: the spread is"
    " <strong>{0}</strong>, larger than the {1} this page uses to decide that two agreement"
    " figures are separable at all. It is weakest on <code>{2}</code>{3}. A score from this judge"
    " means slightly different things depending on whose note it read, and the leaderboard"
    " compares those scores in one column.": (
        "Hodnotitel se s člověkem neshoduje na všech stejně dobře: rozpětí je "
        "<strong>{0}</strong>, větší než {1}, což je hranice, kterou tato stránka používá pro "
        "rozhodnutí, že dvě čísla shody jsou vůbec oddělitelná. Nejslabší je na "
        "<code>{2}</code>{3}. Skóre od tohoto hodnotitele znamená mírně odlišné věci podle toho, "
        "čí zápis četl, a žebříček ta skóre srovnává v jednom sloupci."
    ),
    ", and on {0} it does not reach the ceiling the two therapists set between them": (
        ", a na {0} nedosahuje stropu, který mezi sebou nastavili ti dva terapeuti"
    ),
    # -- does length buy completeness? -------------------------------------------
    "Does completeness rise with how much the model wrote?": (
        "Roste úplnost s tím, kolik toho model napsal?"
    ),
    "<strong>Within a system</strong>, across its own conversations, the correlation is positive"
    " in {0} of the {1} models — the two dated reference systems and the therapist's note are"
    " not in it — median {2}. That cannot separate the note from the transcript: a longer"
    " session yields both a longer note and more rubric material.": (
        "<strong>Uvnitř systému</strong>, napříč jeho vlastními rozhovory, je korelace kladná "
        "u {0} z {1} modelů — dva datované referenční systémy ani terapeutův zápis v tom "
        "nejsou — medián {2}. To neoddělí zápis od přepisu: delší sezení dá zároveň delší "
        "zápis i víc materiálu pro rubriku."
    ),
    "<strong>Within one conversation</strong>, across the systems, the transcript is held fixed"
    " and can explain nothing. Median {0}, positive in {1} of all {2} conversations — not the"
    " shared set the intervals above use — sign test p&nbsp;=&nbsp;{3}.": (
        "<strong>Uvnitř jednoho rozhovoru</strong>, napříč systémy, je přepis pevně držen "
        "a nemůže vysvětlit nic. Medián {0}, kladná u {1} ze všech {2} rozhovorů — ne ze "
        "sdílené množiny, kterou používají intervaly výše — znaménkový test p&nbsp;=&nbsp;{3}."
    ),
    "Every figure in this subsection is <code>{0}</code>'s. The other judge's is in its own"
    " <code>docs/saturation-&lt;judge&gt;.json</code> and is not drawn here — which is why the"
    " verdict above is one judge's and not the panel's.": (
        "Každé číslo v tomto pododdílu patří hodnotiteli <code>{0}</code>. Číslo druhého "
        "hodnotitele je ve vlastním <code>docs/saturation-&lt;judge&gt;.json</code> a tady se "
        "nekreslí — proto je verdikt výše verdiktem jednoho hodnotitele, ne panelu."
    ),
    "<strong>The effect survives here</strong>, so on this judge a longer note does score higher"
    " for being longer.": (
        "<strong>Efekt tady přežívá</strong>, takže u tohoto hodnotitele delší zápis skutečně "
        "boduje výš za to, že je delší."
    ),
    "<strong>The effect does not survive here</strong>: most of the correlation above is the"
    " transcript, not the note.": (
        "<strong>Efekt tady nepřežívá</strong>: většina korelace výše je přepis, ne zápis."
    ),
    "The leaderboard therefore publishes the <strong>length</strong> and not this coefficient."
    " The length is a fact about the note a reader can discount for; the correlation depends on"
    " which judge is asked, and the two judges do not agree about it.": (
        "Žebříček proto publikuje <strong>délku</strong>, a ne tento koeficient. Délka je fakt "
        "o zápise, na který si čtenář může udělat korekci; korelace závisí na tom, kterého "
        "hodnotitele se zeptáte, a ti dva se na ní neshodnou."
    ),
    # -- do the two judges agree? --------------------------------------------------
    "related": "souvisí",
    "judges disagree": "hodnotitelé se neshodnou",
    "not related": "nesouvisí",
    "Do the two judges agree?": "Shodnou se ti dva hodnotitelé?",
    "{0} of {1} systems print the same number, so this measure does not order them and there is"
    " no agreement to report": (
        "u {0} z {1} systémů vychází totéž číslo, takže je tato míra neseřadí a není co uvádět "
        "jako shodu"
    ),
    "{0} of {1}": "{0} z {1}",
    "nobody moved": "nikdo se nepohnul",
    "<code>{0}</code> beats {1}: {2}": "<code>{0}</code> poráží {1}: {2}",
    "No system beats another on every measure under both judges.": (
        "Žádný systém neporáží jiný na každé míře pod oběma hodnotiteli."
    ),
    "Rank correlation": "Korelace pořadí",
    "Systems placed differently": "Systémy umístěné jinam",
    "Moved furthest": "Nejdál se pohnul",
    "Rank correlation is between <code>{0}</code>'s ordering and <code>{1}</code>'s, over the"
    " {2} systems both have scored. Scores that print the same are treated as tied rather than"
    " ordered by a digit the table does not show. Only measures a judge decides are compared"
    " here: {3}.{4}": (
        "Pořadová korelace je mezi pořadím <code>{0}</code> a pořadím <code>{1}</code>, přes {2} "
        "systémů, které obodovali oba. Skóre, která se zobrazují jako stejná, se berou jako "
        "shodná, ne jako seřazená podle číslice, kterou tabulka neukazuje. Srovnávají se tu jen "
        "míry, o kterých rozhoduje hodnotitel: {3}.{4}"
    ),
    "The rest are computed from the note and the expert note, so they are identical under every"
    " judge and agreeing about them would say nothing.": (
        "Zbytek se počítá ze zápisu a z expertního zápisu, takže jsou pod každým hodnotitelem "
        "stejné a shoda na nich by neřekla nic."
    ),
    "Do the columns agree with each other?": "Shodnou se sloupce mezi sebou?",
    "A separate question from whether the judges do, and the one that decides whether the"
    ' ordering column can be read as "quality". A model that answers every question satisfies'
    " more criteria <em>and</em> invents more.": (
        "Jiná otázka než ta, zda se shodnou hodnotitelé, a právě ona rozhoduje, jestli se dá "
        "řadicí sloupec číst jako „kvalita“. Model, který odpoví na každou otázku, splní víc "
        "kritérií <em>a zároveň</em> si víc vymyslí."
    ),
    "Pair": "Dvojice",
    "Better with no weighting required": "Lepší, aniž je třeba cokoli vážit",
    "A system that is at least as good on <em>every</em> measure under <em>both</em> judges, and"
    " strictly better somewhere, is better however a reader weighs the measures — and weighing"
    " them is a clinical decision, not a measurement. Everything else on this page is a column,"
    " not a verdict.": (
        "Systém, který je aspoň tak dobrý na <em>každé</em> míře pod <em>oběma</em> hodnotiteli "
        "a někde je ostře lepší, je lepší, ať už čtenář ty míry váží jakkoli — a vážit je je "
        "klinické rozhodnutí, ne měření. Všechno ostatní na této stránce je sloupec, ne verdikt."
    ),
    "<strong>{0} of {1} systems are beaten outright by nobody</strong>, so no single winner is"
    " named.": (
        "<strong>{0} z {1} systémů neporazí naplno nikdo</strong>, proto tu není jmenován "
        "jediný vítěz."
    ),
    # -- does either judge favour its own? -------------------------------------------
    "Does either judge favour its own models?": (
        "Nadržuje některý z hodnotitelů vlastním modelům?"
    ),
    "Both judges score every system. The effect is the difference between their tables for a"
    " judge's own family, taken against the systems <em>neither</em> vendor wrote, in {0}, with a"
    " paired bootstrap over conversations <em>and</em> systems — 2000 draws. Resampling"
    " conversations alone would treat three or four models as the whole of a vendor.": (
        "Oba hodnotitelé bodují každý systém. Efekt je rozdíl mezi jejich tabulkami pro vlastní "
        "rodinu daného hodnotitele, vztažený k systémům, které nenapsal <em>ani jeden</em> "
        "z dodavatelů, v míře {0}, s párovým bootstrapem přes rozhovory <em>i</em> přes systémy "
        "— 2000 výběrů. Převzorkování samotných rozhovorů by považovalo tři čtyři modely za "
        "celého dodavatele."
    ),
    "Its family": "Jeho rodina",
    "Effect": "Efekt",
    "95% interval": "95% interval",
    "Detected": "Detekováno",
    "{0}{1} to {2}{3}": "{0}{1} až {2}{3}",
    "yes": "ano",
    "no": "ne",
    "<strong>And the two against each other.</strong> {0}": (
        "<strong>A ti dva proti sobě.</strong> {0}"
    ),
    # -- which judges this measurement separates ----------------------------------------
    "<code>{0}</code> over {1}": "<code>{0}</code> nad {1}",
    "<strong>{0} of those {1} compare two different instruments</strong>: the candidates were not"
    " all asked at the same settings, and the alphas above are over slightly different item"
    " sets. What each ran at is in that table.": (
        "<strong>V {0} z těchto {1} dvojic jde o dva různé nástroje</strong>: kandidáti nebyli "
        "všichni "
        "dotazováni při stejném nastavení a alfy výše jsou nad mírně odlišnými množinami "
        "položek. Při čem který běžel, je v té tabulce."
    ),
    "Read as bands, not as an order. Two candidates closer than {0} are reported here as"
    ' inseparable rather than ranked — the rule <a href="index.html">the leaderboard</a> uses for'
    " models, applied to the judges for the same reason.": (
        "Čtěte jako pásma, ne jako pořadí. Dva kandidáti blíž než {0} se tu vykazují jako "
        'neoddělitelní, místo aby byli seřazeni — je to pravidlo, které <a href="index.html">'
        "žebříček</a> používá na modely, tady použité na hodnotitele ze stejného důvodu."
    ),
    "Of the {0} pairs, {1} are separated by more than that: {2}. Every other pair is not,"
    " including all three <code>flash</code> candidates among themselves and the two GPT"
    " candidates against each other — so price does not buy a better judge here.{3}": (
        "Z {0} dvojic je jich {1} oddělených o víc než to: {2}. Žádná další dvojice ne, včetně "
        "všech tří kandidátů <code>flash</code> mezi sebou a obou kandidátů GPT proti sobě — "
        "cena tady tedy lepšího hodnotitele nekoupí.{3}"
    ),
    "No pair is separated by more than that: this measurement orders them and cannot tell them"
    " apart.": (
        "Žádná dvojice není oddělená o víc než to: toto měření je sice seřadí, ale rozlišit je "
        "nedokáže."
    ),
    "{0} ({1}), but only {2} clear{3} it by the margin.": (
        "{0} ({1}), ale o tu hranici ho překonává jen {2}."
    ),
    "Every candidate agrees with a therapist at least as often as the two therapists agree with"
    " each other": (
        "Každý kandidát se s terapeutem shodne aspoň tak často, jako se ti dva terapeuti shodnou "
        "mezi sebou"
    ),
    "Not every candidate reaches the ceiling the two therapists set between them": (
        "Ne každý kandidát dosáhne stropu, který mezi sebou nastavili ti dva terapeuti"
    ),
    "none of them": "žádný z nich",
    "The spread from <code>{0}</code> {1} to <code>{2}</code> {3} is {4}.": (
        "Rozpětí od <code>{0}</code> {1} po <code>{2}</code> {3} je {4}."
    ),
    "Every judge clears the human ceiling on {0}.": (
        "Každý hodnotitel překonává lidský strop na {0}."
    ),
    "None of them does on {0}, which is why those columns carry the caveat they do in every table"
    " above — the two therapists barely agree there either.": (
        "Na {0} to nezvládne ani jeden, a proto ty sloupce nesou v každé tabulce výše tu "
        "výhradu, kterou nesou — vždyť ani ti dva terapeuti se tam skoro neshodnou."
    ),
    "— in the panel": "— v panelu",
    "Krippendorff's alpha against the two therapists who annotated TN-Eval's own data, over the"
    " same {0} notes. The bottom row is what those two therapists reach <em>with each other</em>"
    " — the ceiling any judge is measured against, and it is not high.": (
        "Krippendorffova alfa proti dvěma terapeutům, kteří anotovali vlastní data TN-Eval, přes "
        "týchž {0} zápisů. Spodní řádek je to, čeho ti dva terapeuti dosáhnou <em>mezi "
        "sebou</em> — strop, proti kterému se měří každý hodnotitel, a není vysoký."
    ),
    "<strong>Some of these rows were measured at different settings from others of the same"
    " kind.</strong> Each candidate is shown at the settings its answers were produced at, under"
    " its name. A judge's settings change its answers — measured here, one judge's thinking"
    " budget going from 128 to 256 moved every model's completeness and reversed the order of the"
    " three <code>flash</code> candidates — so those rows are not strictly comparable.": (
        "<strong>Některé z těchto řádků byly změřeny při jiném nastavení než jiné řádky téhož "
        "druhu.</strong> Každý kandidát je ukázán při nastavení, ve kterém vznikly jeho "
        "odpovědi, pod svým jménem. Nastavení hodnotitele mění jeho odpovědi — změřeno tady: "
        "rozpočet na přemýšlení jednoho hodnotitele šel ze 128 na 256 a pohnul úplností každého "
        "modelu a obrátil pořadí tří kandidátů <code>flash</code> — takže ty řádky nejsou "
        "striktně srovnatelné."
    ),
    "Every candidate of a kind was measured at one setting. Across kinds there is no such thing:"
    " a thinking budget and a reasoning effort are different controls, and no value of one is the"
    " same as a value of the other. That is a limit of comparing judges from two vendors, not a"
    " gap in this run.": (
        "Každý kandidát daného druhu byl změřen při jednom nastavení. Napříč druhy nic takového "
        "neexistuje: rozpočet na přemýšlení a míra uvažování jsou dva různé parametry a žádná "
        "hodnota "
        "jednoho není totéž co hodnota druhého. To je mez srovnávání hodnotitelů od dvou "
        "dodavatelů, ne mezera v tomto běhu."
    ),
    "the two therapists": "ti dva terapeuti",
    # -- withdrawn ---------------------------------------------------------------------
    "Withdrawn from the tables": "Staženo z tabulek",
    # -- measure keys, wherever a panel prints one -------------------------------------
    "trace": "trace",
    "rouge_l": "rouge_l",
    "bertscore": "bertscore",
    "temporal_past": "temporal_past",
    "temporal_next": "temporal_next",
    "conciseness": "stručnost",
    "accurate": "přesnost",
    "thorough": "důkladnost",
    "useful": "užitečnost",
    "organized": "uspořádanost",
    "comprehensible": "srozumitelnost",
    "succinct": "úspornost",
    "synthesized": "syntéza",
    "stigmatizing": "bez stigmatizujícího jazyka",
}


#: The last of the payload: what each source was used for and on what terms,
#: the worked example's own note, and the track ids a withdrawal names.
_METHODS_PAYLOAD = {
    "SOAP prompt, the five scoring prompts, the 23-item rubric": (
        "prompt SOAP, pět bodovacích promptů, rubrika o 23 položkách"
    ),
    "Reproduced verbatim in this repository, with attribution in NOTICE.": (
        "Reprodukováno v tomto repozitáři doslova, s uvedením zdroje v NOTICE."
    ),
    "150 notes and the ratings of two human annotators": (
        "150 zápisů a hodnocení dvou lidských anotátorů"
    ),
    "The Apache licence is on the code repository, not this one. Fetched at run time, never"
    " redistributed.": (
        "Licence Apache je na repozitáři s kódem, ne na tomhle. Stahuje se za běhu, nikdy se "
        "nešíří dál."
    ),
    "the 133 transcripts, 50 of which are scored": ("133 přepisů, z nichž 50 se boduje"),
    "Released “to benefit research community”, with a citation requested. Fetched at run time.": (
        "Vydáno „to benefit research community“, s prosbou o citaci. Stahuje se za běhu."
    ),
    "the 17 section instructions": "instrukce k 17 oddílům",
    "No licence file and no statement of terms. The instructions are fetched at run time and"
    " never shown here.": (
        "Žádný licenční soubor a žádné prohlášení o podmínkách. Instrukce se stahují za běhu "
        "a tady se nikdy nezobrazují."
    ),
    "the iHOPE transcripts and expert notes": "přepisy iHOPE a expertní zápisy",
    "A badge on a code repository, for a corpus collected elsewhere. Treated as no licence for"
    " the data.": (
        "Odznak na repozitáři s kódem, pro korpus posbíraný jinde. Bereme to tak, že data "
        "licenci nemají."
    ),
    "Tingling in the stomach and butterflies in the stomach are the same symptom, as are"
    " palpitations and a rapid heartbeat; trembling hands appear in both. The model also records"
    " how long each symptom has lasted and when it occurs, which the expert note does not. It"
    " shares almost no *words* with the clinician, and a word-overlap metric scores it"
    " accordingly.": (
        "Mravenčení v žaludku a motýlci v břiše jsou tentýž příznak, stejně jako palpitace "
        "a zrychlený tep; třesoucí se ruce jsou v obou. Model navíc zaznamenává, jak dlouho "
        "každý příznak trvá a kdy k němu dochází, což expertní zápis neuvádí. S klinikem "
        "nesdílí skoro žádná *slova* a metrika, která počítá shodná slova, ho podle toho "
        "oboduje."
    ),
    "TN-Eval SOAP · AnnoMI conversations": "TN-Eval SOAP · rozhovory AnnoMI",
    "PDSQI-9 · the SOAP notes on AnnoMI, rated for quality": (
        "PDSQI-9 · zápisy SOAP na AnnoMI, hodnocené na kvalitu"
    ),
    "faithfulness": "věrnost",
    # Track ids, printed where a group is named. Identifiers, so they stay as
    # they are -- but they are answered here, because a key with no entry is
    # how this dictionary reports a gap and these are not one.
    "tneval-soap": "tneval-soap",
    "pdsqi-soap": "pdsqi-soap",
    "icare": "icare",
}


#: The two tables the leaderboard draws only when one instrument has run
#: without the other, and the Czech track, which is registered so a local
#: report can draw it and whose rows never reach `results/rows.jsonl`. Neither
#: is visible in the published payload, which is why the registries are checked
#: directly -- `tests/test_i18n.py` asks `report.COLUMNS`, not a run.
_TRACK_REGISTRIES = {
    # -- PDSQI-9, when it is not merged into the rubric's table ---------------
    "PDSQI-9 on SOAP": "PDSQI-9 na SOAP",
    "The note itself, and for two of the eight attributes the transcript as well -- accurate and"
    " thorough ask whether the note is true and complete, which cannot be answered without the"
    " session. There is no gold note, so this track is reference-free in the same sense the"
    " rubric track is.": (
        "Samotný zápis, a u dvou z osmi atributů i přepis — přesnost a důkladnost se ptají, zda "
        "je zápis pravdivý a úplný, což bez sezení odpovědět nelze. Není tu žádný zlatý zápis, "
        "takže je tato větev bez reference v témž smyslu jako větev s rubrikou."
    ),
    "The therapist's note is scored by the identical protocol and sits in the table as its own"
    " row, exactly as it does on the rubric track. That is the reason this table exists next to"
    " that one: the same notes, two instruments, and a reader can see where they disagree about"
    " who wrote well.": (
        "Terapeutův zápis je obodován týmž protokolem a stojí v tabulce jako vlastní řádek, "
        "přesně jako ve větvi s rubrikou. Právě proto tato tabulka stojí vedle té druhé: tytéž "
        "zápisy, dva nástroje, a čtenář vidí, kde se ty dva neshodnou v tom, kdo psal dobře."
    ),
    "No human has rated these notes on this instrument, so there is no agreement figure for this"
    " judge. What the instrument publishes instead is a ceiling: trained physicians agreed with"
    " each other at Krippendorff's alpha 0.575, against the 0.18 two therapists reach on"
    " faithfulness. A judge cannot be asked to agree with a person better than people agree with"
    " each other -- but a ceiling is not a measurement, and these columns have not been checked"
    " against anyone.": (
        "Na tento nástroj tyto zápisy nikdo z lidí nehodnotil, takže pro tohoto hodnotitele "
        "žádné číslo shody neexistuje. Co nástroj publikuje místo toho, je strop: školení lékaři "
        "se mezi sebou shodli na Krippendorffově alfě 0.575, proti 0.18, na které se dva "
        "terapeuti dostanou u věrnosti. Po hodnotiteli nelze chtít, aby se s člověkem shodl líp, "
        "než se lidé shodnou mezi sebou — jenže strop není měření a tyto sloupce nebyly ověřeny "
        "proti nikomu."
    ),
}


#: Czech, keyed by the English. Read the module docstring for the three shapes.
CS: dict[str, str] = {
    **_STATIC,
    **_SENTENCES,
    **_PAYLOAD,
    **_METHODS,
    **_METHODS_PAYLOAD,
    **_TRACK_REGISTRIES,
}


def dictionary() -> dict[str, dict[str, str]]:
    """What the pages inline: one table per language that is not the default.

    Keys are normalised here and values are not. A fragment written to begin
    with a space -- one of them joins a clause onto the sentence before it --
    would lose it to a trim, and the page it is looked up from does the same
    normalisation on the key alone.
    """
    return {"cs": {norm(key): value for key, value in CS.items()}}
