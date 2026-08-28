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
        "Zápisy z psychoterapeutických sezení psané jazykovými modely, hodnocené podle dvou "
        "publikovaných protokolů — rubriky SOAP z TN-Eval a 17 oddílů z iCARE — a přeměřované, "
        "jak se modely mění. "
        '<a href="https://github.com/JanNehyba/therapy-note-bench">Kód a data na GitHubu</a>.'
    ),
    "page.methods-link": (
        '<a href="methods.html">Jak se to měřilo →</a> '
        "Definice každého sloupce, který hodnotitel a jak těsně se shoduje se dvěma terapeuty, "
        "jak daleko od sebe jsou oba hodnotitelé, co jsou ty dva korpusy a odkud pocházejí, "
        "a které řádky se už nekreslí."
    ),
    "page.brief-link": (
        '<a href="brief.html">Jak tato čísla číst a nenechat se zmást →</a> '
        "Co žebříček těchto modelů může a nemůže říct tomu, kdo takový systém staví nebo "
        "kupuje — čtyři tvrzení, čtyři obrázky a soubor, ze kterého každé číslo pochází. "
        'Také jako <a href="therapy-note-bench.pdf">PDF</a>.'
    ),
    "page.foot.columns": (
        "Rozsah každého sloupce, co počítá a jak se nesmí číst, stojí pod tou tabulkou, ke "
        "které patří, ne tady dole — včetně téměř nulové shody dvou terapeutů na "
        "<strong>věrnosti</strong> (Krippendorffova alfa 0.18)."
    ),
    "page.foot.notes": (
        "<strong>Zápisy</strong> počítají, kolik zápisů dokázal protokol vůbec přečíst. Model, "
        "který napíše dobrý zápis ve špatném tvaru, ztrácí zápisy na formátu, ne na klinickém "
        "obsahu — přečtěte si ten počet dřív, než začnete srovnávat skóre."
    ),
    "page.foot.provider": (
        "Štítek za názvem modelu je <strong>poskytovatel</strong>, který ho obsluhoval. Stejné "
        "id modelu u dvou poskytovatelů mohou být dvě různá sestavení — jiná kvantizace, jiné "
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
        "<strong>Co ty korpusy jsou a co nejsou.</strong> Čtyři stránky nesou pozadí, na kterém "
        "tyto tabulky stojí, a až do 27. 8. 2026 na ně z tohoto webu nevedl jediný odkaz: "
        '<a href="datasets.md">datové sady</a> — odkud každá pochází, jakou licenci publikuje '
        "(dvě ze tří žádnou) a jaké pasti v nich jsou; "
        '<a href="methodology.md">metoda</a>; '
        '<a href="limitations.md">co výsledek nesmí tvrdit</a>; a '
        '<a href="landscape.md">co v tomto oboru existuje</a> a co ne.'
    ),
}


