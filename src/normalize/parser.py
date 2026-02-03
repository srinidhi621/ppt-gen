"""Markdown to ContentModel parser.

Parses structured Markdown content into ContentModel with stable section IDs.
Supports metadata comments for layout hints and section IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.content import ContentCue, ContentModel, ContentSection


def _compute_hash(content: str) -> str:
    """Compute a stable hash of the content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _generate_section_id(title: str, index: int) -> str:
    """Generate a stable section ID from title."""
    # Normalize title to create a slug
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower().strip())
    slug = slug.strip("_")
    if not slug:
        slug = f"section_{index}"
    return slug


def _extract_metadata_comment(line: str) -> Optional[Tuple[str, str]]:
    """Extract key-value from HTML comment metadata.
    
    Supports format: <!-- key: value -->
    """
    match = re.match(r"<!--\s*(\w+)\s*:\s*(.+?)\s*-->", line.strip())
    if match:
        return match.group(1), match.group(2)
    return None


def _parse_bullet(line: str) -> Optional[str]:
    """Parse a bullet line, returning the content or None."""
    match = re.match(r"^\s*[-*+]\s+(.+)$", line)
    if match:
        return match.group(1).strip()
    return None


def _is_section_separator(line: str) -> bool:
    """Check if line is a section separator (---)."""
    return line.strip() == "---"


def _parse_heading(line: str) -> Optional[Tuple[int, str]]:
    """Parse a heading line, returning (level, title) or None."""
    match = re.match(r"^(#{1,6})\s+(.+)$", line)
    if match:
        return len(match.group(1)), match.group(2).strip()
    return None


def parse_markdown(path: Path, cues_path: Optional[Path] = None) -> ContentModel:
    """Parse Markdown into ContentModel with stable section IDs.
    
    The parser recognizes:
    - Section separators (---)
    - HTML comment metadata (<!-- section_id: xxx --> <!-- layout_hint: xxx -->)
    - Headings (# ## ###)
    - Bullet lists (- * +)
    - Plain paragraphs
    
    Args:
        path: Path to content.md file
        cues_path: Optional path to cues.json for visualization hints
        
    Returns:
        ContentModel with stable IDs and source hash
    """
    content = path.read_text(encoding="utf-8")
    source_hash = _compute_hash(content)
    lines = content.split("\n")
    
    sections: List[ContentSection] = []
    current_section: Optional[Dict[str, Any]] = None
    metadata: Dict[str, str] = {}
    doc_title = ""
    doc_subtitle = ""
    section_index = 0
    
    def finalize_section():
        nonlocal current_section, metadata, section_index
        if current_section is None:
            return
        
        # Determine section_id from metadata or generate from title
        section_id = metadata.get("section_id")
        if not section_id:
            section_id = _generate_section_id(current_section["title"], section_index)
        
        sections.append(ContentSection(
            section_id=section_id,
            title=current_section["title"],
            bullets=current_section.get("bullets", []),
            paragraphs=current_section.get("paragraphs", []),
        ))
        current_section = None
        metadata = {}
        section_index += 1
    
    # Track if we just saw a separator (expect new section)
    expecting_new_section = False
    
    for line in lines:
        stripped = line.strip()
        
        # Check for metadata comment
        meta = _extract_metadata_comment(stripped)
        if meta:
            metadata[meta[0]] = meta[1]
            continue
        
        # Check for section separator
        if _is_section_separator(stripped):
            finalize_section()
            expecting_new_section = True
            continue
        
        # Check for heading
        heading = _parse_heading(stripped)
        if heading:
            level, title = heading
            if level == 1 and not doc_title:
                # First H1 is document title
                doc_title = title
                continue
            elif level == 2 and not doc_subtitle and not sections and not current_section and not expecting_new_section:
                # H2 right after H1 might be subtitle (but not after separator)
                doc_subtitle = title
                continue
            else:
                # New section or subsection
                if current_section and level <= 2:
                    finalize_section()
                
                if current_section is None:
                    current_section = {"title": title, "bullets": [], "paragraphs": []}
                    expecting_new_section = False
                else:
                    # Subsection - add as a heading bullet
                    current_section["bullets"].append(f"**{title}**")
                continue
        
        # Check for bullet
        bullet = _parse_bullet(stripped)
        if bullet:
            if current_section is None:
                current_section = {"title": "Untitled", "bullets": [], "paragraphs": []}
                expecting_new_section = False
            current_section["bullets"].append(bullet)
            continue
        
        # Plain text paragraph
        if stripped:
            if current_section is None:
                # Start a new section for orphan paragraph
                current_section = {"title": "Content", "bullets": [], "paragraphs": []}
                expecting_new_section = False
            current_section["paragraphs"].append(stripped)
    
    # Finalize last section
    finalize_section()
    
    # Load cues if available
    cues: List[ContentCue] = []
    if cues_path and cues_path.exists():
        cues_data = json.loads(cues_path.read_text(encoding="utf-8"))
        for cue in cues_data.get("cues", []):
            cues.append(ContentCue(
                section_id=cue.get("section_id", ""),
                layout_hint=cue.get("layout_hint"),
                notes=cue.get("notes"),
                icon_hints=cue.get("icon_hints", []),
                image_hint=cue.get("image_hint"),
            ))
    
    # Generate doc_id from path or title
    doc_id = path.stem if path else "untitled"
    
    return ContentModel(
        doc_id=doc_id,
        version="1.0",
        source_hash=source_hash,
        sections=sections,
        cues=cues,
    )


def parse_markdown_string(content: str, doc_id: str = "inline") -> ContentModel:
    """Parse Markdown string directly into ContentModel.
    
    Convenience function for testing or programmatic use.
    """
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)
    
    try:
        model = parse_markdown(temp_path)
        # Override doc_id
        return ContentModel(
            doc_id=doc_id,
            version=model.version,
            source_hash=model.source_hash,
            sections=model.sections,
            cues=model.cues,
        )
    finally:
        temp_path.unlink()
