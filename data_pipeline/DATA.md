# Dataset documentation

## Summary

| | |
|---|---|
| Rows | **500**: 350 real people, 150 fictional characters |
| Of which | 91 hand-curated and reviewed entry by entry (`roster.csv`); 409 generated from Wikidata by fixed rules (`roster_auto.csv`) |
| Attributes | **107** Yes/No attributes: 56 hand-designed core questions + 51 questions in the reviewed question pool. Each value is `true`, `false` or `unknown` |
| Popularity | `sitelinks`: number of Wikipedia/Wikimedia language editions with an article (26–340) |
| Game file | `../dataset/characters.csv` (plus `questions.csv`) (generated; do not edit by hand) |
| Wikidata snapshot | `raw/wikidata_snapshot.json`, retrieved 2026-10-17 |
| Licence | Wikidata content is CC0 1.0 (public domain); attribution given anyway |

The roster mixes real people and fictional characters, so the first question,
"Is this a fictional character?", splits the candidates (150 / 350).

## Pipeline

```text
select_candidates.py ─► candidates.csv ─┐   (network: QLever, WDQS, Wikipedia API)
fetch_wikidata.py ──────────────────────┼─► wikidata_snapshot.json   (network: WDQS)
                                        │
roster.csv (curated) ───────────────────┤
build_auto_roster.py ─► roster_auto.csv ┼─► src/preprocess.py ─► ../dataset/characters.csv ─► src/data_loader.py ─► game
question_pool.csv (reviewed) ───────────┘
check_wikidata.py, propose_questions.py, analyse_data.py: review and quality reports
```

```bash
python data_pipeline/scripts/select_candidates.py   # rank candidates (network, ~15 min first time; cached afterwards)
python data_pipeline/scripts/fetch_wikidata.py      # download facts for roster + candidates (network, ~10 min)
python data_pipeline/scripts/build_auto_roster.py   # generate roster_auto.csv (offline)
python data_pipeline/scripts/check_wikidata.py      # verify curated roster facts (offline)
python data_pipeline/src/preprocess.py              # rebuild ../dataset/characters.csv (offline)
python data_pipeline/scripts/analyse_data.py        # distribution, hard pairs, depth check, popularity
python -m pytest data_pipeline/tests  # includes a check that characters.csv is up to date
```

Only the first two steps need the internet; every file they produce is kept,
so the dataset rebuilds offline and reproducibly.

## Reading the data with the pipeline helper

The game reads `../dataset/` with its own code (see `../dataset/README.md`). Inside the pipeline:

```python
from data_loader import load_characters, to_feature_matrix
from questions import CORE_QUESTIONS, FIRST_QUESTION, POOL_QUESTIONS, QUESTIONS

characters = load_characters()                 # tuple of Character (500)
characters[0].name                             # "Albert Einstein"
characters[0].attributes["is_fictional"]       # True / False / None (unknown)
characters[0].sitelinks                        # 322 (popularity)
QUESTIONS["is_fictional"]                      # player-facing question text (107 questions)
FIRST_QUESTION                                 # "is_fictional": always ask this first
```

`None` means the fact is unknown or debatable for that character. **Never
treat it as `False`.** In simulated answer sheets, an unknown value should
produce "not sure" more often than a known one: a player is more likely to
hesitate on a debatable fact (Elon Musk is `unknown` for "from Africa").

## Two kinds of rows

| | Curated (91) | Generated (409) |
|---|---|---|
| File | `raw/roster.csv` | `raw/roster_auto.csv` (regenerate, do not edit) |
| How | Every value chosen by hand, with notes and overrides | Fixed rules on Wikidata facts, plus reviewed tables and corrections |
| Contradictions between facts | Build fails (a review mistake) | The triggering value becomes `unknown` |
| `source` column in `characters.csv` | "manually reviewed" | "generated automatically" |
| Mean unknown values per row | 1.5 | 2.9 |

## Choosing the 409 generated entries (`select_candidates.py`)

1. **Long list:** the 1,200 humans and 700 fictional characters with the most
   sitelinks (QLever Wikidata endpoint; WDQS times out on such rankings).
