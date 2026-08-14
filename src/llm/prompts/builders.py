"""Prompt construction for every LLM node.

See docs/02-technical/prompt-engineering.md for the reasoning behind each element.
Bump PROMPT_VERSION on any content change, then re-run the benchmark.
"""

from __future__ import annotations

from src.core.schemas import CRITERION_NAMES, ExamItem, ScoredCriterion, TextFeatures
from src.llm.rubrics.rubrics import get_rubric

PROMPT_VERSION = "prompt-v1.0"

TASK_LABEL = {
    "task1": "IELTS Academic Writing Task 1 (data/process report)",
    "task2": "IELTS Writing Task 2 (argumentative essay)",
}


def format_features(f: TextFeatures) -> str:
    repeated = (
        ", ".join(f"{w}({n})" for w, n in f.repeated_content_words) or "none detected"
    )
    devices = ", ".join(f.cohesive_devices_found) or "none detected"
    length_flag = "MEETS minimum" if f.meets_min_words else "BELOW minimum"
    return (
        f"- Word count: {f.word_count} (minimum required: {f.min_words_required}) — {length_flag}\n"
        f"- Paragraphs: {f.paragraph_count} | Sentences: {f.sentence_count} | "
        f"Average sentence length: {f.avg_sentence_length:.1f} words\n"
        f"- Unique words: {f.unique_words} | Type-token ratio: {f.type_token_ratio:.2f}\n"
        f"- Most repeated content words: {repeated}\n"
        f"- Cohesive devices detected: {devices}"
    )


# --------------------------------------------------------------------------- #
# Criterion evaluation
# --------------------------------------------------------------------------- #
CRITERION_SYSTEM = (
    "You are a certified IELTS Writing examiner with over ten years of experience "
    "assessing {task_label}. You apply the official band descriptors strictly and "
    "consistently. You are neither lenient nor harsh — you are accurate. You are "
    "willing to award low bands to weak work and high bands to strong work; "
    "defaulting everything to the middle of the scale is the worst mistake an "
    "examiner can make."
)

CRITERION_USER = """## CRITERION UNDER ASSESSMENT
{criterion_name} ({criterion_code}) — assess THIS CRITERION ONLY.

## OFFICIAL BAND DESCRIPTORS
{rubric}

## EXAM PROMPT
{exam_prompt}
{chart_block}
## STUDENT ESSAY
<<<ESSAY
{essay}
ESSAY

## OBJECTIVE TEXT STATISTICS
These were computed programmatically. Treat them as ground truth and do not re-count.
{features}

## WHAT TO PRODUCE
1. `justification` — 3 to 5 sentences in English. Name the band descriptor the essay
   matches and explain why it matches that one rather than the band above or below.
   Write this BEFORE you decide on a number.
2. `band` — a number from 1.0 to 9.0 in steps of 0.5, consistent with your justification.
3. `evidence` — 2 to 4 items. Each `quote` MUST be copied character-for-character from
   between the ESSAY markers above.
4. `strengths`, `weaknesses`, `improvements` — concise English bullet points.
5. `confidence` — 0.0 to 1.0.

## RULES
- Never invent a quote. If you cannot find an exact supporting quote, leave that
  evidence item out rather than paraphrasing or correcting the student's words.
- Assess {criterion_code} only. Ignore problems that belong to other criteria.
- Use the word count given above; do not count words yourself.
{length_rule}"""

LENGTH_RULE_SCORED = (
    "- Do NOT deduct marks for the essay being under the word limit. Length is "
    "handled separately by the scoring system, and deducting here would penalise "
    "the student twice."
)
LENGTH_RULE_OTHER = (
    "- Ignore essay length entirely; it is not part of this criterion."
)


def build_criterion_messages(
    exam: ExamItem, criterion: str, features: TextFeatures
) -> list[dict[str, str]]:
    chart_block = ""
    if exam.task_type == "task1" and exam.chart_description:
        chart_block = (
            "\n## SOURCE DATA SHOWN IN THE VISUAL\n"
            "Use this to check whether the student reported the figures accurately.\n"
            f"{exam.chart_description}\n"
        )

    is_task_criterion = criterion in ("TA", "TR")
    return [
        {
            "role": "system",
            "content": CRITERION_SYSTEM.format(task_label=TASK_LABEL[exam.task_type]),
        },
        {
            "role": "user",
            "content": CRITERION_USER.format(
                criterion_name=CRITERION_NAMES[criterion],
                criterion_code=criterion,
                rubric=get_rubric(exam.task_type, criterion),
                exam_prompt=exam.prompt.strip(),
                chart_block=chart_block,
                essay=exam.essay.strip(),
                features=format_features(features),
                length_rule=LENGTH_RULE_SCORED if is_task_criterion else LENGTH_RULE_OTHER,
            ),
        },
    ]


