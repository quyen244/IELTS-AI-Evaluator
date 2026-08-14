"""Word lists used by the deterministic preprocessor. Data, not logic."""

from __future__ import annotations

STOPWORDS: frozenset[str] = frozenset(
    """
a an the and or but so because although though while whereas however therefore thus
hence moreover furthermore also besides then than that this these those there here
is are was were be been being am do does did done have has had having will would
shall should can could may might must of in on at to for with from by about into
over under between among during before after above below up down out off again
further once all any both each few more most other some such no nor not only own
same too very just as if it its it's they them their theirs he she his her hers we
us our ours you your yours i me my mine who whom whose which what when where why how
one two three many much lot lots kind sort thing things people person get got make
made take taken go going come coming say said see seen know known
""".split()
)

# Discourse markers checked against the essay text. Multi-word entries are matched
# as phrases, single words as whole words.
COHESIVE_DEVICES: tuple[str, ...] = (
    "however", "therefore", "moreover", "furthermore", "nevertheless", "nonetheless",
    "consequently", "thus", "hence", "meanwhile", "similarly", "likewise",
    "conversely", "instead", "additionally", "besides", "otherwise", "accordingly",
    "firstly", "secondly", "thirdly", "finally", "lastly", "overall",
    "in conclusion", "to conclude", "in summary", "to sum up",
    "for example", "for instance", "such as", "in particular", "namely",
    "in addition", "as a result", "as a consequence", "due to", "owing to",
    "because of", "in contrast", "by contrast", "on the other hand",
    "on the one hand", "in other words", "that is to say", "in fact",
    "indeed", "although", "though", "whereas", "while", "despite", "in spite of",
    "at the outset", "subsequently", "afterwards", "eventually", "ultimately",
    "arguably", "notably", "significantly", "importantly", "specifically",
)