2. **Removed** (status in `candidates.csv`):
   - already in the curated roster;
   - listed in `raw/exclusions.csv` (71 entries, each with a reason):
     religious figures, people known mainly for atrocities, terrorism or
     organised crime, Nazi or fascist leaders; for fiction, characters from
     mythology, religion, folklore or legend, things that are not story
     characters (memes, mascots, thought experiments) and ambiguous names;
   - no English Wikipedia article;
   - fictional characters that belong to no identifiable work (no P1441,
     P4584, P1080, P170 or P8345), which removes most legendary figures.
3. **Ranking:** score = English Wikipedia pageviews over the last 60 days ×
   sitelinks. Sitelinks reflect long-term, worldwide recognition but favour
   historical and occasionally spam-inflated entries; pageviews reflect who
   people look up today but spike with the news. The product balances both.
   Pageviews come from the batched Wikipedia API without following redirects,
   so a minor character whose page redirects to a list does not inherit the
   list's views.
4. Entries are taken in rank order until there are 350 real people and 150
   fictional characters in total (`scripts/dataset_config.py`). Four were
   skipped by the generator (see `raw/auto_roster_report.txt`), so the
   next-ranked candidates took their places.

## Rules for generated rows (`build_auto_roster.py`)

| Column | Real people | Fictional characters |
|---|---|---|
| gender | P21 (incl. trans man/woman); other values → unknown | same |
| origin_year | Earliest birth year (P569) | Publication date of the first-appearance work (P4584), else its inception; else its series; else the character's inception (P571); else unknown. Publication wins: *Harry Potter and the Philosopher's Stone* was begun in 1990 but published in 1997 |
| alive, age_at_death | Any death statement → no, age from exact dates (BCE: year precision, no year 0); no death, born 1900 or later and at most 110 years old → yes; otherwise unknown. "Unknown value" dates are ignored | `na` |
| region, country | Citizenship (P27) via `countries.csv`; several citizenships → debatable; any citizenship missing from the table → unknown | Country of origin (P495) of the character, else of the first-appearance work and its series, else a franchise named in the description (`franchise_countries.csv`) |
| domains | Keywords in the one-line Wikidata description (`domain_keywords.csv`), longest first ("martial artist" is sport, not art); rulers and royals also count as politics; no domain → entry skipped | empty |
| species | human | Classes (P31) via `character_classes.csv`; conflicting or hybrid → unknown |
| media | — | First match of: specific type of the first-appearance work or its series; medium words in the description; a generic "literary work"; a franchise or author in the description; classes naming exactly one medium; a generic screen type ("film" counts as specific live action, but "animated film" beats it) |
| tags | nobel (Nobel Prize labels only, not the Ig Nobel); ruler from office words, ruling titles and capitalised state positions that name what they govern ("Prime Minister of India", not a bare "president" or "President of the Jury at the Cannes Festival"); royal from titles not inside names ("rock band Queen" does not count) and phrases such as "royal family" | powers, villain, royal and ruler from `fictional_traits.csv`, reviewed by hand for every generated character; robot from classes or description |

Why the description? Wikidata lists many secondary occupations (most actors
are also "singer", most politicians "writer"); the one-line description states
what someone is mainly known for, which is what the questions ask.

### Reviewed tables (all in `raw/`)

| File | Rows | Purpose |
|---|---|---|
| `countries.csv` | 56 | Country name → region, with the Wikidata IDs of modern and historical states mapped to it (Kingdom of England → UK, Soviet Union → Russia, Qing dynasty → China, ...) |
| `domain_keywords.csv` | 151 | Description keyword → "known for" domain (ruling titles are handled by the ruler/royal rules instead) |
| `work_types.csv` | 89 | Wikidata work type → medium; `generic` marks broad types ("television series", "literary work") that only count when nothing more specific is known |
| `character_classes.csv` | 100 | Character class → species / tags / medium hint |
| `franchise_countries.csv` | 44 | Franchise, publisher or author in a description → country and original medium (Marvel → USA, comic; Agatha Christie → UK, book) |
| `fictional_traits.csv` | 122 | Hand-reviewed superpowers, villain, royal and ruler values (yes/no/unknown) for generated characters; descriptions such as "fictional character in Marvel Comics" mention none of them. Three rows are for candidates not currently selected |
| `auto_corrections.csv` | 11 | Column fixes found by spot-checks, each with a reason (a first appearance mistyped as a film series, a wrong country, a queen consort, ambiguous display names); the name column must match Wikidata |
| `exclusions.csv` | 71 | Entries never selected, with reasons |

