"""Fix RST inline markup followed by CJK punctuation.

Docutils doesn't recognize CJK fullwidth punctuation (（ ） 、 。 ）
as valid inline markup end delimiters, causing "Inline literal start-string
without end-string" warnings.
"""

import os
import re

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")

# CJK punctuation that's not a valid RST end delimiter
CJK_PUNCT = set("（）、。．：；？！【】《》「」『』")


def fix_inline_markup(content: str) -> str:
    """Add a space between inline markup end and CJK punctuation.

    Patterns fixed:
    - ``code``（  → ``code`` （
    - ``code``、  → ``code`` 、
    - **bold**（  → **bold** （
    - single backtick patterns similar
    """
    lines = content.split("\n")
    result = []

    for line in lines:
        # Fix double-backtick literal followed by CJK punct
        # Pattern: closing `` then CJK
        line = re.sub(r'``([^`]+)``([' + ''.join(CJK_PUNCT) + r'])', r'``\1`` \2', line)

        # Fix strong emphasis **text** followed by CJK punct
        line = re.sub(r'\*\*([^*]+)\*\*([' + ''.join(CJK_PUNCT) + r'])', r'**\1** \2', line)

        result.append(line)

    return "\n".join(result)


def main():
    fixed = 0
    for root, dirs, files in os.walk(DOCS):
        dirs[:] = [d for d in dirs if d != '_build']
        for f in files:
            if not f.endswith('.rst'):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                orig = fh.read()
            new_content = fix_inline_markup(orig)
            if new_content != orig:
                with open(path, 'w') as fh:
                    fh.write(new_content)
                fixed += 1
    return fixed


if __name__ == "__main__":
    count = main()
    print(f"Fixed {count} files.")
