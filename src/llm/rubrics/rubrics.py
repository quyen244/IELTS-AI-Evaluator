"""Compressed IELTS band descriptors, bands 4-9.

These are paraphrased and condensed from the public IELTS Writing band descriptors.
Compression preserves the *discriminating keywords* between adjacent bands, because
those are what let the model tell a 6 from a 7. Compressing those away is how you
end up with a model that scores everything 6.5.

This file is DATA. Editing it should not require touching pipeline code, and every
edit must be followed by a benchmark run (see docs/03-evaluation/evaluation-protocol.md).
"""

from __future__ import annotations

RUBRIC_VERSION = "rubric-v1.0"

TASK1_TA = """\
Band 9: Fully satisfies all requirements. Presents a clear, fully developed overview and accurate key features.
Band 8: Covers all requirements sufficiently. Presents a clear overview; key features are well selected and highlighted.
Band 7: Covers the requirements. Presents a CLEAR OVERVIEW of main trends/differences/stages. Key features are highlighted, but details may be inadequate or occasionally irrelevant.
Band 6: Addresses the requirements. Presents an overview WITH INFORMATION APPROPRIATELY SELECTED. Some key features are covered but details may be irrelevant, inappropriate or inaccurate.
Band 5: Generally addresses the task but format may be inappropriate. RECOUNTS DETAIL MECHANICALLY WITH NO CLEAR OVERVIEW. There may be no data to support the description.
Band 4: Attempts the task but does not cover all key features; format may be inappropriate. May confuse key features with detail; parts may be unclear, irrelevant, repetitive or inaccurate.

DISCRIMINATOR: the single strongest signal separating Band 5 from Band 6+ is the
presence of a genuine OVERVIEW that summarises main features, rather than a
mechanical recount of every data point."""

TASK2_TR = """\
Band 9: Fully addresses all parts. Presents a fully developed position with relevant, fully extended, well-supported ideas.
Band 8: Sufficiently addresses all parts. Presents a well-developed response with relevant, extended and supported ideas.
Band 7: Addresses all parts, though some parts may be more fully covered than others. Presents a CLEAR POSITION THROUGHOUT. Presents, extends and supports main ideas, but there may be a tendency to over-generalise or supporting ideas may lack focus.
Band 6: Addresses all parts although some parts may be more fully covered than others. Presents a RELEVANT POSITION although conclusions may become unclear or repetitive. Presents relevant main ideas but some may be inadequately developed or unclear.
Band 5: Addresses the task only PARTIALLY; format may be inappropriate in places. Expresses a position but the development is not always clear. Presents some main ideas but these are limited and not sufficiently developed; there may be irrelevant detail.
Band 4: Responds to the task only in a minimal way or the answer is tangential; format may be inappropriate. Presents a position but this is unclear. Presents some main ideas but these are difficult to identify and may be repetitive, irrelevant or not well supported.

DISCRIMINATOR: Band 6 vs 7 turns on whether the position is CLEAR AND CONSISTENT
throughout, and whether main ideas are EXTENDED (developed with reasoning/examples)
rather than merely stated."""

CC = """\
Band 9: Uses cohesion in such a way that it attracts no attention. Skilfully manages paragraphing.
Band 8: Sequences information and ideas logically. Manages all aspects of cohesion well. Uses paragraphing sufficiently and appropriately.
Band 7: Logically organises information and ideas; there is CLEAR PROGRESSION throughout. Uses a range of cohesive devices appropriately although there may be some under-/over-use. Presents a clear central topic within each paragraph.
Band 6: Arranges information and ideas coherently and there is a clear overall progression. Uses cohesive devices EFFECTIVELY, but cohesion within and/or between sentences may be faulty or MECHANICAL. May not always use referencing clearly or appropriately.
Band 5: Presents information with some organisation but there may be a LACK OF OVERALL PROGRESSION. Makes INADEQUATE, INACCURATE OR OVER-USE of cohesive devices. May be repetitive because of lack of referencing and substitution.
Band 4: Presents information and ideas but these are not arranged coherently and there is no clear progression. Uses some basic cohesive devices but these may be inaccurate or repetitive. May not write in paragraphs or paragraphing may be inadequate.

DISCRIMINATOR: Band 6 typically shows MECHANICAL connectors (Firstly/Secondly/
Finally used as scaffolding). Band 7+ shows cohesion arising from logical sequencing
and referencing, with connectors used selectively rather than formulaically."""