# --------------------------------------------------------------------------- #
# Sentence corrector
# --------------------------------------------------------------------------- #
CORRECTOR_SYSTEM = (
    "You are an IELTS writing tutor who corrects student work. Your corrections are "
    "minimal and surgical: you fix what is wrong and leave the student's own voice "
    "and ideas intact. You explain in Vietnamese because your students are Vietnamese."
)

CORRECTOR_USER = """## STUDENT ESSAY
<<<ESSAY
{essay}
ESSAY

## TASK
Identify at most {max_issues} sentence-level problems, ordered by how much each one
damages the band score — most damaging first.

For each issue:
- `original`: the problematic text, copied character-for-character from between the
  ESSAY markers. Never paraphrase it.
- `corrected`: the same text with the problem fixed and nothing else changed.
- `error_types`: one or more of grammar, agreement, tense, article, word choice,
  collocation, word form, spelling, punctuation, capitalisation.
- `impact`: negligible / minor / moderate / major / critical.
- `explanation_vi`: a short explanation IN VIETNAMESE of what was wrong and why the
  correction is better.

## RULES
- Prioritise errors that affect accuracy or meaning over matters of style.
- If the same error pattern recurs, report it at most twice and raise its `impact`
  instead of listing every instance.
- If the essay has fewer than {max_issues} genuine problems, return fewer items.
  Do not invent errors to fill the list."""


def build_corrector_messages(essay: str, max_issues: int) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": CORRECTOR_SYSTEM},
        {
            "role": "user",
            "content": CORRECTOR_USER.format(essay=essay.strip(), max_issues=max_issues),
        },
    ]


# --------------------------------------------------------------------------- #
# Feedback synthesiser
# --------------------------------------------------------------------------- #
SYNTH_SYSTEM = (
    "You are an IELTS coach writing to a Vietnamese student. You are direct, "
    "specific and encouraging. You never give vague advice such as 'improve your "
    "vocabulary' — you say exactly which words, which sentences, and what to do instead."
)

SYNTH_USER = """## ASSESSMENT ALREADY COMPLETED
Overall band: {overall}

{criteria_block}

## TOP SENTENCE-LEVEL ISSUES
{issues_block}

## TASK
Write the student's feedback in VIETNAMESE.

- `summary_vi`: 3 to 5 sentences. State honestly where the student stands, what is
  genuinely working, and what is holding the score down.
- `priority_actions`: EXACTLY 3 actions, ordered by how much band improvement each
  would produce. Each needs `action` (imperative, specific), `criterion` (the code
  it targets), `expected_gain` (e.g. "+0.5 LR"), and `example` — a concrete example
  taken from the analysis above, not a generic one.
- `next_band_gap`: what specifically stands between this student and the next half band.

## RULES
- Base everything on the analysis above. Do not invent new errors or new quotes.
- Do not contradict the bands that have already been awarded."""


def build_synthesizer_messages(
    overall: float,
    criteria: dict[str, ScoredCriterion],
    issues: list,
) -> list[dict[str, str]]:
    parts = []
    for code, c in criteria.items():
        band = "n/a" if c.band is None else f"{c.band}"
        parts.append(
            f"### {code} — Band {band}\n"
            f"Justification: {c.justification}\n"
            f"Strengths: {'; '.join(c.strengths) or 'none recorded'}\n"
            f"Weaknesses: {'; '.join(c.weaknesses) or 'none recorded'}\n"
            f"Suggested improvements: {'; '.join(c.improvements) or 'none recorded'}"
        )
    criteria_block = "\n\n".join(parts)

    if issues:
        issues_block = "\n".join(
            f"- [{i.impact}] \"{i.original}\" -> \"{i.corrected}\" ({', '.join(i.error_types)})"
            for i in issues[:6]
        )
    else:
        issues_block = "None recorded."

    return [
        {"role": "system", "content": SYNTH_SYSTEM},
        {
            "role": "user",
            "content": SYNTH_USER.format(
                overall=overall,
                criteria_block=criteria_block,
                issues_block=issues_block,
            ),
        },
    ]
