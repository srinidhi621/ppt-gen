#!/usr/bin/env python3
"""
Convert SVG icons to PNG format for use in PowerPoint generation.

This script:
1. Reads all SVG files from the source directory
2. Converts them to high-resolution PNG (512x512 with transparent background)
3. Saves them with a clean, referenceable naming scheme
4. Generates an icons.json metadata file for the pipeline

Output naming convention:
    icon_001.png, icon_002.png, etc. (for easy sorting and reference)
    
The icons.json maps icon_id to the original filename for traceability.

Usage (macOS with Homebrew cairo):
    DYLD_LIBRARY_PATH=/opt/homebrew/lib python scripts/convert_svg_to_png.py
"""

import os
import sys
import json
import re
from pathlib import Path
import cairosvg

# Configuration
DEFAULT_OUTPUT_SIZE = 512  # pixels (square)


def extract_icon_number(filename: str) -> int:
    """Extract the numeric ID from an icon filename like 'Ascendion_P_Icon_123.svg'"""
    match = re.search(r'Icon_(\d+)\.svg$', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def convert_svg_to_png(svg_path: Path, png_path: Path, output_size: int = DEFAULT_OUTPUT_SIZE) -> bool:
    """
    Convert a single SVG file to PNG using cairosvg.
    
    Args:
        svg_path: Path to source SVG file
        png_path: Path for output PNG file
        output_size: Target size in pixels (square)
        
    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        # Read SVG content
        with open(svg_path, 'rb') as f:
            svg_content = f.read()
        
        # Convert to PNG with cairosvg
        # output_width and output_height ensure consistent sizing
        cairosvg.svg2png(
            bytestring=svg_content,
            write_to=str(png_path),
            output_width=output_size,
            output_height=output_size,
            background_color=None  # Transparent background
        )
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error converting {svg_path.name}: {e}")
        return False


def main():
    # Paths
    base_path = Path(__file__).parent.parent
    
    svg_source_dir = base_path / "Assets" / "Icons and Dimensional Keywords" / "2025 New Icons"
    png_output_dir = base_path / "assets" / "icons" / "png"
    icons_json_path = base_path / "assets" / "icons" / "icons.json"
    
    # Ensure output directory exists
    png_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all SVG files
    svg_files = sorted(svg_source_dir.glob("*.svg"), key=lambda f: extract_icon_number(f.name))
    
    if not svg_files:
        print(f"❌ No SVG files found in: {svg_source_dir}")
        sys.exit(1)
    
    print(f"Found {len(svg_files)} SVG icons to convert")
    print(f"Output directory: {png_output_dir}")
    print(f"Output size: {DEFAULT_OUTPUT_SIZE}x{DEFAULT_OUTPUT_SIZE} pixels")
    print("-" * 60)
    
    # Track conversions for metadata
    icons_metadata = {
        "version": "1.0",
        "source": "2025 New Icons (SVG)",
        "output_size_px": DEFAULT_OUTPUT_SIZE,
        "icons": []
    }
    
    success_count = 0
    fail_count = 0
    
    for svg_file in svg_files:
        # Extract original icon number
        icon_num = extract_icon_number(svg_file.name)
        
        # Create standardized output filename
        # Using zero-padded numbers for proper sorting: icon_001.png
        icon_id = f"icon_{icon_num:03d}"
        png_filename = f"{icon_id}.png"
        png_path = png_output_dir / png_filename
        
        print(f"  Converting: {svg_file.name} → {png_filename}", end=" ")
        
        if convert_svg_to_png(svg_file, png_path):
            print("✓")
            success_count += 1
            
            # Add to metadata
            icons_metadata["icons"].append({
                "icon_id": icon_id,
                "filename": png_filename,
                "original_svg": svg_file.name,
                "original_number": icon_num,
                "tags": [],  # To be filled in later with semantic tags
                "synonyms": []  # For LLM icon selection
            })
        else:
            fail_count += 1
    
    print("-" * 60)
    print(f"Conversion complete: {success_count} succeeded, {fail_count} failed")
    
    # Sort icons by ID
    icons_metadata["icons"].sort(key=lambda x: x["original_number"])
    icons_metadata["total_count"] = len(icons_metadata["icons"])
    
    # Write icons.json metadata file
    icons_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(icons_json_path, 'w') as f:
        json.dump(icons_metadata, f, indent=2)
    
    print(f"✓ Icons metadata saved to: {icons_json_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"PNG icons location:  {png_output_dir}")
    print(f"Icons metadata:      {icons_json_path}")
    print(f"Total icons:         {icons_metadata['total_count']}")
    print(f"Icon ID format:      icon_NNN (e.g., icon_001, icon_042)")
    print("\nNote: The 'tags' and 'synonyms' fields in icons.json are empty.")
    print("These should be populated later with semantic descriptions")
    print("to enable LLM-based icon selection.")


if __name__ == "__main__":
    main()
