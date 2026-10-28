# Playtests

Games played by real people, newest last. Each failed game was traced against the
dataset; the cause and the fix that followed are listed so the history of the
project's improvements is visible.

## Real players

| # | Player | Version | Thinking of | Result | What went wrong | Fix that followed |
|---|---|---|---|---|---|---|
| 1 | Lawrence | 10 questions, tree leaf guess | Elon Musk | Miss (guessed Mark Zuckerberg, Mila Kunis) | Answered "not sure" to three birth-year questions; the tree's "unknown" branches had almost no training sheets | Birth-year questions get their own answer model (40% "not sure"), so the tree asks them less |
| 2 | Lawrence | 10 questions, tree leaf guess | Unknown (US actor) | Miss (guessed Cristiano Ronaldo, Gambit, Katy Perry) | The leaf held 6 sheets, one per character, all from simulated wrong answers | Guess by scoring every character with all answers instead of counting leaf sheets |
| 3 | Lawrence, with Claude asking | 10 questions | Bill Gates | Hit with scoring (Gates 50%, Musk 46%); the leaf guess would have said Musk | Wikidata does not list Gates as an engineer, the player said yes | Removed the engineer question (Wikidata clashes with common belief) |
| 4 | Tutor | 10 questions, scoring | Severus Snape | Miss (ranked 5th) | Harry, Ron, Dumbledore and Sirius had identical answers; football and "died before 40" were asked of a wizard | Added main hero, child/teen, teacher and elderly questions for fictional characters |
| 5 | Tutor | 10 questions, scoring | Batman | Miss (ranked 21st) | Player answered "superpowers: yes" and "X-Men: yes" (both wrong) | None needed for the data; later versions still find Batman despite these answers |
| 6 | Tutor | 10 questions, scoring | Donald Trump | Miss (ranked 6th) | "Known for acting or appearing on TV" - the player said yes (The Apprentice), data said no | Acting question reworded to actors only |
| 7 | Lawrence | 15 questions, focus mode | Hermione Granger | Miss (ranked 19th) | Answered North America yes, main hero yes, royal yes | Hermione's "main hero" set to unknown (she is one of the central trio) |
| 8 | Lawrence | 15 questions, focus mode | Michael Jordan | Miss (ranked 13th) | Answered "known for acting" yes (Space Jam) | Jordan's acting set to unknown; question reworded |
| 9 | Lawrence | 15 questions, focus mode | Donald Trump | Miss (guessed Joe Biden) | Answered acting no (data had just been changed to yes) and "Vice President" yes (wrong) | Showed the TV wording was ambiguous both ways: question now asks about actors only |
| 10 | Lawrence | 15 questions, focus mode | Hermione Granger | Miss (ranked 15th, Harry Potter never asked) | Answered North America yes and USA yes, thinking of the Hollywood films | Where-from questions refer to the original story; Hollywood-adapted UK/European characters are unknown |
| 11 | Lawrence | 15 questions, linked questions (branch) | Hermione Granger | **Hit, first guess** (82%; Harry Potter 13%, Luna 9%) | - | - |
| 12 | Lawrence | 15 questions, linked questions (branch) | Batman | **Hit, first guess** (Tarzan 24%, Zorro 19%) | Answered "first appeared in a book" yes, reading it as a comic book; the comic question only came at Q14 | Book question now says "a novel or other book (not a comic book)" |
| 13 | Lawrence | 15 questions, linked questions (branch) | Thor | **Hit, first guess** (Iron Man 6%, Hulk 1%) | Answered "known as an inventor" yes (data: no, that is Iron Man); scoring still put Thor first | None needed: one wrong answer only lowers a score |
| 14 | Lawrence | 15 questions, linked questions (branch) | Kobe Bryant | **Hit, first guess** (LeBron James 5%) | After "basketball: yes" it still asked football and tennis; Kobe was 88% but never reached the 95% early-guess threshold; data missed his Olympic golds | Siblings of a Yes are no longer followed up; early guess when the leader is 20x the runner-up; added missing Olympic golds (Kobe, LeBron, Ali, Nadal, Djokovic, Neymar) |
| 15 | Lawrence | 15 questions, linked questions (branch) | Donald Trump | **Hit, first guess** (George W. Bush 4%) | Asked "ruled a country" after "US President: yes" and the player answered no; asked Canada after USA yes | A question is skipped once a narrower one under it is Yes (President Yes means ruled a country) |
| 16 | Lawrence | 15 questions, linked questions (branch) | Taylor Swift | Miss (ranked 3rd, guessed Lana Del Rey) | Answered "won a Grammy" no (she has 14); the player typed the name at the yes/no prompt | After a wrong guess the game now asks who it was and lists the answers that disagreed with the data; replayed with the new rules Taylor is guessed first |
| 17 | Lawrence | 15 questions, linked questions (branch) | Justin Bieber | Miss (ranked 2nd, guessed Michael Jackson) | Answered "from the United States" yes (Bieber is Canadian); MJ also had one mismatch (alive), so fame decided; two award questions answered "not sure" | Same miss when replayed after the later fixes (MJ also had one mismatch, so fame decided) |
| 18 | Lawrence | 15 questions, linked questions (branch) | Severus Snape | **Hit, first guess, after 9 questions** (early guess) | - | - |
| 19 | Lawrence | 15 questions, linked questions (branch) | Mark Zuckerberg | Miss (ranked 5th, guessed Bill Gates); typing "Mark Elliot Zuckerberg" was not recognised | Data had Zuckerberg (and Bezos) as not known for technology | Founders marked as known for technology; names now match with a middle name, a surname alone or a typo; replayed: hit |
| 20 | Lawrence | 15 questions, linked questions (branch) | Donald Trump | Miss (ranked 5th, guessed George W. Bush); typing "trump" was not recognised | Answered "assassinated or executed" yes (the 2024 attempt) and business no; in the data Trump and Bush were almost identical | Question reworded to "killed by"; new question "impeached or forced to resign"; replayed with the same answers: hit |
| 21 | Lawrence | 15 questions, one year question + event questions (branch) | Elon Musk | **Hit, first guess** (Jeff Bezos 27%, Bill Gates 18%) | Q15 asked a fictional-only question ("first appeared in a comic") because Iron Man matched the other answers | Possible data-only fix noted: link fictional-only questions to "is this a fictional character?" |
| 22 | Lawrence | 15 questions, one year question + event questions (branch) | Vladimir Putin | **Hit, first guess, after 10 questions** (early guess) | - | - |
| 23 | Lawrence | 15 questions, one year question + event questions (branch) | Hulk | **Hit, first guess, after 8 questions** (Thor 4%, Martian Manhunter 3%) | - | The new "green skin" question decided it; before it Hulk could not be told apart from Spider-Man and Iron Man |
| 24 | Lawrence | 15 questions, one year question + event questions (branch) | Albus Dumbledore | **Hit, first guess, after 11 questions** (McGonagall 4%) | - | Wizard, teacher, elderly, Harry Potter, then "spy: no" to rule out Snape; in game 4 these characters could not be told apart |
| 25 | Lawrence | 15 questions, one year question + event questions (branch) | Captain America | **Hit, first guess, after 15 questions** (Spider-Man 13%, Daredevil 9%) | Answered "wears a mask" yes, but the data has unknown for his helmet; the last questions (teenager, lawyer) separated him from Spider-Man and Daredevil | - |
| 26 | Lawrence | 15 questions, one year question + event questions (branch) | Justin Bieber | Miss (ranked 14th, guessed Bruno Mars); typing "justion" was not recognised | Answered USA yes (he is Canadian, the second player to say so, see game 17), guitar yes and piano yes; the data had no for all three | Bieber's USA set to unknown, guitar to yes (YouTube guitar covers), piano to unknown |
| 27 | Lawrence | 15 questions, one year question + event questions (branch) | Donald Trump | **Hit, first guess, after 9 questions** (Bill Clinton 4%, George W. Bush 1%) | - | The new "impeached or forced to resign" question narrowed it to Trump, Clinton and Nixon; "lawyer: no" ruled out Clinton. Trump was missed in games 6, 9 and 20 (game 15 was a hit) |
| 28 | Lawrence | 15 questions, one year question + event questions (branch) | George Washington | **Hit, first guess, after 11 questions** (Muammar Gaddafi 5%) | Answered "killed by assassination or execution" yes (Washington died of illness) | None needed: military commander, led a revolution and Founding Father brought him back to first despite the wrong answer |
| 29 | Lawrence | 15 questions, plain screen (arcade branch) | Leonardo DiCaprio | Miss (ranked 4th, 7%; guessed Brad Pitt 20%, Morgan Freeman 18%, Denzel Washington 17%) | Every answer matched the data, but DiCaprio and Brad Pitt have identical data except "known for conservation" (DiCaprio unknown, Pitt no); answering no made DiCaprio about 3 times less likely than Pitt, and no question tells the top US Oscar-winning actors apart | Five signature-film questions (Titanic, Mission: Impossible, Ocean's Eleven, The Shawshank Redemption, Forrest Gump) for the US Oscar-winning actors no other question separated; replayed with the same answers: hit (Denzel Washington 9%, Tom Hanks 4%) |

After the fixes, games 4-10 were replayed with the players' original answers
(including the wrong ones): all seven are now guessed first.

## Claude playing as a player (black box)

Claude chose a character, answered only through the game's input and output from
its own knowledge, and did not look at the dataset during the game.

| Batch | Version | Characters | First guess | Top 3 | Not in the dataset |
|---|---|---|---|---|---|
| 10 very famous | 10 questions, scoring | Taylor Swift, Obama, Harry Potter, Einstein, Pikachu, Messi, Darth Vader, da Vinci, Spider-Man, Elizabeth II | 10/10 | 10/10 | - |
| 10 less famous | 10 questions, scoring | Ada Lovelace, Frida Kahlo, Alan Turing, Hermione, Luigi, Wolverine, Serena Williams, Tesla, Sun Yat-sen, Bart Simpson | 5/10 | 8/10 | Luigi, Sun Yat-sen |
| 30 new | 10 questions, data fixes | Michael Jordan, Cleopatra, Mickey Mouse, Napoleon, Beyoncé, Sherlock Holmes, Gandhi, Batman, Cristiano Ronaldo, Marilyn Monroe, Isaac Newton, Superman, Steve Jobs, Frodo, Martin Luther King Jr., SpongeBob, Putin, Mozart, Hello Kitty, Usain Bolt, Joker, Lincoln, Goku, Oprah Winfrey, Darwin, Iron Man, Bruce Lee, Sonic, Angela Merkel, Shrek | 24/30 | 27/30 | Oprah Winfrey, Angela Merkel, Shrek |

Every character that was in the dataset was guessed within the top 3.

## Independent agents playing as players (black box)

Separate agents, given no access to the data or the code, chose characters and
answered from general knowledge only.

| Batch | Version | Games | First guess | In the dataset | Not in the dataset |
|---|---|---|---|---|---|
| External review playtest | 15 questions, linked questions | 14 | 12/14 | 12/12 | Rosalind Franklin, Atticus Finch |
| 20 new characters | before the data fixes below | 20 | 17/20 | 17/18 (Tom Hanks missed: "known for directing" was yes in the data) | Link, Shrek |
| Same 20, replayed | after the data fixes below | 20 | 18/20 | **18/18** | Link, Shrek |

Data fixes between the last two rows: real people with several citizenships now
have the country players associate with them (37 people, e.g. Tom Hanks USA, not
unknown), actors who only sometimes direct are unknown for "known for directing",
and verified label errors (The Joker's medium, Miley Cyrus and Demi Lovato,
Amelia Earhart, Chuck Norris, Miss Marple, human/animal for 21 characters,
Cambridge for Charles III and Nehru) were corrected. Questions the agent had not
answered before (the retrained tree asks a few new ones) were answered from
common knowledge by Claude, without looking at the data.
