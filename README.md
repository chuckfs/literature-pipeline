# 📚 Literature Pipeline

A modular, schema-driven pipeline for converting recovery literature PDFs into structured, reader-ready JSON.

---

## 🧠 Overview

This project transforms raw PDF literature (NA, AA, and beyond) into a consistent, structured format that can power apps, search systems, and AI features.

Instead of treating PDFs as static files, this pipeline extracts and organizes them into a tree of semantic content blocks (paragraphs, quotes, chapters, etc.).

---

## 🚀 Features

- 📄 Layout-aware extraction using Docling
- 🧩 Modular parser system (per book / per program)
- 🧱 Universal JSON schema (consistent across all literature)
- 🖼️ Inline image extraction
- 🔌 Plug-and-play architecture (add new books easily)
- 🧠 Future-ready for search + AI integration

---

## 🏗️ Architecture

text PDF ↓ Docling (layout-aware extraction) ↓ Flow Builder (ordered blocks) ↓ Parser (book-specific structure) ↓ Structured JSON (universal schema) 

---

## 📁 Project Structure

text literature-pipeline/ │ ├── main.py              # Entry point ├── config.py            # Job definitions (what to process) ├── requirements.txt │ ├── core/                # Engine (no book-specific logic) │   ├── extractor.py │   ├── flow_builder.py │   ├── schema.py        # Universal schema + block definitions │   └── utils.py │ ├── parsers/             # Book-specific logic │   ├── __init__.py      # Dynamic parser loader │   ├── generic.py       # Fallback parser │   │ │   └── na/ │       ├── basic_text.py │       ├── living_clean.py │       └── just_for_today.py │ ├── input/               # Raw PDFs (not committed) ├── output/              # Generated JSON + images └── tests/ 

---

## 🧱 Universal JSON Schema

All output follows a consistent structure:

json {   "program": "NA",   "book": "Just For Today",   "type": "daily",   "structure": "entry_list",    "content": [     {       "type": "entry",       "title": "Vigilance",       "meta": { "date": "January 1" },       "children": [         { "type": "quote", "text": "..." },         { "type": "paragraph", "text": "..." },         { "type": "affirmation", "text": "..." }       ]     }   ] } 

---

## 🧩 Block Types

All content is built from a shared set of block types:

text chapter section entry heading paragraph quote affirmation list list_item image divider 

> ⚠️ These types must remain consistent across all parsers.

---

## ⚙️ Setup

### 1. Install dependencies

bash pip install -r requirements.txt 

---

### 2. Add PDFs

Place files in:

text input/<program>/ 

Example:

text input/na/just_for_today.pdf 

---

### 3. Configure jobs

Edit config.py:

python JOBS = [     {         "input": "input/na/just_for_today.pdf",         "output": "output/na",         "parser": "na.just_for_today",         "program": "NA",         "book": "Just For Today",         "type": "daily"     } ] 

---

### 4. Run pipeline

bash python main.py 

---

## 📤 Output

text output/ └── na/     ├── just_for_today.json     └── images/ 

JSON is:
- structured
- schema-compliant
- ready for UI rendering

---

## 🧠 Design Principles

- Single extraction engine (Docling)
- Many small parsers (per book)
- Strict schema, flexible structure
- Content as a tree of typed nodes

---

## ➕ Adding a New Book

1. Add PDF → input/<program>/
2. Create parser → parsers/<program>/<book>.py
3. Implement:

python def parse(flow):     return [...] 

4. Register in config.py
5. Run pipeline

---

## ⚠️ Rules

- Parsers must not modify extraction logic
- Core must not contain book-specific logic
- All output must follow the schema
- Block types must remain consistent

---

## 🧭 Roadmap

- [ ] Improve parser accuracy (JFT, Basic Text)
- [ ] Add additional programs (AA, Dharma, etc.)
- [ ] Build reader UI
- [ ] Add search + indexing
- [ ] Add semantic tagging / AI layer

---

## 📌 Summary

This project turns unstructured literature into:

> structured, navigable, and reusable knowledge
