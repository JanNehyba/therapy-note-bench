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
    ("therapy-note-bench · Czech track · measured, not published"): (
        "therapy-note-bench · česká větev · změřeno, nepublikováno"
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
    "Two halves, both read only from a directory that is not in version control. Every "
    "model was asked for a note from every transcript, on e-INFRA -- that is the design, "
    "and {written} of the {asked} notes are the outcome. Which models wrote fewer, and "
    "how many fewer, is named in the first of the caveats above.": (
        "Dvě půlky, obě čtené jen z adresáře, který není ve verzovacím systému. Každý "
        "model dostal zadání napsat zápis z každého přepisu, na e-INFRA — to je záměr "
        "a výsledek je {written} zápisů z {asked}. Které modely napsaly míň a o kolik, "
        "je jmenované v první z výhrad výše."
    ),
    "Where each step ran is the confidentiality boundary of this whole project. Every "
    "note was written on e-INFRA, the infrastructure that also holds the sessions, so no "
    "transcript ever left it to be summarised. Only the notes went anywhere else: each "
    "was put to two judges, one question at a time, on Google's and OpenAI's endpoints.": (
        "Kde který krok běžel, to je hranice důvěrnosti celého tohohle projektu. Každý "
        "zápis vznikl na e-INFRA, tedy na infrastruktuře, která drží i sezení — žádný "
        "přepis ji tedy kvůli shrnování neopustil. Ven šly jen zápisy: každý dostali dva "
        "soudci, po jedné otázce, na serverech Googlu a OpenAI."
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
        "PDSQI na přeložené půlce. Ty přepisy jsou AnnoMI, publikované pod CC-BY, "
        "takže se poslat smějí. Tím se kupují dva atributy, na které se bez sezení "
        "odpovědět nedá: jestli je zápis přesný a jestli je důkladný. Skutečná "
        "půlka dostane zbylých šest. Ty dva sloupce v ní chybějí proto, že se ta "
        "otázka nedala položit — ne proto, že by v nich zápisy propadly."
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
    "Attribute": "Atribut",
    "Real sessions": "Skutečná sezení",
    "Translated AnnoMI": "Přeložené AnnoMI",
    "one client, de-identified by hand, never released": (
        "jeden klient, anonymizováno ručně, nikdy nezveřejněno"
    ),
    ("public counselling conversations, translated for this track"): (
        "veřejné poradenské rozhovory, přeložené pro tuhle větev"
    ),
    "What each column is": "Co který sloupec je",
    # --- per-table prose ---------------------------------------------------
    "What was measured, and on what": "Co se měřilo a na čem",
    "PDSQI-9": "PDSQI-9",
    (
        "Every model was asked for a note from every one of these transcripts, in both "
        "halves, so no two models are ever compared on sessions of different "
        "difficulty. One half is recordings of real therapy with a single client, "
        "transcribed and de-identified by hand and never released. The other is public "
        "counselling conversations from the AnnoMI corpus, translated into spoken Czech "
        "for this track."
    ): (
        "Každý model dostal za úkol napsat zápis z každého z těchto přepisů, v obou "
        "půlkách — takže se nikdy neporovnávají dva modely na různě těžkých sezeních. "
        "Jedna půlka jsou nahrávky skutečné terapie s jedním klientem, přepsané a ručně "
        "anonymizované, nikdy nezveřejněné. Druhá jsou veřejné poradenské rozhovory z "
        "korpusu AnnoMI, přeložené pro tuhle větev do mluvené češtiny."
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
        "dají — takže u skutečných sezení se ty otázky nikdy nepoložily. Jde o tyhle dva "
        "sloupce: {columns}. Nechybí tam proto, že by v nich zápisy propadly. Chybí "
        "tam otázka, ne odpověď."
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
    (
        "Two judges, two tables, and they are not averaged. Where they disagree about a "
        "model is the only control this track has, so the disagreement is the thing to "
        "read."
    ): (
        "Dva soudci, dvě tabulky, a neprůměrují se. To, kde se na modelu neshodnou, je "
        "jediná kontrola, kterou tahle větev má — takže ta neshoda je to, co se má "
        "číst."
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
    ", an earlier version of the rubric. Those rows are a different instrument rather "
    "than an earlier attempt at this one, so they are named here and not placed beside "
    "these. They remain in the local record.": (
        ", což je starší verze rubriky. Ty řádky jsou jiný nástroj, ne dřívější pokus "
        "o tenhle, takže jsou tu jmenovány a nekladou se vedle těchto. V lokálním "
        "záznamu zůstávají."
    ),
    # --- the join section --------------------------------------------------
    "Does the English leaderboard predict the Czech?": ("Předpovídá anglický žebříček tu češtinu?"),
    "Asked the same question, quality transfers": ("Při stejně položené otázce se kvalita přenáší"),
    "Asked the leaderboard's own measure, it does not": (
        "U míry, podle které žebříček řadí, se nepřenáší"
    ),
    # Printed only if a payload records no ranking measure at all. Translated in
    # advance so that the day it does, the sentence around it stays Czech.
    "the ranking measure": "míra, podle které se řadí",
    "PDSQI-9 on the English notes against PDSQI-9 on the Czech ones. Same attributes, "
    "same anchors, same judge; only the language of the note differs.": (
        "PDSQI-9 na anglických zápisech proti PDSQI-9 na českých. Tytéž atributy, tytéž "
        "kotvy, týž soudce; liší se jen jazyk zápisu."
    ),
    "Flat on one side and therefore not correlated:": (
        "Ploché na jedné straně, a proto nekorelováno:"
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
    # --- what the numbers from outside say ---------------------------------
    "What the numbers from outside say": "Co říkají čísla zvenčí",
    "Two numbers about these models exist outside this document, and both are the kind "
    "of thing somebody reaches for instead of running a benchmark: this project's own "
    "English leaderboard, and a published index of general capability. This chapter "
    "asks what either one tells a reader about the Czech notes. Each half opens with "
    "its chart, because a chart is the part of this that can be read without "
    "arithmetic, and the tables under it ask the same question one column at a time. "
    "Bold in those tables marks a correlation that survives an exact permutation test "
    "at p < 0.05; the rest failed it and are printed anyway, because how little there "
    "is to see is the result here, and dropping the weak cells would flatter it.": (
        "O těchhle modelech existují mimo tenhle dokument dvě čísla a po obou by "
        "člověk sáhl místo toho, aby tohle měření spouštěl: vlastní anglický žebříček "
        "tohohle projektu a publikovaný index obecné schopnosti. Tahle kapitola se "
        "ptá, co z kteréhokoli z nich plyne pro české zápisy. Každá polovina začíná "
        "svým grafem, protože graf je ta část, která se dá přečíst bez počítání, "
        "a tabulky pod ním kladou tutéž otázku po jednotlivých sloupcích. Tučně je "
        "v nich korelace, která obstojí v přesném permutačním testu na p < 0.05; "
        "ostatní neobstály a jsou vytištěné stejně, protože výsledkem je tady právě "
        "to, jak málo je vidět, a vypustit slabé buňky by ho přikrášlilo."
    ),
    "{systems} models, and whether a standing in one language predicts a standing in "
    "the other has two answers -- which one a reader gets depends on which English "
    "number they happened to be looking at.": (
        "{systems} modelů — a otázka, jestli umístění v jednom jazyce předpovídá "
        "umístění v druhém, má dvě odpovědi. Kterou z nich čtenář dostane, závisí na "
        "tom, na které anglické číslo se zrovna díval."
    ),
    "One block per judge, one line per model: its place among these models on the "
    "English notes, joined to the place the same instrument gave it in Czech. A level "
    "grey line is a model that kept its place. Each model is counted once under each "
    "judge, so the count in the title is over placings rather than over models. And a "
    "place is not a measurement -- two models a hundredth apart are drawn a whole "
    "place apart -- which is the point of drawing it: a leaderboard hands a reader a "
    "place, and this is what that place is worth in the other language.": (
        "Jeden blok na soudce, jedna čára na model: jeho místo mezi těmito modely na "
        "anglických zápisech, spojené s místem, které mu tentýž nástroj dal v češtině. "
        "Vodorovná šedá čára je model, který si své místo udržel. Každý model se "
        "počítá jednou u každého soudce, takže počet v nadpisu je počet umístění, ne "
        "počet modelů. Místo samo o sobě není měření: dva modely vzdálené o setinu "
        "jsou nakreslené o celé místo od sebe. Právě proto to ale stojí za "
        "nakreslení — žebříček čtenáři podává místo, a tohle je přesně to, co "
        "z takového místa vydrží v druhém jazyce."
    ),
    "The English page sorts by one measure -- {measure} -- and a position on that page "
    "means what that measure says. Here it stands against the Czech quality columns. "
    "Nothing survives the test, and the two judges do not agree even on the sign.": (
        "Anglická stránka řadí podle jediné míry — {measure} — a umístění na ní "
        "znamená to, co říká ona míra. Tady stojí proti sloupcům české kvality. "
        "Nic z toho testem neprojde a soudci se neshodnou ani na znaménku."
    ),
    # --- what these numbers cannot be used for -----------------------------
    "Ten sessions, and they are all one client": ("Deset sezení, a všechna jsou jeden klient"),
    "Every model was asked for a note from every transcript, and that is what makes "
    "comparing them valid at all -- the first attempt gave each model a different "
    "session, and it could not tell a worse model from a harder session. The asking "
    "held; the answering did not always. {written} of the {asked} notes came back, "
    "and where a model wrote fewer it is named: {short}. But ten notes per model is "
    "a small number. One note falling the other way moves a share by a tenth, which "
    "is wider than most of the gaps between neighbouring rows in these tables, so "
    "two models a few hundredths apart are not two models an extra week of "
    "measurement would keep apart. And the real half is ten sessions with one "
    "client and one therapist: everything measured there is also a fact about that "
    "therapist's way of working and that client's way of talking. Read the ordering. "
    "Do not read the gaps between neighbours.": (
        "Každý model dostal zadání napsat zápis z každého přepisu a právě to dělá "
        "srovnání mezi modely vůbec platným — první pokus dal každému modelu jiné "
        "sezení a neuměl odlišit horší model od těžšího sezení. Zadání dostaly "
        "všechny modely stejné, ale ne všechny na ně odpověděly: vrátilo se "
        "{written} zápisů z {asked}. Kde model napsal míň, je tady jmenovaný: "
        "{short}. Deset zápisů na model je ale málo. Jediný "
        "zápis, který by dopadl opačně, posune podíl o desetinu, a to je víc než "
        "většina rozestupů mezi sousedními řádky v těchhle tabulkách — dva modely "
        "vzdálené o pár setin tedy nejsou dva modely, které by od sebe udržel i další "
        "týden měření. A skutečná půlka je deset sezení s jedním klientem a jedním "
        "terapeutem: všechno, co je změřené na ní, je zároveň výrok o tom, jak "
        "pracuje ten terapeut a jak mluví ten klient. Čti pořadí. Nečti rozestupy "
        "mezi sousedy."
    ),
    "The two halves differ by more than language, and mostly by size": (
        "Ty dvě půlky se liší víc než jazykem, a hlavně velikostí"
    ),
    "A real session runs to a median of {real_words} words and {real_turns} turns; a "
    "translated AnnoMI conversation to {other_words} words and {other_turns} turns -- "
    "{ratio} times the material to read before a word of Czech is written. "
    "Summarising the longer one is a harder task on its own. They differ in subject "
    "as well: AnnoMI is motivational interviewing about substance use, the real "
    "sessions are not, and the two were transcribed by different hands to different "
    "conventions. So a model that does worse on one half may be doing worse at "
    "length, at motivational interviewing, or at Czech, and nothing here separates "
    "the three. The one thing the two halves are good for is the comparison between "
    "them: a fault that appears on both is the model's, and a fault that appears "
    "only on the translated half belongs to the text it was given.": (
        "Skutečné sezení má medián {real_words} slov a {real_turns} replik; přeložený "
        "rozhovor AnnoMI {other_words} slov a {other_turns} replik — tedy {ratio}× víc "
        "materiálu, který je potřeba přečíst dřív, než padne první české slovo. Shrnout "
        "to delší je těžší úkol samo o sobě. Liší se i tématem: AnnoMI je motivační "
        "rozhovor o návykových látkách, skutečná sezení nejsou, a přepisoval je někdo "
        "jiný a podle jiných zvyklostí. Model, který dopadne hůř na jedné půlce, tedy "
        "může být horší v délce, v motivačním rozhovoru, nebo v češtině, a nic tady ty "
        "tři věci neoddělí. K jednomu jsou ty dvě půlky dobré: ke srovnání mezi sebou. "
        "Chyba, která se objeví na obou, patří modelu; chyba, která se objeví jen na "
        "přeložené půlce, patří textu, který dostal."
    ),
    "Nothing here says whether a note is true": ("Nic tady neříká, jestli je zápis pravdivý"),
    "This is the caveat to read first if these numbers are going anywhere near a "
    "clinic. The six criteria ask about the Czech and nothing else -- are the "
    "diacritics right, is this phrase a literal translation from English, is the "
    "register a clinician's. A note that is fluent, correctly typeset and entirely "
    "invented passes all six of them. The quality instrument does not close the gap "
    "either: the two attributes that would ask whether the note is accurate and "
    "whether it is thorough are exactly the ones that cannot be asked about a real "
    "session here, because answering them means putting the transcript in front of a "
    "judge and no transcript leaves the machine that holds it. So no number anywhere "
    "in this document is evidence that a note says what happened in the session. For "
    "a clinical team that is the first question, and it is the one measurement "
    "nobody here has made.": (
        "Tohle je výhrada, kterou je třeba přečíst první, pokud se tahle čísla mají "
        "dostat kamkoli blízko ambulanci. Šest kritérií se ptá na češtinu a na nic "
        "jiného — je diakritika správně, není tahle vazba doslovný překlad "
        "z angličtiny, je rejstřík klinikův. Zápis, který je plynulý, správně vysazený "
        "a úplně vymyšlený, projde všemi šesti. Ani nástroj na kvalitu tuhle mezeru "
        "nezaplní. Právě ty dva jeho atributy, které by se ptaly, jestli je zápis "
        "PŘESNÝ a jestli je DŮKLADNÝ, se u skutečného sezení položit nedají: "
        "odpovědět na ně znamená ukázat soudci přepis, a žádný přepis neopouští "
        "tenhle stroj. Žádné číslo v tomhle dokumentu tedy není důkazem, že zápis "
        "říká to, co se v sezení opravdu stalo. Pro klinický tým je to "
        "otázka první v pořadí a je to jediné měření, které tu nikdo neudělal."
    ),
    "Almost nothing here has been checked against a person": (
        "Skoro nic z tohohle nebylo ověřeno proti člověku"
    ),
    (
        "These six criteria are this repository's own. No published Czech note-quality "
        "instrument exists to reproduce, so they were written for this track -- and "
        "unlike PDSQI-9 there is not even a published figure saying how often two "
        "people answering them would agree with each other. What stands in for that "
        "here is two independent judges answering every question separately, which is "
        "why this document prints both of them in every cell and marks the cells where "
        "they differ: the disagreement is the control."
    ): (
        "Těch šest kritérií je vlastních tomuhle repozitáři. Žádný publikovaný český "
        "nástroj na kvalitu zápisů, který by se dal převzít, neexistuje, takže vznikla "
        "pro tuhle větev — a na rozdíl od PDSQI-9 u nich není ani publikované číslo, "
        "jak často by se na odpovědi shodli dva lidé. Místo toho tu stojí dva nezávislí "
        "soudci, kteří odpovídají na každou otázku zvlášť. Právě proto tenhle dokument "
        "tiskne v každé buňce oba a buňky, kde se liší, zvýrazňuje: tou kontrolou je "
        "právě jejich neshoda."
    ),
    "One exception, and it is small enough to state exactly. A native speaker has "
    "answered all {criteria} questions about {notes} of these notes, and the two judges "
    "answered as he did on {low} and {high} of them. That is a comparison and not a "
    "ceiling: with one rater there is no second person to say how far two people would "
    "have agreed with each other, so where a judge and he differ, nothing here says "
    "which of them was right. The count for each criterion is in the criterion-by-"
    "criterion chapter above, and it is all there is -- nobody has rated a note in the "
    "Deepsy format, a note from the translated half, or any note at all on PDSQI-9.": (
        "Jedna výjimka, a je dost malá na to, aby se dala popsat přesně. Rodilý mluvčí "
        "odpověděl na všech {criteria} otázek u {notes} těchhle zápisů a oba soudci "
        "odpověděli stejně jako on u {low} a {high} z nich. Je to srovnání, ne strop: "
        "když je soudce jeden, není tu druhý člověk, který by řekl, jak moc by se "
        "spolu dva lidé shodli — takže tam, kde se soudce a on rozejdou, odsud neplyne, "
        "kdo z nich měl pravdu. Počet u každého kritéria je v kapitole kritérium po "
        "kritériu výše a je to všechno, co existuje: nikdo nehodnotil zápis ve formátu "
        "Deepsy, zápis z přeložené půlky ani jakýkoli zápis na PDSQI-9."
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
    # The three cells of the control table. The subject is the criterion, which
    # is neuter in Czech, so the verb agrees with it and not with the fault.
    "found it": "chybu našlo",
    "also fires on a clean note": "spustí se i na čistém zápisu",
    "did not find it": "chybu nenašlo",
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
    # --- bands, not places -------------------------------------------------
    "sessions": "sezeních",
    "the SOAP halves": "české větve ve formátu SOAP",
    "the Deepsy format": "formát Deepsy",
    "Those names do not all rest on the same amount, and the thinnest of them is "
    "worth reading beside the claim: {named}. That count is the notes answered on "
    "every criterion the band averages, out of the sessions its table has, and the "
    "notes column of the tables below prints it beside every row it applies to.": (
        "Za každým z těch jmen ale nestojí stejně zápisů. U toho, za kterým jich stojí "
        "nejmíň, je dobré to vědět, než se tvrzení výš vezme vážně: {named}. To číslo "
        "znamená, "
        "kolik zápisů daného modelu mělo zodpovězená všechna kritéria, ze kterých se "
        "pásmo počítá — z počtu sezení, která ta tabulka má. V tabulkách níž je "
        "u každého takového řádku ve sloupci se zápisy."
    ),
    "A band boundary is drawn at a threshold that resampling the sessions reproduces "
    "only to about {jitter}. These models sit within that of one, so this measurement "
    "does not place them: a different resample puts them in the next band along.": (
        "Hranice pásma se kreslí na mezi, kterou převzorkování sezení reprodukuje jen "
        "asi na {jitter}. Tyto modely leží od některé hranice blíž než to, takže je "
        "toto měření neumísťuje: jiné převzorkování je posune do sousedního pásma."
    ),
    "Band": "Pásmo",
    "Models": "Modely",
    # --- three views of one question ---------------------------------------
    # The three names are written lower case and in the nominative, because
    # they are read inside a list ("A and B") as often as at the head of a
    # paragraph, and a Czech noun phrase built to decline in one place will be
    # wrong in the other. `_perspectives` recases the first letter where one
    # opens a paragraph.
    "the six Czech criteria on the SOAP notes": "šest českých kritérií na zápisech SOAP",
    "PDSQI-9 on the same SOAP notes": "PDSQI-9 na týchž zápisech SOAP",
    "the six Czech criteria on the Deepsy notes": "šest českých kritérií na zápisech Deepsy",
    "Three views of one question": "Tři pohledy na jednu otázku",
    "This document has now asked one question three times over, and a reader who has come "
    "this far is holding three sets of tables with nothing saying whether they are three "
    "answers or one answer printed three ways. The question is the same every time: which "
    "of these models writes a note worth having. What changes is what is asked about the "
    "note, and which note was written. This chapter says what differs between the three, "
    "what follows from that, whether any one of them could be dropped, and what keeping all "
    "three costs.": (
        "Tenhle dokument se teď na jednu otázku zeptal třikrát a čtenář, který došel až "
        "sem, drží v ruce tři sady tabulek, aniž by mu kdokoli řekl, jestli jsou to tři "
        "odpovědi, nebo jedna odpověď vytištěná třikrát. Otázka je pokaždé táž: který "
        "z těch modelů napíše zápis, který stojí za to mít. Mění se to, na co se u zápisu "
        "ptáme, a to, který zápis vlastně vznikl. Tahle kapitola říká, čím se ty tři "
        "pohledy liší, co z toho plyne, jestli by se některý z nich dal vypustit a co "
        "stojí držet všechny tři."
    ),
    "What differs between them": "Čím se liší",
    "Six yes/no questions about the Czech itself, put to the note each model wrote in the "
    "SOAP format from both halves of the corpus: {models} models, {notes} notes. It cannot "
    "say whether a note is any good. A flawless Czech sentence about nothing passes all six "
    "of them.": (
        "Šest otázek ano/ne o samotné češtině, položených nad zápisem, který každý model "
        "napsal ve formátu SOAP z obou půlek korpusu: {models} modelů, {notes} zápisů. "
        "Neumí říct, jestli je zápis dobrý. Bezchybná česká věta o ničem projde všemi "
        "šesti."
    ),
    "A published instrument asking whether the note is worth filing -- whether it is useful, "
    "whether it is organised, whether it says what it says in as few words as it can. It "
    "reads the notes the criteria have already read, {notes} of them from {models} models, "
    "and writes none of its own.": (
        "Publikovaný nástroj, který se ptá, jestli zápis stojí za založení do dokumentace "
        "— jestli je užitečný, jestli je uspořádaný, jestli říká to, co říká, tak stručně, "
        "jak jen může. Čte zápisy, které už přečetla kritéria, {notes} zápisů od {models} "
        "modelů, a žádný vlastní nepíše."
    ),
    "Its two halves are not even the same questions: {missing} of its attributes cannot be "
    "asked about a real session, because answering them means reading the transcript and no "
    "transcript is ever sent to a judge. On that half those attributes are missing rather "
    "than low.": (
        "Jeho dvě půlky nejsou ani tytéž otázky: na některé jeho atributy — je jich "
        "{missing} — se u skutečného sezení zeptat nejde, protože odpovědět na ně znamená "
        "přečíst si přepis a žádný přepis se soudci neposílá. Na téhle půlce ty atributy "
        "chybí, ne že by byly nízké."
    ),
    "The same six questions about the Czech, put to the note format the Deepsy application "
    "actually writes: {models} models, {notes} notes. Same criteria as the first view with a "
    "different note under them, so where those two disagree it is the note that changed.": (
        "Týchž šest otázek o češtině, položených nad formátem zápisu, který aplikace Deepsy "
        "opravdu píše: {models} modelů, {notes} zápisů. Stejná kritéria jako v prvním "
        "pohledu, jen pod nimi leží jiný zápis — takže kde se ty dva rozejdou, změnil se "
        "zápis."
    ),
    "Those are not the same models, and that on its own forbids adding the three together. "
    "{shared} of them are in all three views and {only} are in some views and not others -- "
    "either the endpoint refused those notes or that view never asked for them. An average "
    "over three views would be an average over three different fields of models, which is a "
    "statement about who was present rather than about who writes well.": (
        "Nejsou to tytéž modely a už jen to zakazuje ty tři pohledy sčítat. Ve všech třech "
        "pohledech jich je {shared}; zbytek, tedy {only}, je v některých pohledech a "
        "v jiných ne — buď server ty zápisy odmítl, nebo si o ně ten pohled nikdy "
        "neřekl. Průměr přes tři pohledy by "
        "byl průměrem přes tři různá pole modelů, což je výrok o tom, kdo byl přítomen, ne "
        "o tom, kdo píše dobře."
    ),
    "What follows from that": "Co z toho plyne",
    "If the three were saying one thing, they would put the models in one order. The order "
    "each view uses is the one its own tables print -- by dominance, which needs no scale "
    "and can therefore be compared between instruments that do not share one -- and how far "
    "two orders agree is a rank correlation over the models both views hold. There are "
    "{comparisons} of those: each pair of views, on each half of the corpus, under each "
    "judge separately. A correlation of 1 would mean the two put every model in the same "
    "place; 0 would mean that knowing one order tells a reader nothing about the other.": (
        "Kdyby ty tři pohledy říkaly jednu věc, seřadily by modely do jednoho pořadí. "
        "Každý pohled používá pořadí, které tisknou jeho vlastní tabulky: podle "
        "dominance. Ta nepotřebuje žádnou škálu, takže jde porovnávat i dva nástroje, "
        "které žádnou společnou škálu nemají. To, jak moc se dvě pořadí shodují, je "
        "pak pořadová korelace přes modely, které mají oba pohledy. Takových "
        "porovnání je "
        "{comparisons}: každá dvojice pohledů, na každé půlce korpusu, u každého soudce "
        "zvlášť. Korelace 1 by znamenala, že oba dávají každý model na totéž místo; 0, že "
        "z jednoho pořadí čtenář o tom druhém nezjistí nic."
    ),
    "The pair that agrees most -- {closest} -- stays between {closest_low} and "
    "{closest_high} across its comparisons. The pair that agrees least -- {furthest} -- runs "
    "from {furthest_low} to {furthest_high}.": (
        "Dvojice, která se shoduje nejvíc — {closest} — se ve svých porovnáních drží mezi "
        "{closest_low} a {closest_high}. Dvojice, která se shoduje nejmíň — {furthest} — "
        "jde od {furthest_low} do {furthest_high}."
    ),
    "There is one pair of views to compare here -- {pair} -- and it runs between {low} and "
    "{high} across its comparisons.": (
        "Porovnat jde tady jediná dvojice pohledů — {pair} — a ve svých porovnáních jde od "
        "{low} do {high}."
    ),
    "Is any one of them redundant?": "Je některý z nich zbytečný?",
    "Here is the test this chapter applies, written out so that a reader who disagrees with "
    "it can say where. A view is redundant when two things are true at once: it puts the "
    "models in the same order as some other view -- under both judges and on both halves, "
    "not on average -- and it separates no pair of models that the other view leaves "
    "together. The first half asks whether it says anything different; the second asks "
    "whether it says anything more. Failing either one is enough to keep it.": (
        "Tady je zkouška, kterou tahle kapitola používá, vypsaná tak, aby čtenář, který "
        "s ní nesouhlasí, mohl říct kde. Pohled je zbytečný, když platí zároveň dvě věci: "
        "řadí modely stejně jako některý jiný pohled — u obou soudců a na obou půlkách, ne "
        "v průměru — a neodliší žádnou dvojici modelů, kterou ten druhý pohled nechává "
        "pohromadě. První půlka se ptá, jestli říká něco jiného; druhá, jestli říká něco "
        "navíc. Stačí neprojít jednou z nich a pohled si necháváme."
    ),
    "The first half: no two views put the models in the same order. The closest any single "
    "comparison comes is {best}, where an identical order would be 1.": (
        "První půlka: žádné dva pohledy neřadí modely stejně. Nejblíž se k tomu dostane "
        "jediné porovnání s hodnotou {best}, přičemž shodné pořadí by bylo 1."
    ),
    "The first half: {pairs} put the models in the same order, under both judges and on both "
    "halves. No other pair of views does.": (
        "První půlka: {pairs} — tyhle pohledy řadí modely stejně, u obou soudců a na obou "
        "půlkách. Žádná jiná dvojice pohledů ne."
    ),
    "The second half: every view separates pairs of models that the others leave together. "
    "The view that adds fewest still adds {fewest} of them, counted over the models the two "
    "views share, and the one that adds most adds {most}.": (
        "Druhá půlka: každý pohled odliší dvojice modelů, které ostatní nechávají "
        "pohromadě. I ten pohled, který přidává nejmíň, jich přidá {fewest}, počítáno přes "
        "modely, které mají oba pohledy společné, a ten, který přidává nejvíc, jich přidá "
        "{most}."
    ),
    "The second half: {names} separates no pair of models that some other view does not "
    "separate as well.": (
        "Druhá půlka: {names} — tenhle pohled neodliší žádnou dvojici modelů, kterou by "
        "neodlišil i některý jiný."
    ),
    "So none of the three can be dropped, and it fails on both halves of the test rather "
    "than on a technicality: the views do not agree about the order, and each of them "
    "separates models the others cannot. That is not a comfortable result. It means this "
    "document holds three answers to one question with no honest way of reducing them to "
    "one, and a team choosing a model has to decide first which of the three they are "
    "choosing on.": (
        "Vypustit tedy nejde ani jeden ze tří a neprojde to na obou půlkách zkoušky, ne na "
        "nějaké formalitě: pohledy se neshodnou na pořadí a každý z nich odliší modely, "
        "které ostatní odlišit neumějí. Není to pohodlný výsledek. Znamená to, že tenhle "
        "dokument drží tři odpovědi na jednu otázku a nemá poctivý způsob, jak je smrštit "
        "na jednu — a tým, který si vybírá model, se musí nejdřív rozhodnout, podle kterého "
        "z těch tří pohledů si vybírá."
    ),
    "So one of them can be dropped: {redundant} adds nothing that {other} does not already "
    "say. It puts the models in the same order, under both judges and on both halves, and it "
    "separates no pair of models that the other one leaves together.": (
        "Jeden z nich tedy vypustit jde: {redundant} nepřidává nic, co by {other} neříkal "
        "už sám. Řadí modely stejně, u obou soudců a na obou půlkách, a neodliší žádnou "
        "dvojici modelů, kterou ten druhý nechává pohromadě."
    ),
    "What keeping all three costs": "Co stojí držet všechny tři",
    "Keeping a view costs whatever its notes cost to write, and only two of the three write "
    "any. The SOAP notes took {soap_calls} calls to e-INFRA for {soap_notes} notes. The "
    "quality view cost no generation at all -- it reads those same notes, so keeping it "
    "costs nothing that was not already spent. The Deepsy notes took {deepsy_calls} calls "
    "for {deepsy_notes} notes, because that format is asked for one section at a time and a "
    "note there is three answers rather than one. Set against three orders that will not "
    "reduce to one, that is the cheap half of the problem.": (
        "Držet pohled stojí tolik, kolik stálo napsat jeho zápisy, a píše je jen jeden ze "
        "tří. Zápisy SOAP stály {soap_calls} volání na e-INFRA za {soap_notes} zápisů. "
        "Pohled na kvalitu nestál žádné generování — čte tytéž zápisy, takže jeho držení "
        "nestojí nic, co už nebylo utraceno. Zápisy Deepsy stály {deepsy_calls} volání za "
        "{deepsy_notes} zápisů, protože ten formát se ptá po jedné sekci zvlášť a zápis "
        "v něm nejsou jedna, ale tři odpovědi. Proti třem pořadím, která se nedají smrštit "
        "na jedno, je tohle ta levnější půlka problému."
    ),
    # --- general capability against these numbers --------------------------
    "Does general capability predict any of this?": ("Předpovídá obecná schopnost něco z tohohle?"),
    "Nothing in this repository records how big a model is, how it was trained or when "
    "it shipped, so this half has to come from outside it. The index used here is a "
    "published one that scores models on general capability -- the kind of number a "
    "team reads before choosing one. The question is whether it says anything about "
    "the notes, and whether it says the same thing in both languages.": (
        "Nic v tomhle repozitáři nezaznamenává, jak velký model je, jak byl trénovaný "
        "ani kdy vyšel, takže tahle polovina musí přijít zvenčí. Použitý index je "
        "publikovaný a hodnotí modely podle obecné schopnosti — je to ten druh čísla, "
        "podle kterého si tým model vybírá. Otázka zní, jestli říká něco o zápisech "
        "a jestli říká totéž v obou jazycích."
    ),
    "On the left the English notes, on the right the Czech ones, one dot per model and "
    "one colour per judge. The vertical axis runs the whole of PDSQI-9, from 1 to 5, "
    "rather than the part these models occupy, so how little of the instrument is in "
    "use is visible before the slope across it is read. Each judge's correlation and "
    "the number of models behind it are both in the legend, and the second number "
    "matters as much as the first.": (
        "Vlevo anglické zápisy, vpravo české, jeden bod na model a jedna barva na "
        "soudce. Svislá osa jde přes celé PDSQI-9, od 1 do 5, a ne jen přes tu část, "
        "kterou modely obsazují — je tedy vidět, jak málo se z nástroje využívá, dřív "
        "než se začne číst sklon přes něj. V legendě je u každého soudce jeho korelace "
        "i počet modelů, na kterých stojí, a to druhé číslo je stejně důležité jako "
        "to první."
    ),
    "Measured here": "Měřeno tady",
    "Intelligence index": "Index inteligence",
    "Release date": "Datum vydání",
    "English completeness": "Anglická úplnost",
    "English quality (PDSQI-9)": "Anglická kvalita (PDSQI-9)",
    "Czech quality (PDSQI-9)": "Česká kvalita (PDSQI-9)",
    "Czech language (the six criteria)": "Čeština (šest kritérií)",
    "Neither of the outside numbers in this chapter was measured by this project, and "
    "each is joined to it at a weak point.": (
        "Ani jedno z čísel zvenčí, která jsou v téhle kapitole, jsme neměřili my, "
        "a obě jsou k našim číslům připojená ve slabém místě."
    ),
    "The capability index is a published third-party score, and the join to it is "
    "nothing but the model's name: a name on this endpoint is not evidence about which "
    "model is behind it, and this project's first working rule exists because one id "
    "there returned another model's output.": (
        "Index schopnosti je publikované skóre třetí strany a spojuje ho s naším "
        "měřením jediné: jméno modelu. To je slabý článek. Jméno na tomhle serveru "
        "totiž není důkaz o tom, který model za ním doopravdy stojí — první pracovní "
        "pravidlo tohohle projektu vzniklo právě proto, že jedno z tamních id "
        "vracelo výstup jiného modelu."
    ),
    "Models whose name does not identify a variant are absent rather than guessed:": (
        "Modely, jejichž jméno neurčuje variantu, tu nejsou, místo aby se hádaly:"
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
        "sezení. Deset z nich je skutečných a deset přeložených. Každý model psal ve "
        "dvou formátech: SOAP a ten, který píše aplikace Deepsy. Každý zápis, který "
        "přišel, pak ohodnotili dva nezávislí soudci. Ne každý model dostal obě "
        "zadání; napsáno bylo {written} zápisů z {asked} a kde některý chybí, je to "
        "napsané u té tabulky. Měřily se dvě různé věci. Šest kritérií ano/ne se "
        "ptá, jestli je čeština správně. PDSQI-9, publikovaný nástroj, se ptá, "
        "jestli je zápis dobrý — a ten dostaly jen zápisy SOAP. "
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
    # --- the criterion measured but not drawn ------------------------------
    "The {deepsy} notes in the Deepsy format were read against the criteria only. "
    "PDSQI-9 was never asked about a Deepsy note, so no quality figure anywhere in "
    "this document is about one.": (
        "{deepsy} zápisů ve formátu Deepsy prošlo jen kritérii. Na zápis v Deepsy se "
        "PDSQI-9 nikdy nikdo neptal, takže žádné číslo o kvalitě v tomhle dokumentu "
        "není o něm."
    ),
    # --- length ------------------------------------------------------------
    "How long the notes are, and whether length is rewarded": (
        "Jak dlouhé zápisy modely píšou a jestli se délka vyplácí"
    ),
    "the data section": "sekce data",
    "the hypotheses section": "sekce hypotézy",
    "the plan section": "sekce plán",
    "{quiet} of the {families} prompt families say nothing at all about how long a "
    "note should be. "
    "The Deepsy prompt says it twice: a ceiling of {limit} words per section, which "
    "the prompt itself calls invalid to exceed, and a target of the same {limit} "
    "words.": (
        "{quiet} ze {families} rodin zadání o délce zápisu neříkají vůbec nic. Zadání "
        "pro Deepsy to říká "
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
        "necháme být. Je to jediné místo v celém projektu, kde jde lidský zápis "
        "s modelovým vůbec porovnat — a celé pole modelů leží na jedné straně."
    ),
    "Where a length WAS set, the ceiling was kept and the target was not. Only {over} "
    "of {answers} answers exceed the {limit}-word limit -- but {section} uses {share} "
    "of the length it was asked for. The models read \u201cmust not exceed\u201d and "
    "did not read \u201cthe target is {limit} words\u201d.": (
        "Tam, kde délka zadaná BYLA, se dodržel strop a nedodržel cíl. Limit {limit} "
        "slov překračuje jen {over} z {answers} odpovědí — ale {section} využívá "
        "{share} délky, o kterou si zadání řeklo. Modely si přečetly „nesmí "
        "překročit“ a nepřečetly si „cílová délka je {limit} slov“."
    ),
    (
        "The two languages then pull in opposite directions, and this is the most "
        "useful thing to know before reading any table above. In English a longer note "
        "scores higher for completeness under both judges. In Czech it scores lower on "
        "{against} of the {total} criterion-and-judge coefficients -- {soap_against} of "
        "{soap_total} on the SOAP halves and {deepsy_against} of {deepsy_total} in the "
        "Deepsy format, which is one reason the two are never pooled -- and the "
        "exceptions are named rather than rounded away: the columns where the "
        "coefficient stays positive under BOTH judges are {positive}. The chart below "
        "says the same thing without the coefficients. Each dot is one model: its "
        "median note length across the bottom, the six criteria averaged up the side, "
        "one panel for each half of the corpus. The two judges are drawn in separate "
        "colours and never averaged, so a model they disagree about appears as two dots "
        "at different heights instead of as one number somewhere between them. The "
        "dashed line is the straight line that best fits one judge's dots -- drawn "
        "rather than described, because a slope is easier to argue with when the points "
        "it was fitted to are on the page beside it."
    ): (
        "Oba jazyky pak táhnou na opačné strany a tohle je to nejužitečnější, co je "
        "dobré vědět dřív, než se člověk pustí do kterékoli tabulky výše. V angličtině "
        "delší zápis dostává vyšší úplnost, a to u obou soudců. V češtině je to naopak: "
        "delší zápis má horší skóre, a to v {against} z {total} kombinací kritéria a "
        "soudce. Rozpad je {soap_against} z {soap_total} ve větvích SOAP a "
        "{deepsy_against} z {deepsy_total} ve formátu Deepsy — což je jeden z důvodů, "
        "proč se obojí nikdy nesčítá. Výjimky se jmenují, nezaokrouhlují: sloupce, ve "
        "kterých koeficient zůstává kladný u OBOU soudců, jsou {positive}. Graf níže "
        "říká totéž bez koeficientů. Každý bod je jeden model: vodorovně mediánová "
        "délka jeho zápisu, svisle průměr šesti kritérií, jeden panel pro každou půlku "
        "korpusu. Oba soudci jsou vykreslení zvlášť, každý svou barvou, a nikdy se "
        "neprůměrují — model, na kterém se neshodnou, je proto vidět jako dva body v "
        "různé výšce, ne jako jedno číslo někde mezi nimi. Přerušovaná čára je přímka, "
        "která nejlíp prokládá body jednoho soudce; je nakreslená, a ne popsaná, "
        "protože se sklonem se lépe polemizuje, když má člověk na stránce vedle něj i "
        "body, ze kterých vznikl."
    ),
    "Two panels, one for each half of the corpus, and one colour for each judge. The "
    "thing to look at is whether the two dashed lines in a panel fall the same way: a "
    "slope one judge sees and the other does not would be a fact about that judge "
    "rather than about length.": (
        "Dva panely, jeden pro každou půlku korpusu, a jedna barva pro každého soudce. "
        "Dívat se je třeba na to, jestli obě přerušované čáry v panelu klesají stejně: "
        "sklon, který vidí jeden soudce a druhý ne, by byl výrok o tom soudci, ne "
        "o délce."
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
    (
        "The same test in the Deepsy format comes out {hit} of its {total} table-and-judge "
        "combinations, and the three models that write longest there are a different three, "
        "because the two formats were not asked of the same models. Where the last three "
        "places go is a fact about the SOAP halves rather than a law about length."
    ): (
        "Táž zkouška ve formátu Deepsy vychází {hit} z jeho {total} tabulek a tři "
        "modely, které tam píšou nejdéle, jsou jiné tři, protože oba formáty nedostaly "
        "tytéž modely. Kam padnou poslední tři místa, je výrok o větvích SOAP, ne "
        "zákon o délce."
    ),
    # --- the sort, named beside the table ----------------------------------
    "and": "a",
    "Nothing here separates these models: no column takes two different values.": (
        "Tady modely nerozlišuje nic: žádný sloupec nemá dvě různé hodnoty."
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
    # --- how often the two judges agreed, read rather than written --------
    "The two judges answered the same way on {agreed} of the {compared} notes both of "
    "them answered, {rate}% of them.": (
        "Oba soudci odpověděli stejně u {agreed} ze {compared} zápisů, které "
        "zodpověděli oba, tedy u {rate} % z nich."
    ),
    "Notes only one of the two answered are left out of that count rather than counted "
    "against it: {unanswered} of them.": (
        "Zápisy, které zodpověděl jen jeden ze soudců, do toho počtu nevstupují, místo "
        "aby se počítaly proti němu: {unanswered}."
    ),
    "How often the two judges answered the same way is not printed here: the answers "
    "on disk were counted under {measured} and these tables draw {drawn}. Re-run "
    "tools/czech_anchor.py.": (
        "Jak často oba soudci odpověděli stejně, se tu netiskne: odpovědi na disku "
        "byly spočítané pod {measured} a tyhle tabulky kreslí {drawn}. Spusťte znovu "
        "tools/czech_anchor.py."
    ),
    # --- what each criterion catches, without a figure in it --------------
    "Read this column as a flag rather than as a score. Whether a Czech phrase is a "
    "literal translation from English is a judgement people make differently, and the "
    "count below shows that rather than hiding it.": (
        "Tenhle sloupec čti jako upozornění, ne jako známku. Jestli je nějaké české "
        "spojení doslovný překlad z angličtiny, posuzují lidé různě, a počet níže to "
        "ukazuje, místo aby to schovával."
    ),
    "The fault it catches is unambiguous: an English term left sitting in a Czech sentence.": (
        "Chyba, kterou chytá, je jednoznačná: anglický termín ponechaný uprostřed české věty."
    ),
    "Catches real grammatical faults.": "Chytá skutečné gramatické chyby.",
    "Catches colloquial words where clinical ones belong.": (
        "Chytá hovorová slova tam, kam patří odborná."
    ),
    # --- the conclusion, before the tables ---------------------------------
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
        "Kolik z toho, co ty jazykové tabulky měří, je ve skutečnosti jen délka? Není to "
        "odhad, je to změřené: "
        "každých sto slov navíc stojí {low} až {high} setin bodu, u každého soudce a na "
        "obou polovinách. Ten vliv se ale odečíst nedá tak, aby z toho vyšlo pořadí, "
        "které by vydrželo — proto se žádné takové netiskne. Zbývá jen otázka, kolik "
        "dvojic modelů obstojí i tehdy, když se delšímu pisateli přičte co největší "
        "možný postih za délku: obstojí {survived} z {decided} rozhodnutých dvojic."
    ),
    (
        "On writing correct Czech, {top} in the top band of all {tables} table-and-judge "
        "combinations the bands cover -- the SOAP halves, both judges. {bottom} in the bottom "
        "band of all {tables}. Between those two ends the tables disagree with each other, so "
        "nothing else here is a ranking."
    ): (
        "Ve psaní správné češtiny: {top} v nejvyšším pásmu ve všech {tables} tabulkách "
        "najednou. Ty tabulky jsou obě větve SOAP, každá očima obou soudců. Naopak "
        "{bottom} v nejnižším pásmu ve všech {tables}. Mezi těmi dvěma konci si tabulky "
        "odporují, takže nic mezi nimi pořadí není."
    ),
    (
        "The Deepsy format was asked the same question over its own {tables} table-and-judge "
        "combinations, and it is counted separately rather than pooled with the four above: "
        "{top} in the top band of all of them and {bottom} in the bottom band of all of them. "
        "The two formats are not added together because not every model was asked in both, "
        "because a Deepsy note is written to a different prompt and comes out a different "
        "shape, and because the one native-speaker anchor this project has was measured on "
        "SOAP notes alone. Length does not settle it either way: it runs against "
        "{soap_against} of the {soap_total} criterion-and-judge coefficients on the SOAP "
        "halves and against {deepsy_against} of {deepsy_total} in the Deepsy format, so it is "
        "not the uniform penalty one number could stand for."
    ): (
        "Tutéž otázku dostal i formát Deepsy, na svých vlastních tabulkách — je jich "
        "{tables} a počítají se zvlášť, ne dohromady se čtyřmi výše. I tady platí "
        "totéž: {top} v nejvyšším pásmu všech z nich a {bottom} v nejnižším. Oba "
        "formáty se nesčítají ze tří důvodů: ne každý model dostal obě zadání; zápis "
        "Deepsy vzniká z jiného zadání a má jiný tvar; a jediné srovnání s rodilým "
        "mluvčím, které tenhle projekt má, proběhlo jen na zápisech SOAP. Délka to "
        "nerozhoduje ani na jednu stranu: působí proti modelu u {soap_against} "
        "z {soap_total} dvojic kritérium–soudce ve větvích SOAP a u {deepsy_against} "
        "z {deepsy_total} ve formátu Deepsy. Není to tedy postih, který by platil "
        "všude stejně a dal se shrnout jedním číslem."
    ),
    (
        "One caution about that second count. {subject} in the bottom band of all {tables} "
        "SOAP table-and-judge combinations and in no Deepsy band at all -- not because of "
        "anything written, but because e-INFRA answered {calls} of the calls asking for those "
        "notes with an error and returned no note. Adding the two counts together would have "
        "removed it from the bottom of the table on the strength of an outage."
    ): (
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
    (
        "On whether the note is any good, no model is in the top band of all {tables} "
        "table-and-judge combinations and none is in the bottom band of all {tables}. The "
        "quality instrument does not agree with itself from one judge or one half to the "
        "next, and no model can be called better on it."
    ): (
        "U otázky, jestli je zápis k něčemu, nestojí v nejvyšším pásmu všech {tables} "
        "tabulek žádný model — a v nejnižším taky žádný. Nástroj na kvalitu se totiž "
        "neshodne ani sám se sebou: jinak vychází u jednoho soudce než u druhého "
        "a jinak na jedné půlce než na druhé. Podle něj tedy nelze žádný model "
        "označit za lepší."
    ),
    "Part of why: under {judge}, {dead} of its {total} columns are the same for every "
    "model, so they order nothing. Of the {moving} that do move, the one no model does "
    "well on is {alive} -- the best reaches {worst} out of 5. The other judge separates "
    "more of them, and that the two disagree about which columns work is itself the "
    "finding.": (
        "Zčásti proto, že podle soudce {judge} mají {dead} z jeho {total} sloupců "
        "všechny modely stejné, takže nic neřadí. Ze zbylých {moving}, které se "
        "hýbou, je jeden takový, že si v něm nevede dobře nikdo: {alive}. Nejlepší model "
        "v něm dosáhne {worst} z 5. Druhý soudce jich rozliší víc, a to, že se ti dva "
        "neshodnou na "
        "tom, které sloupce fungují, je samo o sobě nález."
    ),
    (
        "Read the bottom of those tables carefully: the three models that write the longest "
        "notes take the last three places in all {total} table-and-judge combinations of "
        "them. Each criterion asks whether there is a fault anywhere in a note, and a longer "
        "note has more places to hide one. On the quality instrument, rating the very same "
        "notes, those three models are not at the bottom."
    ): (
        "Spodek těch tabulek čti opatrně: tři modely, které píšou nejdelší zápisy, "
        "obsazují poslední tři místa ve všech {total}. Každé kritérium se ptá, jestli "
        "je v zápisu někde chyba, a delší zápis má víc míst, kde ji schovat. Na "
        "nástroji na kvalitu, který hodnotí úplně tytéž zápisy, ty tři modely na "
        "spodku nejsou."
    ),
    (
        "That pattern is not a law: in the {total} Deepsy table-and-judge combinations the "
        "three longest-writing models -- a different three, because the two formats were not "
        "asked of the same set of models -- do not all land in the last three places under "
        "either judge. Length and rank travel together on the SOAP halves and more loosely "
        "here, which is one more reason the two formats are counted apart rather than added "
        "up."
    ): (
        "Ten vzorec není zákon: na {total} tabulkách Deepsy tři modely s nejdelšími zápisy "
        "— jsou to jiné tři, protože oba formáty nedostaly tutéž sadu modelů — neobsadí "
        "poslední tři místa ani u jednoho soudce. Délka a příčka jdou spolu ve větvích SOAP "
        "a tady volněji, což je další důvod, proč se oba formáty počítají zvlášť a nesčítají."
    ),
    "And the English leaderboard does not predict this. The same instrument asked in "
    "both languages transfers; the single measure the English page ranks by -- "
    "{measure} -- does not. A model's standing there says nothing about the Czech it "
    "writes.": (
        "A anglický žebříček tohle nepředpovídá. Týž nástroj položený v obou "
        "jazycích se přenáší; jediná míra, podle které anglická stránka řadí — "
        "{measure} — se nepřenáší. Postavení modelu na anglickém žebříčku tedy neříká "
        "nic o češtině, kterou ten model píše."
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
        "Pro srovnání: terapeutka, která psala referenční zápisy pro TN-Eval, použila "
        "{human} slov na zápis. {over}"
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
    # The count of copies stands between dashes, as an apposition: a Czech noun
    # after a numeral declines differently at three and at five, and a
    # placeholder cannot know which the payload holds.
    "The same question has to be put to the quality instrument a different way. "
    "Several of its columns come back with the same score for every model in this "
    "document, and how many of them depends on which judge is asked. A column that "
    "never moves is either measuring something these models genuinely do not differ "
    "on or measuring nothing at all, and nothing already scored can tell those apart, "
    "because nothing already scored is a badly written note. So one was written: an "
    "invented note with no model and no session behind it, and copies of it -- "
    "{variants} of them -- each damaged in one named way, sentences put into the wrong "
    "section or a note cut off before it reaches a plan. What each copy was expected "
    "to move was written down before the judge was asked, and what follows is which "
    "columns actually moved.": (
        "Nástroji na kvalitu se tatáž otázka musí položit jinak. Několik jeho sloupců "
        "vrací u každého modelu v tomhle dokumentu totéž skóre a kolik jich je, závisí "
        "na tom, kterého soudce se zeptáme. Sloupec, který se nikdy nehne, buď měří "
        "něco, v čem se tyhle modely doopravdy neliší, nebo neměří nic — a nic z toho, "
        "co už je oskórované, tyhle dvě možnosti nerozliší, protože nic z toho není "
        "špatně napsaný zápis. Jeden se tedy napsal: vymyšlený zápis, za kterým "
        "nestojí žádný model ani žádné sezení, a jeho kopie — v počtu {variants} — "
        "každá poškozená jedním pojmenovaným způsobem, třeba větami přesunutými do "
        "špatné sekce nebo zápisem useknutým dřív, než dojde na plán. Co má která "
        "kopie pohnout, bylo zapsáno dřív, než se soudce zeptal, a co následuje, je "
        "to, které sloupce se opravdu pohnuly."
    ),
    "It can, and this settles the flat columns: {columns} all drop under both "
    "judges on the note built to attack them. The judge is looking. The models score "
    "the same on those columns because they write into the same dictated four-part "
    "structure and genuinely do not differ, not because the question goes "
    "unanswered -- so those columns stay in the tables, as an honest measurement "
    "of something that does not vary here.": (
        "Umí, a tím jsou ploché sloupce vysvětlené: {columns} klesnou u obou soudců "
        "na tom zápisu, který je na ně ušitý. Soudce se tedy dívá. Modely mají v těch "
        "sloupcích stejné skóre proto, že píšou do téže předepsané čtyřdílné "
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
    "the six Czech criteria": "šest českých kritérií",
    "PDSQI-9, without the session": "PDSQI-9, bez sezení",
    "PDSQI-9, with the session": "PDSQI-9, se sezením",
    # --- criterion by criterion ------------------------------------------------
    "Criterion by criterion": "Kritérium po kritériu",
    "The six criteria one at a time. A table can say what a column scored and it cannot say what "
    "the column is worth, and the second half is what a reader needs before acting on the first. "
    "Each paragraph gives the same four things in the same order: the level, under both judges in "
    "every table that has the criterion; the direction, which way the criterion moves from one "
    "table to the next; where it breaks down; and what it is actually catching.": (
        "Šest kritérií po jednom. Tabulka umí říct, kolik sloupec dostal, ale ne, jakou má ten "
        "sloupec cenu — a ta druhá půlka je to, co čtenář potřebuje dřív, než podle té první začne "
        "jednat. Každý odstavec dává tytéž čtyři věci ve stejném pořadí: úroveň, u obou soudců v "
        "každé tabulce, která to kritérium má; směr, kterým se kritérium hýbe od jedné tabulky ke "
        "druhé; kde se to láme; a co to vlastně zachycuje."
    ),
    "The order is computed rather than chosen. The criterion whose value changes most between one "
    "table and the next comes first, because that is the order in which one number about a "
    "criterion would mislead a reader furthest -- a column that reads the same everywhere can be "
    "summarised and a column that does not, cannot.": (
        "Pořadí je spočítané, ne zvolené. První je kritérium, jehož hodnota se mezi jednou "
        "tabulkou a druhou mění nejvíc, protože přesně v tomhle pořadí by jedno číslo o kritériu "
        "svedlo čtenáře nejdál — sloupec, který je všude stejný, se shrnout dá, a sloupec, který "
        "stejný není, ne."
    ),
    (
        "Every pair of numbers is the two judges, in the order the tables print them, "
        "and they are never averaged: where the two point in opposite directions that "
        "is said rather than smoothed, because a mean of two judges pointing opposite "
        "ways is a number neither of them stated. And the last sentence of each "
        "paragraph -- what the criterion catches, and how often the two judges and one "
        "native speaker said the same thing -- was measured on the ten real Czech "
        "sessions under these six criteria and nowhere else. Nobody has read a Deepsy "
        "note or a translated one against a person at all."
    ): (
        "Každá dvojice čísel jsou dva soudci v pořadí, ve kterém je tisknou tabulky. "
        "Nikdy se neprůměrují. Tam, kde ti dva ukazují opačnými směry, se to říká a "
        "neuhlazuje — průměr dvou soudců mířících proti sobě je totiž číslo, které "
        "neřekl ani jeden z nich. A poslední věta každého odstavce — co kritérium "
        "zachycuje a jak často řekli dva soudci a jeden rodilý mluvčí totéž — byla "
        "změřena na deseti skutečných českých sezeních podle těchto šesti kritérií a "
        "nikde jinde. Zápis v Deepsy ani přeložený zápis proti člověku nikdo nečetl."
    ),
    "The level: {items}.": "Úroveň: {items}.",
    "The direction: {items}.": "Směr: {items}.",
    "up": "nahoru",
    "down": "dolů",
    "no change": "beze změny",
    "the judges differ": "soudci se rozcházejí",
    "Where it breaks down: the two judges do not both point the same way {names}.": (
        "Kde se to láme: oba soudci neukazují stejným směrem {names}."
    ),
    (
        "Where it breaks down: on {where} the resampling can tell only {separable} of the "
        "{pairs} pairs of models apart, so the order this column puts them in there is not "
        "one to read, and it is that thin in {places} of the {total} table-and-judge "
        "combinations."
    ): (
        "Kde se to láme: v jedné z tabulek ({where}) odliší převzorkování jen {separable} z "
        "{pairs} dvojic modelů, takže pořadí, do kterého je tam tenhle sloupec staví, není pořadí "
        "ke čtení; takhle tenké je to v {places} z {total} tabulek."
    ),
    "Where it breaks down: on {names} the column falls as a model writes longer notes, under both "
    "judges, between {low} and {high}, and whether that is the fault or the length is not "
    "something this document can separate.": (
        "Kde se to láme: délka. Sloupec klesá, čím delší zápisy model píše — {names} —, u obou "
        "soudců, mezi {low} a {high}, a jestli za to může ta chyba, nebo délka, tenhle dokument "
        "rozlišit neumí."
    ),
    "Nothing breaks it here: the judges point the same way in every comparison, the resampling can "
    "tell the models apart, and length does not predict it.": (
        "Tady se nic neláme: soudci ukazují ve všech srovnáních stejným směrem, převzorkování "
        "dokáže modely odlišit a délka to nepředpovídá."
    ),
    "from the real sessions to the translated ones": "ze skutečných sezení do přeložených",
    "from SOAP to Deepsy on the real half": "ze SOAP do Deepsy na skutečné půlce",
    "from SOAP to Deepsy on the translated half": "ze SOAP do Deepsy na přeložené půlce",
    # --- what each chapter came to --------------------------------------------
    "The two judges point opposite ways on {names}, so between the halves there is no "
    "answer there at all.": (
        "Tady ukazují oba soudci opačnými směry — {names} — takže mezi půlkami tam žádná "
        "odpověď není."
    ),
    "Neither judge sees any difference between the halves on {names}: to the last digit "
    "these tables print, the two halves are the same there.": (
        "Rozdíl mezi půlkami tu nevidí ani jeden ze soudců — {names} — na poslední "
        "číslici, kterou tyhle tabulky tisknou, jsou obě půlky stejné."
    ),
    "On {names} one judge sees a difference between the halves and the other sees none, "
    "so there is nothing there that both of them say.": (
        "Tady vidí rozdíl mezi půlkami jeden soudce a druhý žádný — {names} — takže tam "
        "není nic, co by říkali oba."
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
    (
        "Which fault survives most often is not the same in all {tables} table-and-judge "
        "combinations, so none is named here: the weakest column changes with the table and "
        "with the judge."
    ): (
        "Která chyba přežívá nejčastěji, není ve všech {tables} těchto tabulkách totéž, takže se "
        "tu žádná nejmenuje: nejslabší sloupec se mění s tabulkou i se soudcem."
    ),
    "What these two tables come to": "K čemu tyhle dvě tabulky došly",
    (
        "One fault survives more often than any other, and it is the same one in all {tables} "
        "table-and-judge combinations -- both halves, both judges. It is {worst}: averaged "
        "over the models, between {low} and {high} of the notes are free of it, where 1.00 "
        "would mean every note was clean and 0.00 that none was."
    ): (
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
    (
        "In all {tables} table-and-judge combinations, every model scores {value} on {names} "
        "-- the top of the scale. That is a ceiling rather than a result: an attribute no "
        "model can fail cannot tell the models apart, and it should not be read as one they "
        "all did well on."
    ): (
        "Ve všech {tables} těchto tabulkách má každý model {value}, což je vrchol škály, a je to "
        "pokaždé táž položka: {names}. To je strop, ne výsledek: položka, ve které nemůže žádný "
        "model selhat, modely od sebe neodliší, a nemá se číst jako něco, v čem všechny obstály."
    ),
    (
        "The attribute every model does worst on is {worst}, in all {tables} table-and-judge "
        "combinations: {low} to {high} out of 5, averaged over the models in each of them."
    ): (
        "Položka, ve které dopadají všechny modely nejhůř, je {worst}. Ve všech {tables} "
        "těchto tabulkách a u obou soudců z ní vychází {low} až {high} z 5, v průměru přes modely "
        "v každé z nich."
    ),
    (
        "These {tables} table-and-judge combinations do not agree on which attribute the "
        "models do worst on, so none is named here."
    ): (
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
        "Chyba, která v zápisech Deepsy přežívá nejčastěji, je {worst}. Bez ní je {low} až "
        "{high} z nich. Je to táž chyba, která nejčastěji přežívá v zápisech SOAP výše, takže to, "
        "co tyhle modely v češtině kazí, není vlastnost formátu, který se po nich chtěl."
    ),
    "The fault that survives most often in the Deepsy notes is {worst}, with between {low} and "
    "{high} of them free of it. In the SOAP notes above it is {soap} instead, so what a model gets "
    "wrong changes with the shape it was asked for.": (
        "Chyba, která v zápisech Deepsy přežívá nejčastěji, je {worst}. Bez ní je {low} až "
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
        "To srovnání s sebou nese tutéž potíž jako to ve větvích SOAP: obě půlky se liší "
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
        "data, která tohle měření nedodává."
    ),
    "Two things this format does that SOAP does not. It sets a ceiling of {limit} "
    "words a section, which its own prompt calls invalid to exceed. And it asks for "
    "the answer as structured data rather than as prose, so a reply that does not "
    "parse is a failure rather than a poor note. Both are the application's "
    "decisions, reproduced from its own prompt files rather than retyped.": (
        "Dvě věci, které tenhle formát dělá a SOAP ne. Stanovuje strop {limit} slov "
        "na sekci a jeho vlastní zadání označuje delší odpověď za neplatnou. A žádá "
        "odpověď jako strukturovaná data, ne jako prózu, takže odpověď, kterou nelze "
        "rozebrat, je selhání, ne špatný zápis. Obojí je rozhodnutí té aplikace, "
        "převzaté z jejích vlastních souborů se zadáními, ne přepsané rukou."
    ),
    (
        "That is why this chapter is here, and it is worth reading before the tables "
        "above are taken too literally. SOAP is not what a Czech psychologist writes. "
        "The prompt behind every table so far is a translation of TN-Eval's, so that "
        "the task is the same task in another language, and it reproduces no Czech "
        "documentation standard because there is none to reproduce -- which makes those "
        "notes formally artificial, equally so for every model, and that equality is "
        "what keeps the comparison between them fair rather than what makes them less "
        "artificial. Here the same models write from the same sessions and the only "
        "thing that changes is the shape they were asked for. The figure below shows "
        "what came of that, and the paragraph under it names the one thing the "
        "comparison cannot hold still."
    ): (
        "Proto tahle kapitola je a stojí za to přečíst ji dřív, než se tabulky výše "
        "vezmou příliš doslova. SOAP není to, co píše český psycholog. Zadání za všemi "
        "dosavadními tabulkami je překlad toho z TN-Eval, aby úkol byl týž úkol v jiném "
        "jazyce. Žádnou českou dokumentační normu nereprodukuje, protože žádná k "
        "reprodukci není. Ty zápisy jsou tedy formálně umělé — ale u každého modelu "
        "stejně, a právě ta stejnost drží srovnání mezi nimi poctivé. Menší umělost z "
        "toho ale neplyne. Tady tytéž modely píšou z týchž sezení a mění se jediné: "
        "tvar, který se po nich chtěl. Obrázek níž ukazuje, co z toho vzešlo, a "
        "odstavec pod ním pojmenovává jednu věc, kterou to srovnání neudrží."
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
        "Nečti to jako „formát Deepsy vede k horší češtině“. Může to tak být, ale "
        "tahle čísla to říct neumějí. Formát a délka se totiž hýbou spolu. Zápis "
        "v Deepsy je DELŠÍ: {longer} z {models} modelů v něm píše víc, medián "
        "{deepsy} slov proti {soap}. A delší zápis je v těchhle kritériích ve "
        "nevýhodě, protože každé se ptá, jestli je v něm chyba NĚKDE — čím delší "
        "text, tím víc míst, kde být může. Níž je to změřené: délka působí proti "
        "modelu u {soap_against} z {soap_total} dvojic kritérium–soudce ve větvích "
        "SOAP a u {deepsy_against} z {deepsy_total} ve formátu Deepsy. Obojí tedy "
        "ukazuje týmž směrem a {compared} modelů to od sebe neodliší."
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
    ("What the Czech track found, in {count} short paragraphs"): (
        "Co česká větev zjistil, ve {count} odstavcích"
    ),
    # --- one table, both judges --------------------------------------------
    (
        "Every cell holds both judges, {judges}, in that order and never averaged: "
        "where they disagree about a model is the only control this track has, so it is "
        "shown rather than smoothed. A cell whose two numbers differ is marked."
    ): (
        "V každé buňce jsou oba soudci, {judges}, v tomto pořadí a nikdy se "
        "neprůměrují: to, kde se na modelu neshodnou, je jediná kontrola, kterou tahle "
        "větev má, takže je vidět místo aby se zahladila. Buňka, kde se ta dvě čísla "
        "liší, je zvýrazněná."
    ),
    "The rows are ordered by dominance -- a model is above another only when it is "
    "at least as good on every column under BOTH judges, and better than it on at "
    "least one -- so models the evidence cannot separate share a place, and "
    "{systems} models fall into {places} places of which {tied} hold more than one. "
    "Within a place the rows are ordered by the mean of the columns that vary, "
    "which puts a row somewhere without claiming the evidence separates it.": (
        "Řádky jsou seřazené podle dominance. Model je výš jen tehdy, když je aspoň "
        "tak dobrý v každém sloupci u OBOU soudců a aspoň v jednom je lepší. Modely, "
        "které se takhle oddělit nedají, tedy sdílejí místo: {systems} modelů padne "
        "do {places} míst a {tied} z těch míst drží víc než jeden model. Uvnitř "
        "jednoho místa řadí řádky průměr sloupců, které se hýbou — to řádek někam "
        "postaví, ale netvrdí, že ho měření od sousedů odlišilo."
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
    # --- how large the length effect is, and what survives it --------------
    (
        "How large is it? Fitting each judge's composite of the criteria against the "
        "model's median note length costs {low} to {high} hundredths of a point per "
        "hundred words, across the four track-and-judge combinations. Drawing the "
        "{systems} models again with replacement {resamples} times, the ninety per cent "
        "interval clears zero on all four and the sign reverses in at most {wrong} of "
        "the draws. The direction is settled: on this corpus a longer note scores lower "
        "on Czech."
    ): (
        "Jak je ten vliv velký? Když se u každého soudce proloží složené skóre kritérií "
        "mediánovou délkou zápisu, stojí to {low} až {high} setin bodu na sto slov, a "
        "to ve všech čtyřech kombinacích větve a soudce. Když se těch {systems} modelů "
        "vylosuje znovu s vracením ({resamples} losování), devadesátiprocentní interval "
        "se ve všech čtyřech vyhne nule a znaménko se obrátí nejvýš v {wrong} losování. "
        "Směr je tedy rozhodnutý: na tomhle korpusu má delší zápis nižší skóre v "
        "češtině."
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
    "So what can be said about which model is better, without fitting anything at "
    "all? Take the models two at a time. A pair counts as decided when one of them "
    "beats the other by more than {separation} on the composite of the six criteria "
    "under BOTH judges -- one judge on its own decides nothing here. A decided pair "
    "then survives the handicap when the winner also wrote at least as many words as "
    "the loser: the longer note offered more places for a fault to be found and had "
    "fewer of them anyway, so length is not what won it. {survived} of the {decided} "
    "decided pairs survive, counting the two halves of the corpus separately. That is "
    "a partial order and not a ranking: it says which model beats which, and about "
    "most pairs it says nothing at all. It also reaches only part of the field -- "
    "{winners} models ever appear on the winning side of a surviving pair and "
    "{losers} on the losing side, and a model can be in both lists, beaten by one "
    "model and beating another. How little of this there is is the finding.": (
        "Co se tedy dá říct o tom, který model je lepší, aniž by se cokoli prokládalo? "
        "Vezměme modely po dvou. Dvojice se počítá za rozhodnutou, když jeden z nich "
        "porazí druhého o víc než {separation} ve složeném skóre šesti kritérií "
        "u OBOU soudců — jeden soudce sám o sobě tu nerozhoduje o ničem. Rozhodnutá "
        "dvojice pak přežije handicap tehdy, když vítěz zároveň napsal aspoň tolik "
        "slov jako poražený: delší zápis nabízel víc míst, kde chybu najít, a přesto "
        "jich měl míň, takže to, co dvojici rozhodlo, není délka. Handicap přežije "
        "{survived} z {decided} rozhodnutých dvojic, počítáno na obou půlkách korpusu "
        "zvlášť. Je to částečné uspořádání, ne žebříček: říká, který model poráží "
        "který, a o většině dvojic neříká vůbec nic. Navíc dosáhne jen na část pole — "
        "na vítězné straně dvojice, která handicap přežila, se objeví {winners} "
        "modelů a na poražené {losers}, a model může být v obou seznamech, jedním "
        "poražený a jiný porážející. A nález je právě to, jak málo toho je."
    ),
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
        "Párováno podle jména a jméno je slabý článek: na tomhle serveru už jedno id "
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
    # --- the box that closes the document -----------------------------------
    "Where this leaves a team choosing a model": ("Kde to nechává tým, který vybírá model"),
    "Everything above is one run. {models} models -- whichever ones e-INFRA had "
    "deployed the week it was measured -- were asked for {asked} notes, wrote "
    "{written} of them from {sessions} sessions, and every note that came back was "
    "read by both judges. Nothing here is averaged over runs, over judges or over the "
    "two halves. And the list of models is a deployment rather than a field: rebuilt "
    "after the next one, this document would hold different names, and in places a "
    "different model behind the same name.": (
        "Všechno výše je jeden běh. {models} modelů — ty, které měla e-INFRA nasazené "
        "v týdnu, kdy se měřilo — dostalo zadání napsat {asked} zápisů, napsalo jich "
        "{written} z {sessions} sezení a každý zápis, který se vrátil, přečetli oba "
        "soudci. Nic se tu neprůměruje přes běhy, přes soudce ani přes obě půlky. "
        "A ten seznam modelů je nasazení, ne startovní pole: sestavený znovu po dalším "
        "nasazení by tenhle dokument měl jiná jména a místy jiný model pod stejným "
        "jménem."
    ),
    "The finest distinction that survives both judges is a band and not a place -- and "
    "even the band moves: of the {total} models these tables place, {differ} are put in "
    "different bands by the two judges somewhere. Two models inside one band are two "
    "models this measurement did not tell apart, and two models a band apart under one "
    "judge may be that judge.": (
        "Nejjemnější rozlišení, které přežije oba soudce, je pásmo, ne příčka — a i to "
        "pásmo se hýbe: z {total} modelů, které tyhle tabulky umísťují, jich {differ} "
        "dostane od obou soudců někde jiné pásmo. Dva modely v jednom pásmu jsou dva "
        "modely, které tohle měření nerozlišilo, a dva modely vzdálené o jedno pásmo "
        "u jednoho soudce můžou být rozdílem mezi soudci, ne mezi modely."
    ),
    "The finest distinction that survives both judges is a band and not a place, and "
    "here the two of them agree: every one of the {total} models these tables place is "
    "put in the same band by both. Two models inside one band are still two models this "
    "measurement did not tell apart.": (
        "Nejjemnější rozlišení, které přežije oba soudce, je pásmo, ne příčka — a tady "
        "se oba shodnou: každý z {total} modelů, které tyhle tabulky umísťují, dostane "
        "od obou stejné pásmo. Dva modely v jednom pásmu jsou i tak dva modely, které "
        "tohle měření nerozlišilo."
    ),
    "What would let this document say more is more measuring, and what is missing is "
    "short enough to list.": (
        "Aby tenhle dokument mohl říct víc, muselo by se víc měřit — a to, co chybí, "
        "se dá vyjmenovat."
    ),
    "The real half of these {sessions} sessions is one client and one therapist, so "
    "everything measured there is also a fact about how those two people talk; more "
    "sessions, with other clients and other therapists, is what would lift that.": (
        "Skutečná půlka z těchhle {sessions} sezení je jeden klient a jeden terapeut, "
        "takže všechno, co se na ní změřilo, je zároveň fakt o tom, jak spolu mluví ti "
        "dva konkrétní lidé; zvednout by to šlo víc sezeními, s jinými klienty "
        "a jinými terapeuty."
    ),
    "One Czech reader has checked {notes} of these notes by hand, and one reader cannot "
    "say how far two would have agreed -- a second would turn every place where a judge "
    "and he differ into a figure rather than an open question.": (
        "{notes} z těchhle zápisů prošel ručně jeden český čtenář, a jeden čtenář neumí "
        "říct, jak moc by se shodli dva — druhý by z každého místa, kde se soudce a on "
        "rozcházejí, udělal číslo místo otevřené otázky."
    ),
    "And PDSQI-9 has never been put to a note in the Deepsy format: those {deepsy} "
    "notes are already written, so asking would cost no generation at all, and it is "
    "the only way to find out whether the format a clinic would actually use produces "
    "a note worth filing.": (
        "A PDSQI-9 se nikdy neptalo na zápis ve formátu Deepsy. Těch {deepsy} zápisů "
        "už je přitom napsaných, takže by se kvůli tomu nic negenerovalo. A je to "
        "jediná cesta, jak zjistit, jestli formát, který by klinika opravdu "
        "používala, dává zápis, který stojí za založení do dokumentace."
    ),
    "Until then, the reading this document has taken throughout is the one to keep. "
    "Decide first which of the three questions the choice is really about -- is the "
    "Czech right, is the note worth filing, does the Deepsy format work -- because none "
    "of the three answers the other two. Then read the ordering, read it as bands "
    "rather than as places, and do not read the gaps between neighbours.": (
        "Do té doby platí to čtení, kterého se tenhle dokument drží celou dobu. Nejdřív "
        "se rozhodněte, o kterou ze tří otázek při výběru vlastně jde — jestli je "
        "čeština správně, jestli zápis stojí za založení do dokumentace, jestli funguje "
        "formát Deepsy — protože žádná z těch tří neodpovídá na zbylé dvě. Pak čtěte "
        "pořadí, čtěte ho jako pásma, ne jako příčky, a nečtěte rozdíly mezi sousedy."
    ),
    # --- what the models write, one sentence at a time ----------------------
    "What the models write, one sentence at a time": "Co modely píšou, věta po větě",
    "Restatement": "Převyprávění",
    "Clinical hypothesis": "Klinická hypotéza",
    "Client quotation": "Citace klientky",
    "Unsupported observation": "Nepodložené pozorování",
    "Verbal expression": "Hodnocení řeči",
    "Declines to judge": "Odmítne posoudit",
    "Sentences": "Vět",
    "Notes": "Zápisů",
    "None": "Žádná",
    "not answered": "nezodpovězeno",
    "A model with fewer than ten notes is marked: its share rests on less.": (
        "Model s méně než deseti zápisy je označený hvězdičkou: jeho podíl stojí na méně datech."
    ),
    "The six criteria ask whether a fault appears ANYWHERE in a note, so a longer "
    "note offers more places for one and the columns scale with length. These six "
    "ask about one sentence at a time. Each note was cut into sentences -- "
    "{units} of them across {notes} notes -- and two coders from two vendors were "
    "asked the same yes/no question about every one. A cell is the share of the "
    "ANSWERED verdicts that are yes, so a model that writes twice as much is not "
    "twice as likely to be marked.": (
        "Šest kritérií se ptá, jestli je chyba NĚKDE v zápisu, takže delší zápis nabízí "
        "víc míst, kde být může, a sloupce rostou s délkou. Těchhle šest se ptá vždy na "
        "jednu větu. Každý zápis se rozřezal na věty — {units} vět v {notes} zápisech — "
        "a dva kodéři od dvou dodavatelů odpověděli u každé z nich na tutéž otázku "
        "ano/ne. Buňka je podíl vět daného modelu, na které kategorie sedí, takže "
        "model, který píše dvakrát tolik, nemá dvakrát větší šanci dostat značku."
    ),
    "No person has read these notes as a clinician. Two models agreeing is "
    "evidence that a distinction is stable and codeable, and no evidence at all "
    "that it matters. Nothing here says a higher number is worse.": (
        "Žádný člověk tyhle zápisy nečetl jako klinik. Shoda dvou modelů je důkaz, že "
        "je rozlišení stabilní a zakódovatelné, a není to vůbec žádný důkaz, že na něm "
        "záleží. Nic tady neříká, že vyšší číslo je horší."
    ),
    "Source: local/czech-graduation-{track}.json, from local/czech-codes.jsonl. "
    "Coders gemini-3.1-pro-preview and deepseek-v4-flash, prompt czech-open-v1, "
    "temperature 0. The row order is the one the PDSQI-9 table above prints.": (
        "Zdroj: local/czech-graduation-{track}.json, z local/czech-codes.jsonl. "
        "Kodéři gemini-3.1-pro-preview a deepseek-v4-flash, prompt czech-open-v1, "
        "teplota 0. Pořadí řádků je totéž, které tiskne tabulka PDSQI-9 výše."
    ),
    "Both coders answered {both} of the {units} sentences. The second coder "
    "returned nothing for {gap}, so those carry one reading rather than two, and "
    "the share for the models they belong to leans on the first coder.": (
        "Oba kodéři odpověděli na {both} z {units} vět. Druhý kodér nevrátil nic u "
        "{gap} z nich, takže ty nesou jedno čtení místo dvou a podíl u modelů, "
        "kterým patří, se opírá o prvního kodéra."
    ),
    "{name}, released {date}": "{name}, vydáno {date}",
    "That is the lowest of the six.": "Je to nejnižší ze šesti.",
    (
        "There are two corpora so that a difference can be told apart from its cause. "
        "The same eleven models wrote from real sessions with one client and from "
        "public counselling conversations translated into Czech. A category that "
        "behaves the same on both is telling you about the models. One that behaves "
        "differently is telling you about the material, and this chapter is where that "
        "shows."
    ): (
        "Korpusy jsou dva proto, aby šlo odlišit rozdíl od jeho příčiny. Týchž jedenáct "
        "modelů psalo ze skutečných sezení s jednou klientkou a z veřejných "
        "poradenských rozhovorů přeložených do češtiny. Kategorie, která se chová "
        "stejně na obojím, vypovídá o modelech. Ta, která se chová jinak, vypovídá o "
        "materiálu — a tady je to vidět."
    ),
    (
        "The same six questions, on notes written from ten public counselling "
        "conversations translated into Czech -- {units} sentences across {notes} "
        "notes. These transcripts are a seventh the length of a real session, they "
        "are motivational interviewing about substance use rather than therapy with "
        "one client, and somebody else transcribed them. A category that weakens "
        "here may be weakening because of any of those, or because it was partly "
        "chance on the other half. These numbers cannot tell those apart."
    ): (
        "Týchž šest otázek na zápisech psaných z deseti veřejných poradenských "
        "rozhovorů přeložených do češtiny — {units} vět ve {notes} zápisech. Tyhle "
        "přepisy jsou sedminou délky skutečného sezení, jsou to motivační rozhovory o "
        "návykových látkách místo terapie s jednou klientkou, a přepisoval je někdo "
        "jiný. Kategorie, která tady zeslábne, může slábnout kvůli kterékoliv z těch "
        "věcí — nebo proto, že na druhé půlce byla zčásti náhoda. Tahle čísla to od "
        "sebe odlišit neumějí."
    ),
    (
        "{name} passes every decided gate on the real sessions and fails on the "
        "translated ones: the share of its variation belonging to the model rather than "
        "to the session falls from {high} to {low}, where a column needs 0.40 and three "
        "times the session's share. It is a measure of the real half, and saying it is "
        "a measure would be saying more than was found."
    ): (
        "{name} projde na skutečných sezeních všemi rozhodnutými branami a na "
        "přeložených propadne: podíl kolísání, který patří modelu a ne sezení, klesne z "
        "{high} na {low}, přičemž sloupec potřebuje 0,40 a trojnásobek podílu sezení. "
        "Je to míra skutečné půlky, a říct, že je to míra, by bylo víc, než se našlo."
    ),
    (
        "Only {passed} of the {total} passed the gates that decide whether a column is "
        "possible: does it vary, does it belong to the model rather than the session, "
        "do the coders agree, is its evidence real, is it separable from length, and "
        "does it fire on a sentence written to carry it. The others are printed as "
        "description and are not measures. {failed} fall outside the 20-80% band a "
        "column needs to tell ten notes per model apart."
    ): (
        "Branami, které rozhodují, jestli je sloupec vůbec možný, prošlo jen {passed} z "
        "{total}: kolísá to; patří to modelu, ne sezení; shodnou se kodéři; je ta "
        "evidence skutečná; jde to oddělit od délky; a vystřelí to na větě napsané tak, "
        "aby to nesla. Ostatní se tisknou jako popis a nejsou to míry. {failed} leží "
        "mimo pásmo 20–80 %, které sloupec potřebuje, aby deset zápisů na model od sebe "
        "odlišil."
    ),
    (
        "Gate 7 was run. One sentence was written for each category and planted in an "
        "invented note, and {fired} of {total} were marked on the planted sentence by "
        "both coders. Adding that one sentence changed {moved} of the {compared} "
        "verdicts on the sentences around it, so a coder is reading one sentence at a "
        "time rather than the note it sits in. The note the variants are built from is "
        "an ordinary therapy note and carries five of the six categories itself, which "
        "is why there is no note-level negative control here and why none of that is a "
        "false alarm."
    ): (
        "Brána 7 proběhla. Ke každé kategorii se napsala jedna věta a nastražila do "
        "vymyšleného zápisu; {fired} z {total} kodéři na té nastražené větě označili "
        "oba. Přidání té jediné věty změnilo {moved} z {compared} verdiktů na větách "
        "kolem ní — kodér tedy čte jednu větu po druhé, ne zápis kolem ní. Zápis, ze "
        "kterého varianty vznikly, je běžný terapeutický zápis a pět ze šesti kategorií "
        "nese sám. Proto tady žádná negativní kontrola na úrovni zápisu být nemůže a "
        "proto nic z toho není falešný poplach."
    ),
    (
        "Two pairs share a planted sentence: {pairs}. Both are overlaps the codebook "
        "declares, and the pair that had to stay apart did: nothing marked as "
        "restatement was also marked as a clinical hypothesis."
    ): (
        "Dvě dvojice sdílejí nastraženou větu: {pairs}. Obojí je překryv, ke kterému se "
        "codebook hlásí, a dvojice, která se rozejít musela, se rozešla: nic označeného "
        "jako převyprávění nebylo zároveň označeno jako klinická hypotéza."
    ),
    "What each word here means": "Co která slova znamenají",
    "a note": "zápis",
    (
        "What a model writes after reading one session transcript. It is the thing "
        "being measured; nothing here measures the therapy."
    ): (
        "To, co model napíše, když si přečte přepis jednoho sezení. Měří se právě tohle "
        "— nic tady neměří samotnou terapii."
    ),
    "a judge": "soudce",
    (
        "Another language model, which reads a note and answers the questions about it. "
        "There are two, from two different vendors, and they answer separately and are "
        "never averaged. They are not people, and where they disagree is the only check "
        "this study has."
    ): (
        "Další jazykový model, který si zápis přečte a odpoví na otázky o něm. Jsou "
        "dva, od dvou různých firem, odpovídají nezávisle na sobě a nikdy se "
        "neprůměrují. Nejsou to lidé — a to, kde se neshodnou, je jediná kontrola, "
        "kterou tahle studie má."
    ),
    "a criterion": "kritérium",
    (
        "One yes/no question about a note. Six of them, all about whether the Czech "
        "itself is right -- diacritics, calques, untranslated terms, agreement, "
        "register, non-words. A column is the share of notes free of that fault."
    ): (
        "Jedna otázka ano/ne o zápisu. Je jich šest a všechny se ptají jen na to, "
        "jestli je správně čeština: diakritika, kalky z angličtiny, nepřeložené "
        "termíny, shoda, rejstřík, neslova. Sloupec je podíl zápisů, které tou chybou "
        "netrpí."
    ),
    (
        "A published instrument that asks something else: whether the note is any good "
        "clinically. Eight attributes, six of them answerable here. It was put only to "
        "the SOAP notes."
    ): (
        "Publikovaný nástroj, který se ptá na něco jiného: jestli je zápis k něčemu "
        "klinicky. Má osm atributů, šest z nich jde tady zodpovědět. Byl použit jen na "
        "zápisy ve formátu SOAP."
    ),
    "SOAP and Deepsy": "SOAP a Deepsy",
    (
        "Two note formats. SOAP has four sections and every model has seen thousands of "
        "them. Deepsy is the form the Deepsy application really writes: eleven "
        "sections, and no model has seen it before. They are never pooled."
    ): (
        "Dva formáty zápisu. SOAP má čtyři sekce a každý model jich viděl tisíce. "
        "Deepsy je formulář, který opravdu píše aplikace Deepsy: jedenáct sekcí, a ten "
        "žádný model předtím neviděl. Nikdy se nesčítají dohromady."
    ),
    "the two halves": "dvě půlky korpusu",
    (
        "The two sets of sessions. One is real therapy with one client, transcribed and "
        "de-identified by hand and never published. The other is public counselling "
        "conversations translated into Czech. Every model wrote from both, so two "
        "models are never compared on different sessions."
    ): (
        "Dvě sady sezení. Jedna je skutečná terapie s jednou klientkou, přepsaná a "
        "ručně anonymizovaná, nikdy nezveřejněná. Druhá jsou veřejné poradenské "
        "rozhovory přeložené do češtiny. Každý model psal z obou, takže se nikdy "
        "neporovnávají dva modely na různých sezeních."
    ),
    "a track": "větev",
    (
        "One format on one half -- SOAP on the real sessions, SOAP on the translated "
        "ones, and the same two for Deepsy. Four in all, and each is judged twice, "
        "which is where the eight tables come from."
    ): (
        "Jeden formát na jedné půlce — SOAP na skutečných sezeních, SOAP na "
        "přeložených, a totéž dvakrát pro Deepsy. Dohromady čtyři, a každou hodnotí dva "
        "soudci. Odtud je těch osm tabulek."
    ),
    "a band": "pásmo",
    (
        "A group of models this measurement cannot tell apart. It is not a rank: inside "
        "a band nothing separates them, and the band ends where the difference is "
        "bigger than resampling the sessions can explain away. A narrow band means the "
        "measurement resolves finely, not that a model is good."
    ): (
        "Skupina modelů, které tohle měření od sebe neodliší. Není to pořadí: uvnitř "
        "pásma je nic nerozlišuje a pásmo končí tam, kde je rozdíl větší, než co dokáže "
        "vysvětlit převzorkování sezení. Úzké pásmo znamená, že měření rozlišuje jemně "
        "— ne že je model dobrý."
    ),
    "Czech notes, the short version": "České zápisy, krátká verze",
    ("the short version · measured, not published"): ("krátká verze · změřeno, nepublikováno"),
    (
        "Thirteen language models were each asked to write clinical notes from twenty "
        "psychotherapy sessions. Ten of those sessions are real therapy with one "
        "client, recorded, transcribed and de-identified by hand. Ten are public "
        "counselling conversations translated into Czech. Every model wrote from the "
        "same sessions, so no two models are being compared on different material. "
        "{written} of the {asked} notes were written; where one is missing, this "
        "document says so rather than leaving it out of an average."
    ): (
        "Třináct jazykových modelů dostalo za úkol napsat klinické zápisy z dvaceti "
        "psychoterapeutických sezení. Deset z těch sezení je skutečná terapie s jednou "
        "klientkou — nahraná, přepsaná a ručně anonymizovaná. Deset jsou veřejné "
        "poradenské rozhovory přeložené do češtiny. Každý model psal z týchž sezení, "
        "takže se nikdy neporovnávají dva modely na různém materiálu. Napsáno bylo "
        "{written} zápisů z {asked}; kde některý chybí, je to tady napsané — místo aby "
        "se prostě vynechal z průměru."
    ),
    (
        "Every note was then read by two other language models, which answered the same "
        "questions about it separately. Two sets of questions were asked. Six ask only "
        "whether the Czech is correct. A published instrument called PDSQI-9 asks "
        "something harder: whether the note is any good clinically. Both, because "
        "neither answers the other -- a flawless Czech sentence about nothing passes "
        "all six criteria, and a note full of insight can be written in bad Czech."
    ): (
        "Každý zápis pak přečetly dva další jazykové modely a nezávisle na sobě "
        "odpověděly na tytéž otázky. Otázky byly dvojího druhu. Šest se ptá jen na to, "
        "jestli je správně čeština. Publikovaný nástroj jménem PDSQI-9 se ptá na těžší "
        "věc: jestli je ten zápis klinicky k něčemu. Obojí, protože jedno neodpoví na "
        "druhé — bezchybná česká věta o ničem projde všemi šesti kritérii a zápis plný "
        "vhledu se dá napsat špatnou češtinou."
    ),
    (
        "No clinician has read these notes. Everything below is one machine's account "
        "of what another machine wrote, and the only check on it is that the two "
        "readers answered separately and are never averaged: where they disagree, this "
        "document shows both numbers instead of splitting the difference."
    ): (
        "Žádný klinik tyhle zápisy nečetl. Všechno níž je zpráva jednoho stroje o tom, "
        "co napsal jiný stroj. Jediná kontrola je, že ti dva čtenáři odpovídali "
        "nezávisle a nikdy se neprůměrují: kde se neshodnou, ukazuje tenhle dokument "
        "obě čísla místo toho, aby si to rozdělil napůl."
    ),
    "What came out of it": "Co z toho vyšlo",
    "What the notes were written from": "Z čeho se ty zápisy psaly",
    "The tables the findings come from": "Tabulky, ze kterých ty nálezy jsou",
    ("Does the measurement react when a fault is put in on purpose?"): (
        "Zareaguje to měření, když se do zápisu chyba nasadí schválně?"
    ),
    "What these numbers may not be used for": "K čemu se tahle čísla použít nesmějí",
    (
        "A column that never moves may be measuring something these models do not "
        "differ on, or may be measuring nothing. Nothing already scored can tell those "
        "apart, because none of it is a badly written note. So notes were written to be "
        "bad: one clean invented note and one copy per fault, each damaged in exactly "
        "one named way, with the expected answer written down before the readers were "
        "asked."
    ): (
        "Sloupec, který se nikdy nehne, buď měří něco, v čem se tyhle modely doopravdy "
        "neliší, nebo neměří nic. Nic z toho, co je už obodované, ty dvě možnosti "
        "nerozliší — protože nic z toho není špatně napsaný zápis. Takže se špatné "
        "zápisy napsaly schválně: jeden čistý vymyšlený zápis a k němu jedna kopie na "
        "každou chybu, každá poškozená právě jedním pojmenovaným způsobem. Co se má u "
        "které stát, bylo zapsáno dřív, než se čtenářů kdokoli zeptal."
    ),
    (
        "Two tables, both on the real sessions. The first asks whether the Czech is "
        "right, the second whether the note is any good. Every cell holds both readers' "
        "answers in the same order, and a cell where they disagree is marked. The long "
        "version of this document draws six more tables -- the translated half, and the "
        "same four again in the other note format -- and says where they differ."
    ): (
        "Čtyři tabulky. První dvě jsou ze skutečných sezení, druhé dvě z přeložených "
        "rozhovorů — a jsou tu obojí právě proto, aby šlo vidět, jestli to, co vyšlo na "
        "jedné půlce, platí i na druhé. V každé dvojici se první tabulka ptá, jestli je "
        "správně čeština, a druhá, jestli je zápis k něčemu. V každé buňce jsou "
        "odpovědi obou čtenářů ve stejném pořadí a buňka, kde se neshodnou, je "
        "označená. Dlouhá verze kreslí ještě čtyři tabulky pro druhý formát zápisu."
    ),
    ("Ten sessions, one client, one therapist."): (
        "Deset sezení, jedna klientka, jedna terapeutka."
    ),
    (
        "Everything measured on the real half is also a fact about how those two people "
        "talk. A measure over ten notes per model has eleven possible values, so read "
        "the ends of a table and never the gap between two neighbours."
    ): (
        "Všechno, co se změřilo na skutečné půlce, je zároveň fakt o tom, jak spolu ty "
        "dvě ženy mluví. Míra přes deset zápisů na model má jedenáct možných hodnot — "
        "čti tedy konce tabulky, nikdy ne rozdíl mezi dvěma sousedy."
    ),
    "Nothing here says a note is true.": "Nic tady neříká, že je zápis pravdivý.",
    (
        "The questions ask whether the Czech is right and how the note is built. "
        "Whether what it says actually happened in the session is the question a "
        "clinical team would ask first, and it is the one measurement nobody made -- "
        "answering it means showing a judge the transcript, and no transcript leaves "
        "this machine."
    ): (
        "Otázky se ptají, jestli je správně čeština a jak je zápis postavený. Jestli se "
        "to, co se v něm píše, v sezení opravdu stalo, by klinický tým chtěl vědět jako "
        "první — a je to jediné měření, které tu nikdo neudělal. Odpovědět na ně "
        "znamená ukázat soudci přepis, a žádný přepis tenhle stroj neopouští."
    ),
    ("Longer notes score worse, and that is partly the instrument."): (
        "Delší zápisy mají horší skóre a zčásti za to může samo měřidlo."
    ),
    (
        "Each of the six criteria asks whether a fault appears ANYWHERE in the note, so "
        "a longer note offers more places for one. Measured rather than guessed: every "
        "hundred words costs a few hundredths of a point, under both readers and on "
        "both halves."
    ): (
        "Každé z těch šesti kritérií se ptá, jestli je chyba NĚKDE v zápisu — a delší "
        "zápis nabízí víc míst, kde být může. Není to dohad, je to změřené: každých sto "
        "slov navíc stojí několik setin bodu, u obou čtenářů a na obou půlkách."
    ),
    ("Two readers agreeing is not evidence that a distinction matters."): (
        "Shoda dvou čtenářů není důkaz, že na tom rozlišení záleží."
    ),
    (
        "It is evidence that the distinction is stable and can be coded. Whether it is "
        "something a psychologist would care about is a question no arrangement of "
        "language models answers."
    ): (
        "Je to důkaz, že je to rozlišení stabilní a dá se zakódovat. Jestli je to něco, "
        "na čem by psychologovi záleželo, neodpoví žádné uspořádání jazykových modelů."
    ),
    ("These models were what one provider had deployed on one day."): (
        "Tyhle modely byly to, co měl jeden poskytovatel nasazené jeden den."
    ),
    (
        "The line-up changed under this project once already. A result here is about "
        "these systems at that moment, not about the companies behind them."
    ): (
        "Sestava se pod tímhle projektem už jednou změnila. Výsledek tady je o těchhle "
        "systémech v tu chvíli, ne o firmách, které za nimi stojí."
    ),
    (
        "The long version -- every table, every caveat and the file behind every figure "
        "-- is local/czech-report-cs.pdf. Both are built from the same measurements by "
        "the same code, so no figure here was retyped and none can drift from it."
    ): (
        "Dlouhá verze — všechny tabulky, všechny výhrady a u každého čísla soubor, ze "
        "kterého pochází — je local/czech-report-cs.pdf. Obě vznikají z týchž měření "
        "týmž kódem, takže se tady žádné číslo nepřepisovalo ručně a žádné se od té "
        "dlouhé verze nemůže rozejít."
    ),
    (
        "The same instrument was put to the notes in the Deepsy format over "
        "{tables} table-and-judge combinations of its own: {top} in the top band of "
        "all of them and {bottom} in the bottom band of all of them. It is counted "
        "separately from the four above and not added to them, for the reason the "
        "criteria are: not every model was asked in both formats. Every half's band "
        "is built from the columns that exist there and separate models, the same "
        "set for both formats and both judges: {real} on the real half, "
        "{translated} on the translated one. The real half cannot ask `accurate` or "
        "`thorough` -- they need the session, and the real sessions never leave "
        "e-INFRA."
    ): (
        "Týž nástroj dostaly i zápisy ve formátu Deepsy, a to ve {tables} vlastních "
        "kombinacích tabulky a soudce: {top} v horním pásmu všech a {bottom} v "
        "dolním pásmu všech. Počítá se to zvlášť od čtyř tabulek výše a nesčítá se "
        "to s nimi, ze stejného důvodu jako u kritérií: ne každý model dostal obě "
        "zadání. Pásmo každé půlky stojí na sloupcích, které na ní existují a "
        "něco mezi modely rozlišují, a na týchž sloupcích pro oba formáty i oba "
        "soudce: {real} na skutečné půlce, {translated} na přeložené. Skutečná "
        "půlka se na `accurate` a `thorough` zeptat nemůže — k nim je potřeba "
        "sezení a skutečná sezení e-INFRA neopouštějí."
    ),
    (
        "This chapter says nothing about whether a Deepsy note is a good note, but "
        "the document now does."
    ): (
        "Tahle kapitola neříká nic o tom, jestli je zápis Deepsy dobrý zápis. "
        "Zbytek dokumentu už ano."
    ),
    (
        "The six criteria here ask whether the Czech is right. PDSQI-9, which asks "
        "whether a note is worth filing, was put to these same notes under both "
        "judges and has two tables of its own further down. On the real half it "
        "answers on six of its eight attributes rather than all eight, because "
        "`accurate` and `thorough` need the session and the real sessions never "
        "leave e-INFRA."
    ): (
        "Šest kritérií se tady ptá, jestli je správně čeština. PDSQI-9, které se "
        "ptá, jestli za zápis stojí ho založit do dokumentace, dostalo tytéž zápisy "
        "pod oběma soudci a má níž dvě vlastní tabulky. Na skutečné půlce odpovídá "
        "na šest svých osmi atributů místo na všech osm, protože na `accurate` a "
        "`thorough` je potřeba sezení a skutečná sezení e-INFRA neopouštějí."
    ),
    (
        "One caution about that second count. {subject} in the bottom band of all "
        "{tables} SOAP table-and-judge combinations and in no Deepsy band at all -- "
        "not because of anything written, but because e-INFRA answered {calls} of "
        "the calls asking for those notes with an error and returned no note. The "
        "endpoint no longer serves it at all, so this is not a gap that will close "
        "on a later run: the question can no longer be put. Adding the two counts "
        "together would have removed it from the bottom of the table on the "
        "strength of a model being retired."
    ): (
        "Jedna výhrada k tomu druhému počtu. {subject} v dolním pásmu všech "
        "{tables} kombinací tabulky a soudce u SOAP a v žádném pásmu Deepsy — ne "
        "kvůli tomu, co napsal, ale protože e-INFRA na {calls} volání, která si o "
        "ty zápisy říkala, odpověděla chybou a žádný zápis nevrátila. Endpoint ten "
        "model už vůbec nenabízí, takže tohle není mezera, která se pozdějším během "
        "zaplní: ta otázka se už nedá položit. Sečíst ty dva počty dohromady by ho "
        "z konce tabulky odstranilo na základě toho, že byl model vyřazen."
    ),
    "Beats": "Poráží",
    (
        "The Beats column counts how many of the other models this one beats "
        "outright: at least as good on every column of this table, under both "
        "judges, and better on at least one. Nothing is weighted and nothing is "
        "averaged, so no column is quietly given more say than another -- which "
        "matters here, because the columns are on different scales and do not agree "
        "with each other."
    ): (
        "Sloupec Poráží počítá, kolik ostatních modelů tenhle poráží naprosto: je "
        "aspoň tak dobrý v každém sloupci téhle tabulky, pod oběma soudci, a aspoň "
        "v jednom je lepší. Nic se neváží a nic se neprůměruje, takže žádný sloupec "
        "nedostane tiše větší slovo než jiný — a na tom tady záleží, protože "
        "sloupce mají různé stupnice a neshodují se spolu."
    ),
    (
        "A 0 is not a low score. It says the evidence does not place that model "
        "above any other, and a model can be beaten by nobody and beat nobody at "
        "once. Where most of a column is 0, that is the finding: these measures do "
        "not separate these models."
    ): (
        "Nula není špatná známka. Znamená, že důkazy ten model nestavějí nad žádný "
        "jiný — a model může zároveň nikoho neporážet a nikým poražený nebýt. Kde "
        "je většina sloupce nulová, je to nález: tyhle míry ty modely od sebe "
        "neodliší."
    ),
    ("What the Band column rests on, measured rather than assumed:"): (
        "Na čem sloupec Pásmo doopravdy stojí, změřeno a ne odhadnuto:"
    ),
    ("under {judge}, {measure} supplies {share}% of what separates the models"): (
        "pod {judge} dodává {measure} {share} % všeho, co modely odlišuje"
    ),
    (
        "and {n} of the {total} sit in the mean supplying none of it, because every "
        "model scores the same on them ({measures})"
    ): (
        "a {n} z {total} sedí v tom průměru, aniž by dodaly cokoli, protože v nich "
        "mají všechny modely totéž ({measures})"
    ),
    (
        "and 1 of the {total} sits in the mean supplying none of it, because every "
        "model scores the same on it ({measures})"
    ): (
        "a 1 z {total} sedí v tom průměru, aniž by dodal cokoli, protože v něm mají "
        "všechny modely totéž ({measures})"
    ),
    (
        "The row order is not built this way: a model is above another only when it "
        "is at least as good on every column under both judges, which uses no "
        "weights at all. The two therefore disagree on some rows, and neither is "
        "the corrective for the other -- they fail in opposite directions. A mean "
        "lets one wide column decide the order; an every-column rule lets one "
        "narrow cell veto it, so a model beaten on eleven of twelve cells can still "
        "be beaten by nobody on the strength of the twelfth. Read the two together, "
        "and where they disagree read the columns themselves."
    ): (
        "Pořadí řádků takhle nevzniká: model je nad jiným, jen když je aspoň tak "
        "dobrý v každém sloupci pod oběma soudci, a v tom nejsou žádné váhy. Obojí "
        "si proto u některých řádků odporuje a ani jedno není opravou toho druhého "
        "— selhávají v opačných směrech. U průměru může o pořadí rozhodnout jeden "
        "široký sloupec; u pravidla „ve všech sloupcích“ může jedna úzká buňka "
        "vetovat, takže model poražený v jedenácti buňkách z dvanácti nemusí být "
        "poražený nikým, a to silou té dvanácté. Čti obojí dohromady, a kde si to "
        "odporuje, čti rovnou ty sloupce."
    ),
}