### Spot-check findings that changed the rules

- "singer-songwriter" was not matched as a singer (hyphen handling): fixed
  with an explicit keyword.
- A recorded sport (P641) is not what someone is known for (Stanley Kubrick:
  chess; Prince William: football): sport now comes from the description only.
- "Present in work" (P1441) lists later films and games for comic characters
  (Gambit came out as a 2000 Japanese video game): no longer used.
- Episodes are typed only "television series episode": the series is now
  fetched (P179) so Harley Quinn's first appearance counts as animation.
- Kylo Ren's Wikidata description was vandalised ("former King of Naboo"):
  his traits are now reviewed by hand like every generated character.
- A code review of all 409 generated rows found more rule errors, all fixed:
  the Ig Nobel Prize counted as a Nobel Prize (Trump, Putin); "President of
  the Jury at the Cannes Festival" counted as ruling a country (De Niro,
  Spielberg); "rock band Queen" made Freddie Mercury royal; "martial artist"
  counted as visual art; Gollum and Spock got the wrong medium; Harry Potter
  characters got the year writing began (1990) instead of publication (1997).

## Roster format (`roster.csv` and `roster_auto.csv`)

| Column | Allowed values | Notes |
|---|---|---|
| `name` | text | Unique (case-insensitive) across both files |
| `wikidata_id` | `Q` + digits | Unique across both files |
| `popularity_wikidata_id` | empty or `Q` + digits | Use another item's sitelinks for popularity (Totoro → My Neighbor Totoro) |
| `kind` | `real`, `fictional` | |
| `gender` | `male`, `female`, `unknown` | |
| `species` | `human`, `animal`, `other`, `unknown` | `other` = clearly neither (robot, hobbit, alien) |
| `origin_year` | empty (unknown) or a non-zero year, negative for BCE | Birth year or year of first appearance |
| `alive` | `yes`, `no`, `unknown` (real); `na` (fictional) | Living status as of 2026-10-17 |
| `age_at_death` | integer or empty if `alive=no`, otherwise empty | |
| `region` | `;`-list of regions, or `unknown` | Several regions = debatable |
| `country` | `;`-list of names from `countries.csv`, or empty | Must lie in the listed regions; several = debatable |
| `domains` | `;`-list of `science`, `technology`, `politics`, `sport`, `football`, `music`, `acting`, `film`, `writing`, `art`, `business`, `exploration` | At least one for real people |
| `media` | `book`, `comic`, `animation`, `video_game`, `live_action`, `unknown` | Fictional only |
| `tags` | `;`-list of `nobel`, `ruler`, `royal`, `powers`, `villain`, `robot` | `nobel` real only; `powers`, `villain` fictional only |
| `overrides` | `;`-list of `attribute=true/false/unknown` | Any core or pool attribute; must change the derived value |
| `notes` | text | Curated: reasoning. Generated: the Wikidata description (used by the pool's description gate) |

Unknown values derive as follows: unknown year → every year question unknown;
several regions → those regions unknown, the rest false; unknown country →
country questions unknown only for countries in the listed regions.

## Core questions (56)

Identity (fictional, male, human, animal, alive, died before 40); origin year
(BCE, before 1500/1800/1900/1950, 1960/1970/1980/1995 or later); region (6);
country (China/HK/Taiwan, USA, UK, Japan, France, Germany, Italy, Spain,
Russia, India, Canada, Brazil); known for (12 domains); traits (Nobel Prize,
ruled a country, monarch or royal, superpowers or magic, villain, robot);
medium of first appearance (5).

## Question pool (`raw/question_pool.csv`, 51 questions)

Built from Wikidata properties (occupation, awards, positions, sport,
instrument, education, narrative universe) and reviewed by hand; two manual
groups (Disney/Nintendo, X-Men/Avengers). `scripts/propose_questions.py`
lists every shared value as candidates (1,330 for the 500 entries); questions
were kept only if players can answer them, they are objective, and they help
separate similar entries.

| Column | Meaning |
|---|---|
| `attribute`, `question` | Column name and player-facing text |
| `sources` | `Pxxx=Qyyy` facts that make the answer Yes; empty for manual questions |
| `add` / `remove` / `unknown` | Names corrected to Yes / No / unknown, with reasons in `notes` |
| `gate`, `keywords` | For generated rows only, the description decides: keyword in the description → yes; Wikidata fact but no keyword → unknown; neither → no. `real` = people only, `all` = everyone |

Answer for a name: listed in `unknown` → unknown; in `remove` → no; in `add`
→ yes; holds a source fact → yes (subject to the gate); otherwise no.

The gate exists because occupation data is noisy for generated rows: without
it, "Is this person a singer?" was yes for Nicole Kidman and Keanu Reeves,
"chemist" yes for Margaret Thatcher, and "emperor" no for Augustus (missing
statement). Awards, positions and universes are not gated. Manual lists were
extended for generated characters (superheroes such as Hulk and Thor; Disney's
Donald Duck and Goofy).

New for the 500-entry dataset: Marvel, Star Wars, X-Men and Avengers
characters; Golden Globe winners; US vice presidents; UK prime ministers;
rappers, boxers and racing drivers; more Oscar and Grammy categories.

## Popularity (`sitelinks`)

- Range 26–340. Most popular: Barack Obama (340), William Shakespeare (336),
  Donald Trump (334), Albert Einstein and Michael Jackson (322).
- Characters usually covered by the article about their work point to the
  work instead (`popularity_wikidata_id`): Totoro, Peppa Pig.
- **Real vs fictional bias:** medians 151 (real) and 47 (fictional). Compare
  popularity within each group (e.g. divide by the group median).

## Verification

`scripts/check_wikidata.py` compares the curated roster's names, gender,
birth year, living status, age at death and Nobel Prizes with the snapshot.
Result on 2026-10-17: all agree except four reviewed cases (Julius Caesar's
BCE age precision; Winnie-the-Pooh, Darth Vader and Jack Sparrow use aliases
of the Wikidata label). Generated rows are not checked entry by entry: their
rules were spot-checked on random samples, every generated fictional
character's traits were reviewed by hand, and a code review read all 409
rows; the errors found were fixed in the rules or in `auto_corrections.csv`.

## Data-quality report (`scripts/analyse_data.py`)

A greedy information-gain split over all 500 entries, with "Is this a
fictional character?" first and **every answer matching the data**, after 10
questions:

| | Core questions only | Core + pool (107) |
|---|---|---|
| Entry isolated (1 candidate left) | 41% | **57%** |
| 3 or fewer candidates left | 73% | **88%** |
| Pairs no question can separate | 519 | 202 |

The remaining inseparable pairs are entries with almost no public difference
the questions capture: Homer and Bart Simpson, Bugs Bunny and Daffy Duck,
Roger Federer and Novak Djokovic, several US presidents and actresses of the
same age. Real players make mistakes and say "not sure", so real accuracy
will be lower; the game should guess among the top few candidates at the end.

## Limitations

- **Closed roster.** The game can only identify these 500 entries; held-out
  *unseen characters* cannot be guessed by construction. Evaluation should
  hold out simulated answer sheets, not identities.
- **Generated rows are noisier** than curated ones. They inherit Wikidata's
  coverage and occasional vandalism; spot-checks fixed what was found.
- **Selection bias.** Rankings come from English Wikipedia and global
  sitelinks: the roster leans towards the USA (249 entries from North
  America), Europe (156) and men (373 male, 119 female). The 60-day pageview
  window favours people in the news in August–October 2026.
- **Judgement calls.** "Known for", region, species, the reviewed traits and
  the pool corrections involve judgement; every rule and correction is
  recorded so it can be inspected and changed.
- **Time-sensitive facts.** Living status, ages, sitelinks and pageviews
  reflect 2026-10-17.
- **Educational sample.** Not intended for any purpose beyond this project.
