---
name: english-tech-writing
description: Writing rules for English technical prose — knowledge-base notes, documentation, articles, explanations. Use when writing or revising anything in English so it reads as competent human technical writing, not generic LLM output.
---

# English Technical Writing

## Overview

Direct, plain, honest prose. Short sentences, named actors, one idea per paragraph. Every sentence must add information; if it only adds tone, delete it.

## Sentences

- Active voice with a named actor. Not "the token is validated" but "the server validates the token".
- Subject and verb come early. Break any sentence doing two jobs into two.
- Present tense for how things work ("returns", "stores", "fails").
- No throat-clearing openers ("When it comes to X,", "In the world of Y,").

## Paragraphs

- One topic per paragraph. The first sentence states what the paragraph is about.
- Arguments move in one direction: state, support, close. Don't hedge, conclude, then re-hedge.
- Introduce new terms concretely: what it does first, definition after.

## Banned stock phrases (LLM-isms)

These add tone without content. Never use them:

- "delve (into)", "dive into", "unpack", "embark on", "navigate the landscape"
- "It's important to note", "it goes without saying", "needless to say"
- "In today's fast-paced world", "now more than ever"
- "leverage", "utilize" (say "use"), "empower", "unlock", "elevate", "supercharge", "game-changer"
- "seamless", "robust", "cutting-edge", "best-in-class", "scalable" (unless measured), "crucial", "vital" as decoration
- "Moreover," / "Furthermore," / "Additionally," chains as sentence openers
- "not just X, but Y", "isn't about X — it's about Y"
- "In conclusion", "To summarize" used to only restate the previous paragraph
- Empty intensifiers: "very", "really", "extremely", "incredibly"

If a claim is strong, show the number, the code, or the mechanism — don't add an adjective.

## Structure and formatting

- Headings name the topic or the question the section answers. No filler headings ("Introduction", "Other considerations").
- One sentence per line is NOT required in English prose; normal paragraph flow is fine. (This differs from the Japanese rules.)
- Define a term on first use, then use that same term consistently. Don't retreat to vague words ("the tool", "the system") after naming something.
- Code, commands, output, config: fenced blocks with a language tag.
- Enumerations as lists. Comparisons as tables.
- Em-dashes at most once per paragraph; prefer commas or parentheses.

## Honesty

- Never state as fact what wasn't verified. Mark uncertainty explicitly ("probably", "we didn't verify X") and say what would confirm it.
- Code samples must have actually been run before publication.

## Post-draft checklist

Apply mechanically after writing:

1. **Delete self-referential filling**: any sentence that only announces, previews, or summarizes the document itself.
2. Search the draft for every banned phrase above.
3. Read the first sentence of each paragraph in sequence; it should read as an outline of the argument.
4. Every claim has evidence next to it: a number, code, or a citation. If not, add evidence or soften the claim.
