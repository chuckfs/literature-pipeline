import json
from pathlib import Path
from tqdm import tqdm
import time

from core.extractor import extract_document
from core.flow_builder import build_flow
from core.cleaner import clean_flow
from parsers import load_parsers
from config import JOBS


def run():
    parsers = load_parsers()

    total = len(JOBS)
    for idx, job in enumerate(tqdm(JOBS, desc="Processing PDFs", unit="pdf", dynamic_ncols=True), start=1):
        print(f"\n[{idx}/{total}] Processing: {job['input']}")

        start = time.time()

        doc = extract_document(job["input"])

        image_dir = Path(job["output"]) / "images"
        flow = build_flow(doc, image_dir)

        # Clean and normalize extracted content
        flow = clean_flow(flow)

        parser = parsers.get(job["parser"])

        if not parser:
            print(f"⚠️ Parser not found: {job['parser']} — skipping")
            continue

        structured_content = parser(flow)

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

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        duration = time.time() - start
        print(f"Saved → {output_path}  ({duration:.2f}s)")


if __name__ == "__main__":
    run()
