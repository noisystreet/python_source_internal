"""Fix RST title underline too short warnings.

Sphinx requires the underline (--- or ===) to be at least as long as the title text.
This script finds all underlines that are too short and extends them.
"""

import re
import os

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")


def display_width(text: str) -> int:
    """Calculate display width, counting CJK characters as 2."""
    width = 0
    for ch in text:
        if ord(ch) > 0x2e80:  # CJK range start
            width += 2
        else:
            width += 1
    return width


def fix_underlines(content: str) -> str:
    """Extend title underlines that are shorter than the title text."""
    lines = content.split("\n")
    result = []
    for i, line in enumerate(lines):
        # Check if next line is an underline (--- or ===)
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            # Title underline must be --- or === (with optional trailing whitespace)
            if re.match(r'^[-=]+$', next_line.strip()):
                title = line.strip()
                uline = next_line.rstrip()
                if display_width(title) > len(uline):
                    # Extend underline to match title display width
                    char = uline[0]  # preserve - or =
                    lines[i + 1] = char * display_width(title)
    return "\n".join(lines)


def main() -> None:
    fixed = 0
    for root, dirs, files in os.walk(DOCS):
        # Skip _build
        dirs[:] = [d for d in dirs if d != '_build']
        for f in files:
            if not f.endswith('.rst'):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                orig = fh.read()
            fixed_content = fix_underlines(orig)
            if fixed_content != orig:
                with open(path, 'w') as fh:
                    fh.write(fixed_content)
                fixed += 1
                print(f"  FIXED: {os.path.relpath(path, DOCS)}")
    
    print(f"\nFixed {fixed} files.")


if __name__ == "__main__":
    main()