#: Sentences written in the page script, keyed by their English with numbered
#: holes. Read the module docstring for why a hole may go unused.
_SENTENCES = {
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
    "Spent about <strong>{0} tokens reasoning</strong> before writing, averaged over its notes"
    " — as reported by the provider. <em>Not comparable across providers:</em> what counts as a"
    " reasoning token depends on the serving stack, not only on the model.": (
        "Před psaním strávil <strong>asi {0} tokenů uvažováním</strong>, v průměru přes své "
        "zápisy — tak, jak to hlásí poskytovatel. <em>Mezi poskytovateli to není "
        "srovnatelné:</em> co se počítá jako token uvažování, závisí na obslužné vrstvě, "
        "ne jen na modelu."
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
    "Not every row is a model under test: {0}. They sit in the ranking because they were"
    " measured the same way, and a human note placing low says something about the measure"
    " rather than about the clinician &mdash; the rubric counts what a note contains and cannot"
    " see what a clinician chose to leave out.": (
        "Ne každý řádek je testovaný model: {0}. V pořadí stojí proto, že byly změřeny stejně, "
        "a nízko umístěný lidský zápis vypovídá spíš o měřítku než o klinikovi &mdash; rubrika "
        "počítá, co zápis obsahuje, a nevidí, co se klinik rozhodl vynechat."
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
    "harness <code>{0}</code>": "harness <code>{0}</code>",
    "prompt <code>{0}</code>": "prompt <code>{0}</code>",
    # -- the grid itself ------------------------------------------------------
    "Band on {0}: rows this evidence cannot tell apart share a band. It does not follow the sort"
    " -- sorting by another column reorders the rows, not what the bootstrap could separate.": (
        "Pásmo podle sloupce {0}: řádky, které tato evidence nedokáže rozlišit, sdílejí pásmo. "
        "Neřídí se řazením — seřazení podle jiného sloupce přeskládá řádky, ne to, co bootstrap "
        "dokázal oddělit."
    ),
    "Band": "Pásmo",
    "System": "Systém",
    "Median words in this model’s notes. Completeness counts coverage, so a longer note covers"
    " more.": (
        "Medián počtu slov v zápisech tohoto modelu. Úplnost počítá pokrytí, takže delší zápis "
        "pokryje víc."
    ),
    "Words": "Slova",
    "Notes": "Zápisy",
    "{0} judged": "ohodnoceno {0}",
    "settings": "nastavení",
    "scored by a judge from the same vendor, whose self-preference is measured in the panel"
    " below": (
        "obodováno hodnotitelem od téhož dodavatele; jak moc nadržuje sám sobě, je změřeno "
        "v panelu níže"
    ),
    "judge's own {0}": "hodnotitelova vlastní {0}",
    "ranks this table": "řadí tuto tabulku",
    # -- the sentences under the grid ----------------------------------------
    "<strong>Systems that share a rank cannot be told apart by this evidence.</strong> {0} of {1}"
    " ranks are shared, and the top one has {2} system(s) in it. Measured on <strong>{3}</strong>"
    " over the {4} conversations every system here was scored on, by resampling those"
    " conversations — not by whether two intervals overlap, which is a weaker test.": (
        "<strong>Systémy, které sdílejí příčku, tato evidence od sebe nerozliší.</strong> "
        "Sdílených příček je {0} z {1} a na té nejvyšší stojí systémů: {2}. Změřeno na "
        "<strong>{3}</strong> přes {4} rozhovorů, na kterých byl obodován každý zdejší systém, "
        "převzorkováním těch rozhovorů — ne tím, zda se dva intervaly překrývají, což je slabší "
        "test."
    ),
    "<strong>Which of these can be told apart has not been measured for this table.</strong>"
    " Read the order as roughly who is near the top and near the bottom, not as a ranking: two"
    " adjacent rows are not a result.": (
        "<strong>U této tabulky nebylo změřeno, které systémy od sebe lze rozlišit.</strong> "
        "Čtěte to pořadí jen zhruba jako to, kdo je blízko vrcholu a kdo blízko dna, ne jako "
        "žebříček: dva sousední řádky nejsou výsledek."
    ),
    "Measured against the {0} systems neither judge's vendor wrote: {1}. Named rather than"
    " counted, because the estimate is only as good as this group.": (
        "Měřeno proti {0} systémům, které nenapsal dodavatel ani jednoho z hodnotitelů: {1}. "
        "Vyjmenováno, ne spočítáno, protože odhad je jen tak dobrý jako tahle skupina."
    ),
    "{0} are in it under a name their model family does not share, and pull the answer toward"
    " zero.": (
        "{0} v ní jsou pod jménem, které jejich rodina modelů nesdílí, a táhnou odpověď k nule."
    ),
    "Ordered by <strong>{0}</strong>, because it is the only column checked against people: on"
    " it the judge and a trained therapist agree at <strong>{1}</strong> where two therapists"
    " reach <strong>{2}</strong>. On the 1&#8211;5 scales two therapists agree at {3}, so those"
    " carry too little signal to rank on. Every other column is context and is not a ranking.": (
        "Seřazeno podle sloupce <strong>{0}</strong>, protože je to jediný sloupec ověřený proti "
        "lidem: na něm se hodnotitel a školený terapeut shodnou na <strong>{1}</strong> tam, "
        "kde dva terapeuti dosáhnou <strong>{2}</strong>. Na škálách 1&#8211;5 se dva terapeuti "
        "shodnou na {3}, takže ty nesou příliš málo signálu, než aby se podle nich dalo řadit. "
        "Každý další sloupec je kontext, ne žebříček."
    ),
    "Ordered by <strong>{0}</strong>, because it is the only column with a human anchor at all."
    " <strong>This judge's agreement with the two therapists is not published here</strong>, so"
    " the figure that belongs in this sentence is missing rather than borrowed from another"
    " judge. Every other column is context and is not a ranking.": (
        "Seřazeno podle sloupce <strong>{0}</strong>, protože je to jediný sloupec, který má "
        "vůbec lidskou kotvu. <strong>Shoda tohoto hodnotitele s oběma terapeuty tu není "
        "publikovaná</strong>, takže číslo, které do téhle věty patří, chybí — místo aby se "
        "půjčilo od jiného hodnotitele. Každý další sloupec je kontext, ne žebříček."
    ),
    "Provider": "Poskytovatel",
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
    "<strong>Sources:</strong> {0} — every prompt and rubric here is reproduced verbatim"
    ' from them. <a href="methods.html#licences">What each is used for, and on what terms</a>:'
    " two of them publish no licence at all.": (
        "<strong>Zdroje:</strong> {0} — každý zdejší prompt i rubrika jsou z nich "
        'převzaté doslova. <a href="methods.html#licences">K čemu se každý používá a za '
        "jakých podmínek</a>: dva z nich nezveřejňují žádnou licenci."
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
    "AnnoMI": "AnnoMI",
    "133 publicly released motivational-interviewing sessions, transcribed and annotated by"
    " therapists. 50 of them are scored here.": (
        "133 veřejně vydaných nahrávek motivačních rozhovorů, přepsaných a anotovaných "
        "terapeuty. Hodnotí se z nich 50."
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
    "iHOPE": "iHOPE",
    "40 counselling sessions, each with one note written by the clinician who saw it. That note"
    " is the answer key, not an entry.": (
        "40 poradenských sezení, u každého jeden zápis od klinika, který ho vedl. Ten zápis "
        "je klíč k odpovědím, ne soutěžící."
    ),
    "The iCARE form": "Formulář iCARE",
    "17 fields to fill in rather than a note to write, so a blank field is a different thing"
    " from a short sentence.": (
        "17 políček k vyplnění místo zápisu k napsání, takže prázdné políčko je něco jiného "
        "než krátká věta."
    ),
    "The first three columns count what a note contains — TN-Eval's rubric. The other eight"
    " rate how it is written — PDSQI-9. **Nothing is averaged across them**: different"
    " questions on different scales, and neither instrument publishes a total either.": (
        "První tři sloupce počítají, co zápis obsahuje — rubrika TN-Eval. Dalších osm "
        "hodnotí, jak je napsaný — PDSQI-9. **Nic se přes ně neprůměruje**: jsou to jiné "
        "otázky na jiných škálách a ani jeden nástroj sám žádný souhrn nezveřejňuje."
    ),
    "This track is deliberately <strong>not ranked</strong>: its columns measure different things"
    " and the source paper found they disagree. That disagreement is the result.": (
        "Tato větev <strong>záměrně nemá pořadí</strong>: její sloupce měří různé věci a zdrojový "
        "článek zjistil, že si odporují. Ten rozpor je ten výsledek."
    ),
    "Each row also records how many tokens its model spent <strong>reasoning</strong> before"
    " writing — open a row to see it. It is not a column because it is not comparable between"
    " providers: vLLM, which serves the e-INFRA models, reports zero for models whose reasoning"
    " is text-delimited even when they reason, and OpenAI counts differently again. A gap there"
    " can be bookkeeping rather than behaviour.": (
        "Každý řádek také zaznamenává, kolik tokenů jeho model strávil <strong>uvažováním</strong> "
        "před psaním — rozbalte řádek a uvidíte to. Není to sloupec, protože to není srovnatelné "
        "mezi poskytovateli: vLLM, které obsluhuje modely e-INFRA, hlásí nulu u modelů, jejichž "
        "uvažování je vymezeno textem, i když uvažují, a OpenAI to zase počítá jinak. Rozdíl tam "
        "může být účetnictví, ne chování."
    ),
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
    "Every figure on this page is generated from <code>results/{0}</code>, which is append-only:"
    " a re-run adds rows beside the old ones rather than replacing them, and what is drawn here"
    " is the newest of each.": (
        "Každé číslo na této stránce je vygenerováno ze souboru <code>results/{0}</code>, do "
        "kterého se jen přidává: opakovaný běh přidá řádky vedle starých, místo aby je nahradil, "
        "a kreslí se tu z každého ten nejnovější."
    ),
    # Leading space, like the English fragment it replaces: it joins onto the
    # sentence before it and the key it is found by was trimmed.
    "— <code>{0}</code> furthest, {1}{2} in this table and {3}{4} in that one": (
        " — nejdál <code>{0}</code>, {1}{2} v této tabulce a {3}{4} v té druhé"
    ),
    "<strong>The two judges agree on the shape of this ranking and not on its order.</strong> On"
    " {0}, {1} of {2} systems land somewhere else under <code>{3}</code>{4}. Near the top and"
    " near the bottom are claims this table supports; ninth against tenth is not.": (
        "<strong>Oba hodnotitelé se shodnou na tvaru tohoto pořadí, ne na jeho sledu.</strong> "
        "Na sloupci {0} přistane pod hodnotitelem <code>{3}</code> jinde {1} z {2} systémů{4}. "
        "Blízko vrcholu a blízko dna jsou tvrzení, která tato tabulka unese; devátý proti "
        "desátému ne."
    ),
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
    # -- track titles and blurbs ---------------------------------------------
    "SOAP notes on AnnoMI · two instruments, the same notes": (
        "Zápisy SOAP na AnnoMI · dva nástroje, tytéž zápisy"
    ),
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
    "An expert note written by the clinician who saw the session. ROUGE-L and BERTScore measure"
    " how closely the model reproduced it; TRACE asks a judge to rate the note itself, the way"
    " the paper's experts did.": (
        "Expertní zápis, který napsal klinik, jenž to sezení viděl. ROUGE-L a BERTScore měří, "
        "jak těsně jej model zreprodukoval; TRACE žádá hodnotitele, aby ohodnotil samotný zápis, "
        "tak jako to dělali experti v tom článku."
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
    "Fraction of the section's rubric criteria the judge found present. 0.65 means about two"
    " thirds of the required items are in the note.": (
        "Podíl kritérií rubriky daného oddílu, která hodnotitel našel přítomná. 0.65 znamená, že "
        "v zápise jsou zhruba dvě třetiny požadovaných položek."
    ),
    "Counts coverage of a checklist, not judgement. A therapist writes what matters for the next"
    " session and leaves out what does not; the rubric sees what is present and cannot see why"
    " anything was left out -- which is why every model here scores above the therapist on it."
    " This is the column the table is ordered by, so the caveat travels with the ranking: quote"
    " the number with this sentence attached, or do not quote it.": (
        "Počítá pokrytí seznamu položek, ne úsudek. Terapeut píše to, co je důležité pro příští "
        "sezení, a co není, vynechá; rubrika vidí, co v zápise je, a nevidí, proč bylo něco "
        "vynecháno — a právě proto tu na ní každý model boduje výš než terapeut. Podle tohoto "
        "sloupce je tabulka seřazena, takže tato výhrada cestuje spolu s pořadím: citujte to "
        "číslo i s touto větou, nebo je necitujte."
    ),
    "Conciseness": "Stručnost",
    "Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is"
    " off-topic; it does not mean the note is short.": (
        "Podíl vět zápisu, které padnou aspoň na jednu položku rubriky. 1.00 znamená, že nic "
        "není mimo téma; neznamená to, že je zápis krátký."
    ),
    "Not a length measure, despite the name: a note twice as long scores the same if every added"
    " sentence is on topic. It is also the measure most moved by the judge's own settings --"
    " raising the thinking budget from 128 to 256 tokens shifted all nineteen systems and"
    " reordered sixteen of them.": (
        "Navzdory jménu to není míra délky: dvakrát delší zápis boduje stejně, pokud je každá "
        "přidaná věta k tématu. Je to také míra, kterou nejvíc hýbe vlastní nastavení "
        "hodnotitele — zvednutí rozpočtu na přemýšlení ze 128 na 256 tokenů posunulo všech "
        "devatenáct systémů a šestnácti z nich změnilo pořadí."
    ),
    "Faithfulness": "Věrnost",
    "Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies."
    " TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert"
    " scale.": (
        "Zda zápis odporuje přepisu, hodnoceno 1 až 5, kde 5 je bez nepřesností. Protokol "
        "TN-Eval nemá verzi této otázky založenou na kritériích, takže zůstává Likertovou "
        "škálou."
    ),
    "A different scale from the two columns beside it, and a weak one: TN-Eval measured"
    " Krippendorff's alpha of 0.18 between trained therapists on this rating. Read it as a flag"
    " for gross invention, not as a ranking.": (
        "Jiná škála než u dvou sloupců vedle, a slabá: TN-Eval na tomto hodnocení naměřil mezi "
        "školenými terapeuty Krippendorffovu alfu 0.18. Čtěte to jako signál hrubého výmyslu, "
        "ne jako pořadí."
    ),
    # -- PDSQI-9 ---------------------------------------------------------------
    "Accurate": "Přesnost",
    "The note is true and free of incorrect information. PDSQI-9 item 2, rated 1 (not at all) to"
    " 5 (extremely).": (
        "Zápis je pravdivý a bez nesprávných informací. PDSQI-9, položka 2, hodnoceno 1 (vůbec) "
        "až 5 (zcela)."
    ),
    "PDSQI-9 was validated on clinical summaries from a corpus that excluded psychiatry notes,"
    " and rates a summary of several earlier notes rather than a note written from one session."
    " Trained physicians agreed with each other at Krippendorff's alpha 0.575, which is the"
    " ceiling on what a judge can be asked for.": (
        "PDSQI-9 byl validován na klinických souhrnech z korpusu, který psychiatrické zápisy "
        "vylučoval, a hodnotí souhrn několika dřívějších zápisů, ne zápis psaný z jednoho "
        "sezení. Školení lékaři se mezi sebou shodli na Krippendorffově alfě 0.575, což je "
        "strop toho, co lze po hodnotiteli chtít."
    ),
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
        "Je v něm všechna informace, která je užitečná cílovému poskytovateli péče / zamýšlenému "
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
    " compares the whole rendered note, which puts our own field labels and every `Nil` the"
    " expert wrote on both sides -- a note where the model wrote nothing at all scores 0.379 that"
    " way, above most real notes. This compares the field values of the sections the expert"
    " answered, where the same empty note scores 0.000, and every model's figure fell by about a"
    " third. It also cannot tell a good paraphrase from a wrong answer, and the source paper"
    " found it disagrees with what clinicians preferred.": (
        "Není to ROUGE-L ze zdrojového článku a s jejich publikovanou tabulkou to není "
        "srovnatelné. Ta jejich srovnává celý vykreslený zápis, což staví naše vlastní názvy "
        "polí a každé `Nil`, které expert napsal, na obě strany — zápis, do kterého model "
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
        "proti komu, nad kterými korpusy a v čem se ti dva hodnotitelé neshodnou. Každý zdejší "
        "panel je vykreslen z téhož běhu, který vyrobil ty tabulky — nic na této stránce není "
        'psáno ručně. <a href="https://github.com/JanNehyba/therapy-note-bench">Zdroj '
        "a metoda</a>."
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
    "methods.saturation.figure": (
        "Jak velkou část rozsahu každé míry modely skutečně obsadí. Vlevo: jeden pruh na každé "
        "kritérium rubriky, od nejhoršího modelu k nejlepšímu, s vyznačeným terapeutem. Vpravo: "
        "totéž čtení TRACE, kde jeden pruh jsou všechny modely najednou. Kreslí "
        "<code>tools/figures.py</code> ze souborů jmenovaných v patičce obrázku."
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
        '<a href="brief.html">Osmistránkový briefing →</a> Co žebříček těchto modelů může '
        "a nemůže říct tomu, kdo takový systém staví nebo kupuje — čtyři tvrzení, čtyři obrázky "
        'a soubor, ze kterého každé číslo pochází. Také jako <a href="therapy-note-bench.pdf">'
        "PDF</a>."
    ),
    "methods.foot.columns": (
        "Rozsah každého sloupce, co počítá a jak se nesmí číst, stojí pod tou tabulkou, ke které "
        'patří, na <a href="index.html">žebříčku</a> — včetně téměř nulové lidské shody na '
        "<strong>věrnosti</strong> (Krippendorffova alfa 0.18) a toho, že <strong>TRACE</strong> "
        "je reimplementace <em>bez lidské kotvy</em>. Číslo a jeho výhradu by nemělo dělit "
        "rolování, a proto jsou ony tam a tato stránka je tady."
    ),
    "methods.foot.provider": (
        "Štítek za názvem modelu je <strong>poskytovatel</strong>, který ho obsluhoval. Stejné "
        "id modelu u dvou poskytovatelů mohou být dvě různá sestavení — jiná kvantizace, jiné "
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
    " table above averages each system over its own notes; this section averages every system"
    " over the <strong>{0} of {1}</strong> conversations they <em>all</em> have, because a"
    " paired comparison is only paired on a shared set. The set is smaller because {2}. Expect"
    " small differences from the table, and expect closely-matched systems to change places:"
    " that two orderings disagree over which 42 of 50 conversations you use is itself a result"
    " about how tightly packed these models are.": (
        "<strong>Tato čísla nejsou čísla z tabulky, a ani být nemají.</strong> Tabulka výše "
        "průměruje každý systém přes jeho vlastní zápisy; tento oddíl průměruje každý systém "
        "přes <strong>{0} z {1}</strong> rozhovorů, které mají <em>všechny</em>, protože "
        "párové srovnání je párové jen na sdílené množině. Ta množina je menší proto, že {2}. "
        "Očekávejte drobné rozdíly oproti tabulce a očekávejte, že si těsně vyrovnané systémy "
        "prohodí místa: to, že se dvě uspořádání neshodnou podle toho, kterých 42 z 50 "
        "rozhovorů použijete, je samo o sobě výsledek o tom, jak nahusto tyto modely stojí."
    ),
    "{0} was scored on {1} fewer": "{0} byl obodován o {1} méně",
    "{0}, and the other {1} on {2}": "{0}, a zbývajících {1} o {2}",
    "one each": "jeden každý",
    "no more than {0} each": "nejvýš {0} každý",
    "Computed from <code>{0}</code>'s individual answers{1}.": (
        "Spočteno z jednotlivých odpovědí modelu <code>{0}</code>{1}."
    ),
    "at {0}": " při nastavení {0}",
    "The cache also held answers at other settings; they are two instruments and were not mixed"
    " in.": (
        "Cache držela i odpovědi z jiných nastavení; jsou to dva nástroje a nebyly do sebe míchány."
    ),
    "A ranking always prints an order. This asks whether the evidence supports one. Both parts"
    " read the individual judgements, not the averages, over the <strong>{0} conversations every"
    " system wrote a note for</strong>.": (
        "Žebříček vždycky vytiskne nějaké pořadí. Tady se ptáme, jestli ho evidence unese. Obě "
        "části čtou jednotlivé soudy, ne průměry, přes <strong>{0} rozhovorů, ke kterým napsal "
        "zápis každý systém</strong>."
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
    "Both corpora are transcripts of published counselling demonstrations, not clinical"
    " sessions. Sizes are of the splits this benchmark actually scores; lengths are in words of"
    " transcript, which is what a model has to read.": (
        "Oba korpusy jsou přepisy publikovaných poradenských ukázek, ne klinických sezení. "
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
        "<code>Nil</code>. Publikované poradenské video nemá číslo hospitalizace ani odesílajícího "
        "lékaře, takže na několik polí nemůže odpovědět nikdo. Na těch model boduje tím, že mlčí, "
        "ne tím, že napíše dobrý zápis — nízké řádky čtěte jako <em>žádný signál</em>, ne jako "
        "těžkou zkoušku."
    ),
    "Filled by the expert": "Vyplněno expertem",
    # -- licences -------------------------------------------------------------
    "Checked repository by repository — licence field, file tree and README — rather than"
    " assumed from a sibling project. <strong>Only one of the five carries a licence.</strong>"
    " Nothing here redistributes a corpus: every dataset is fetched from its origin when a run"
    " needs it, and this page shows field names and scores, never transcripts, notes, or"
    " somebody else's prompt.": (
        "Ověřeno repozitář po repozitáři — pole s licencí, strom souborů a README — ne "
        "odhadnuto podle sousedního projektu. <strong>Licenci nese jen jeden z pěti.</strong> "
        "Nic tady korpus dál nešíří: každá datová sada se stahuje ze svého zdroje, až když ji "
        "běh potřebuje, a tato stránka ukazuje názvy polí a skóre, nikdy ne přepisy, zápisy "
        "nebo cizí prompt."
    ),
    "Source": "Zdroj",
    "Used for": "Použito na",
    "Licence": "Licence",
    # -- the protocol ---------------------------------------------------------
    "{0} — {1} criteria": "{0} — {1} kritérií",
    "A note here is a <strong>SOAP note</strong>: four sections, in this order. The descriptions"
    " are the ones the models are given, quoted from TN-Eval's own prompt.": (
        "Zápis je tu <strong>zápis SOAP</strong>: čtyři oddíly, v tomto pořadí. Popisy jsou ty, "
        "které dostávají modely, citované z vlastního promptu TN-Eval — a proto zůstávají "
        "anglicky."
    ),
    "Completeness is scored by asking the judge, once per item, whether that item is present in"
    " the matching section. These are TN-Eval's <strong>{0} criteria</strong>, reproduced"
    " verbatim — a note scoring 0.50 contained half of them.": (
        "Úplnost se boduje tak, že se hodnotitele u každé položky zvlášť zeptáme, jestli je ta "
        "položka v odpovídajícím oddílu. Tohle je <strong>{0} kritérií</strong> z TN-Eval, "
        "reprodukovaných doslova — zápis se skóre 0.50 jich obsahoval polovinu."
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
    "Two of the four iCARE columns measure how closely a model reproduced the clinician's"
    " wording. Here is what that misses — section <strong>{0}</strong> of session {1}, written by"
    " the clinician who saw it and by <code>{2}</code>, both verbatim.": (
        "Dva ze čtyř sloupců iCARE měří, jak těsně model zreprodukoval klinikovo znění. Tady je "
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
        "shodují lépe než škály 1–5{0}. Vykázáno, ne vysvětleno pryč."
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
        "a ordinální pro škály, a je to ta statistika, kterou k tomu zjištění došel sám TN-Eval."
    ),
    "Whose notes the judge was checked on": "Na čích zápisech byl hodnotitel ověřen",
    "Human ratings exist for {0} systems and no others: {1}. <strong>No human has read a note"
    " written by any of the models the leaderboard ranks</strong>, so the figure above is"
    " measured on one set of notes and applied to another.": (
        "Lidská hodnocení existují pro {0} systémy a pro žádné jiné: {1}. <strong>Žádný člověk "
        "nečetl zápis od kteréhokoli z modelů, které žebříček řadí</strong>, takže číslo výše je "
        "změřeno na jedné sadě zápisů a použito na jinou."
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
    " in {0} of {1} systems, median {2}. That cannot separate the note from the transcript: a"
    " longer session yields both a longer note and more rubric material.": (
        "<strong>Uvnitř systému</strong>, napříč jeho vlastními rozhovory, je korelace kladná "
        "u {0} z {1} systémů, medián {2}. To neoddělí zápis od přepisu: delší sezení dá zároveň "
        "delší zápis i víc materiálu pro rubriku."
    ),
    "<strong>Within one conversation</strong>, across the systems, the transcript is held fixed"
    " and can explain nothing. Median {0}, positive in {1} of {2} conversations, sign test"
    " p&nbsp;=&nbsp;{3}.": (
        "<strong>Uvnitř jednoho rozhovoru</strong>, napříč systémy, je přepis pevně držen "
        "a nemůže vysvětlit nic. Medián {0}, kladná u {1} z {2} rozhovorů, znaménkový test "
        "p&nbsp;=&nbsp;{3}."
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
        "{0} z {1} systémů tiskne totéž číslo, takže je tato míra neseřadí a není co vykazovat "
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
    "Rank correlation is between <code>{0}</code>'s ordering and <code>{1}</code>'s, over the {2}"
    " systems both have scored. Scores that print the same are treated as tied rather than"
    " ordered by a digit the table does not show. Only measures a judge decides are compared"
    " here: {3}. The rest are computed from the note and the expert note, so they are identical"
    " under every judge and agreeing about them would say nothing.": (
        "Korelace pořadí je mezi uspořádáním od <code>{0}</code> a od <code>{1}</code>, přes {2} "
        "systémů, které obodovali oba. Skóre, která se tisknou stejně, se berou jako shodná, "
        "místo aby je řadila číslice, kterou tabulka neukazuje. Srovnávají se tu jen míry, "
        "o kterých rozhoduje hodnotitel: {3}. Zbytek se počítá ze zápisu a z expertního zápisu, "
        "takže je pod každým hodnotitelem stejný a shoda o něm by neřekla nic."
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
    "<strong>{0} of {1} systems are beaten outright by nobody.</strong> That is why there is no"
    " single winner named here.": (
        "<strong>{0} z {1} systémů neporáží naplno nikdo.</strong> Proto tu není jmenován jediný "
        "vítěz."
    ),
    # -- does either judge favour its own? -------------------------------------------
    "Does either judge favour its own models?": (
        "Nadržuje některý z hodnotitelů vlastním modelům?"
    ),
    "Measured, not disclaimed. Both judges score everything, and the difference between their"
    " tables for a judge's own family — against the systems <em>neither</em> of them wrote — is"
    " the effect, in {0}, with a paired bootstrap over conversations.": (
        "Změřeno, ne odbyto poznámkou pod čarou. Oba hodnotitelé bodují všechno a rozdíl mezi "
        "jejich tabulkami pro hodnotitelovu vlastní rodinu — proti systémům, které nenapsal "
        "<em>ani jeden</em> z nich — je ten efekt, v míře {0}, s párovým bootstrapem přes "
        "rozhovory."
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
    " all asked at the same settings, and the alphas below are over slightly different item sets."
    " What each ran at is in the table above.": (
        "<strong>{0} z těch {1} srovnává dva různé nástroje</strong>: kandidáti nebyli všichni "
        "dotazováni při stejném nastavení a alfy níže jsou nad mírně odlišnými množinami "
        "položek. Při čem který běžel, je v tabulce výše."
    ),
    "Read as bands, not as an order. Two candidates closer than {0} are reported here as"
    " inseparable rather than ranked — the rule the tables above use for models, applied to the"
    " judges for the same reason.": (
        "Čtěte jako pásma, ne jako pořadí. Dva kandidáti blíž než {0} se tu vykazují jako "
        "neoddělitelní, místo aby byli seřazeni — je to pravidlo, které tabulky výše používají "
        "na modely, tady použité na hodnotitele ze stejného důvodu."
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
        "neexistuje: rozpočet na přemýšlení a míra uvažování jsou různé ovladače a žádná hodnota "
        "jednoho není totéž co hodnota druhého. To je mez srovnávání hodnotitelů od dvou "
        "dodavatelů, ne mezera v tomto běhu."
    ),
    "the two therapists": "ti dva terapeuti",
    # -- withdrawn ---------------------------------------------------------------------
    "scored by <code>{0}</code>": "obodovaných modelem <code>{0}</code>",
    "of generation coverage": "o pokrytí generování",
    "the measures were redefined in <code>{0}</code> and the two are not comparable": (
        "míry byly předefinovány ve verzi <code>{0}</code> a ty dvě nejsou srovnatelné"
    ),
    "the judge's settings were not recorded, so the rows cannot be shown to have come from one"
    " instrument": (
        "nastavení hodnotitele nebylo zaznamenáno, takže se nedá ukázat, že ty řádky pocházejí "
        "z jednoho nástroje"
    ),
    "; and": "; a ",
    "{0} row(s) on <strong>{1}</strong>, {2}, at harness <code>{3}</code>, are no longer shown:"
    " {4}. They are still in <code>results/rows.jsonl</code>.": (
        "Řádky ve větvi <strong>{1}</strong>, {2}, při harnessu <code>{3}</code> — je jich {0} — "
        "se už nekreslí: {4}. Pořád jsou v <code>results/rows.jsonl</code>."
    ),
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
    "redistributed.": (
        "Licence Apache je na repozitáři s kódem, ne na tomhle. Stahuje se za běhu, nikdy se "
        "nešíří dál."
    ),
    "the 133 transcripts, 50 of which are scored": ("133 přepisů, z nichž 50 se boduje"),
    "Released “to benefit research community”, with a citation requested. Fetchedat run time.": (
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
    "Read the two. Tingling in the stomach and butterflies in the stomach are the same symptom;"
    " palpitations and a rapid heartbeat are the same symptom; trembling hands appear in both."
    " The model also records how long each has lasted and when it happens, which the expert note"
    " does not. It shares almost no *words* with the clinician, and a metric that counts shared"
    " words scores it accordingly.": (
        "Přečtěte si obojí. Mravenčení v žaludku a motýlci v břiše jsou tentýž příznak; "
        "palpitace a zrychlený tep jsou tentýž příznak; třesoucí se ruce jsou v obou. Model "
        "navíc zaznamenává, jak dlouho co trvá a kdy k tomu dochází, což expertní zápis "
        "neuvádí. S klinikem nesdílí skoro žádná *slova* a metrika, která sdílená slova počítá, "
        "ho podle toho i oboduje."
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
    # -- the Czech track, both halves ------------------------------------------
    "Czech · ten real sessions, one client": "Čeština · deset skutečných sezení, jeden klient",
    "Czech, real sessions": "Čeština, skutečná sezení",
    "Czech · AnnoMI conversations, translated": "Čeština · rozhovory AnnoMI, přeložené",
    "Czech, translated": "Čeština, přeložená",
    # --- the Deepsy format ------------------------------------------------
    "Deepsy format \u00b7 ten real sessions, one client": (
        "Formát Deepsy \u00b7 deset skutečných sezení, jeden klient"
    ),
    "Deepsy format \u00b7 AnnoMI conversations, translated": (
        "Formát Deepsy \u00b7 rozhovory AnnoMI, přeložené"
    ),
    "Deepsy, real sessions": "Deepsy, skutečná sezení",
    "Deepsy, translated": "Deepsy, přeložená",
    "The same models and the same ten sessions, asked for the note format the Deepsy"
    " application actually writes rather than for SOAP. Three of its eleven sections,"
    " the three with a SOAP counterpart, scored by the same seven criteria. **What"
    " changes between this table and the Czech one is the shape the model was asked"
    " for and nothing else**, so a difference between them is a fact about the"
    " format.": (
        "Tytéž modely a tatáž desítka sezení, ale požádané o formát zápisu, který "
        "aplikace Deepsy opravdu píše, místo o SOAP. Tři z jejích jedenácti sekcí — "
        "ty tři, které mají protějšek v SOAP — hodnocené týmiž sedmi kritérii. **Mezi "
        "touto tabulkou a tou českou se mění tvar, o který byl model požádán, a nic "
        "jiného**, takže rozdíl mezi nimi je výrok o formátu."
    ),
    "The Deepsy sections on notes written from translated AnnoMI. The same comparison"
    " as the real half, on conversations that are public -- and the same warning: the"
    " two halves differ in length by a factor of seven before any question of format"
    " arises.": (
        "Sekce Deepsy na zápisech psaných z přeloženého AnnoMI. Totéž srovnání jako "
        "u skutečné půlky, na rozhovorech, které jsou veřejné — a totéž varování: ty "
        "dvě půlky se liší délkou sedmkrát, ještě než přijde na řadu otázka formátu."
    ),
    "The note alone, on the same seven Czech criteria as the SOAP tracks. The prompts"
    " are reproduced from the Deepsy application word for word, with its questionnaire"
    " blocks removed the way the application removes them for a client who has filled"
    " nothing in.": (
        "Samotný zápis, na týchž sedmi českých kritériích jako tracky SOAP. Prompty "
        "jsou reprodukované z aplikace Deepsy slovo od slova, s odstraněnými "
        "dotazníkovými bloky — tak, jak je aplikace odstraňuje klientovi, který nic "
        "nevyplnil."
    ),
    "None. Nobody has rated these notes, and the therapist wrote no comparison note in"
    " this format either.": (
        "Žádná. Tyhle zápisy nikdo nehodnotil a terapeut v tomhle formátu srovnávací "
        "zápis nenapsal."
    ),
    "Not calibrated, like the Czech criteria it shares. What this track adds is not a"
    " calibration but a control: the same models and sessions in a second format, so"
    " that what a criterion measures about a model can be told apart from what it"
    " measures about the shape of the note.": (
        "Nekalibrováno, stejně jako česká kritéria, která sdílí. Co tenhle track "
        "přidává, není kalibrace, ale kontrola: tytéž modely a sezení ve druhém "
        "formátu, aby šlo odlišit, co kritérium měří na modelu, od toho, co měří na "
        "tvaru zápisu."
    ),
    "The note alone, on the same seven criteria, over the translated AnnoMI conversations.": (
        "Samotný zápis, na týchž sedmi kritériích, přes přeložené rozhovory AnnoMI."
    ),
    "None, in the same two senses as the real half.": (
        "Žádná, ve stejných dvou smyslech jako u skutečné půlky."
    ),
    "Not calibrated. Read against the Czech SOAP table on the same conversations,"
    " which is the comparison this track exists for.": (
        "Nekalibrováno. Čte se proti české tabulce SOAP na týchž rozhovorech, což je "
        "srovnání, kvůli kterému tenhle track existuje."
    ),
    # --- PDSQI-9 over the Czech notes -----------------------------------
    "PDSQI-9 · the Czech notes from the real sessions": (
        "PDSQI-9 · české poznámky ze skutečných sezení"
    ),
    "PDSQI-9, real sessions": "PDSQI-9, skutečná sezení",
    "PDSQI-9 · the Czech notes from translated AnnoMI": (
        "PDSQI-9 · české poznámky z přeloženého AnnoMI"
    ),
    "PDSQI-9, translated": "PDSQI-9, přeložená",
    "The same Czech notes as the real-session table, asked a published quality "
    "instrument instead of the seven language criteria. The criteria cannot say "
    "whether a note is any good -- a flawless Czech sentence about nothing passes "
    "all seven -- and this is the half of the question they leave out. **Six "
    "attributes, not eight:** `accurate` and `thorough` can only be answered "
    "by reading the session, and both judges run at Google and at OpenAI -- "
    "outside the university infrastructure the sessions sit on. Asking those "
    "two would mean sending a real session out to them. The columns are absent "
    "because of where the judge is, not because of anything the notes lack.": (
        "Tytéž české poznámky jako v tabulce se skutečnými sezeními, ale místo sedmi "
        "jazykových kritérií se jich ptá publikovaný nástroj na kvalitu. Kritéria "
        "neumějí říct, jestli je poznámka dobrá — bezchybná česká věta o ničem projde "
        "všemi sedmi — a tohle je ta půlka otázky, kterou vynechávají. **Šest "
        "atributů, ne osm:** na `accurate` a `thorough` se dá odpovědět jen "
        "z přečteného sezení, a oba soudci běží u Googlu a u OpenAI — mimo "
        "univerzitní infrastrukturu, na které ta sezení leží. Zeptat se na ně by "
        "znamenalo poslat jim skutečné sezení. Ty dva sloupce chybějí kvůli tomu, "
        "kde je soudce, ne kvůli něčemu, co by poznámkám chybělo."
    ),
    "PDSQI-9 on the notes written from translated AnnoMI. All eight attributes "
    "here: these transcripts are public, so the judge may read the session and "
    "answer whether the note is accurate and thorough. **Eight columns against "
    "the real half's six is two instruments, not one**, and the two tables are "
    "not rows of each other.": (
        "PDSQI-9 na poznámkách psaných z přeloženého AnnoMI. Tady všech osm atributů: "
        "tyhle přepisy jsou veřejné, takže soudce smí přečíst sezení a odpovědět, jestli "
        "je poznámka přesná a důkladná. **Osm sloupců proti šesti u skutečné půlky jsou "
        "dva přístroje, ne jeden**, a ty dvě tabulky nejsou navzájem svými řádky."
    ),
    "The note alone, on six of PDSQI-9's eight attributes. The instrument and "
    "its prompt are reproduced in English; the note is Czech and is shown with "
    "the Czech headings the model wrote, because rendering it under English ones "
    "would rate an artefact nobody produced.": (
        "Samotná poznámka, na šesti z osmi atributů PDSQI-9. Nástroj i jeho prompt jsou "
        "reprodukované anglicky; poznámka je česky a ukazuje se s českými nadpisy, které "
        "napsal model — vykreslit ji pod anglickými by znamenalo hodnotit útvar, jaký "
        "nikdo nenapsal."
    ),
    "None. No human has rated these notes on PDSQI-9, and the therapist wrote "
    "no comparison note here.": (
        "Žádná. Tyhle poznámky nikdo z lidí na PDSQI-9 nehodnotil a terapeut sem "
        "srovnávací poznámku nenapsal."
    ),
    "Not calibrated. Physicians agree with each other on this instrument at "
    "Krippendorff's alpha 0.575, which is the ceiling any judge would be read "
    "against -- but nobody has rated these notes, so there is no agreement "
    "figure for this table, only the ceiling one would be read against if it "
    "existed.": (
        "Nekalibrováno. Lékaři se na tomhle nástroji navzájem shodnou na "
        "Krippendorffově alfa 0.575, což je strop, proti kterému by se každý soudce "
        "četl — jenže tyhle poznámky nikdo nehodnotil, takže pro tuhle tabulku žádné "
        "číslo shody není, jen strop, proti kterému by se četlo, kdyby existovalo."
    ),
    "The note and the session, on all eight attributes. These transcripts are "
    "AnnoMI translated into Czech and carry nothing confidential, which is the "
    "whole reason `accurate` and `thorough` can be asked here and not of the "
    "real half.": (
        "Poznámka i sezení, na všech osmi atributech. Tyhle přepisy jsou AnnoMI "
        "přeložené do češtiny a nenesou nic důvěrného — a přesně proto se tu `accurate` "
        "a `thorough` ptát smí a u skutečné půlky ne."
    ),
    "None, in the same two senses as the real half: no comparison note and no human rating.": (
        "Žádná, ve stejných dvou smyslech jako u skutečné půlky: žádná srovnávací "
        "poznámka a žádné lidské hodnocení."
    ),
    "Not calibrated, and read against the same 0.575 ceiling. What this half "
    "adds is the join: the same conversations carry PDSQI-9 numbers in English "
    "on the `pdsqi-soap` track, so a model's quality there and its quality here "
    "are about the same sessions on the same instrument.": (
        "Nekalibrováno, a čte se proti témuž stropu 0.575. Co tahle půlka přidává, je "
        "spojení: tytéž rozhovory nesou anglická čísla PDSQI-9 na tracku `pdsqi-soap`, "
        "takže kvalita modelu tam a jeho kvalita tady jsou o týchž sezeních a o témž "
        "přístroji."
    ),
    "Seven yes/no criteria about the Czech, asked of the note alone. Each column is the share of"
    " notes free of that fault. **Ten sessions with one client, so adjacent positions are not"
    " separable** -- and the generation prompt is a translation of TN-Eval's rather than a"
    " reproduction of anything.": (
        "Sedm kritérií ano/ne o té češtině, kladených samotnému zápisu. Každý sloupec je podíl "
        "zápisů, které tou vadou netrpí. **Deset sezení s jedním klientem, takže sousední pozice "
        "nejsou oddělitelné** — a generovací prompt je překlad promptu z TN-Eval, ne reprodukce "
        "čehokoli."
    ),
    "The same criteria on notes written from AnnoMI conversations translated into Czech. **The"
    " two halves differ by more than language** -- AnnoMI is motivational interviewing about"
    " substance use and the real sessions are not -- so a model doing worse here may be doing"
    " worse at motivational interviewing rather than at translated Czech.": (
        "Táž kritéria na zápisech psaných z rozhovorů AnnoMI přeložených do češtiny. **Ty dvě "
        "poloviny se liší víc než jazykem** — AnnoMI je motivační rozhovor o užívání návykových "
        "látek a skutečná sezení nejsou — takže model, kterému to tu jde hůř, může být horší "
        "v motivačním rozhovoru, a ne v přeložené češtině."
    ),
    "The note alone. Seven yes/no questions about the Czech itself -- diacritics, calques,"
    " untranslated English terms, agreement, register, quotation marks, non-words -- and each"
    " column is the share of notes free of that fault. The judge is never shown the transcript,"
    " which is why a confidential session can be scored at all.": (
        "Samotný zápis. Sedm otázek ano/ne o té češtině — diakritika, kalky, nepřeložené "
        "anglické termíny, shoda, rejstřík, uvozovky, neslova — a každý sloupec je podíl zápisů, "
        "které tou vadou netrpí. Hodnotiteli se přepis nikdy neukáže, a právě proto se důvěrné "
        "sezení vůbec dá obodovat."
    ),
    "The same seven criteria as the real-session table, on notes written from AnnoMI"
    " conversations translated into Czech. The translation is identical for every model, so it"
    " cancels when models are compared; it does not cancel for any claim about how well models"
    " write Czech.": (
        "Týchž sedm kritérií jako v tabulce se skutečnými sezeními, na zápisech psaných "
        "z rozhovorů AnnoMI přeložených do češtiny. Překlad je pro každý model stejný, takže se "
        "při srovnávání modelů vyruší; nevyruší se u žádného tvrzení o tom, jak dobře modely píší "
        "česky."
    ),
    "None. No human wrote a comparison note in Czech and no human has rated these notes on these"
    " criteria. That is one row this table does not have and the two English tables do.": (
        "Nikde. Žádný člověk nenapsal srovnávací zápis v češtině a žádný člověk tyto zápisy podle "
        "těchto kritérií nehodnotil. To je řádek, který tato tabulka nemá a obě anglické mají."
    ),
    "Not possible yet, and weaker than either English track. There is no published Czech"
    " note-quality instrument to reproduce, so these criteria are this repository's own; no human"
    " has rated these notes on them, and unlike PDSQI-9 there is not even a published figure for"
    " how well two people would agree. Two independent judges answer every question, and where"
    " they disagree is the only control this track has -- which is also why a criterion every"
    " model passes is reported as unmeasured rather than as agreement.": (
        "Zatím to nejde, a je to slabší než u kterékoli anglické větve. Neexistuje publikovaný "
        "český nástroj na kvalitu zápisu, který by se dal reprodukovat, takže tato kritéria jsou "
        "vlastní tomuto repozitáři; nikdo z lidí podle nich tyto zápisy nehodnotil a na rozdíl "
        "od PDSQI-9 tu není ani publikované číslo o tom, jak moc by se shodli dva lidé. Na každou "
        "otázku odpovídají dva nezávislí hodnotitelé a to, kde se neshodnou, je jediná kontrola, "
        "kterou tato větev má — a proto se také kritérium, které projde každému modelu, vykazuje "
        "jako nezměřené, ne jako shoda."
    ),
    "Not possible yet, for the reasons the real-session table gives. What this half adds is a"
    " join: the same conversations carry English numbers on the TN-Eval track, so a model's"
    " standing there and its Czech here are about the same sessions. Whether one predicts the"
    " other is the question this track was built to answer.": (
        "Zatím to nejde, z důvodů, které uvádí tabulka se skutečnými sezeními. Co tato polovina "
        "přidává, je spojka: tytéž rozhovory nesou anglická čísla ve větvi TN-Eval, takže "
        "postavení modelu tam a jeho čeština tady jsou o týchž sezeních. Jestli jedno předpovídá "
        "druhé, je otázka, kvůli které tato větev vznikla."
    ),
    # -- the seven criteria ------------------------------------------------------
    "Diacritics": "Diakritika",
    "Whether any Czech word in the note has a missing or wrong length mark or hachek. A word"
    " Czech does not have at all belongs to another criterion. Reported as the share of notes"
    " free of it.": (
        "Zda má některé české slovo v zápise chybějící nebo špatnou čárku či háček. Slovo, které "
        "čeština vůbec nemá, patří k jinému kritériu. Vykázáno jako podíl zápisů, které tím "
        "netrpí."
    ),
    "Calques": "Kalky",
    "Whether the note contains a phrase built by translating English word for word. An English"
    " word left as it was belongs to another criterion. Reported as the share of notes free of"
    " it.": (
        "Zda zápis obsahuje obrat vzniklý překladem angličtiny slovo od slova. Anglické slovo "
        "ponechané tak, jak bylo, patří k jinému kritériu. Vykázáno jako podíl zápisů, které tím "
        "netrpí."
    ),
    "Untranslated terms": "Nepřeložené termíny",
    "Whether an English clinical term was left in English. International abbreviations that Czech"
    " documentation uses as they are do not count. Reported as the share of notes free of it.": (
        "Zda byl anglický klinický termín ponechán anglicky. Mezinárodní zkratky, které česká "
        "dokumentace používá tak, jak jsou, se nepočítají. Vykázáno jako podíl zápisů, které tím "
        "netrpí."
    ),
    "Agreement": "Shoda",
    "Whether any sentence has broken agreement, a wrong case, or is left unfinished. A clumsy but"
    " grammatical sentence does not count. Reported as the share of notes free of it.": (
        "Zda má některá věta porušenou shodu, špatný pád, nebo zůstala nedokončená. Neobratná, "
        "ale gramatická věta se nepočítá. Vykázáno jako podíl zápisů, které tím netrpí."
    ),
    "Register": "Rejstřík",
    "Whether the note slips out of the register of clinical documentation into colloquial or"
    " emotive wording. A quotation of the client does not count. Reported as the share of notes"
    " free of it.": (
        "Zda zápis vypadává z rejstříku klinické dokumentace do hovorového nebo citově "
        "zabarveného vyjadřování. Citace klienta se nepočítá. Vykázáno jako podíl zápisů, které "
        "tím netrpí."
    ),
    "Quotation marks": "Uvozovky",
    "Whether the note uses a straight quotation mark or an apostrophe where Czech uses its own"
    " marks. Counted from the characters in the note rather than asked of a judge, and only of"
    " notes that quote anything at all. Reported as the share of notes free of it.": (
        "Zda zápis používá rovnou uvozovku nebo apostrof tam, kde má čeština své vlastní "
        "znaky. Počítáno ze znaků v zápisu, nikoli dotazem na soudce, a jen u zápisů, které "
        "vůbec něco citují. Vykázáno jako podíl zápisů, které tím netrpí."
    ),
    "Non-words": "Neslova",
    "Whether the note contains a word Czech does not have. A proper noun, a diacritic slip and an"
    " English term left in English each belong elsewhere. Reported as the share of notes free of"
    " it.": (
        "Zda zápis obsahuje slovo, které čeština nemá. Vlastní jméno, přehlédnutá diakritika "
        "a anglický termín ponechaný anglicky patří každé jinam. Vykázáno jako podíl zápisů, "
        "které tím netrpí."
    ),
    # One sentence, seven columns: the caveat is the same on every criterion,
    # because what it warns about is the shape of the question rather than the
    # fault it asks about.
    "Asked of the note alone, with no transcript and no reference: it says nothing about whether"
    " the note is true or complete. An invented note in faultless Czech passes. Reported as the"
    " share of notes free of the fault, so higher is better.": (
        "Kladeno samotnému zápisu, bez přepisu a bez reference: neříká to nic o tom, zda je zápis "
        "pravdivý nebo úplný. Vymyšlený zápis v bezchybné češtině projde. Vykázáno jako podíl "
        "zápisů, které tou vadou netrpí, takže vyšší je lepší."
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
