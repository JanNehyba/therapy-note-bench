"""The Czech text of the briefing, keyed by the English it replaces.

Separate from `czech_brief.py` so that the document's prose can be read and
corrected as prose, by somebody who is not reading the code around it -- and so
that the tool itself carries no Czech, which keeps the diacritic scanner's
allow-list to the files that genuinely need to be on it.

**Only this document's own sentences.** Column labels, measure definitions and
caveats are already translated in `tnb.i18n`, because the published pages are
bilingual and those are the same strings; `_t` looks there second and nothing is
duplicated here.

Two rules the translations keep, both because the English keeps them:

- **A number in the English appears in the Czech**, unchanged. `tests/test_i18n.py`
  enforces that on the published pages for a reason: a translation that quietly
  states a different figure is worse than no translation.
- **A hedge stays a hedge.** "may be doing worse" is not "dela hur"; the
  caveats are the half of this document that matters when it leaves the machine,
  and a translation that firms them up has removed the point of them.
"""

from __future__ import annotations

CS: dict[str, str] = {
    # --- the page itself ---------------------------------------------------
    "Does an English leaderboard say anything about clinical Czech?": (
        "Říká anglický žebříček něco o klinické češtině?"
    ),
    "therapy-note-bench · Czech track · measured, not published": (
        "therapy-note-bench · český track · změřeno, nepublikováno"
    ),
    "The benchmark this belongs to scores model-written psychotherapy notes on two "
    "English corpora. A model's standing there is a statement about English. This "
    "track asks whether it carries over: the same models write notes in Czech, from "
    "real sessions and from translated ones, and two instruments are asked about the "
    "result. Six yes/no criteria ask whether the Czech is right. PDSQI-9, a "
    "published instrument, asks whether the note is any good -- because the criteria "
    "cannot: a flawless Czech sentence about nothing passes all six.": (
        "Benchmark, ke kterému tohle patří, hodnotí modely psané psychoterapeutické "
        "zápisy na dvou anglických korpusech. Umístění modelu tam je výrok o angličtině. "
        "Tenhle track se ptá, jestli se to přenáší: tytéž modely píší zápisy česky, ze "
        "skutečných sezení i z přeložených, a na výsledek se ptají dva nástroje. Sedm "
        "kritérií ano/ne se ptá, jestli je čeština správně. PDSQI-9, publikovaný "
        "nástroj, se ptá, jestli je zápis dobrý — protože kritéria to neumějí: "
        "bezchybná česká věta o ničem projde všemi šesti."
    ),
    "These numbers are not on the public site and this document is not a publication.": (
        "Tato čísla nejsou na veřejném webu a tento dokument není publikace."
    ),
    "They were measured from confidential clinical material and the decision to "
    "publish anything from them has not been made. The transcripts were de-identified "
    "before any model saw them, and no transcript text appears in this document or in "
    "any file it was built from.": (
        "Byla změřena z důvěrného klinického materiálu a rozhodnutí cokoli z nich "
        "publikovat nepadlo. Přepisy byly anonymizovány dřív, než je uviděl jakýkoli "
        "model, a v tomto dokumentu ani v žádném souboru, ze kterého vznikl, není "
        "žádný text z přepisů."
    ),
    "What these numbers cannot be used for": "K čemu tato čísla nejdou použít",
    "How it was measured": "Jak se to měřilo",
    "The two corpora": "Dva korpusy",
    "Two halves, both read only from a directory that is not in version control. "
    "Every model wrote a note from every transcript, on e-INFRA.": (
        "Dvě půlky, obě čtené jen z adresáře, který není ve verzovacím systému. Každý "
        "model napsal zápis z každého přepisu, na e-INFRA."
    ),
    "They are not the same size:": "Nejsou stejně velké:",
    "a real session runs seven times longer than a translated AnnoMI conversation, so "
    "the two halves differ in how hard the summarising is before language is "
    "considered at all.": (
        "skutečné sezení je sedmkrát delší než přeložený rozhovor AnnoMI, takže se ty "
        "dvě půlky liší v tom, jak těžké je shrnování, ještě než přijde na řadu jazyk."
    ),
    "No judge is ever shown a real session.": "Žádný soudce nikdy neuvidí skutečné sezení.",
    "What leaves for the judge's provider is the note a model wrote, which is what "
    "lets a confidential session be scored at all. The one place a transcript is sent "
    "is the PDSQI table on the translated half: those transcripts are AnnoMI, "
    "published under CC-BY, and sending them buys the two attributes -- is the note "
    "accurate, is it thorough -- that cannot be answered without the session. The real "
    "half is asked the other six and those two columns are absent from it, because the "
    "question could not be put rather than because a note failed.": (
        "K poskytovateli soudce odchází zápis, který napsal model, a právě to umožňuje "
        "důvěrné sezení vůbec hodnotit. Jediné místo, kam se posílá přepis, je tabulka "
        "PDSQI na přeložené půlce: ty přepisy jsou AnnoMI, publikované pod CC-BY, a "
        "jejich odesláním se kupují dva atributy — je zápis přesný, je důkladný — na "
        "které se bez sezení odpovědět nedá. Skutečná půlka dostane zbylých šest a ty "
        "dva sloupce v ní chybějí proto, že se ta otázka nedala položit, ne proto, že "
        "by zápis propadl."
    ),
    "Each criterion is one question, answered yes or no, asked in its own call. A "
    "column is the share of notes free of that fault, so higher is better throughout. "
    "A judge that answered neither yes nor no is recorded as not having answered -- "
    'never as "no fault" -- and a note with no content is not asked at all, because '
    "every one of the six asks about the absence of a fault and an empty note would "
    "pass all six.": (
        "Každé kritérium je jedna otázka, odpověď ano nebo ne, každá ve vlastním dotazu. "
        "Sloupec je podíl zápisů, které tou chybou netrpí, takže vyšší je vždy lepší. "
        "Soudce, který neodpověděl ani ano ani ne, je veden jako bez odpovědi — nikdy "
        "jako „bez chyby“ — a na zápis bez obsahu se neptáme vůbec, protože všech šest "
        "kritérií se ptá na nepřítomnost chyby a prázdný zápis by prošel všemi."
    ),
    "PDSQI-9 is reproduced in English, word for word, because a translated instrument "
    "is a different instrument with nothing validating it. The note it rates is Czech "
    "and is shown with the Czech headings the model wrote. Seven of its eight "
    "attributes are rated 1 to 5 and the eighth is a yes/no; they are reported "
    "separately and never averaged, which is how the instrument's own authors report "
    "them.": (
        "PDSQI-9 je reprodukované anglicky, slovo od slova, protože přeložený nástroj "
        "je jiný nástroj a nic ho nevaliduje. Zápis, který hodnotí, je český a ukazuje "
        "se s českými nadpisy, které napsal model. Sedm z osmi atributů se hodnotí "
        "1 až 5 a osmý je ano/ne; vykazují se zvlášť a nikdy se neprůměrují, jak je "
        "vykazují sami autoři nástroje."
    ),
    # --- table headings ----------------------------------------------------
    "Model": "Model",
    "Notes in the mean": "Zápisů v průměru",
    "Half": "Půlka",
    "Sessions": "Sezení",
    "Words, median": "Slov, medián",
    "Words, range": "Slov, rozsah",
    "Turns, median": "Replik, medián",
    "Does it separate the models?": "Rozliší modely?",
    "What is behind the number": "Co je za tím číslem",
    "Criterion": "Kritérium",
    "Attribute": "Atribut",
    "Real sessions": "Skutečná sezení",
    "Translated AnnoMI": "Přeložené AnnoMI",
    "one client, de-identified by hand, never released": (
        "jeden klient, anonymizováno ručně, nikdy nezveřejněno"
    ),
    "public counselling conversations, translated for this track": (
        "veřejné poradenské rozhovory, přeložené pro tenhle track"
    ),
    "What each column is": "Co který sloupec je",
    # --- per-table prose ---------------------------------------------------
    "Judged by": "Hodnotil",
    "Two judges, two tables, and they are not averaged. Where they disagree about a "
    "model is the only control this track has, so the disagreement is the thing to "
    "read.": (
        "Dva soudci, dvě tabulky, a neprůměrují se. To, kde se na modelu neshodnou, je "
        "jediná kontrola, kterou tenhle track má — takže ta neshoda je to, co se má číst."
    ),
    "These rows are an average of well under all their notes, because the judge left "
    "some questions unanswered and a note is only counted when every criterion of it "
    "was answered:": (
        "Tyto řádky jsou průměrem výrazně méně než všech svých zápisů, protože soudce "
        "nechal některé otázky bez odpovědi a zápis se počítá jen tehdy, když byla "
        "zodpovězena všechna jeho kritéria:"
    ),
    "Unanswered questions cluster on the longer notes, so what is missing is not a "
    "random sample of the corpus. Read these rows as provisional.": (
        "Nezodpovězené otázky se hromadí u delších zápisů, takže to, co chybí, není "
        "náhodný vzorek korpusu. Čtěte tyto řádky jako předběžné."
    ),
    "Not drawn: this track was also scored under": (
        "Nevykresleno: tenhle track byl hodnocen také podle"
    ),
    ", an earlier version of the rubric. Those rows are a different instrument rather "
    "than an earlier attempt at this one, so they are named here and not placed beside "
    "these. They remain in the local record.": (
        ", což je starší verze rubriky. Ty řádky jsou jiný nástroj, ne dřívější pokus "
        "o tenhle, takže jsou tu jmenovány a nekladou se vedle těchto. V lokálním "
        "záznamu zůstávají."
    ),
    # --- the verdicts section ---------------------------------------------
    "What is behind each number": "Co je za každým číslem",
    "A column that gives most models the same value cannot rank them, however "
    "confidently it is printed, and the first thing worth knowing about any column "
    "here is whether it separates anything at all. That half is counted from the rows. "
    "The second half — what the column actually catches, and how far two judges and "
    "one native speaker agreed about it — is written down rather than computed, "
    "because no arithmetic supplies it.": (
        "Sloupec, který dává většině modelů tutéž hodnotu, je nemůže seřadit, ať je "
        "vytištěný sebejistěji — a první, co se o kterémkoli sloupci vyplatí vědět, je, "
        "jestli vůbec něco rozlišuje. Tuhle půlku počítáme z řádků. Druhou půlku — co "
        "ten sloupec doopravdy chytá a nakolik se na něm shodli dva soudci a jeden "
        "rodilý mluvčí — píšeme, ne počítáme, protože ji žádná aritmetika nedodá."
    ),
    "cannot rank": "nedokáže seřadit",
    "share one value": "sdílí jednu hodnotu",
    "tells": "rozliší",
    "apart": "z",
    # --- the join section --------------------------------------------------
    "Does the English leaderboard predict the Czech?": ("Předpovídá anglický žebříček tu češtinu?"),
    "Asked the same question, quality transfers": ("Při stejně položené otázce se kvalita přenáší"),
    "Asked the leaderboard's own measure, it does not": (
        "Při měřítku, podle kterého žebříček řadí, se nepřenáší"
    ),
    "PDSQI-9 on the English notes against PDSQI-9 on the Czech ones. Same attributes, "
    "same anchors, same judge; only the language of the note differs.": (
        "PDSQI-9 na anglických zápisech proti PDSQI-9 na českých. Tytéž atributy, tytéž "
        "kotvy, týž soudce; liší se jen jazyk zápisu."
    ),
    "-- what the page sorts by, so what a position means -- against the Czech quality "
    "columns. Nothing here survives the test, and the two judges do not agree even on "
    "the sign.": (
        "— podle čeho stránka řadí, tedy co znamená umístění — proti českým sloupcům "
        "kvality. Nic z toho testem neprojde a dva soudci se neshodnou ani na znaménku."
    ),
    "Flat on one side and therefore not correlated:": (
        "Ploché na jedné straně, a proto nekorelováno:"
    ),
    # --- the anchor section ------------------------------------------------
    "How often a judge and one native speaker said the same thing": (
        "Jak často řekli soudce a jeden rodilý mluvčí totéž"
    ),
    "not answered yet": "zatím bez odpovědi",
    "unanswered": "bez odpovědi",
    "All questions": "Všechny otázky",
    "notes, drawn by a hash of the session and the model so that no score could "
    "influence which ones were rated.": (
        "zápisů, vybraných hashem sezení a modelu, aby výběr nemohlo ovlivnit žádné skóre."
    ),
    # --- small words in composed lines -------------------------------------
    "models": "modelů",
    "notes": "zápisů",
    "rubric": "rubrika",
    "of": "z",
    "flat": "ploché",
    "Czech note quality": "Kvalita českých zápisů",
    "Generated by tools/czech_brief.py from local/czech-rows.jsonl. Both are gitignored.": (
        "Vygenerováno nástrojem tools/czech_brief.py z local/czech-rows.jsonl. "
        "Oba soubory jsou mimo verzování."
    ),
    "models. Whether a standing in one predicts a standing in the other has two "
    "answers, and which one a reader gets depends on which English number they were "
    "looking at. Bold is a correlation that survives an exact permutation test at "
    "p < 0.05.": (
        "modelů. Zda umístění v jedné předpovídá "
        "umístění v druhé, má dvě odpovědi, a kterou "
        "čtenář dostane, závisí na tom, na které "
        "anglické číslo se díval. Tučně je korelace, "
        "která obstojí v přesném permutačním testu na "
        "p < 0.05."
    ),
    # --- the human anchor's own sentences ----------------------------------
    "One native speaker answered all six questions for each of twenty notes. A "
    "language model presented each note, pointed at candidate faults and asked; the "
    "person decided every answer, including one where he overruled the model. The "
    "sample was drawn by a hash of the session and the model, so no score could "
    "influence which notes were rated.": (
        "Jeden rodilý mluvčí odpověděl na všech šest "
        "otázek u každého z dvaceti zápisů. Jazykový model "
        "mu každý zápis předložil, ukázal na "
        "možné chyby a zeptal se; člověk rozhodl každou "
        "odpověď, včetně jedné, kde model přehlasoval. "
        "Vzorek byl vybrán hashem sezení a modelu, aby výběr "
        "nemohlo ovlivnit žádné skóre."
    ),
    "There is one rater, so there is no human-against-human ceiling to read this "
    "against. It is not an accuracy: it is how often a judge and one native speaker "
    "said the same thing.": (
        "Hodnotitel je jeden, takže neexistuje strop člověk proti "
        "člověku, proti kterému by se to dalo číst. Není "
        "to úspěšnost: je to, jak často řekli soudce a jeden "
        "rodilý mluvčí totéž."
    ),
    # --- what these numbers cannot be used for -----------------------------
    "Ten sessions, and they are all one client": ("Deset sezení, a všechna jsou jeden klient"),
    "Every model wrote a note from every transcript, which is what makes the "
    "comparison between models valid at all -- the first attempt gave each model a "
    "different session and could not tell a worse model from a harder session. But "
    "ten notes per model is a small number, and the real half is one client with one "
    "therapist. Read the ordering, not the gaps between neighbours.": (
        "Každý model napsal zápis z každého přepisu, a "
        "právě to dělá srovnání mezi modely vůbec "
        "platným — první pokus dal každému modelu jiné "
        "sezení a neuměl odlišit horší model od "
        "těžšího sezení. Deset zápisů na model je "
        "ale málo a skutečná půlka je jeden klient s "
        "jedním terapeutem. Čti pořadí, ne rozestupy mezi "
        "sousedy."
    ),
    "The two halves differ by more than language, and mostly by size": (
        "Ty dvě půlky se liší víc než jazykem, a hlavně velikostí"
    ),
    "A real session runs to a median of {real_words} words and {real_turns} turns; a "
    "translated AnnoMI conversation to {other_words} words and {other_turns} turns. Seven "
    "times the material, so the "
    "summarising is a harder task before any question of Czech arises. They differ in "
    "topic too -- AnnoMI is motivational interviewing about substance use and the real "
    "sessions are not -- and in who transcribed them. A model that does worse on one "
    "half may be doing worse at length, at motivational interviewing, or at Czech, and "
    "these numbers cannot separate the three.": (
        "Skutečné sezení má medián {real_words} slov a {real_turns} replik; "
        "přeložený rozhovor AnnoMI {other_words} slov a {other_turns} replik. Sedmkrát "
        "víc materiálu, takže shrnování je těžší "
        "úkol ještě před jakoukoli otázkou o "
        "češtině. Liší se i tématem — AnnoMI je "
        "motivační rozhovor o návykových látkách a "
        "skutečná sezení nejsou — a tím, kdo je "
        "přepisoval. Model, který dopadne hůř na jedné "
        "půlce, může být horší v délce, v "
        "motivačním rozhovoru, nebo v češtině, a tato "
        "čísla ty tři věci neumějí oddělit."
    ),
    "Nothing here says whether a note is true": ("Nic tady neříká, jestli je zápis pravdivý"),
    "The criteria ask about the Czech and nothing else. A fluent, correctly typeset, "
    "entirely invented note passes all six. Whether the note says what the session "
    "contained is a different measurement and this is not it.": (
        "Kritéria se ptají na češtinu a na nic jiného. "
        "Plynulý, správně vysazený a úplně vymyšlený "
        "zápis projde všemi šesti. Zda zápis říká to, co "
        "sezení obsahovalo, je jiné měření a tohle to "
        "není."
    ),
    "The instrument has never been checked against a person": (
        "Nástroj nebyl nikdy ověřen proti člověku"
    ),
    "These six criteria are this repository's own, because no published Czech "
    "note-quality instrument exists to reproduce. Nobody has rated these notes by "
    "hand, and unlike PDSQI-9 there is not even a published figure for how well two "
    "people would agree on them. Two independent judges answer every question, and "
    "where they disagree is the only control there is.": (
        "Těch šest kritérií je vlastních tomuto "
        "repozitáři, protože žádný publikovaný "
        "český nástroj na kvalitu zápisů neexistuje. Tyto "
        "zápisy nikdo ručně nehodnotil a na rozdíl od PDSQI-9 "
        "není ani publikované číslo, jak dobře by se na nich "
        "shodli dva lidé. Na každou otázku odpovídají dva "
        "nezávislí soudci a to, kde se neshodnou, je jediná kontrola, "
        "která tu je."
    ),
    "SOAP is not what a Czech psychologist writes": ("SOAP není to, co píše český psycholog"),
    "The prompt is a translation of TN-Eval's, so that the task is the same task in "
    "another language and the English numbers mean something beside these. It is not a "
    "reproduction of any Czech documentation standard -- there is none to reproduce. "
    "The notes are therefore formally artificial, equally so for every model.": (
        "Prompt je překlad toho z TN-Eval, aby úkol byl týž "
        "úkol v jiném jazyce a anglická čísla vedle "
        "těchto něco znamenala. Není to reprodukce žádné "
        "české dokumentační normy — žádná k "
        "reprodukci není. Zápisy jsou proto formálně "
        "umělé, stejně tak u každého modelu."
    ),
    "A criterion every model passes is not agreement": (
        "Kritérium, kterým projdou všechny modely, není shoda"
    ),
    "Where every model scores the same, two judges agreeing about it says nothing: a "
    "correlation over a column of identical values is a coin. Such columns are "
    "reported as unmeasured rather than as unanimous.": (
        "Tam, kde mají všechny modely stejné skóre, "
        "neříká shoda dvou soudců nic: korelace přes sloupec "
        "shodných hodnot je hod mincí. Takové sloupce se vykazují "
        "jako nezměřené, ne jako jednomyslné."
    ),
    # --- what each column catches ------------------------------------------
    "Reliable. The two judges answered the same way on 79% of notes and one native "
    "speaker agreed with them on 18 of 20.": (
        "Spolehlivé. Dva soudci odpověděli stejně u 79 % "
        "zápisů a jeden rodilý mluvčí s nimi souhlasil u 18 "
        "z 20."
    ),
    "The weakest column here, and it should be read as a flag rather than a score. The "
    "two judges agree on only 67% of notes -- the lowest of the seven -- and a native "
    "speaker agreed with them on 11 of 20 and 7 of 20. Whether a Czech phrase is a "
    "literal translation from English is a judgement people make differently, and "
    "these numbers show that rather than hiding it.": (
        "Nejslabší sloupec tady a měl by se číst jako "
        "upozornění, ne jako známka. Dva soudci se shodnou jen u 67 % "
        "zápisů — nejméně ze sedmi — a rodilý "
        "mluvčí s nimi souhlasil u 11 z 20 a 7 z 20. Zda je český "
        "obrat doslovným překladem z angličtiny, posuzují lidé "
        "různě, a tato čísla to ukazují, místo aby to "
        "skrývala."
    ),
    "Reliable, and the fault it catches is unambiguous: an English term sitting in a "
    "Czech sentence. Judges agree on 87% of notes, the native speaker on 19 of 20.": (
        "Spolehlivé a chyba, kterou chytá, je jednoznačná: "
        "anglický termín sedící v české větě. "
        "Soudci se shodnou u 87 % zápisů, rodilý mluvčí u 19 "
        "z 20."
    ),
    "Catches real grammatical faults, but the two judges answer differently on a "
    "quarter of notes. A gap of one or two notes between models is inside that noise.": (
        "Chytá skutečné gramatické chyby, ale dva soudci "
        "odpovídají různě u čtvrtiny zápisů. "
        "Rozdíl jednoho nebo dvou zápisů mezi modely je uvnitř "
        "tohohle šumu."
    ),
    "Catches colloquial words where clinical ones belong. Judges agree on 75% of "
    "notes; the native speaker agreed with the first judge on 19 of 20 and with the "
    "second on 15.": (
        "Chytá hovorová slova tam, kam patří odborná. Soudci "
        "se shodnou u 75 % zápisů; rodilý mluvčí souhlasil s "
        "prvním soudcem u 19 z 20 a s druhým u 15."
    ),
    "Read this one against the prompt, not against the models. The same models on the "
    "same sessions score 0.00 here and 0.90 to 1.00 in the Deepsy format, and the "
    "prompt behind this table contains no Czech quotation mark at all while the Deepsy "
    "one does. "
    "Exact. It is not a judgement at all any more -- the characters in the note are "
    "counted. It became a count after a native speaker and a judge disagreed on nearly "
    "half the notes and neither was wrong: the question named only the straight double "
    "mark, and 45 of the 75 notes that quote anything use an apostrophe instead. The "
    "question now names both.": (
        "Tenhle sloupec čti proti promptu, ne proti modelům. Tytéž modely na týchž "
        "sezeních tu mají 0.00 a ve formátu Deepsy 0.90 až 1.00, a prompt za touhle "
        "tabulkou neobsahuje jedinou českou uvozovku, zatímco ten od Deepsy ano. "
        "Přesné. Už to vůbec není úsudek — "
        "počítají se znaky v zápisu. Počítáním "
        "se to stalo poté, co se rodilý mluvčí a soudce "
        "neshodli u skoro poloviny zápisů a ani jeden se nemýlil: "
        "otázka jmenovala jen rovnou dvojitou uvozovku a 45 ze 75 zápisů, "
        "které něco citují, místo ní používá "
        "apostrof. Otázka teď jmenuje obě."
    ),
    "The strongest agreement with a person of the seven: 20 of 20 against the first "
    "judge, 17 against the second.": (
        "Nejsilnější shoda s člověkem ze sedmi: 20 z 20 proti prvnímu soudci, 17 proti druhému."
    ),
    "Says almost nothing. One judge gave 5.00 to every model.": (
        "Neříká skoro nic. Jeden soudce dal 5.00 všem modelům."
    ),
    "Says nothing, and this was written down before the run rather than after. Every "
    "model writes into the same four-part template because the prompt tells it to, so "
    "a question about structure has nothing left to separate.": (
        "Neříká nic, a bylo to zapsáno před během, ne po "
        "něm. Každý model píše do též "
        "čtyřdílné šablony, protože mu to zadání "
        "říká, takže otázce po struktuře nezbývá "
        "co rozlišovat."
    ),
    "Does not separate the models: most of them print the same value.": (
        "Neodliší modely: většina jich má tutéž hodnotu."
    ),
    "Works, and every model fails it. No model reaches the middle of the scale under "
    "either judge. This is the one column on the real half that tells the models apart "
    "at all.": (
        "Funguje a každý model v něm propadá. Žádný "
        "model nedosáhne středu stupnice ani u jednoho soudce. Je to jediný "
        "sloupec na skutečné půlce, který modely vůbec "
        "rozlišuje."
    ),
    "Says nothing. 5.00 for every model under both judges on both halves.": (
        "Neříká nic. 5.00 pro každý model u obou soudců na obou půlkách."
    ),
    "Does not separate the models. Most of them are free of it, which is the good news "
    "and also why the column cannot rank anything.": (
        "Neodliší modely. Většina jich tím netrpí, "
        "což je dobrá zpráva a zároveň důvod, proč "
        "ten sloupec nemůže nic řadit."
    ),
    "The most informative column in this document, and it exists only on the "
    "translated half, because answering it means reading the session. The two judges "
    "order the models almost identically here.": (
        "Nejinformativnější sloupec v tomto dokumentu a existuje jen na "
        "přeložené půlce, protože odpovědět na "
        "něj znamená číst sezení. Dva soudci tu řadí "
        "modely skoro stejně."
    ),
    "Also only on the translated half. The judges agree far less about it than about "
    "accuracy, so read large gaps and ignore small ones.": (
        "Také jen na přeložené půlce. Soudci se na něm "
        "shodnou mnohem méně než na přesnosti, takže "
        "čti velké rozestupy a malé ignoruj."
    ),
    # --- the planted-error control -----------------------------------------
    "Does each column detect what it claims?": "Chytá každý sloupec to, co tvrdí?",
    "One clean note and {variants} variants, each carrying exactly one deliberate fault of "
    "one kind. This is the only check that can tell a column that measures something "
    "from a column that produces numbers.": (
        "Jeden čistý zápis a {variants} variant, každá s právě jednou "
        "záměrnou chybou jednoho druhu. Je to jediná kontrola, "
        "která umí odlišit sloupec, jenž něco měří, od sloupce, "
        "jenž jen vyrábí čísla."
    ),
    "at least one judge reports this fault in a note that does not have it, or misses "
    "it in a note that does. Read that column as a question rather than as an answer "
    "-- the disagreement is the finding.": (
        "aspoň jeden soudce hlásí tuto chybu v zápisu, který ji nemá, "
        "nebo ji přehlédne v zápisu, který ji má. Čti ten sloupec "
        "jako otázku, ne jako odpověď — ta neshoda je ten nález."
    ),
    "Every criterion found its own fault under every judge, and none fired on the clean note.": (
        "Každé kritérium našlo svou vlastní chybu u každého soudce "
        "a žádné se nespustilo na čistém zápisu."
    ),
    # --- the join's caveats ------------------------------------------------
    "The English scores are over all 50 AnnoMI conversations and the Czech over the 10 "
    "that were translated, so these are two standings rather than two scores on one "
    "set of sessions. Removing it means recomputing the English side over the same "
    "ten, which has not been done.": (
        "Anglická skóre jsou přes všech 50 rozhovorů AnnoMI a "
        "česká přes těch 10, které byly přeložené, takže jde o "
        "dvě umístění, ne o dvě skóre na jedné množině sezení. "
        "Odstranit to znamená přepočítat anglickou stranu přes "
        "týchž deset, což uděláno nebylo."
    ),
    "Nine models. Read a column that says the same thing under both judges; treat one "
    "that does not as unmeasured rather than as weak evidence.": (
        "Devět modelů. Čti sloupec, který říká totéž u obou soudců; "
        "s tím, který ne, zacházej jako s nezměřeným, ne jako se slabým "
        "důkazem."
    ),
    # --- how far apart is far enough ---------------------------------------
    "How far apart is far enough?": "Jak daleko od sebe je dost daleko?",
    "Ten notes per model. The sessions were resampled two thousand times, paired on "
    "the transcript because every model wrote from all ten, and each pair of models "
    "compared on the middle 95% of the result. Two numbers per column: how many of "
    "the model pairs come out apart, and how large a gap it takes. A difference "
    "smaller than that is the same reading printed twice, whichever way round it "
    "fell.": (
        "Deset zápisů na model. Sezení byla dva tisíckrát převzorkována, "
        "párově podle přepisu, protože každý model psal ze všech deseti, "
        "a každá dvojice modelů porovnána na prostředních 95 % výsledku. "
        "Dvě čísla na sloupec: kolik dvojic modelů vyjde odlišně a jak velký "
        "rozdíl je na to potřeba. Menší rozdíl je totéž měření vytištěné "
        "dvakrát, ať vyšlo v kterémkoli pořadí."
    ),
    "pairs apart": "odlišené dvojice",
    "gap needed": "potřebný rozdíl",
    "These columns order the transcripts, not the models.": (
        "Tyto sloupce řadí přepisy, ne modely."
    ),
    "The ten sessions differ from each other more than the eleven models do, so "
    "whatever order the rows come out in is a fact about which transcripts were "
    "drawn. No threshold rescues them; do not read them:": (
        "Těch deset sezení se od sebe liší víc než těch jedenáct modelů, "
        "takže ať řádky vyjdou v jakémkoli pořadí, je to výrok o tom, které "
        "přepisy padly. Žádná mez je nezachrání; nečtěte je:"
    ),
    # --- bands, not places -------------------------------------------------
    "Bands, not places": "Pásma, ne pořadí",
    "Eleven models over ten notes cannot be put in order, and a table that prints "
    "them in one invites a comparison it cannot support. These are the same numbers "
    "grouped instead: within a band nothing separates the models, between bands "
    "something does. A band ends where the gap exceeds what resampling the sessions "
    "can rule out, so its width is the measurement's own resolution.": (
        "Jedenáct modelů na deseti zápisech nejde seřadit a tabulka, která je "
        "v pořadí vytiskne, zve ke srovnání, které neunese. Tady jsou tatáž čísla "
        "seskupená: uvnitř pásma modely nic neodlišuje, mezi pásmy ano. Pásmo končí "
        "tam, kde rozdíl přesáhne to, co převzorkování sezení dokáže vyloučit — "
        "jeho šířka je tedy rozlišovací schopnost samotného měření."
    ),
    "a band is": "pásmo je široké",
    "wide, over": "a stojí na",
    "sessions": "sezeních",
    "Band": "Pásmo",
    "Score": "Skóre",
    "Models": "Modely",
    # --- dominance ---------------------------------------------------------
    "The only claim about better that survives": ("Jediné tvrzení o lepším, které obstojí"),
    "Two judges order the models differently, so a position in a table is not a "
    "claim. What survives both of them is dominance: one model at least as good as "
    "another on every criterion, under each judge separately, and strictly better on "
    "at least one. Everything not listed here is a pair this project cannot "
    "separate. Each block below is one note format, and a pair holds only inside it: "
    "a Deepsy note is longer than a SOAP one, and length costs points on every one of "
    "these criteria, so a pair read across the two would be reporting that confound "
    "as a verdict.": (
        "Dva soudci řadí modely různě, takže umístění v tabulce není tvrzení. Co "
        "obstojí u obou, je dominance: model, který je aspoň tak dobrý jako jiný "
        "v každém kritériu, u každého soudce zvlášť, a aspoň v jednom je striktně "
        "lepší. Všechno, co tu není vypsané, je dvojice, kterou tenhle projekt "
        "neumí odlišit. Každý blok níž je jeden formát zápisu a dvojice platí jen "
        "uvnitř něj: zápis Deepsy je delší než SOAP a délka stojí body v každém "
        "z těchto kritérií, takže dvojice čtená napříč oběma formáty by ohlašovala "
        "tenhle zmatek jako výsledek."
    ),
    "is at least as good as": "je aspoň tak dobrý jako",
    "possible pairs.": "možných dvojic.",
    "No model here is at least as good as another on every criterion under both judges.": (
        "Žádný zdejší model není aspoň tak dobrý jako jiný ve všech kritériích u obou soudců."
    ),
    # --- the columns that do not order -------------------------------------
    "These columns do not order the models either.": ("Ani tyto sloupce modely neseřadí."),
    "Fewer than a quarter of the model pairs come apart, so the sequence of rows is "
    "mostly the order chance put them in. The column may still be worth reading as a "
    "level -- how often the fault appears at all -- but not as a ranking:": (
        "Odliší se méně než čtvrtina dvojic modelů, takže posloupnost řádků je "
        "většinou pořadí, do kterého je dala náhoda. Sloupec může pořád stát za "
        "čtení jako úroveň — jak často se ta chyba vůbec objevuje — ale ne jako "
        "pořadí:"
    ),
    # --- general capability against these numbers --------------------------
    "Does general capability predict any of this?": ("Předpovídá obecná schopnost něco z tohohle?"),
    "Nothing in this repository records how big a model is or when it shipped, so this "
    "comes from outside it. Bold survives a permutation test at p < 0.05.": (
        "Nic v tomhle repozitáři nezaznamenává, jak velký model je ani kdy vyšel, "
        "takže tohle pochází zvenčí. Tučné obstálo v permutačním testu na p < 0.05."
    ),
    "Measured here": "Měřeno tady",
    "Intelligence index": "Index inteligence",
    "Release date": "Datum vydání",
    "English completeness": "Anglická úplnost",
    "English quality (PDSQI-9)": "Anglická kvalita (PDSQI-9)",
    "Czech quality (PDSQI-9)": "Česká kvalita (PDSQI-9)",
    "Czech language (the six criteria)": "Čeština (šest kritérií)",
    "None of this was measured here.": "Nic z toho jsme neměřili my.",
    "The models are matched to the public ones by name, and a name on the endpoint is "
    "not evidence about which model is behind it -- this project's first working rule "
    "exists because one returned another's output. Models whose name does not identify "
    "a variant are absent rather than guessed:": (
        "Modely jsou k těm veřejným přiřazené podle jména a jméno na endpointu není "
        "důkaz o tom, který model za ním stojí — první pracovní pravidlo tohohle "
        "projektu vzniklo proto, že jeden vracel výstup jiného. Modely, jejichž jméno "
        "neurčuje variantu, tu nejsou, místo aby se hádaly:"
    ),
    "The external score is versioned like the measures here are, so it is recorded "
    "with the version and the day it was read:": (
        "Externí skóre má verzi stejně jako měřidla tady, takže se zaznamenává "
        "s verzí a dnem, kdy bylo přečteno:"
    ),
    # --- the reframing and the scales --------------------------------------
    "How well do language models write Czech therapy notes?": (
        "Jak dobře píší jazykové modely české terapeutické zápisy?"
    ),
    "{models} models were each asked for a note from twenty psychotherapy sessions -- "
    "ten real and ten translated -- and two independent judges rated every note that "
    "came back. {written} of the {asked} notes were written; the rest are named where "
    "they are missing. Two "
    "instruments: six yes/no criteria asking whether the Czech is right, and "
    "PDSQI-9, a published instrument, asking whether the note is any good. Both, "
    "because neither answers the other: a flawless Czech sentence about nothing passes "
    "all six criteria, and a note full of insight can be written in bad Czech.": (
        "{models} modelů dostalo zadání napsat zápis z dvaceti psychoterapeutických "
        "sezení — deseti skutečných a deseti přeložených — a každý zápis, který "
        "přišel, ohodnotili dva nezávislí soudci. Napsáno bylo {written} zápisů z "
        "{asked}; kde některý chybí, je to napsané u té tabulky. Dva nástroje: šest "
        "kritérií ano/ne, která se ptají, "
        "jestli je čeština správně, a PDSQI-9, publikovaný nástroj, který se ptá, "
        "jestli je zápis dobrý. Oba, protože jeden na druhého neodpovídá: bezchybná "
        "česká věta o ničem projde všemi šesti kritérii a zápis plný vhledu může být "
        "napsaný špatnou češtinou."
    ),
    "A second question runs alongside: the same models are ranked on an English "
    "leaderboard, and whether that standing says anything about the Czech they write "
    "has its own section below.": (
        "Vedle toho běží druhá otázka: tytéž modely jsou seřazené na anglickém "
        "žebříčku a jestli to umístění říká něco o češtině, kterou píší, má vlastní "
        "sekci níže."
    ),
    "Every column is 0 to 1 and higher is better: the share of notes free of that fault.": (
        "Každý sloupec je 0 až 1 a vyšší je lepší: podíl zápisů, které tou chybou netrpí."
    ),
    "Every column is 1 to 5 and higher is better.": ("Každý sloupec je 1 až 5 a vyšší je lepší."),
    "Higher is better throughout. Most columns are rated 1 to 5; the last is the share "
    "of notes free of the fault, from 0 to 1.": (
        "Vyšší je lepší všude. Většina sloupců je hodnocená 1 až 5; poslední je podíl "
        "zápisů bez té chyby, od 0 do 1."
    ),
    # --- real against translated -------------------------------------------
    "Real sessions or translated ones?": "Skutečná sezení, nebo přeložená?",
    "real": "skutečná",
    "translated": "přeložená",
    "The translated half comes out ahead on four of the six criteria under both "
    "judges. Each judge alone gives it five, but not the same five: "
    "gemini-3.1-pro-preview puts the real half ahead on Register and gpt-5.6-terra on "
    "Untranslated terms, and neither reversal is rounding. Bold marks where translated "
    "beats real.": (
        "Přeložená půlka je napřed ve čtyřech ze šesti kritérií u obou soudců. Každý "
        "soudce sám jí dá pět, ale pokaždé jiných pět: gemini-3.1-pro-preview dává "
        "skutečnou půlku napřed v Rejstříku a gpt-5.6-terra v Nepřeložených termínech, "
        "a ani jedno obrácení není zaokrouhlení. Tučně je vyznačeno, kde přeložená "
        "přebíjí skutečnou."
    ),
    "It does not follow that the models write better Czech there.": (
        "Neplyne z toho, že tam modely píší lepší češtinu."
    ),
    "A real session runs seven times longer, the notes written from it are longer in "
    "turn, and every criterion asks whether a note contains a fault -- more text, more "
    "chances to have one. Matching the two halves on note length shrinks the gap but "
    "does not settle it: of three length bands, two still favour the translated half "
    "and one favours the real one, on 18 to 59 notes each. The halves also differ in "
    "topic and in who transcribed them. This comparison is worth printing and is not "
    "worth concluding from.": (
        "Skutečné sezení je sedmkrát delší, zápisy z něj jsou tím pádem delší taky, "
        "a každé kritérium se ptá, jestli zápis obsahuje chybu — víc textu, víc "
        "příležitostí ji mít. Srovnání obou půlek při stejné délce zápisu ten rozdíl "
        "zmenší, ale nerozhodne: ze tří délkových pásem dvě pořád nahrávají přeložené "
        "půlce a jedno té skutečné, na 18 až 59 zápisech. Půlky se navíc liší tématem "
        "a tím, kdo je přepisoval. Tohle srovnání stojí za vytištění a nestojí za "
        "závěr."
    ),
    # --- the criterion measured but not drawn ------------------------------
    # --- what it took ------------------------------------------------------
    "What it took": "Kolik to bylo práce",
    "Judges": "Soudci",
    "Every note was written on e-INFRA, the infrastructure that holds the sessions. "
    "Only the notes went anywhere else: each was put to two judges, one question per "
    "criterion, on Google's and OpenAI's endpoints. No price is given here -- a list "
    "price is a fact about a vendor on one day and is unreadable a year later without "
    "it.": (
        "Každý zápis vznikl na e-INFRA, tedy na infrastruktuře, která ta sezení drží. "
        "Ven šly jen zápisy: každý dostali dva soudci, jedna otázka na kritérium, na "
        "endpointech Googlu a OpenAI. Cena tu není — ceníková cena je výrok o jednom "
        "dodavateli v jeden den a bez toho dne je za rok nečitelná."
    ),
    "The two instruments rated the same notes, so the rows do not add up: "
    "{models} models wrote {written} notes in all, and each note was read twice by "
    "each judge -- once against the criteria and once against PDSQI-9.": (
        "Oba nástroje hodnotily tytéž zápisy, takže se řádky nesčítají: {models} "
        "modelů napsalo celkem {written} zápisů a každý z nich četl každý soudce "
        "dvakrát — jednou podle kritérií a jednou podle PDSQI-9."
    ),
    # --- what it took, the second pass ---------------------------------------
    "Calls to write them": ("Volání, aby vznikly"),
    "Every note was written on e-INFRA, the infrastructure that holds the sessions. Only "
    "the notes went anywhere else: each was put to two judges, one question per "
    "criterion, on Google's and OpenAI's endpoints.": (
        "Každý zápis vznikl na e-INFRA, tedy na infrastruktuře, která ta sezení drží. Ven šly "
        "jen zápisy: každý dostali dva soudci, jedna otázka na kritérium, na endpointech "
        "Googlu a OpenAI."
    ),
    "The Deepsy format is asked for one section at a time, so a note there is three "
    "answers rather than one: the same number of notes costs three times the calls.": (
        "Formát Deepsy se ptá po jedné sekci zvlášť, takže zápis v něm nejsou jedna, ale tři "
        "odpovědi: za týž počet zápisů se zaplatí trojnásobkem volání."
    ),
    # --- length ------------------------------------------------------------
    "How long the notes are, and whether length is rewarded": (
        "Jak dlouhé zápisy modely píšou a jestli se délka vyplácí"
    ),
    "Column": "Sloupec",
    "English \u00b7 TN-Eval SOAP": "Angličtina \u00b7 TN-Eval SOAP",
    "the data section": "sekce data",
    "the hypotheses section": "sekce hypotézy",
    "the plan section": "sekce plán",
    "{quiet} of the {families} prompt families say nothing at all about how long a "
    "note should be. "
    "The Deepsy prompt says it twice: a ceiling of {limit} words per section, which "
    "the prompt itself calls invalid to exceed, and a target of the same {limit} "
    "words.": (
        "{quiet} ze {families} rodin promptů o délce zápisu neříkají vůbec nic. Deepsy "
        "prompt to říká "
        "dvakrát: strop {limit} slov na sekci, jehož překročení sám označuje za "
        "nevalidní, a cílovou délku týchž {limit} slov."
    ),
    "The therapist who wrote the {n} reference notes for the English corpus used "
    "{human} words. Not one of the {systems} models comes near that: they write "
    "between {low} and {high} words, which is {share_low} to {share_high} of what the "
    "person wrote. Nobody set any of them a length, so this is what they do when left "
    "alone. It is the one place in this project where a human note can be compared "
    "with a model's at all, and the whole field of models sits on one side of "
    "it.": (
        "Terapeut, který napsal {n} referenčních poznámek k anglickému korpusu, "
        "použil {human} slov. Ani jeden z {systems} modelů se tomu nepřiblíží: píšou "
        "{low} až {high} slov, tedy {share_low} až {share_high} toho, co napsal "
        "člověk. Délku nikomu z nich nikdo nezadal, takže tohle dělají, když je "
        "necháme být. Je to jediné místo v celém projektu, kde jde lidskou poznámku s "
        "modelovou vůbec porovnat — a celé pole modelů leží na jedné straně."
    ),
    "Where a length WAS set, the ceiling was kept and the target was not. Only {over} "
    "of {answers} answers exceed the {limit}-word limit -- but {section} uses {share} "
    "of the length it was asked for. The models read \u201cmust not exceed\u201d and "
    "did not read \u201cthe target is {limit} words\u201d.": (
        "Tam, kde délka zadaná BYLA, se dodržel strop a nedodržel cíl. Limit {limit} "
        "slov překračuje jen {over} z {answers} odpovědí — ale {section} využívá "
        "{share} délky, o kterou si prompt řekl. Modely si přečetly „nesmí "
        "překročit“ a nepřečetly si „cílová délka je {limit} slov“."
    ),
    "The two languages then pull in opposite directions, and this is the most useful "
    "thing to know before reading any table above. In English a longer note scores "
    "higher for completeness under both judges. In Czech it scores lower on 38 of the "
    "48 criterion-judge coefficients, and the exceptions are named rather than rounded "
    "away: two hold under BOTH judges, and both are in the Deepsy format -- calques on "
    "the real half and agreement on the translated one. A column is printed here only "
    "when "
    "both judges agree on the direction and at least one of them reaches 0.40; both "
    "numbers are shown, so a column the two judges feel differently strongly about is "
    "visible as that rather than averaged away.": (
        "Oba jazyky pak táhnou na opačné strany a tohle je to nejužitečnější, co je "
        "dobré vědět dřív, než se člověk pustí do kterékoli tabulky výše. V angličtině "
        "delší zápis dostává vyšší úplnost, a to u obou soudců. V češtině má horší "
        "skóre v 38 z 48 kombinací kritéria a soudce — a výjimky se jmenují, ne "
        "zaokrouhlují: dvě platí u OBOU soudců a obě jsou ve formátu Deepsy, kalky na "
        "skutečné půlce a shoda na přeložené. "
        "Sloupec je tu vypsaný jen tehdy, když se oba soudci shodnou na směru a aspoň "
        "jeden z nich dosáhne 0,40; ukázaná jsou obě čísla, takže sloupec, který každý "
        "ze soudců cítí jinak silně, je vidět právě takový, a ne zprůměrovaný."
    ),
    "Before reading that as \u201cthese models write worse Czech\u201d: each Czech "
    "criterion asks one yes/no question about a whole note -- is there a fault "
    "ANYWHERE in it. A note of {longest} words offers more places for one to be found "
    "than a note of {shortest}. The check is what happens to the same models under the "
    "other instrument: on the language criteria the three longest-writing models take "
    "the last three places {hit} times out of {total}, and on PDSQI-9, rating the very "
    "same notes, they do not. Part of the bottom of the Czech tables is length, not "
    "Czech.": (
        "Než si to někdo přečte jako „tyhle modely píšou horší češtinu“: každé české "
        "kritérium klade jednu otázku ano/ne o celém zápisu — je v něm někde chyba? "
        "Zápis o {longest} slovech nabízí víc míst, kde ji najít, než zápis o "
        "{shortest} slovech. Kontrolou je, co se s týmiž modely stane pod druhým "
        "nástrojem: na jazykových kritériích obsadí tři nejdelší pisatelé poslední tři "
        "místa {hit}krát ze {total}, kdežto na PDSQI-9, které hodnotí úplně tytéž "
        "zápisy, ne. Část spodku českých tabulek je délka, ne čeština."
    ),
    "by design": "tak to má být",
    # --- the sort, named beside the table ----------------------------------
    "and": "a",
    "Nothing here separates these models: no column takes two different values.": (
        "Tady modely nerozlišuje nic: žádný sloupec nemá dvě různé hodnoty."
    ),
    "Sorted best first, by the one column that separates these models: {names}.": (
        "Seřazeno od nejlepšího, podle jediného sloupce, který tyhle modely rozlišuje: {names}."
    ),
    "Sorted best first, by the mean of these {count} columns: {names}.": (
        "Seřazeno od nejlepšího, podle průměru těchto {count} sloupců: {names}."
    ),
    "One more is the same for every model here, so it orders nothing and is left out.": (
        "Ještě jeden mají všechny modely stejný, takže nic neřadí a do pořadí nevstupuje."
    ),
    "The other {dropped} are the same for every model here, so they order nothing "
    "and are left out.": (
        "Ostatní sloupce ({dropped}) mají všechny modely stejné, takže nic neřadí a do "
        "pořadí nevstupují."
    ),
    # --- the rater figure, read rather than written ------------------------
    "One native speaker agreed with the two judges on {pairs} notes.": (
        "Jeden rodilý mluvčí se s oběma soudci shodl u {pairs} zápisů."
    ),
    "Reliable: the two judges answered the same way on 79% of notes.": (
        "Spolehlivé: oba soudci odpověděli stejně u 79 % zápisů."
    ),
    "The weakest column here, and it should be read as a flag rather than a score. "
    "The two judges agree on only 67% of notes, the lowest of the six. Whether a "
    "Czech phrase is a literal translation from English is a judgement people make "
    "differently, and these numbers show that rather than hiding it.": (
        "Nejslabší sloupec tady, a je lepší číst ho jako upozornění než jako známku. "
        "Oba soudci se shodnou jen u 67 % zápisů, což je ze šesti nejméně. Jestli je "
        "nějaké české spojení doslovný překlad z angličtiny, posuzují lidé různě, a "
        "tahle čísla to ukazují, místo aby to schovávala."
    ),
    "Reliable, and the fault it catches is unambiguous: an English term sitting in a "
    "Czech sentence. Judges agree on 87% of notes.": (
        "Spolehlivé a chyba, kterou chytá, je jednoznačná: anglický termín uprostřed "
        "české věty. Soudci se shodnou u 87 % zápisů."
    ),
    "Catches colloquial words where clinical ones belong. Judges agree on 75% of notes.": (
        "Chytá hovorová slova tam, kam patří odborná. Soudci se shodnou u 75 % zápisů."
    ),
    "The strongest agreement with a person under one judge, and tied with Diacritics over both.": (
        "U jednoho soudce nejsilnější shoda s člověkem, přes oba je na tom stejně jako Diakritika."
    ),
    # --- the conclusion, before the tables ---------------------------------
    "What eleven models did, in five sentences": ("Co jedenáct modelů dokázalo, v pěti větách"),
    "no models": "žádné modely",
    "No model": "Žádný model",
    "is": "je",
    "are": "jsou",
    "Part of what those language tables measure is length, and how much was measured "
    "rather than argued: each extra hundred words costs {low} to {high} hundredths of "
    "a point, under every judge on both halves. "
    "Subtracting it does not give an order that holds still, so none is printed. What "
    "survives a handicap that never lets the shorter writer win is {survived} of {decided} "
    "decided pairs.": (
        "Kolik z toho, co ty jazykové tabulky měří, je délka, je změřeno, ne dohadováno: "
        "každých sto slov navíc stojí {low} až {high} setin bodu, u každého soudce a na "
        "obou polovinách. Odečíst to "
        "nedá pořadí, které by se drželo, takže se žádné netiskne. Handicap, který kratšího "
        "pisatele nikdy nenechá vyhrát, přežije {survived} z {decided} rozhodnutých dvojic."
    ),
    "On writing correct Czech, {top} {top_verb} in the top band of all {tables} tables "
    "the bands cover -- the SOAP halves, both judges. {bottom} {bottom_verb} in the "
    "bottom band of all {tables}. Between those two ends the tables disagree with each "
    "other, so nothing else here is a ranking. The Deepsy tables are not in this: no "
    "band, dominance or separability figure has been computed for them.": (
        "Ve psaní správné češtiny {top_verb} {top} v nejvyšším pásmu všech {tables} "
        "tabulek, které pásma pokrývají — půlky SOAP, oba soudci. {bottom} {bottom_verb} "
        "v nejnižším pásmu všech {tables}. Mezi těmito dvěma konci si tabulky odporují, "
        "takže nic dalšího tu není pořadí. Deepsy tabulky v tom nejsou: nemají spočítané "
        "pásmo, dominanci ani odlišitelnost."
    ),
    "On whether the note is any good, no model is in the top band of all {tables} "
    "tables and none is in the bottom band of all {tables}. The quality instrument "
    "does not agree with itself from one judge or one half to the next, and no model "
    "can be called better on it.": (
        "V tom, jestli je zápis k něčemu, není v nejvyšším pásmu všech {tables} tabulek "
        "žádný model a v nejnižším také žádný. Nástroj na kvalitu se neshodne sám se "
        "sebou mezi soudci ani mezi půlkami, a žádný model podle něj nelze označit za "
        "lepší."
    ),
    "Part of why: under {judge}, {dead} of its {total} columns are the same for every "
    "model, so they order nothing. Of the {moving} that do move, the one no model does "
    "well on is {alive} -- the best reaches {worst} out of 5. The other judge separates "
    "more of them, and that the two disagree about which columns work is itself the "
    "finding.": (
        "Zčásti proto, že podle soudce {judge} mají {dead} z jeho {total} sloupců "
        "všechny modely stejné, takže nic neřadí. Ze zbylých {moving}, které se "
        "hýbou, je ten, v němž si nevede dobře nikdo, {alive} — nejlepší dosáhne "
        "{worst} z 5. Druhý soudce jich rozliší víc, a to, že se ti dva neshodnou na "
        "tom, které sloupce fungují, je samo o sobě nález."
    ),
    "Read the bottom of those tables carefully: the three models that write the "
    "longest notes take the last three places in all {total} of them. Each criterion "
    "asks whether there is a fault anywhere in a note, and a longer note has more "
    "places to hide one. On the quality instrument, rating the very same notes, those "
    "three models are not at the bottom.": (
        "Spodek těch tabulek čti opatrně: tři modely, které píšou nejdelší zápisy, "
        "obsazují poslední tři místa ve všech {total}. Každé kritérium se ptá, jestli "
        "je v zápisu někde chyba, a delší zápis má víc míst, kde ji schovat. Na "
        "nástroji na kvalitu, který hodnotí úplně tytéž zápisy, ty tři modely na "
        "spodku nejsou."
    ),
    "And the English leaderboard does not predict this. The same instrument asked in "
    "both languages transfers; the single measure the English page ranks by -- "
    "{measure} -- does not. A model's standing there says nothing about the Czech it "
    "writes.": (
        "A anglický leaderboard tohle nepředpovídá. Týž nástroj položený v obou "
        "jazycích se přenáší; jediné měřítko, podle kterého anglická stránka řadí — "
        "{measure} — nikoli. Postavení modelu tam neříká nic o češtině, kterou píše."
    ),
    # --- the plain length table --------------------------------------------
    "How long each model writes": "Jak dlouhé zápisy píše který model",
    "The median length of one note, in words, for every model and every corpus it "
    "wrote for. These are the notes the models generated -- not anything a judge "
    "wrote. Everything the rest of this section claims is about these numbers.": (
        "Medián délky jednoho zápisu ve slovech, pro každý model a každý korpus, do "
        "kterého psal. Jsou to zápisy, které vygenerovaly modely — ne nic, co by psal "
        "soudce. Všechno, co zbytek téhle sekce tvrdí, se týká těchhle čísel."
    ),
    "For scale: the therapist who wrote TN-Eval's reference notes used {human} words a "
    "note. {over}": (
        "Pro měřítko: terapeut, který psal referenční poznámky pro TN-Eval, použil "
        "{human} slov na poznámku. {over}"
    ),
    "No model here reaches that on any corpus.": (
        "Žádný model se tomu tady na žádném korpusu nepřiblíží."
    ),
    "Every model writes less than that on the English corpus, where nobody was given a "
    "length; on the Czech ones {names} write more.": (
        "Na anglickém korpusu, kde délku nikdo nezadal, píšou všechny modely méně; na "
        "těch českých píšou víc {names}."
    ),
    # --- the PDSQI control --------------------------------------------------
    "Can a quality column come back below 5?": ("Umí sloupec o kvalitě vůbec spadnout pod pětku?"),
    "Note": "Zápis",
    "the clean note": "čistý zápis",
    "same sentences, wrong sections": "tytéž věty, špatné sekce",
    "first section only, no assessment or plan": ("jen první sekce, bez hodnocení a bez plánu"),
    "every sentence said three times": "každá věta řečená třikrát",
    "One invented note, and three copies each damaged in one named way. No model "
    "and no session is involved: the question is not who writes well but whether "
    "the instrument can see a fault at all. What each variant was expected to move "
    "was written down before it was asked.": (
        "Jeden vymyšlený zápis a tři jeho kopie, každá poškozená jedním "
        "pojmenovaným způsobem. Nefiguruje v tom žádný model ani žádné sezení: "
        "otázka nezní, kdo píše dobře, ale jestli nástroj chybu vůbec uvidí. Co má "
        "která varianta pohnout, bylo zapsáno dřív, než se soudce zeptal."
    ),
    "It can, and this settles the flat columns: {columns} all drop under both "
    "judges on the note built to attack them. The judge is looking. These eleven "
    "models score the same because they write into the same dictated four-part "
    "structure and genuinely do not differ, not because the question goes "
    "unanswered -- so those columns stay in the tables, as an honest measurement "
    "of something that does not vary here.": (
        "Umí, a tím jsou ploché sloupce vysvětlené: {columns} klesnou u obou soudců "
        "na tom zápisu, který je na ně ušitý. Soudce se tedy dívá. Těch jedenáct "
        "modelů má stejné skóre proto, že píšou do téže předepsané čtyřdílné "
        "struktury a doopravdy se neliší — ne proto, že by otázka zůstala "
        "nezodpovězená. Ty sloupce tedy v tabulkách zůstávají jako poctivé měření "
        "něčeho, co tady nekolísá."
    ),
    "{columns} did not move even on the note built to attack them. A column whose "
    "value does not change when the fault it names is put in front of it is not "
    "measuring that fault, and its figures in the tables above should be read as "
    "unmeasured rather than as full marks.": (
        "{columns} se nehnuly ani na zápisu, který je na ně ušitý. Sloupec, jehož "
        "hodnota se nezmění, když mu člověk podstrčí přesně tu chybu, kterou "
        "pojmenovává, tu chybu neměří — a jeho čísla v tabulkách výše se mají číst "
        "jako nezměřeno, ne jako plný počet."
    ),
    "The damage is deliberate and extreme -- every sentence in the wrong section, "
    "a note with no plan at all. This says the instrument responds, not that it "
    "tells two ordinary notes apart. And no person has yet rated any of these "
    "notes on this instrument, so nothing here says a 5 is what a clinician would "
    "give.": (
        "To poškození je záměrné a hrubé — každá věta ve špatné sekci, zápis úplně "
        "bez plánu. Říká to, že nástroj reaguje, ne že rozliší dva obyčejné zápisy. "
        "A tímhle nástrojem zatím nehodnotil žádný člověk, takže odsud neplyne nic o "
        "tom, jestli by pětku dal i klinik."
    ),
    # --- said once, and named by what each section does ---------------------
    "Not drawn:": "Nevykresleno:",
    "were also scored under": "byly hodnoceny také podle",
    "which columns can rank": "které sloupce umí řadit",
    "who is ahead": "kdo je napřed",
    "how far apart is far enough": "jak daleko je dost daleko",
    "the six Czech criteria": "šest českých kritérií",
    "PDSQI-9, without the session": "PDSQI-9, bez sezení",
    "PDSQI-9, with the session": "PDSQI-9, se sezením",
    # --- two formats --------------------------------------------------------
    "The same models, the same sessions, two note formats": (
        "Tytéž modely, táž sezení, dva formáty zápisu"
    ),
    "Corpus": "Korpus",
    "Judge": "Soudce",
    "difference": "rozdíl",
    "worse in Deepsy": "horší v Deepsy",
    "{models} models wrote from the same sessions twice, on both corpora: once as a "
    "SOAP note, "
    "which is what TN-Eval asks for and what makes the English comparison possible, "
    "and once in the format the Deepsy application actually writes. The same six "
    "criteria, the same judges, the same rubric version -- only the format differs. "
    "Every one of the four comparisons goes the same way.": (
        "{models} modelů psalo z týchž sezení dvakrát, na obou korpusech: jednou jako "
        "SOAP zápis, "
        "což je to, oč si říká TN-Eval a co teprve umožňuje srovnání s angličtinou, a "
        "jednou ve formátu, který skutečně píše aplikace Deepsy. Táž šestice kritérií, "
        "titíž soudci, táž verze rubriky — liší se jen formát. Všechna čtyři srovnání "
        "vycházejí stejným směrem."
    ),
    "Do not read that as the Deepsy format producing worse Czech. It might, and "
    "these numbers cannot say so, because the two things move together: a Deepsy "
    "note is LONGER -- {longer} of {models} models write more in it, a median of "
    "{deepsy} words against {soap} -- and this document has already measured that a "
    "longer note scores lower on every one of these criteria, because each asks "
    "whether there is a fault ANYWHERE in it. Format and length point the same way "
    "here and ten models cannot separate them.": (
        "Nečti to jako „formát Deepsy vede k horší češtině“. Může, a tahle čísla to "
        "říct neumějí, protože se obojí hýbe společně: zápis v Deepsy je DELŠÍ — "
        "{longer} z {models} modelů v něm píše víc, medián {deepsy} slov proti {soap} "
        "— a tenhle dokument už změřil, že delší zápis má horší skóre na každém z "
        "těchto kritérií, protože každé se ptá, jestli je v něm chyba NĚKDE. Formát a "
        "délka tady ukazují týmž směrem a deset modelů je od sebe neoddělí."
    ),
    # --- the order column ---------------------------------------------------
    "Order": "Pořadí",
    "The Order column is the mean of these {count}: {names}. It is what the rows "
    "are sorted by and it is not a measurement -- weighting spelling against "
    "clinical terminology is a judgement, which is why no such index is "
    "published. It is here so the order can be checked rather than trusted.": (
        "Sloupec Pořadí je průměr těchto {count}: {names}. Podle něj jsou řádky "
        "seřazené a není to měření — vážit pravopis proti odborné terminologii je "
        "úsudek, a proto se žádný takový index nepublikuje. Je tu proto, aby se dalo "
        "pořadí ověřit, ne aby se mu muselo věřit."
    ),
    "The Order column is {names}, the one column that separates these models at "
    "all, and it is what the rows are sorted by.": (
        "Sloupec Pořadí je {names} — jediný sloupec, který tyhle modely vůbec "
        "rozlišuje, a řádky jsou seřazené podle něj."
    ),
    "What the Czech track found, in {count} short paragraphs": (
        "Co český track zjistil, ve {count} odstavcích"
    ),
    # --- one table, both judges --------------------------------------------
    "Every cell holds both judges, {judges}, in that order and never averaged: "
    "where they disagree about a model is the only control this track has, so it "
    "is shown rather than smoothed. A cell whose two numbers differ is marked.": (
        "V každé buňce jsou oba soudci, {judges}, v tomto pořadí a nikdy se "
        "neprůměrují: to, kde se na modelu neshodnou, je jediná kontrola, kterou "
        "tenhle track má, takže je vidět místo aby se zahladila. Buňka, kde se ta "
        "dvě čísla liší, je zvýrazněná."
    ),
    "The rows are ordered by dominance -- a model is above another only when it is "
    "at least as good on every column under BOTH judges -- so models the evidence "
    "cannot separate share a place, and {systems} models fall into {places} places "
    "of which {tied} hold more than one. Within a place the order is alphabetical "
    "and means nothing.": (
        "Řádky jsou seřazené podle dominance — model je výš jen tehdy, když je "
        "aspoň tak dobrý v každém sloupci u OBOU soudců — takže modely, které "
        "důkazy neoddělí, sdílejí místo: {systems} modelů padne do {places} míst, "
        "z toho {tied} drží víc než jeden model. Uvnitř místa je pořadí abecední a "
        "neznamená nic."
    ),
    # --- the external index, whose columns are judges ----------------------
    "as {judge} sees it": "jak to vidí {judge}",
    "Nothing here. All {cells} coefficients between {what} and what this project "
    "measures are inside what chance produces at this sample size, under both "
    "judges. Printed as a sentence rather than as a grid of numbers a reader has "
    "to work out says nothing.": (
        "Nic. Všech {cells} korelací mezi „{what}“ a tím, co tenhle projekt měří, "
        "leží uvnitř toho, co při téhle velikosti vzorku vyrobí náhoda, a to u obou "
        "soudců. Napsané větou místo mřížkou čísel, ze které si čtenář musí sám "
        "odvodit, že neříká nic."
    ),
    # --- what the notes column counts, and which rows are thin --------------
    "The notes column counts the ones every criterion of was answered, out of "
    "the sessions the model was asked for; a single column may average over more, "
    "because a note missing one answer still has the others.": (
        "Sloupec se zápisy počítá ty, u kterých bylo zodpovězeno každé kritérium, "
        "z počtu sezení, o která byl model požádán; jednotlivý sloupec může "
        "průměrovat přes víc zápisů, protože zápis, kterému chybí jedna odpověď, má "
        "ty ostatní."
    ),
    "These rows rest on well under their corpus, either because the model did not "
    "write the note or because the judge did not answer it. What goes missing "
    "clusters on the longest sessions, so it is not a random sample. Read them as "
    "provisional:": (
        "Tyhle řádky stojí na výrazně menším počtu, než je korpus — buď model zápis "
        "nenapsal, nebo na něj soudce neodpověděl. To, co chybí, se hromadí u "
        "nejdelších sezení, takže to není náhodný výběr. Čti je jako předběžné:"
    ),
    # --- refusals ----------------------------------------------------------
    "Refusing to write: a row carries something that is not a score.": (
        "Odmítám zapsat: řádek nese něco, co není skóre."
    ),
    "is not there. Run `tnb score-czech` first.": ("tam není. Spusťte nejdřív `tnb score-czech`."),
    ": a system id carries a run of digits": ": id systému nese řadu číslic",
    "scored row(s) from": "hodnocených řádků z",
    # --- how large the length effect is, and what survives it --------------
    "How large is it? Fitting each judge's composite of the criteria against the "
    "model's median note length costs {low} to {high} hundredths of a point per "
    "hundred words, across the four track-and-judge combinations. Drawing the "
    "{systems} models again with replacement {resamples} times, the ninety per cent "
    "interval clears zero on all four and the sign reverses in at most {wrong} of the "
    "draws. The direction is settled: on this corpus a longer note scores lower on "
    "Czech.": (
        "Jak je ten vliv velký? Když se u každého soudce proloží složené skóre "
        "kritérií mediánovou délkou zápisu, stojí to {low} až {high} setin bodu na "
        "sto slov, a to ve všech čtyřech kombinacích tracku a soudce. Když se těch "
        "{systems} modelů vylosuje znovu s vracením ({resamples} losování), "
        "devadesátiprocentní interval se ve všech čtyřech vyhne nule a znaménko se "
        "obrátí nejvýš v {wrong} losování. Směr je tedy rozhodnutý: na tomhle korpusu "
        "má delší zápis nižší skóre v češtině."
    ),
    "So why is there no length-adjusted column here? It was computed, and it will not "
    "hold still. Subtracting what length predicts and re-ranking gives an order whose "
    "safest position -- the last place -- survives redrawing the same models only "
    "{holds} of the time. A well-measured slope and a dependable order are different "
    "things: the slope is one number fitted to every model at once, while the adjusted "
    "order is {systems} small residuals competing with each other. The second reason "
    "would apply even if it held: length was not assigned to the models, they chose "
    "it. A model may write long BECAUSE it summarises badly, and then removing what "
    "length predicts removes the result along with the artefact.": (
        "Proč tu tedy není sloupec očištěný o délku? Spočítaný byl a neudrží se na "
        "místě. Když se odečte to, co délka předpovídá, a pořadí se sestaví znovu, "
        "vydrží i jeho nejjistější místo — poslední příčka — jen v {holds} případů, "
        "kdy se tytéž modely vylosují znovu. Dobře změřený sklon a spolehlivé pořadí "
        "jsou dvě různé věci: sklon je jedno číslo proložené všemi modely najednou, "
        "kdežto očištěné pořadí je {systems} malých zbytků, které spolu soupeří. "
        "Druhý důvod by platil, i kdyby se pořadí drželo: délka nebyla modelům "
        "přidělena, zvolily si ji samy. Model může psát dlouze PROTOŽE špatně "
        "shrnuje, a pak odečtení toho, co délka předpovídá, odečte spolu s artefaktem "
        "i výsledek."
    ),
    "What can be said without fitting anything is in the table. A pair of models "
    "counts as decided when one beats the other by more than {separation} on the "
    "composite under BOTH judges, and it survives the handicap when the winner also "
    "wrote at least as many words as the loser -- so the longer note had more places "
    "for a fault to be found and had fewer of them anyway. That leaves {survived} of "
    "the {decided} decided pairs, counting the two halves separately. What survives "
    "is a partial order and not a ranking, "
    "and how little of it there is is the finding.": (
        "Co se dá říct, aniž by se cokoli prokládalo, je v tabulce. Dvojice modelů se "
        "počítá za rozhodnutou, když jeden porazí druhého o víc než {separation} ve "
        "složeném skóre u OBOU soudců, a handicap přežije tehdy, když vítěz zároveň "
        "napsal aspoň tolik slov jako poražený — delší zápis tedy nabízel víc míst, "
        "kde chybu najít, a přesto jich měl míň. Takových je {survived} z {decided} "
        "rozhodnutých dvojic, počítáno na obou polovinách zvlášť. Co zbude, je "
        "částečné uspořádání, ne žebříček, a nález "
        "je právě to, jak málo toho je."
    ),
    "on the real sessions": "na skutečných sezeních",
    "on the translated ones": "na přeložených",
    "{margin} · {winner} vs {loser} words": "{margin} · {winner} vs {loser} slov",
    "Beats": "Poráží",
    "this model": "tento model",
}
