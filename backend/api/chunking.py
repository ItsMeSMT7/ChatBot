# d:\Sumit\Project\P Square\backend\api\chunking.py

"""
Intelligent chunking engine.

Instead of splitting every 500 characters (which breaks sentences
and loses context), this module:

1. Splits text into sentences using spaCy
2. Groups sentences under their section headings
3. Merges sentences into chunks that respect a max character limit
4. Overlaps 1 sentence between chunks for context continuity
5. Extracts keywords from each chunk using NLP
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Load spaCy once ──
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
    _nlp.max_length = 2_000_000
    SPACY_AVAILABLE = True
except Exception:
    logger.warning("spaCy not available — using regex sentence splitter")
    SPACY_AVAILABLE = False

# ── Chunking configuration ──
MAX_CHUNK_CHARS = 800       # max characters per chunk
MIN_CHUNK_CHARS = 100       # discard tiny chunks
OVERLAP_SENTENCES = 1       # overlap between adjacent chunks


class ProcessedChunk:
    """One chunk ready for embedding."""

    def __init__(self, content, section_title=None, page_number=None,
                 keywords=None, chunk_index=0, metadata=None):
        self.content = content
        self.section_title = section_title
        self.page_number = page_number
        self.keywords = keywords or []
        self.chunk_index = chunk_index
        self.metadata = metadata or {}


# ────────────────────────────────────────────────────────────
#  Sentence Splitting
# ────────────────────────────────────────────────────────────
def _split_sentences(text):
    """Split text into sentences using spaCy or regex fallback."""
    if SPACY_AVAILABLE:
        doc = _nlp(text)
        return [s.text.strip() for s in doc.sents if s.text.strip()]
    else:
        parts = re.split(r'(?<=[.!?])\s+', text)
        return [p.strip() for p in parts if p.strip()]


# ────────────────────────────────────────────────────────────
#  Keyword Extraction
# ────────────────────────────────────────────────────────────
def _extract_keywords(text, max_keywords=10):
    """
    Extract important keywords from text using:
    1. spaCy named entities (people, orgs, policies)
    2. spaCy noun chunks (key phrases)
    3. Capitalized multi-word phrases (often important terms)
    """
    keywords = set()

    if SPACY_AVAILABLE:
        doc = _nlp(text[:5000])

        # Named entities
        for ent in doc.ents:
            if ent.label_ not in ("CARDINAL", "ORDINAL", "QUANTITY"):
                kw = ent.text.strip()
                if 2 < len(kw) < 60:
                    keywords.add(kw.lower())

        # Noun chunks (key phrases like "leave policy", "working hours")
        for chunk in doc.noun_chunks:
            phrase = chunk.text.strip()
            if 2 < len(phrase) < 60:
                keywords.add(phrase.lower())

    # Capitalized phrases (e.g., "Annual Leave", "Code of Conduct")
    caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    for c in caps:
        keywords.add(c.lower())

    return list(keywords)[:max_keywords]


# ────────────────────────────────────────────────────────────
#  Sentence → Chunk Merging
# ────────────────────────────────────────────────────────────
def _merge_sentences(sentences, heading=None, page_number=None):
    """
    Merge a list of sentences into chunks of ≤ MAX_CHUNK_CHARS.
    Keeps OVERLAP_SENTENCES overlap between consecutive chunks.

    BEFORE (old system):
        "The company provides 12 da"  ← broken mid-word
        "ys of paid leave per year."  ← context lost

    AFTER (this system):
        "The company provides 12 days of paid leave per year.
         Employees must apply through the HR portal."  ← complete thoughts
    """
    chunks = []
    current_sentences = []
    current_length = 0

    for sent in sentences:
        # If adding this sentence would exceed the limit, flush
        if current_length + len(sent) > MAX_CHUNK_CHARS and current_sentences:
            chunk_text = " ".join(current_sentences).strip()

            if len(chunk_text) >= MIN_CHUNK_CHARS:
                chunks.append(ProcessedChunk(
                    content=chunk_text,
                    section_title=heading,
                    page_number=page_number,
                    keywords=_extract_keywords(chunk_text),
                ))

            # Keep last N sentences for overlap (context continuity)
            if OVERLAP_SENTENCES > 0 and len(current_sentences) > OVERLAP_SENTENCES:
                current_sentences = current_sentences[-OVERLAP_SENTENCES:]
                current_length = sum(len(s) for s in current_sentences)
            else:
                current_sentences = []
                current_length = 0

        current_sentences.append(sent)
        current_length += len(sent) + 1  # +1 for space

    # Flush remaining sentences
    if current_sentences:
        chunk_text = " ".join(current_sentences).strip()
        if len(chunk_text) >= MIN_CHUNK_CHARS:
            chunks.append(ProcessedChunk(
                content=chunk_text,
                section_title=heading,
                page_number=page_number,
                keywords=_extract_keywords(chunk_text),
            ))

    return chunks


# ────────────────────────────────────────────────────────────
#  Main Entry Point
# ────────────────────────────────────────────────────────────
def create_chunks(parsed_doc):
    """
    Takes a ParsedDocument and returns a list of ProcessedChunks.

    Strategy:
    ─────────
    If the parser detected headings:
        Group paragraphs under each heading → chunk each group separately
        This means "Leave Policy" paragraphs stay together,
        "Working Hours" paragraphs stay together, etc.

    If no headings detected:
        Treat the full text as one group → sentence-based chunking

    Each chunk gets:
        - content: the actual text
        - section_title: which heading it belongs to
        - page_number: which page (for PDFs)
        - keywords: auto-extracted important terms
        - chunk_index: sequential order in document
    """
    has_headings = any(s.section_type == "heading" for s in parsed_doc.sections)

    if has_headings:
        logger.info("Using SECTION-AWARE chunking (headings found)")
        chunks = _chunk_by_sections(parsed_doc)
    else:
        logger.info("Using SENTENCE-BASED chunking (no headings)")
        sentences = _split_sentences(parsed_doc.full_text)
        chunks = _merge_sentences(sentences, heading=None, page_number=1)

    # Assign sequential index and source metadata
    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i
        chunk.metadata["source"] = parsed_doc.title
        chunk.metadata["total_chunks"] = len(chunks)

    logger.info(
        f"Created {len(chunks)} chunks from '{parsed_doc.title}' "
        f"(avg {_avg_chars(chunks)} chars/chunk)"
    )
    return chunks


def _chunk_by_sections(parsed_doc):
    """Group sections by heading, then chunk each group."""
    # Step 1: Group consecutive paragraphs under same heading
    groups = []  # each group = (heading, page_number, [text, text, ...])
    current_heading = None
    current_page = None
    current_texts = []

    for section in parsed_doc.sections:
        if section.section_type == "heading":
            # Save previous group
            if current_texts:
                groups.append((current_heading, current_page, current_texts))
            current_heading = section.heading
            current_page = section.page_number
            current_texts = []
        else:
            current_texts.append(section.content)
            if section.page_number:
                current_page = section.page_number

    # Save last group
    if current_texts:
        groups.append((current_heading, current_page, current_texts))

    # If somehow no groups were created, use full text
    if not groups and parsed_doc.full_text:
        groups.append((None, 1, [parsed_doc.full_text]))

    # Step 2: Chunk each group into sentences → merged chunks
    all_chunks = []
    for heading, page, texts in groups:
        combined = " ".join(texts)
        sentences = _split_sentences(combined)
        if sentences:
            group_chunks = _merge_sentences(sentences, heading, page)
            all_chunks.extend(group_chunks)

    return all_chunks


def _avg_chars(chunks):
    """Average character count across chunks."""
    if not chunks:
        return 0
    return sum(len(c.content) for c in chunks) // len(chunks)