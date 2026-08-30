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
    "Every model was asked for a note from every transcript, on e-INFRA -- that is the "
    "design, and {written} of the {asked} notes are the outcome. Where a model wrote "
    "fewer, it is named: {short}.": (
        "Dvě půlky, obě čtené jen z adresáře, který není ve verzovacím systému. Každý "
        "model dostal zadání napsat zápis z každého přepisu, na e-INFRA — to je záměr "
        "a výsledek je {written} zápisů z {asked}. Kde model napsal míň, je "
        "jmenovaný: {short}."
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
    # --- the sentence every definition of one instrument ends with ---------
    # Cut off the end of each definition and said once above the list instead.
    # Keyed by the English tail, because that is what `czech_brief._SHARED_TAILS`
    # holds and what `_trim` looks up: without these three the Czech list
    # printed the same closing sentence under all six criteria.
    " Reported as the share of notes free of it.": (
        "Vykázáno jako podíl zápisů, které tím netrpí."
    ),
    " rated 1 (not at all) to 5 (extremely).": "hodnoceno 1 (vůbec) až 5 (zcela).",
    " answered yes or no and reported as the fraction of notes free of it.": (
        "odpověď ano/ne, vykázáno jako podíl zápisů, které jsou ho prosté."
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
    "What was measured, and on what": "Co se měřilo a na čem",
    "PDSQI-9": "PDSQI-9",
    "Every model was asked for a note from every one of these transcripts, in both "
    "halves, so no two models are ever compared on sessions of different difficulty. "
    "One half is recordings of real therapy with a single client, transcribed and "
    "de-identified by hand and never released. The other is public counselling "
    "conversations from the AnnoMI corpus, translated into spoken Czech for this "
    "track.": (
        "Každý model dostal za úkol napsat zápis z každého z těchto přepisů, v obou "
        "půlkách — takže se nikdy neporovnávají dva modely na různě těžkých sezeních. "
        "Jedna půlka jsou nahrávky skutečné terapie s jedním klientem, přepsané a ručně "
        "anonymizované, nikdy nezveřejněné. Druhá jsou veřejné poradenské rozhovory "
        "z korpusu AnnoMI, přeložené pro tenhle track do mluvené češtiny."
    ),
    "The translating was done by Claude, which is itself a language model, and anyone "
    "reading these numbers should know that before they read them. It was picked for "
    "being an outsider: no model in any table here, and neither judge, belongs to the "
    "family that wrote this Czech, so nothing is being marked on prose its own "
    "relatives produced.": (
        "Překládal Claude, což je sám o sobě jazykový model, a kdokoli tahle čísla čte, "
        "by to měl vědět dřív, než je začne číst. Vybrali jsme ho proto, že stojí "
        "mimo: žádný model v žádné zdejší tabulce ani jeden ze soudců nepatří do rodiny, "
        "která tuhle češtinu napsala, takže se nikomu neznámkuje text, který vyrobili "
        "jeho vlastní příbuzní."
    ),
    "The translating was done by Claude, which is itself a language model, and anyone "
    "reading these numbers should know that before they read them. It was picked for "
    "being an outsider, and that no longer holds: a model from the same family is in "
    "the tables below, so on this half it is being scored on Czech its own family "
    "wrote. Read its translated column against its real-session column rather than on "
    "its own.": (
        "Překládal Claude, což je sám o sobě jazykový model, a kdokoli tahle čísla čte, "
        "by to měl vědět dřív, než je začne číst. Vybrali jsme ho proto, že stojí mimo — "
        "a to už neplatí: v tabulkách níže je model ze stejné rodiny, takže se mu na "
        "téhle půlce známkuje čeština, kterou napsala jeho vlastní rodina. Jeho sloupec "
        "z přeložené půlky čtěte proti jeho sloupci ze skutečných sezení, ne samostatně."
    ),
    "The same translated text went to every model, and that matters in two opposite "
    "ways. Comparing the models with each other, the translation cancels: whatever it "
    "did to the Czech, it did equally to all of them, so a difference between two "
    "models on this half is still a difference between the models. For an absolute "
    'claim -- "these models write bad Czech" -- it does not cancel at all, because '
    "clumsiness the translation put into a transcript can come back out of the note "
    "written from it. That is what the real half is for: a fault that shows on both "
    "halves is the model's, and one that shows only on the translated half is the "
    "input's.": (
        "Každý model dostal tentýž přeložený text, a to má dva opačné důsledky. Při "
        "srovnávání modelů mezi sebou se překlad vyruší: cokoli s tou češtinou udělal, "
        "udělal to všem stejně, takže rozdíl mezi dvěma modely na téhle půlce je pořád "
        "rozdílem mezi modely. U absolutního tvrzení — „tyhle modely píšou špatnou "
        "češtinu“ — se nevyruší vůbec, protože neobratnost, kterou překlad dostal do "
        "přepisu, může vylézt ven i ze zápisu, který z něj vznikl. Právě na tohle je "
        "tam ta skutečná půlka: vada, která se ukáže na obou půlkách, je vada modelu, "
        "a vada, která se ukáže jen na přeložené, je vada vstupu."
    ),
    "The two halves are nothing like the same size: by the median word count a real "
    "session runs about {ratio} times as long as a translated conversation. The longer "
    "half is a harder summarising task before any question of Czech arises, so every "
    "comparison between the halves in this document is comparing that too.": (
        "Ty dvě půlky nejsou ani zdaleka stejně velké: podle mediánu počtu slov je "
        "skutečné sezení asi {ratio}× delší než přeložený rozhovor. Delší půlka je "
        "těžší úkol na shrnutí ještě dřív, než přijde na řadu čeština — takže každé "
        "srovnání těch dvou půlek v tomhle dokumentu porovnává i tohle."
    ),
    "One difference between the PDSQI tables, and it is an absence with a reason. Some "
    "of these attributes cannot be answered from the note alone: the judge has to read "
    "the session beside it. A real session is confidential and never leaves for a "
    "judge's provider, while the AnnoMI conversations are published under CC-BY and can "
    "be sent -- so on the real sessions those questions were never put. What is missing "
    "there is the question and not an answer a note did badly on, and the columns are "
    "absent rather than low: {columns}.": (
        "Jeden rozdíl mezi tabulkami PDSQI — a je to nepřítomnost s důvodem. Na některé "
        "z těchto atributů se nedá odpovědět ze samotného zápisu: soudce si k němu musí "
        "přečíst i sezení. Skutečné sezení je ale důvěrné a k poskytovateli soudce nikdy "
        "neodchází, zatímco rozhovory AnnoMI jsou publikované pod CC-BY a poslat se "
        "dají — takže u skutečných sezení se ty otázky nikdy nepoložily. Chybí tam ta "
        "otázka, ne odpověď, ve které by zápis propadl: tyhle sloupce tam nejsou vůbec, "
        "nejsou nízké: {columns}."
    ),
    "These columns are absent from one of these tables and this document does not "
    "record why. An absent column is a question that was not put, never a note that "
    "answered it badly: {columns}.": (
        "Tyhle sloupce v jedné z těch tabulek chybí a tenhle dokument nezaznamenává "
        "proč. Chybějící sloupec je otázka, která nebyla položena, nikdy ne zápis, "
        "který v ní propadl: {columns}."
    ),
    "How to read the tables": "Jak číst tabulky",
    "The Band column groups the models rather than ordering them: within a band nothing "
    "separates them, and a band ends where the gap exceeds what resampling the sessions "
    "can rule out, so a band's width is this measurement's own resolution.": (
        "Sloupec Pásmo modely seskupuje, ne řadí: uvnitř pásma je nic neodlišuje a "
        "pásmo končí tam, kde je rozdíl větší než to, co dokáže převzorkování sezení "
        "vyloučit — šířka pásma je tedy vlastní rozlišovací schopnost tohoto měření."
    ),
    "Like every other cell it holds one value per judge, so a model can be in band 1 "
    "under one judge and band 3 under the other; a marked Band cell is that "
    "disagreement, and the number in it is not a rank.": (
        "Stejně jako každá jiná buňka drží jednu hodnotu za každého soudce, takže model "
        "může být u jednoho soudce v pásmu 1 a u druhého v pásmu 3; zvýrazněná buňka "
        "Pásmo je právě tahle neshoda a číslo v ní není pořadí."
    ),
    "Each row is one language model. People wrote and transcribed the sessions; the "
    "models wrote the notes from them.": (
        "Každý řádek je jeden jazykový model. Sezení vedli a přepisy pořídili lidé; "
        "modely z nich napsaly zápisy."
    ),
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
    "because no arithmetic supplies it. It exists for one table only: both agreement "
    "figures were measured on the real Czech sessions under the six criteria, and "
    "nobody has read a Deepsy note, a translated one or a PDSQI answer against a "
    "person at all. Every other table says so in the cell rather than leaving it "
    "blank, because carrying a number across would report one table's measurement "
    "under another's heading.": (
        "Sloupec, který dává většině modelů tutéž hodnotu, je nemůže seřadit, ať je "
        "vytištěný sebejistěji — a první, co se o kterémkoli sloupci vyplatí vědět, je, "
        "jestli vůbec něco rozlišuje. Tuhle půlku počítáme z řádků. Druhou půlku — co "
        "ten sloupec doopravdy chytá a nakolik se na něm shodli dva soudci a jeden "
        "rodilý mluvčí — píšeme, ne počítáme, protože ji žádná aritmetika nedodá. "
        "Existuje jen k jedné tabulce: obě čísla o shodě byla změřena na skutečných "
        "českých sezeních podle šesti kritérií a zápis v Deepsy, přeložený zápis ani "
        "odpověď PDSQI nikdo proti člověku nečetl. Každá další tabulka to říká přímo "
        "v buňce, místo aby ji nechala prázdnou, protože přenést číslo jinam by "
        "znamenalo ohlásit měření jedné tabulky pod hlavičkou druhé."
    ),
    "not measured on this track": "na této větvi neměřeno",
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
    "Every model was asked for a note from every transcript, which is what makes "
    "the comparison between models valid at all -- the first attempt gave each "
    "model a different session and could not tell a worse model from a harder "
    "session. The asking held and the answering did not always: {written} of the "
    "{asked} notes came back, and the shortfalls are {short}. But "
    "ten notes per model is a small number, and the real half is one client with one "
    "therapist. Read the ordering, not the gaps between neighbours.": (
        "Každý model dostal zadání napsat zápis z každého "
        "přepisu, a právě to dělá srovnání mezi modely vůbec "
        "platným — první pokus dal každému modelu jiné "
        "sezení a neuměl odlišit horší model od "
        "těžšího sezení. Zadání drželo, odpovědi ne vždycky: "
        "vrátilo se {written} zápisů z {asked} a chybějící jsou tyhle: {short}. "
        "Deset zápisů na model je "
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
    "Ten notes per model at most. The sessions were resampled two thousand "
    "times and paired on the transcript, so a pair of models is compared only "
    "on the sessions both of them wrote and a pair with fewer than five in "
    "common is not compared at all. Each pair is then read on the middle 95% "
    "of the result. Two "
    "numbers per column: how many of the model pairs come out apart, and "
    "how large a gap it takes. A difference smaller than that is the same "
    "reading printed twice, whichever way round it fell.": (
        "Nanejvýš deset zápisů na model. Sezení byla dva tisíckrát převzorkována "
        "a párována podle přepisu, takže dvojice modelů se porovnává jen na "
        "sezeních, ze kterých psaly obě, a dvojice, která jich má společných méně "
        "než pět, se neporovnává vůbec. Každá dvojice se pak čte na prostředních "
        "95 % výsledku. "
        "Dvě čísla na sloupec: kolik dvojic modelů vyjde odlišně a jak velký "
        "rozdíl je na to potřeba. Menší rozdíl je totéž měření vytištěné "
        "dvakrát, ať vyšlo v kterémkoli pořadí."
    ),
    "Where a model wrote fewer than the corpus holds, that is where: {short}.": (
        "Kde model napsal míň, než kolik korpus obsahuje, je to tady: {short}."
    ),
    "pairs apart": "odlišené dvojice",
    "gap needed": "potřebný rozdíl",
    "These columns order the transcripts, not the models.": (
        "Tyto sloupce řadí přepisy, ne modely."
    ),
    "The sessions differ from each other more than the models do, so whatever order "
    "the rows come out in is a fact about which transcripts were drawn. No threshold "
    "rescues them; do not read them:": (
        "Sezení se od sebe liší víc než modely, "
        "takže ať řádky vyjdou v jakémkoli pořadí, je to výrok o tom, které "
        "přepisy padly. Žádná mez je nezachrání; nečtěte je:"
    ),
    # --- bands, not places -------------------------------------------------
    "Bands, not places": "Pásma, ne pořadí",
    "As many as {models} models over {notes} notes cannot be put in order, and a "
    "table that prints them in one invites a comparison it cannot support. These are "
    "the same numbers grouped instead: within a band nothing separates the models, "
    "between bands something does. A band ends where the gap exceeds what resampling "
    "the sessions can rule out, so its width is the measurement's own resolution.": (
        "Až {models} modelů na {notes} zápisech nejde seřadit a tabulka, která je "
        "v pořadí vytiskne, zve ke srovnání, které neunese. Tady jsou tatáž čísla "
        "seskupená: uvnitř pásma modely nic neodlišuje, mezi pásmy ano. Pásmo končí "
        "tam, kde rozdíl přesáhne to, co převzorkování sezení dokáže vyloučit — "
        "jeho šířka je tedy rozlišovací schopnost samotného měření."
    ),
    "a band is": "pásmo je široké",
    "wide, over at most": "a stojí nejvýš na",
    "sessions": "sezeních",
    "a pair is compared on the sessions both models wrote, and {names} wrote fewer": (
        "dvojice se porovnává na sezeních, ze kterých psaly oba modely, a {names} napsaly míň"
    ),
    "{answered} of {expected} judge answers": "{answered} z {expected} odpovědí soudce",
    "notes entered on fewer than {columns} criteria: {partial}": (
        "zápisů vstoupilo na méně než {columns} kritériích: {partial}"
    ),
    "how much each row rests on was not recorded for this table": (
        "u této tabulky nebylo zaznamenáno, na kolika zápisech každý řádek stojí"
    ),
    "{absent} not asked on this corpus, so this band averages {columns} of {named}": (
        "{absent} se na tomto korpusu neptáme, takže toto pásmo průměruje {columns} z {named}"
    ),
    "The rows do not rest on the same amount. A model's place is the mean of the "
    "notes it has, and where that is fewer than the table's sessions -- the model "
    "wrote no note, or the judge answered only part of one -- the count is printed "
    "beside its name.": (
        "Řádky nestojí na stejném množství. Místo modelu je průměrem zápisů, které má, "
        "a tam, kde je jich méně než sezení v tabulce — model zápis nenapsal, nebo "
        "soudce odpověděl jen na jeho část — je počet vytištěn vedle jeho jména."
    ),
    "These models are placed on well under the table's sessions, so the band they "
    "fall in is provisional:": (
        "Tyto modely stojí na výrazně méně než na sezeních tabulky, takže pásmo, "
        "do kterého padnou, je předběžné:"
    ),
    "the SOAP halves": "poloviny SOAP",
    "the Deepsy format": "formát Deepsy",
    "Those names do not all rest on the same amount, and the thinnest of them is "
    "worth reading beside the claim: {named}. That count is the notes answered on "
    "every criterion the band averages, out of the sessions its table has, and the "
    "notes column of the tables below prints it beside every row it applies to.": (
        "Ta jména nestojí všechna na stejném množství a to nejtenčí z nich stojí za "
        "přečtení vedle tvrzení samotného: {named}. Ten počet jsou zápisy zodpovězené "
        "na všech kritériích, která pásmo průměruje, z počtu sezení, která jeho tabulka "
        "má — a sloupec se zápisy v tabulkách níže ho vypisuje u každého řádku, kterého "
        "se to týká."
    ),
    "A band boundary is drawn at a threshold that resampling the sessions reproduces "
    "only to about {jitter}. These models sit within that of one, so this measurement "
    "does not place them: a different resample puts them in the next band along.": (
        "Hranice pásma se kreslí na mezi, kterou převzorkování sezení reprodukuje jen "
        "asi na {jitter}. Tyto modely leží od některé hranice blíž než to, takže je "
        "toto měření neumísťuje: jiné převzorkování je posune do sousedního pásma."
    ),
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
    "the two formats were not asked of the same models, a Deepsy note is written to a "
    "different prompt, and length does not weigh on them alike -- it runs against "
    "{soap_against} of the {soap_total} criterion-and-judge coefficients on the SOAP "
    "halves and against {deepsy_against} of {deepsy_total} in the Deepsy format. A "
    "pair read across the two would be reporting those differences as a verdict.": (
        "Dva soudci řadí modely různě, takže umístění v tabulce není tvrzení. Co "
        "obstojí u obou, je dominance: model, který je aspoň tak dobrý jako jiný "
        "v každém kritériu, u každého soudce zvlášť, a aspoň v jednom je striktně "
        "lepší. Všechno, co tu není vypsané, je dvojice, kterou tenhle projekt "
        "neumí odlišit. Každý blok níž je jeden formát zápisu a dvojice platí jen "
        "uvnitř něj: oba formáty nedostaly tytéž modely, zápis Deepsy vzniká z jiného "
        "zadání a délka na ně nedoléhá stejně — jde proti {soap_against} "
        "z {soap_total} koeficientů kritérium-soudce na půlkách SOAP a proti "
        "{deepsy_against} z {deepsy_total} ve formátu Deepsy. Dvojice čtená napříč "
        "oběma formáty by tyhle rozdíly ohlašovala jako výsledek."
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
    "{models} models were asked for notes from twenty psychotherapy sessions -- "
    "ten real and ten translated -- in two note formats, SOAP and the one the Deepsy "
    "application writes, and two independent judges rated every note that came back. "
    "Not every model was asked in both formats, and {written} of the {asked} notes "
    "were written; the rest are named where they are missing. Two "
    "instruments: six yes/no criteria asking whether the Czech is right, and "
    "PDSQI-9, a published instrument, asking whether the note is any good -- and "
    "PDSQI-9 was put only to the SOAP notes. Both, "
    "because neither answers the other: a flawless Czech sentence about nothing passes "
    "all six criteria, and a note full of insight can be written in bad Czech.": (
        "{models} modelů dostalo zadání napsat zápisy z dvaceti psychoterapeutických "
        "sezení — deseti skutečných a deseti přeložených — ve dvou formátech zápisu: "
        "SOAP a v tom, který píše aplikace Deepsy; každý zápis, který "
        "přišel, ohodnotili dva nezávislí soudci. Ne každý model dostal obě zadání "
        "a napsáno bylo {written} zápisů z "
        "{asked}; kde některý chybí, je to napsané u té tabulky. Dva nástroje: šest "
        "kritérií ano/ne, která se ptají, "
        "jestli je čeština správně, a PDSQI-9, publikovaný nástroj, který se ptá, "
        "jestli je zápis dobrý — a PDSQI-9 dostaly jen zápisy SOAP. "
        "Oba, protože jeden na druhého neodpovídá: bezchybná "
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
    "real": "skutečná",
    "translated": "přeložená",
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
    "The two instruments did not read the same notes, so the rows do not add up: "
    "{models} models wrote {written} notes in all, and the {soap} SOAP notes among "
    "them were each read twice by each judge -- once against the criteria and once "
    "against PDSQI-9.": (
        "Oba nástroje nečetly tytéž zápisy, takže se řádky nesčítají: {models} "
        "modelů napsalo celkem {written} zápisů a {soap} zápisů SOAP z nich četl "
        "každý soudce dvakrát — jednou podle kritérií a jednou podle PDSQI-9."
    ),
    "The {deepsy} notes in the Deepsy format were read against the criteria only. "
    "PDSQI-9 was never asked about a Deepsy note, so no quality figure anywhere in "
    "this document is about one.": (
        "{deepsy} zápisů ve formátu Deepsy prošlo jen kritérii. Na zápis v Deepsy se "
        "PDSQI-9 nikdy nikdo neptal, takže žádné číslo o kvalitě v tomhle dokumentu "
        "není o něm."
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
    "higher for completeness under both judges. In Czech it scores lower on {against} "
    "of the {total} criterion-and-judge coefficients -- {soap_against} of "
    "{soap_total} on the SOAP halves and {deepsy_against} of {deepsy_total} in the "
    "Deepsy format, which is one reason the two are never pooled -- and the exceptions "
    "are named rather than rounded away: the columns where the coefficient stays "
    "positive under BOTH judges are {positive}. A column is printed here only when "
    "both judges agree on the direction and at least one of them reaches 0.40; both "
    "numbers are shown, so a column the two judges feel differently strongly about is "
    "visible as that rather than averaged away.": (
        "Oba jazyky pak táhnou na opačné strany a tohle je to nejužitečnější, co je "
        "dobré vědět dřív, než se člověk pustí do kterékoli tabulky výše. V angličtině "
        "delší zápis dostává vyšší úplnost, a to u obou soudců. V češtině má horší "
        "skóre v {against} z {total} kombinací kritéria a soudce — {soap_against} "
        "z {soap_total} na půlkách SOAP a {deepsy_against} z {deepsy_total} ve formátu "
        "Deepsy, což je jeden z důvodů, proč se obojí nikdy nesčítá — a výjimky se "
        "jmenují, ne zaokrouhlují: sloupce, ve kterých koeficient zůstává kladný "
        "u OBOU soudců, jsou {positive}. "
        "Sloupec je tu vypsaný jen tehdy, když se oba soudci shodnou na směru a aspoň "
        "jeden z nich dosáhne 0,40; ukázaná jsou obě čísla, takže sloupec, který každý "
        "ze soudců cítí jinak silně, je vidět právě takový, a ne zprůměrovaný."
    ),
    "no column at all": "žádné",
    "Before reading that as \u201cthese models write worse Czech\u201d: each Czech "
    "criterion asks one yes/no question about a whole note -- is there a fault "
    "ANYWHERE in it. A SOAP note of {longest} words offers more places for one to be "
    "found than a SOAP note of {shortest}. The check is what happens to the same models "
    "under the other instrument: on the SOAP language criteria the three "
    "longest-writing models take the last three places {hit} times out of {total}, and "
    "on PDSQI-9, rating the very same notes, they do not. Part of the bottom of the "
    "Czech SOAP tables is length, not Czech.": (
        "Než si to někdo přečte jako „tyhle modely píšou horší češtinu“: každé české "
        "kritérium klade jednu otázku ano/ne o celém zápisu — je v něm někde chyba? "
        "Zápis SOAP o {longest} slovech nabízí víc míst, kde ji najít, než zápis SOAP "
        "o {shortest} slovech. Kontrolou je, co se s týmiž modely stane pod druhým "
        "nástrojem: na jazykových kritériích SOAP obsadí tři nejdelší pisatelé poslední "
        "tři místa {hit}krát ze {total}, kdežto na PDSQI-9, které hodnotí úplně tytéž "
        "zápisy, ne. Část spodku českých tabulek SOAP je délka, ne čeština."
    ),
    "The same test in the Deepsy format comes out {hit} of its {total} tables, and the "
    "three models that write longest there are a different three, because the two "
    "formats were not asked of the same models. Where the last three places go is a "
    "fact about the SOAP halves rather than a law about length.": (
        "Táž zkouška ve formátu Deepsy vychází {hit} z jeho {total} tabulek a tři "
        "modely, které tam píšou nejdéle, jsou jiné tři, protože oba formáty nedostaly "
        "tytéž modely. Kam padnou poslední tři místa, je výrok o půlkách SOAP, ne "
        "zákon o délce."
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
    # Subject and verb in one key. English conjugates "No model IS", Czech
    # negates the verb -- "Žádný model NENÍ" -- so the empty end cannot be built
    # from the same "is" the one- and two-model cases use.
    "No model is": "Žádný model není",
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
    "On writing correct Czech, {top} in the top band of all {tables} tables the bands "
    "cover -- the SOAP halves, both judges. {bottom} in the bottom band of all "
    "{tables}. Between those two ends the tables disagree with each other, so nothing "
    "else here is a ranking.": (
        "Ve psaní správné češtiny {top} v nejvyšším pásmu všech {tables} tabulek, které "
        "pásma pokrývají — půlky SOAP, oba soudci. {bottom} v nejnižším pásmu všech "
        "{tables}. Mezi těmito dvěma konci si tabulky odporují, takže nic dalšího tu není "
        "pořadí."
    ),
    "The Deepsy format was asked the same question over its own {tables} tables, and "
    "it is counted separately rather than pooled with the four above: {top} in the top "
    "band of all of them and {bottom} in the bottom band of all of them. The two "
    "formats are not added together because not every model was asked in both, because "
    "a Deepsy note is written to a different prompt and comes out a different shape, "
    "and because the one native-speaker anchor this project has was measured on SOAP "
    "notes alone. Length does not settle it either way: it runs against {soap_against} "
    "of the {soap_total} criterion-and-judge coefficients on the SOAP halves and "
    "against {deepsy_against} of {deepsy_total} in the Deepsy format, so it is not the "
    "uniform penalty one number could stand for.": (
        "Formát Deepsy dostal tutéž otázku nad svými vlastními {tables} tabulkami a počítá "
        "se zvlášť, ne dohromady se čtyřmi výše: {top} v nejvyšším pásmu všech z nich "
        "a {bottom} v nejnižším pásmu všech z nich. Oba formáty se nesčítají, protože ne "
        "každý model dostal obě zadání, protože zápis Deepsy vzniká z jiného zadání a má "
        "jiný tvar, a protože jediná opora u rodilého mluvčího, kterou tenhle projekt má, "
        "byla změřena jen na zápisech SOAP. Délka to nerozhoduje ani na jednu stranu: jde "
        "proti {soap_against} z {soap_total} koeficientů kritérium-soudce na půlkách SOAP "
        "a proti {deepsy_against} z {deepsy_total} ve formátu Deepsy, takže to není "
        "jednotný postih, který by uneslo jedno číslo."
    ),
    "One caution about that second count. {subject} in the bottom band of all {tables} "
    "SOAP tables and in no Deepsy band at all -- not because of anything written, but "
    "because e-INFRA answered {calls} of the calls asking for those notes with an "
    "error and returned no note. Adding the two counts together would have removed it "
    "from the bottom of the table on the strength of an outage.": (
        "Jedna výstraha k tomu druhému počtu. {subject} v nejnižším pásmu všech {tables} "
        "tabulek SOAP a zároveň v žádném pásmu Deepsy — ne kvůli tomu, co napsal, ale "
        "protože e-INFRA odpověděla na {calls} volání žádajících o tyhle zápisy chybou "
        "a nevrátila žádný. Sečtěním obou počtů dohromady by zmizel ze dna tabulky "
        "díky výpadku."
    ),
    "Read the two names carefully: {refused} and {near} differ by one suffix and are "
    "different models. {near} is in the Deepsy bands above and in none of the SOAP "
    "ones.": (
        "Ta dvě jména čti pozorně: {refused} a {near} se liší o jednu příponu a jsou "
        "to jiné modely. {near} je v pásmech Deepsy výše a v žádném z pásem SOAP."
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
    "That pattern is not a law: on the {total} Deepsy tables the three longest-writing "
    "models -- a different three, because the two formats were not asked of the same "
    "set of models -- do not all land in the last three places under either judge. "
    "Length and rank travel together on the SOAP halves and more loosely here, which "
    "is one more reason the two formats are counted apart rather than added up.": (
        "Ten vzorec není zákon: na {total} tabulkách Deepsy tři modely s nejdelšími zápisy "
        "— jsou to jiné tři, protože oba formáty nedostaly tutéž sadu modelů — neobsadí "
        "poslední tři místa ani u jednoho soudce. Délka a příčka jdou spolu na půlkách SOAP "
        "a tady volněji, což je další důvod, proč se oba formáty počítají zvlášť a nesčítají."
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
    # --- what each chapter came to --------------------------------------------
    "The two judges do not both point the same way on {names}, so between the halves there is no "
    "answer there at all.": (
        "Tady se oba soudci neshodnou ani na směru — {names} — takže mezi půlkami tam žádná "
        "odpověď není."
    ),
    "It does not follow that the models write better Czech on either half. The two differ in size, "
    "in topic and in who transcribed them, so a model that does worse on one may be doing worse at "
    "length, at motivational interviewing or at Czech, and nothing measured here separates the "
    "three.": (
        "Neplyne z toho, že by modely psaly na jedné z půlek lepší češtinu. Ty dvě půlky se liší "
        "velikostí, tématem i tím, kdo je přepisoval, takže model, kterému jde jedna hůř, může být "
        "horší v délce, v motivačních rozhovorech nebo v češtině — a nic z toho, co se tu měřilo, "
        "ty tři od sebe neoddělí."
    ),
    "Which fault survives most often is not the same in all {tables} of these tables, so none is "
    "named here: the weakest column changes with the table and with the judge.": (
        "Která chyba přežívá nejčastěji, není ve všech {tables} těchto tabulkách totéž, takže se "
        "tu žádná nejmenuje: nejslabší sloupec se mění s tabulkou i se soudcem."
    ),
    "What these two tables come to": "K čemu tyhle dvě tabulky došly",
    "One fault survives more often than any other, and it is the same one in all {tables} of these "
    "tables -- both halves, both judges. It is {worst}: averaged over the models, between {low} "
    "and {high} of the notes are free of it, where 1.00 would mean every note was clean and 0.00 "
    "that none was.": (
        "Jedna chyba přežívá častěji než kterákoli jiná a ve všech {tables} těchto tabulkách je to "
        "táž — obě půlky, oba soudci. Je to tahle: {worst}. V průměru přes modely je bez ní {low} "
        "až {high} ze všech zápisů, kde 1,00 by znamenalo, že je čistý každý zápis, a 0,00, že "
        "žádný."
    ),
    "Between the two halves, the translated conversations come out ahead on {other} of the {total} "
    "criteria under both judges, and the real sessions on {real}.": (
        "Mezi oběma půlkami: přeložené rozhovory vedou u obou soudců na {other} z {total} "
        "kritérií, skutečná sezení na {real}."
    ),
    "What the two quality tables come to": "K čemu došly obě tabulky kvality",
    "In all {tables} of these tables, every model scores {value} on {names} -- the top of the "
    "scale. That is a ceiling rather than a result: an attribute no model can fail cannot tell the "
    "models apart, and it should not be read as one they all did well on.": (
        "Ve všech {tables} těchto tabulkách má každý model {value}, což je vrchol škály, a je to "
        "pokaždé táž položka: {names}. To je strop, ne výsledek: položka, ve které nemůže žádný "
        "model selhat, modely od sebe neodliší, a nemá se číst jako něco, v čem všechny obstály."
    ),
    "The attribute every model does worst on is {worst}, in all {tables} of these tables and under "
    "both judges: {low} to {high} out of 5, averaged over the models in each of them.": (
        "Položka, ve které dopadají všechny modely nejhůř, je tahle: {worst}. Ve všech {tables} "
        "těchto tabulkách a u obou soudců z ní vychází {low} až {high} z 5, v průměru přes modely "
        "v každé z nich."
    ),
    "These {tables} tables do not agree on which attribute the models do worst on, so none is "
    "named here.": (
        "Těchto {tables} tabulek se neshodne na tom, ve které položce dopadají modely nejhůř, "
        "takže se tu žádná nejmenuje."
    ),
    "Between the two halves, on the {total} attributes both of them were asked: the translated "
    "conversations come out ahead on {other} under both judges, and the real sessions on {real}.": (
        "Mezi oběma půlkami, na {total} položkách, na které se ptaly obě: přeložené rozhovory "
        "vedou u obou soudců na {other}, skutečná sezení na {real}."
    ),
    "Two attributes are missing from the real half rather than low. {names} can only be answered "
    "by reading the session, and a real session is never sent to a judge, so there is no number "
    "rather than a poor one. Nothing about the notes is being left out.": (
        "Dvě položky u skutečné půlky nechybějí proto, že by vyšly nízko. {names} se dají "
        "zodpovědět jen čtením sezení a skutečné sezení se soudci nikdy neposílá, takže tam není "
        "špatné číslo, ale žádné. O zápisech se tím nic nezamlčuje."
    ),
    "What the two Deepsy tables come to": "K čemu došly obě tabulky Deepsy",
    "The fault that survives most often in the Deepsy notes is {worst}, with between {low} and "
    "{high} of them free of it. It is the same fault that survives most often in the SOAP notes "
    "above, so what these models get wrong in Czech is not a fact about the format they were asked "
    "for.": (
        "Chyba, která v zápisech Deepsy přežívá nejčastěji, je tahle: {worst}. Bez ní je {low} až "
        "{high} z nich. Je to táž chyba, která nejčastěji přežívá v zápisech SOAP výše, takže to, "
        "co tyhle modely v češtině kazí, není vlastnost formátu, který se po nich chtěl."
    ),
    "The fault that survives most often in the Deepsy notes is {worst}, with between {low} and "
    "{high} of them free of it. In the SOAP notes above it is {soap} instead, so what a model gets "
    "wrong changes with the shape it was asked for.": (
        "Chyba, která v zápisech Deepsy přežívá nejčastěji, je tahle: {worst}. Bez ní je {low} až "
        "{high} z nich. V zápisech SOAP výše je nejčastější jiná — {soap} —, takže se to, co model "
        "kazí, mění s tvarem, který se po něm chtěl."
    ),
    "No single fault dominates the Deepsy notes the way {soap} does the SOAP ones. Which column is "
    "weakest changes with the table and with the judge, so none is named here.": (
        "V zápisech SOAP převládá jedna chyba nad ostatními — {soap} — a v zápisech Deepsy nic "
        "takového není: který sloupec je nejslabší, se mění s tabulkou i se soudcem, takže se tu "
        "žádný nejmenuje."
    ),
    "That comparison carries the same confound as the one on the SOAP halves: the two halves "
    "differ in size, in topic and in who transcribed them, and nothing measured here separates any "
    "of the three from Czech.": (
        "To srovnání s sebou nese tutéž potíž jako to na půlkách SOAP: obě půlky se liší "
        "velikostí, tématem i tím, kdo je přepisoval, a nic z toho, co se tu měřilo, ani jedno od "
        "češtiny neoddělí."
    ),
    "Between the two halves of the Deepsy notes, the translated conversations come out ahead on "
    "{other} of the {total} criteria under both judges, and the real sessions on {real}.": (
        "Mezi oběma půlkami zápisů Deepsy: přeložené rozhovory vedou u obou soudců na {other} z "
        "{total} kritérií, skutečná sezení na {real}."
    ),
    "One thing to carry into any comparison with the tables above: these two tables hold {here} "
    "models and the SOAP tables hold {there}, because what e-INFRA had deployed changed between "
    "the two runs. Anything read across the two formats holds for the {shared} models they share, "
    "and for those only.": (
        "Jedna věc, kterou je třeba vzít do každého srovnání s tabulkami výše: tyhle dvě tabulky "
        "mají {here} modelů a tabulky SOAP {there}, protože se mezi oběma běhy změnilo, co má "
        "e-INFRA nasazené. Cokoli čteného napříč oběma formáty platí pro {shared} modelů, které "
        "mají společné, a jen pro ně."
    ),
    # --- the Deepsy chapter -------------------------------------------------
    "The note format the Deepsy application actually writes": (
        "Formát zápisu, který aplikace Deepsy opravdu píše"
    ),
    "Every table so far has been about SOAP -- subjective, objective, assessment, "
    "plan. That is the format TN-Eval published, and reusing it is what lets the "
    "English numbers be read beside the Czech ones. It is not the format the Deepsy "
    "application writes. Deepsy asks the model for a note in named sections, one call "
    "per section, in its own words; {sections} of those sections are measured here, "
    "and they are not a preference. They are the ones that have a SOAP counterpart: "
    "the data section is SOAP's subjective and objective together, the "
    "hypotheses section is its assessment, and the plan section is its plan. The "
    "application writes more sections than these, and the rest either work from the "
    "previous note rather than from a transcript or need data this benchmark does "
    "not supply.": (
        "Všechny dosavadní tabulky byly o SOAP — subjektivní, objektivní, hodnocení, "
        "plán. To je formát, který publikoval TN-Eval, a právě jeho převzetí umožňuje "
        "číst anglická čísla vedle českých. Není to formát, který píše aplikace "
        "Deepsy. Deepsy si od modelu žádá zápis v pojmenovaných sekcích, jedno volání "
        "na sekci, vlastními slovy; {sections} z těchto sekcí se měří tady a není to "
        "výběr podle chuti. Jsou to ty, které mají protějšek v SOAP: sekce data je "
        "subjektivní a objektivní část SOAP dohromady, sekce hypotéz je jeho "
        "hodnocení a sekce plánu je jeho plán. Aplikace píše víc sekcí než tyhle a "
        "zbytek buď vychází z předchozího zápisu místo z přepisu, nebo potřebuje "
        "data, která tenhle benchmark nedodává."
    ),
    "Two things this format does that SOAP does not. It sets a ceiling of {limit} "
    "words a section, which its own prompt calls invalid to exceed. And it asks for "
    "the answer as structured data rather than as prose, so a reply that does not "
    "parse is a failure rather than a poor note. Both are the application's "
    "decisions, reproduced from its own prompt files rather than retyped.": (
        "Dvě věci, které tenhle formát dělá a SOAP ne. Stanovuje strop {limit} slov "
        "na sekci a jeho vlastní prompt označuje delší odpověď za neplatnou. A žádá "
        "odpověď jako strukturovaná data, ne jako prózu, takže odpověď, kterou nelze "
        "rozebrat, je selhání, ne špatný zápis. Obojí je rozhodnutí té aplikace, "
        "převzaté z jejích vlastních souborů s prompty, ne přepsané rukou."
    ),
    "That is why this chapter is here, and it is worth reading before the tables "
    "above are taken too literally. SOAP is not what a Czech psychologist writes. "
    "The prompt behind every table so far is a translation of TN-Eval's, so that the "
    "task is the same task in another language, and it reproduces no Czech "
    "documentation standard because there is none to reproduce -- which makes those "
    "notes formally artificial, equally so for every model, and that equality is "
    "what keeps the comparison between them fair rather than what makes them less "
    "artificial. Here the same models write from the same sessions and the only "
    "thing that changes is the shape they were asked for. The figure below shows "
    "what came of that, and the paragraph under it names the one thing the "
    "comparison cannot hold still.": (
        "Proto tahle kapitola je a stojí za to přečíst ji dřív, než se tabulky výše "
        "vezmou příliš doslova. SOAP není to, co píše český psycholog. Prompt za "
        "všemi dosavadními tabulkami je překlad toho z TN-Eval, aby úkol byl týž úkol "
        "v jiném jazyce, a nereprodukuje žádnou českou dokumentační normu, protože "
        "žádná k reprodukci není — tím jsou ty zápisy formálně umělé, u každého "
        "modelu stejně, a právě ta stejnost drží srovnání mezi nimi poctivé; menší "
        "umělost z ní neplyne. Tady tytéž modely píšou z týchž sezení a mění se "
        "jediné: tvar, který se po nich chtěl. Obrázek níž ukazuje, co z toho vzešlo, "
        "a odstavec pod ním pojmenovává jednu věc, kterou to srovnání neudrží."
    ),
    "This chapter says nothing about whether a Deepsy note is a good note. The six "
    "criteria ask whether the Czech is right, and the instrument that asks whether a "
    "note is worth filing was never put to these.": (
        "Tahle kapitola neříká nic o tom, jestli je zápis v Deepsy dobrý zápis. Šest "
        "kritérií se ptá, jestli je čeština správně, a nástroj, který se ptá, jestli "
        "je zápis použitelný, na tyhle zápisy nikdo nepoužil."
    ),
    "Four panels rather than one average: the comparison was made on both halves of "
    "the corpus and under both judges, and that all four go the same way is the "
    "finding. Read the slope of the lines; which line is which model is in the "
    "tables below.": (
        "Čtyři panely místo jednoho průměru: srovnání proběhlo na obou půlkách "
        "korpusu a u obou soudců a nález je, že všechny čtyři jdou stejným směrem. "
        "Čtěte sklon čar; která čára je který model, je v tabulkách níž."
    ),
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
    "{deepsy} words against {soap} -- and this document measures below that length "
    "runs against most of these criteria, {soap_against} of the {soap_total} "
    "criterion-and-judge coefficients on the SOAP halves and {deepsy_against} of "
    "{deepsy_total} in the Deepsy format, because each asks whether there is a fault "
    "ANYWHERE in it. Format and length point the same way here and {compared} models "
    "cannot separate them.": (
        "Nečti to jako „formát Deepsy vede k horší češtině“. Může, a tahle čísla to "
        "říct neumějí, protože se obojí hýbe společně: zápis v Deepsy je DELŠÍ — "
        "{longer} z {models} modelů v něm píše víc, medián {deepsy} slov proti {soap} "
        "— a tenhle dokument níž měří, že délka jde proti většině těchto kritérií: "
        "proti {soap_against} z {soap_total} koeficientů kritérium-soudce na půlkách "
        "SOAP a proti {deepsy_against} z {deepsy_total} ve formátu Deepsy, protože "
        "každé se ptá, jestli je v něm chyba NĚKDE. Formát a délka tady ukazují týmž "
        "směrem a {compared} modelů je od sebe neoddělí."
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
    # --- the four figures ---------------------------------------------------
    # `tools/czech_figures.py` may hold no Czech at all -- it is scanned for
    # diacritics like every other tool -- so every title, caption, axis label
    # and footnote it draws is here. Each entry is a whole sentence, never a
    # clause: a Czech sentence assembled from pieces at drawing time does not
    # decline, and a count glued to a noun declines differently at two, at five
    # and at nine.
    "The Deepsy note scores lower in {worse} of {compared} model-and-judge pairs": (
        "Zápis ve formátu Deepsy dopadl hůř v {worse} z {compared} dvojic model–soudce"
    ),
    "Each line is one model: on the left its SOAP note, on the right its Deepsy note "
    "from the same sessions, read against the same six criteria by the same judge.": (
        "Každá čára je jeden model: vlevo jeho zápis SOAP, vpravo jeho zápis ve formátu "
        "Deepsy z týchž sezení, posuzované stejnými šesti kritérii a stejným soudcem."
    ),
    "{worse} of {models} models score lower": "{worse} z {models} modelů má horší skóre",
    "A Deepsy note is also longer, and length runs against most of these criteria, so "
    "the format and the length point the same way here and {models} models cannot "
    "separate them. Which of the two the drop belongs to is not measured.": (
        "Zápis ve formátu Deepsy je zároveň delší a délka jde proti většině těchto "
        "kritérií, takže formát a délka tu ukazují stejným směrem a {models} modelů je "
        "od sebe neodliší. Kterému z těch dvou ten propad patří, změřené není."
    ),
    "Source: local/czech-rows.jsonl, rubric {rubric}. Nothing in this figure is on the "
    "public site.": (
        "Zdroj: local/czech-rows.jsonl, rubrika {rubric}. Nic z tohoto grafu není na veřejném webu."
    ),
    "The SOAP note and the Deepsy note of each model, side by side": (
        "Zápis SOAP a zápis ve formátu Deepsy u každého modelu vedle sebe"
    ),
    "General capability tracks the English notes more closely than the Czech ones": (
        "Obecná schopnost modelu jde s anglickými zápisy víc než s českými"
    ),
    "Each dot is one model: its score on a published capability index against the "
    "quality a judge gave its notes. The dashed line is least squares, drawn rather "
    "than described.": (
        "Každý bod je jeden model: jeho skóre v publikovaném indexu schopností proti "
        "kvalitě, kterou jeho zápisům dal soudce. Čárkovaná čára je metoda nejmenších "
        "čtverců, nakreslená, ne popsaná."
    ),
    "The English SOAP notes": "Anglické zápisy SOAP",
    "The Czech notes, translated half": "České zápisy, přeložená polovina",
    "PDSQI-9 quality, 1 to 5": "Kvalita podle PDSQI-9, 1 až 5",
    "Spearman {rho}, p {p}, {n} models": "Spearman {rho}, p {p}, {n} modelů",
    "Matched by name, and the name is the weak link: on this endpoint one id has "
    "already returned another model's output, so every dot is an assumption. These "
    "could not be matched to a public model at all and are absent rather than guessed: "
    "{names}.": (
        "Párováno podle jména a jméno je slabý článek: na tomhle endpointu už jedno id "
        "vrátilo výstup jiného modelu, takže každý bod je předpoklad. Tyhle se s žádným "
        "veřejným modelem spárovat nepodařilo, a proto tu nejsou, místo aby se "
        "odhadovaly: {names}."
    ),
    "Source: local/czech-external.json, {version}, fetched {fetched}. Nothing on this "
    "axis was measured by this project.": (
        "Zdroj: local/czech-external.json, {version}, staženo {fetched}. Nic na této ose "
        "tento projekt neměřil."
    ),
    "A published capability index against the quality of the notes": (
        "Publikovaný index schopností proti kvalitě zápisů"
    ),
    "A place in English is not a place in Czech: {moved} of {models} change": (
        "Místo v angličtině není místo v češtině: {moved} z {models} se mění"
    ),
    "PDSQI-9 on the English SOAP notes against PDSQI-9 on the Czech ones, averaged over "
    "the three attributes that are not the same for every model. Same instrument, same "
    "judge, only the language of the note differs.": (
        "PDSQI-9 na anglických zápisech SOAP proti PDSQI-9 na českých, zprůměrováno přes "
        "tři vlastnosti, které nejsou u všech modelů stejné. Stejný nástroj, stejný "
        "soudce, liší se jen jazyk zápisu."
    ),
    "In English": "V angličtině",
    "In Czech": "V češtině",
    "changed place: {moved}": "změna pořadí: {moved}",
    "held their place: {held}": "beze změny: {held}",
    "Source: local/czech-join.json, both judges, the models both tables hold.": (
        "Zdroj: local/czech-join.json, oba soudci, modely, které mají obě tabulky."
    ),
    "Each model's place in English against its place in Czech": (
        "Místo každého modelu v angličtině proti jeho místu v češtině"
    ),
    "The longer a model's note, the worse it does on the Czech criteria": (
        "Čím delší zápis model píše, tím hůř dopadá v českých kritériích"
    ),
    "Each dot is one model: the median length of its notes against the mean of the six "
    "criteria under one judge. The dashed line is least squares, drawn rather than "
    "described.": (
        "Každý bod je jeden model: medián délky jeho zápisů proti průměru šesti kritérií "
        "u jednoho soudce. Čárkovaná čára je metoda nejmenších čtverců, nakreslená, ne "
        "popsaná."
    ),
    "Median words in one note": "Medián počtu slov v jednom zápisu",
    "The six criteria, averaged": "Šest kritérií, zprůměrovaných",
    "Length was not assigned to the models, they chose it, so this is not a correction "
    "to apply -- a model may write long BECAUSE it summarises badly, and subtracting "
    "what length predicts would take the result away with the artefact. It is a reason "
    "not to read the bottom of the table as bad Czech and nothing else.": (
        "Délka modelům nebyla přidělena, zvolily si ji samy, takže tohle není oprava, "
        "kterou by šlo použít — model může psát dlouze PROTOŽE špatně shrnuje, a "
        "odečtení toho, co délka předpovídá, by spolu s artefaktem odečetlo i výsledek. "
        "Je to důvod nečíst spodek tabulky jen jako špatnou češtinu."
    ),
    "Source: local/czech-length.json and local/czech-rows.jsonl, rubric {rubric}. The "
    "lengths are medians over the notes that parsed.": (
        "Zdroj: local/czech-length.json a local/czech-rows.jsonl, rubrika {rubric}. "
        "Délky jsou mediány přes zápisy, které se podařilo rozebrat."
    ),
    "Note length against the criteria score, one dot per model": (
        "Délka zápisu proti skóre v kritériích, jeden bod na model"
    ),
}