LR = """\
Band 9: Uses a wide range of vocabulary with very natural and sophisticated control of lexical features; rare minor errors occur only as slips.
Band 8: Uses a WIDE RANGE of vocabulary fluently and flexibly to convey precise meanings. Skilfully uses uncommon lexical items but there may be occasional inaccuracies in word choice and collocation.
Band 7: Uses a SUFFICIENT RANGE of vocabulary to allow some FLEXIBILITY AND PRECISION. Uses less common lexical items with some awareness of style and collocation. May produce occasional errors in word choice, spelling and/or word formation.
Band 6: Uses an ADEQUATE range of vocabulary for the task. ATTEMPTS to use less common vocabulary but WITH SOME INACCURACY. Makes some errors in spelling and/or word formation, but they do not impede communication.
Band 5: Uses a LIMITED range of vocabulary, but this is minimally adequate for the task. May make noticeable errors in spelling and/or word formation that may cause SOME DIFFICULTY for the reader.
Band 4: Uses only BASIC vocabulary which may be used repetitively or which may be inappropriate for the task. Has limited control of word formation and/or spelling; errors may cause strain for the reader.

DISCRIMINATOR: Band 6 ATTEMPTS less common vocabulary and gets it partly wrong.
Band 7 USES less common vocabulary with awareness of collocation. Band 8 uses it
with PRECISION and natural style. Heavy repetition of content words is a Band 5-6 signal."""

GRA = """\
Band 9: Uses a wide range of structures with full flexibility and accuracy; rare minor errors occur only as slips.
Band 8: Uses a WIDE RANGE of structures. The MAJORITY OF SENTENCES ARE ERROR-FREE. Makes only very occasional errors or inappropriacies.
Band 7: Uses a VARIETY OF COMPLEX STRUCTURES. Produces FREQUENT ERROR-FREE SENTENCES. Has good control of grammar and punctuation but may make a few errors.
Band 6: Uses a MIX of simple and complex sentence forms. Makes SOME ERRORS IN GRAMMAR AND PUNCTUATION but they RARELY REDUCE COMMUNICATION.
Band 5: Uses only a LIMITED RANGE of structures. ATTEMPTS complex sentences but these tend to be less accurate than simple sentences. May make frequent grammatical errors and punctuation may be faulty; errors CAN CAUSE SOME DIFFICULTY for the reader.
Band 4: Uses only a very limited range of structures with only rare use of subordinate clauses. Some structures are accurate but errors PREDOMINATE, and punctuation is often faulty.

DISCRIMINATOR: count error-free sentences. Band 6 = errors are frequent but harmless.
Band 7 = frequent error-free sentences with a few slips. Band 8 = the MAJORITY of
sentences are completely error-free. Systematic subject-verb agreement or tense
failures across the whole text indicate Band 5 or below."""

_RUBRICS: dict[tuple[str, str], str] = {
    ("task1", "TA"): TASK1_TA,
    ("task2", "TR"): TASK2_TR,
    ("task1", "CC"): CC,
    ("task2", "CC"): CC,
    ("task1", "LR"): LR,
    ("task2", "LR"): LR,
    ("task1", "GRA"): GRA,
    ("task2", "GRA"): GRA,
}


def get_rubric(task_type: str, criterion: str) -> str:
    try:
        return _RUBRICS[(task_type, criterion)]
    except KeyError as exc:
        raise KeyError(f"No rubric for {task_type}/{criterion}") from exc
