import json
from pathlib import Path
from tqdm import tqdm
import time
import logging

from core.extractor import extract_document
from core.flow_builder import build_flow
from core.cleaner import clean_flow
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
        flow, stats = clean_flow(flow, return_stats=True)
        logger.info(f"Cleaner complete — {len(flow)} items ready for parsing")
        logger.info(
            f"Cleaner stats → in:{stats['input_items']} | out:{stats['output_items']} | removed:{stats['noise_removed']} | lists:{stats['lists_created']} | list_items:{stats['list_items_created']} | merges:{stats['paragraph_merges']}"
        )

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
