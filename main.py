import json
import logging
import os
import time
from pathlib import Path

from tqdm import tqdm

import config as app_config
from core.cleaner import clean_flow
from core.extractor import extract_document
from core.flow_builder import build_flow
from core.health import (
    check_cleaner_char_shrinkage,
    check_cleaner_stats,
    flow_text_char_count,
    scan_unknown_flow_types,
)
from parsers import load_parsers
from config import JOBS

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def run():
    parsers = load_parsers()

    total = len(JOBS)
    for idx, job in enumerate(tqdm(JOBS, desc="Processing PDFs", unit="pdf", dynamic_ncols=True), start=1):
        print(f"\n[{idx}/{total}] Processing: {job['input']}")
        logger.info("Starting extraction")

        start = time.time()

        doc = extract_document(job["input"])
        logger.info("Extraction complete")

        logger.info("Building flow")
        image_dir = Path(job["output"]) / "images"
        flow = build_flow(doc, image_dir)
        logger.info("Flow built")

        logger.info(
            "Cleaning flow (removing noise, fixing lists, preserving page integrity)")
        chars_before = flow_text_char_count(flow)
        flow, stats = clean_flow(
            flow,
            return_stats=True,
            strip_toc_lines=getattr(app_config, "CLEANER_STRIP_TOC_LINES", False),
        )
        chars_after = flow_text_char_count(flow)
        check_cleaner_stats(stats, logger)
        check_cleaner_char_shrinkage(chars_before, chars_after, logger)

        logger.info(f"Cleaner complete — {len(flow)} items ready for parsing")
        logger.info(
            "Cleaner stats → in:%s | out:%s | removed:%s | toc_lines:%s | toc_blocks:%s | lists:%s | list_items:%s | merges:%s",
            stats["input_items"],
            stats["output_items"],
            stats["noise_removed"],
            stats.get("toc_lines_structured", 0),
            stats.get("toc_blocks_created", 0),
            stats["lists_created"],
            stats["list_items_created"],
            stats["paragraph_merges"],
        )

        _ALLOWED_FLOW = frozenset(
            {"paragraph", "heading", "image", "list", "quote", "toc"}
        )
        unknown = scan_unknown_flow_types(flow, _ALLOWED_FLOW)
        if unknown:
            logger.warning("Unexpected flow block types after clean: %s", ", ".join(unknown))

        logger.info(f"Using parser: {job['parser']}")
        parser = parsers.get(job["parser"])

        if not parser:
            print(f"⚠️ Parser not found: {job['parser']} — skipping")
            continue

        structured_content = parser(flow)
        logger.info("Structuring complete")

        output_data = {
            "program": job["program"],
            "book": job["book"],
            "type": job["type"],
            "structure": job["structure"],
            "content": structured_content
        }

        debug_on = os.environ.get("LITERATURE_PIPELINE_DEBUG", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if debug_on:
            output_data["_debug"] = {
                "cleaner_stats": stats,
                "chars_before_clean": chars_before,
                "chars_after_clean": chars_after,
                "unknown_flow_types": unknown,
            }

        safe_name = job['book'].lower().replace(' ', '_').replace('/', '_')
        output_path = Path(job["output"]) / f"{safe_name}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Writing output JSON")
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        duration = time.time() - start
        print(f"Saved → {output_path}  ({duration:.2f}s)")


if __name__ == "__main__":
    run()
