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
    "therapy-note-bench · Czech track · measured, not published": (
        "therapy-note-bench · český track · změřeno, nepublikováno"
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
        "soudci, po jedné otázce, na endpointech Googlu a OpenAI."
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
        "Při měřítku, podle kterého žebříček řadí, se nepřenáší"
    ),
    # Printed only if a payload records no ranking measure at all. Translated in
    # advance so that the day it does, the sentence around it stays Czech.
    "the ranking measure": "měřítko, podle kterého se řadí",
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
        "člověk sáhl místo toho, aby benchmark spouštěl: vlastní anglický žebříček "
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
        "počet modelů. A místo není měření — dva modely vzdálené o setinu jsou "
        "nakreslené o celé místo od sebe — a právě proto to stojí za nakreslení: "
        "žebříček podává čtenáři místo a tohle je to, co takové místo vydrží "
        "v druhém jazyce."
    ),
    "The English page sorts by one measure -- {measure} -- and a position on that page "
    "means what that measure says. Here it stands against the Czech quality columns. "
    "Nothing survives the test, and the two judges do not agree even on the sign.": (
        "Anglická stránka řadí podle jediného měřítka — {measure} — a umístění na ní "
        "znamená to, co říká ono měřítko. Tady stojí proti sloupcům české kvality. "
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
        "sezení a neuměl odlišit horší model od těžšího sezení. Zadání drželo, "
        "odpovědi ne vždycky: vrátilo se {written} zápisů z {asked} a kde model "
        "napsal míň, je jmenovaný: {short}. Deset zápisů na model je ale málo. Jediný "
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
        "a úplně vymyšlený, projde všemi šesti. Nástroj na kvalitu tu mezeru "
        "nezaplňuje: právě ty dva atributy, které by se zeptaly, jestli je zápis "
        "přesný a jestli je důkladný, jsou ty, na které se u skutečného sezení zeptat "
        "nejde — odpovědět na ně znamená položit soudci před oči přepis a žádný přepis "
        "neopouští stroj, který ho drží. Žádné číslo v tomhle dokumentu tedy není "
        "důkazem, že zápis říká to, co se v sezení stalo. Pro klinický tým je to "
        "otázka první v pořadí a je to jediné měření, které tu nikdo neudělal."
    ),
    "Almost nothing here has been checked against a person": (
        "Skoro nic z tohohle nebylo ověřeno proti člověku"
    ),
    "These six criteria are this repository's own. No published Czech note-quality "
    "instrument exists to reproduce, so they were written for this track -- and "
    "unlike PDSQI-9 there is not even a published figure saying how often two people "
    "answering them would agree with each other. What stands in for that here is two "
    "independent judges answering every question separately, which is why this "
    "document prints both of them in every cell and marks the cells where they "
    "differ: the disagreement is the control.": (
        "Těch šest kritérií je vlastních tomuhle repozitáři. Žádný publikovaný český "
        "nástroj na kvalitu zápisů, který by se dal převzít, neexistuje, takže vznikla "
        "pro tenhle track — a na rozdíl od PDSQI-9 u nich není ani publikované číslo, "
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
        "když je hodnotitel jeden, není tu druhý člověk, který by řekl, jak moc by se "
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
        "v jiných ne — buď endpoint ty zápisy odmítl, nebo si o ně ten pohled nikdy "
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
        "Pořadí, které každý pohled používá, je to, které tisknou jeho vlastní tabulky — "
        "podle dominance, která nepotřebuje žádnou škálu, a dá se tedy porovnávat i mezi "
        "nástroji, které žádnou společnou nemají — a to, jak moc se dvě pořadí shodují, je "
        "pořadová korelace přes modely, které mají oba pohledy. Takových porovnání je "
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
        "Index schopnosti je publikované skóre třetí strany a spojkou k němu není nic "
        "než jméno modelu: jméno na tomhle endpointu není důkaz o tom, který model za "
        "ním stojí, a první pracovní pravidlo tohohle projektu vzniklo proto, že jedno "
        "z tamních id vracelo výstup jiného modelu."
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
    "positive under BOTH judges are {positive}. The chart below says the same thing "
    "without the coefficients. Each dot is one model: its median note length across "
    "the bottom, the six criteria averaged up the side, one panel for each half of "
    "the corpus. The two judges are drawn in separate colours and never averaged, so "
    "a model they disagree about appears as two dots at different heights instead of "
    "as one number somewhere between them. The dashed line is the straight line that "
    "best fits one judge's dots -- drawn rather than described, because a slope is "
    "easier to argue with when the points it was fitted to are on the page beside "
    "it.": (
        "Oba jazyky pak táhnou na opačné strany a tohle je to nejužitečnější, co je "
        "dobré vědět dřív, než se člověk pustí do kterékoli tabulky výše. V angličtině "
        "delší zápis dostává vyšší úplnost, a to u obou soudců. V češtině má horší "
        "skóre v {against} z {total} kombinací kritéria a soudce — {soap_against} "
        "z {soap_total} na půlkách SOAP a {deepsy_against} z {deepsy_total} ve formátu "
        "Deepsy, což je jeden z důvodů, proč se obojí nikdy nesčítá — a výjimky se "
        "jmenují, ne zaokrouhlují: sloupce, ve kterých koeficient zůstává kladný "
        "u OBOU soudců, jsou {positive}. "
        "Graf níže říká totéž bez koeficientů. Každý bod je jeden model: vodorovně "
        "mediánová délka jeho zápisu, svisle průměr šesti kritérií, jeden panel pro "
        "každou půlku korpusu. Oba soudci jsou vykreslení zvlášť, každý svou barvou, "
        "a nikdy se neprůměrují — model, na kterém se neshodnou, je proto vidět jako "
        "dva body v různé výšce, ne jako jedno číslo někde mezi nimi. Přerušovaná "
        "čára je přímka, která nejlíp prokládá body jednoho soudce; je nakreslená, "
        "a ne popsaná, protože se sklonem se lépe polemizuje, když má člověk na "
        "stránce vedle něj i body, ze kterých vznikl."
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
    "The same test in the Deepsy format comes out {hit} of its {total} tables, and the "
    "three models that write longest there are a different three, because the two "
    "formats were not asked of the same models. Where the last three places go is a "
    "fact about the SOAP halves rather than a law about length.": (
        "Táž zkouška ve formátu Deepsy vychází {hit} z jeho {total} tabulek a tři "
        "modely, které tam píšou nejdéle, jsou jiné tři, protože oba formáty nedostaly "
        "tytéž modely. Kam padnou poslední tři místa, je výrok o půlkách SOAP, ne "
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
    "The fault it catches is unambiguous: an English term left sitting in a Czech "
    "sentence.": (
        "Chyba, kterou chytá, je jednoznačná: anglický termín ponechaný uprostřed "
        "české věty."
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
    "Every pair of numbers is the two judges, in the order the tables print them, and they are "
    "never averaged: where the two point in opposite directions that is said rather than smoothed, "
    "because a mean of two judges pointing opposite ways is a number neither of them stated. And "
    "the last sentence of each paragraph -- what the criterion catches, and how often the two "
    "judges and one native speaker said the same thing -- was measured on the ten real Czech "
    "sessions under these six criteria and nowhere else. Nobody has read a Deepsy note or a "
    "translated one against a person at all.": (
        "Každá dvojice čísel jsou dva soudci v pořadí, ve kterém je tisknou tabulky, a nikdy se "
        "neprůměrují: tam, kde ti dva ukazují opačnými směry, se to říká, ne uhlazuje, protože "
        "průměr dvou soudců mířících proti sobě je číslo, které neřekl ani jeden z nich. A "
        "poslední věta každého odstavce — co kritérium zachycuje a jak často řekli dva soudci a "
        "jeden rodilý mluvčí totéž — byla změřena na deseti skutečných českých sezeních podle "
        "těchto šesti kritérií a nikde jinde. Zápis v Deepsy ani přeložený zápis proti člověku "
        "nikdo nečetl."
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
    "Where it breaks down: on {where} the resampling can tell only {separable} of the {pairs} "
    "pairs of models apart, so the order this column puts them in there is not one to read, and it "
    "is that thin in {places} of the {total} tables.": (
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
    "at least as good on every column under BOTH judges, and better than it on at "
    "least one -- so models the evidence cannot separate share a place, and "
    "{systems} models fall into {places} places of which {tied} hold more than one. "
    "Within a place the order is alphabetical and means nothing.": (
        "Řádky jsou seřazené podle dominance — model je výš jen tehdy, když je "
        "aspoň tak dobrý v každém sloupci u OBOU soudců a aspoň v jednom sloupci je "
        "lepší — takže modely, které důkazy neoddělí, sdílejí místo: {systems} "
        "modelů padne do {places} míst, z toho {tied} drží víc než jeden model. "
        "Uvnitř místa je pořadí abecední a neznamená nic."
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
        "A PDSQI-9 se nikdy neptalo na zápis ve formátu Deepsy: těch {deepsy} zápisů už "
        "je napsaných, takže by se kvůli tomu nic negenerovalo, a je to jediná cesta, "
        "jak zjistit, jestli formát, který by klinika opravdu používala, dává zápis, "
        "který stojí za založení do dokumentace."
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
}
