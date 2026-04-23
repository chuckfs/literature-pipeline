"""
Optional pipeline flags (override in this file or set env LITERATURE_PIPELINE_DEBUG=1).
"""

# When True, TOC-like lines (content heuristics) are captured into ``toc`` blocks (not deleted).
# See ``core.semantics.should_capture_as_toc_line`` for heuristics.
CLEANER_STRIP_TOC_LINES = False

JOBS = [
    {
        "input": "input/na/justfortoday.pdf",
        "output": "output/na",
        "parser": "generic",
        "program": "NA",
        "book": "Just For Today",
        "type": "daily",
        "structure": "entry_list"
    },
    {
        "input": "input/na/basictext.pdf",
        "output": "output/na/basic_text",
        "parser": "na.basic_text",
        "program": "NA",
        "book": "Basic Text",
        "type": "chaptered",
        "structure": "hierarchical"
    },
    {
        "input": "input/na/livingclean.pdf",
        "output": "output/na/living_clean",
        "parser": "na.living_clean",
        "program": "NA",
        "book": "Living Clean",
        "type": "chaptered",
        "structure": "nested_sections"
    }
]
