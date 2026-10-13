"""
theme.py: the look of every artefact WDS renders. Part of WDS (agents/wds/tools/theme.md).

neutral.css is the default. The client's brand overrides it with tokens.css, found by walking up
from the folder being rendered, stopping at the repo root. At each level it looks for
brand/design-system/tokens.css, then brand/visual-identity/tokens.css, then visual-identity/tokens.css
(older repos). The nearest one wins.
"""

import re
from pathlib import Path

HERE = Path(__file__).parent
IMPORT = r"""@import\s+(?:url\([^)]*\)|"[^"]*"|'[^']*')[^;]*;"""  # a font URL may itself contain ";"
CANDIDATES = ("brand/design-system/tokens.css", "brand/visual-identity/tokens.css", "visual-identity/tokens.css")


def find_tokens(folder):
    folder = Path(folder).resolve()
    for level in [folder, *folder.parents]:
        for c in CANDIDATES:
            if (level / c).exists():
                return level / c
        if (level / ".git").exists():
            return None
    return None


class Theme:
    """values: the --wds-* roles resolved to plain values (for SVG). imports and css: for HTML pages."""

    def __init__(self, folder, override=None):
        self.tokens = Path(override) if override else find_tokens(folder)
        files = [HERE / "neutral.css"] + ([self.tokens] if self.tokens else [])
        css = "\n".join(f.read_text(encoding="utf-8") for f in files)
        props = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", css))

        def resolve(v, depth=0):
            if depth > 10:
                return v
            return re.sub(r"var\((--[\w-]+)(?:\s*,\s*([^)]+))?\)",
                          lambda m: resolve(props.get(m.group(1), m.group(2) or ""), depth + 1), v).strip()

        self.values = {k: resolve(v) for k, v in props.items() if k.startswith("--wds-")}
        self.imports = "\n".join(re.findall(IMPORT, css))
        self.css = re.sub(IMPORT, "", css)

    def get(self, key, default=""):
        return self.values.get(key, default)

    def describe(self):
        return f"neutral + {self.tokens}" if self.tokens else "neutral (no brand tokens.css found)"

    def style(self, page_css=""):
        """A <style> block for an HTML page: the font imports first, then the theme, then the page's own CSS."""
        return f"<style>{self.imports}\n{self.css}\n{page_css}</style>"
