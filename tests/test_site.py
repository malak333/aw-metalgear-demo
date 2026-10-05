"""Compact in-process checks for the Metal Gear Solid fan overview."""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
HTML = BASE / "index.html"
CSS = BASE / "styles.css"
README = BASE / "DEMO-README.md"


class _Parser(HTMLParser):
    """Collect IDs, fragments, resource refs, and structural signals from HTML."""

    def __init__(self):
        super().__init__()
        self.ids: list[str] = []
        self.fragments: list[str] = []
        self.local_refs: list[str] = []
        self.external_refs: list[str] = []
        self.external_scripts: list[str] = []
        self.has_form: bool = False
        self.has_iframe: bool = False
        self.css_url_refs: list[str] = []
        self.css_imports: list[str] = []
        self.tag_names: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tag_names.append(tag)
        d = dict(attrs)
        # Collect ALL id attributes from every tag
        if d.get("id"):
            self.ids.append(d["id"])
        # Collect href from all tags
        if "href" in d and d["href"]:
            href = d["href"]
            if href.startswith("#"):
                self.fragments.append(href[1:])
            elif re.match(r"^https?://|^//", href):
                self.external_refs.append(href)
            elif href:
                self.local_refs.append(href)
        # Collect src from all tags (img, script, source, video, audio, etc.)
        if "src" in d and d["src"]:
            src = d["src"]
            if re.match(r"^https?://|^//", src):
                self.external_scripts.append(src)
            elif src:
                self.local_refs.append(src)
        # Collect poster from <img> tags
        if "poster" in d and d["poster"]:
            self.local_refs.append(d["poster"])
        # Collect srcset candidate URLs from all tags
        if "srcset" in d and d["srcset"]:
            for candidate in d["srcset"].split(","):
                url = candidate.strip().split()[0] if candidate.strip() else ""
                if url:
                    self.local_refs.append(url)
        if tag == "script" and d.get("src"):
            self.external_scripts.append(d["src"])
        if tag == "form":
            self.has_form = True
        if tag == "iframe":
            self.has_iframe = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        lower = data.lower()
        if "url(" in lower:
            self.css_url_refs.append(data)
        if "@import" in lower:
            self.css_imports.append(data)


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _css() -> str:
    return CSS.read_text(encoding="utf-8")


def _is_safe_relative_path(ref: str) -> bool:
    """Return False if ref is absolute, external, uses scheme/drive/escape."""
    if not ref:
        return False
    # Reject anchor-only refs (handled separately)
    if ref.startswith("#"):
        return False
    # Reject leading / or //
    if ref.startswith("/") and not ref.startswith("//"):
        return False
    if ref.startswith("//"):
        return False
    # Reject URI schemes (protocol:) and Windows drive letters (X:)
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", ref):
        return False
    # Reject backslashes
    if "\\" in ref:
        return False
    # Reject path traversal escapes
    if ".." in ref.split("/"):
        return False
    return True


# ── Deliverables ──────────────────────────────────────────────


class TestFilesExist(unittest.TestCase):
    def test_all_files_present(self):
        self.assertTrue(HTML.is_file(), "index.html missing")
        self.assertTrue(CSS.is_file(), "styles.css missing")
        self.assertTrue(README.is_file(), "DEMO-README.md missing")


# ── Content ───────────────────────────────────────────────────


class TestContent(unittest.TestCase):
    def setUp(self):
        self.html = _html()

    def test_developer_and_location(self):
        self.assertIn("Konami Computer Entertainment Japan", self.html)
        self.assertIn("Shadow Moses", self.html)

    def test_otacon_role(self):
        self.assertIn("engineer", self.html.lower())
        self.assertIn("shadow moses", self.html.lower())

    def test_no_prohibited_content(self):
        forbidden = ("clone", "genetic", "genetically", "s3 project")
        for word in forbidden:
            self.assertNotIn(word, self.html.lower(), f"'{word}' must not appear")
        css = _css()
        self.assertNotIn("url(", css, "No CSS url() references allowed")
        self.assertNotIn("@import", css, "No CSS @import statements allowed")


# ── Structure ─────────────────────────────────────────────────


class TestStructure(unittest.TestCase):
    def setUp(self):
        self.p = _Parser()
        self.p.feed(_html())

    def test_required_sections(self):
        # Semantic elements
        self.assertIn("header", self.p.tag_names, "Must have <header>")
        self.assertIn("main", self.p.tag_names, "Must have <main>")
        self.assertIn("nav", self.p.tag_names, "Must have <nav>")
        self.assertIn("footer", self.p.tag_names, "Must have <footer>")
        # Section IDs
        for sid in ("introduction", "mission", "characters", "stealth", "legacy"):
            self.assertIn(sid, self.p.ids, f"section id={sid} must exist")
        # Content assertions
        html = _html()
        self.assertIn("1998", html, "Must reference 1998 PlayStation")
        self.assertIn("PlayStation", html, "Must reference PlayStation")
        self.assertIn("Snake", html, "Must mention Snake")
        self.assertIn("infiltrate", html.lower(), "Must state Snake infiltrates")
        self.assertIn("Liquid", html, "Must mention Liquid Snake")
        self.assertIn("FOXHOUND", html, "Must mention FOXHOUND")
        self.assertIn("Otacon", html, "Must mention Otacon")
        self.assertIn("engineer", html.lower(), "Otacon must be engineer")
        self.assertIn("radar", html.lower(), "Must mention radar")
        self.assertIn("alert", html.lower(), "Must mention alert state")
        self.assertIn("codec", html.lower(), "Must mention Codec")

    def test_unique_ids(self):
        self.assertEqual(len(self.p.ids), len(set(self.p.ids)), "IDs must be unique")

    def test_fragments_resolve(self):
        for frag in self.p.fragments:
            self.assertIn(frag, self.p.ids, f"Anchor #{frag} must resolve")

    def test_no_external_resources(self):
        self.assertEqual(self.p.external_refs, [], "No external URLs allowed")
        self.assertFalse(self.p.has_iframe, "No iframes allowed")
        self.assertEqual(self.p.external_scripts, [], "No external scripts allowed")
        # Check ALL local references for safety
        for ref in self.p.local_refs:
            self.assertTrue(
                _is_safe_relative_path(ref),
                f"Reference must be safe relative path, got: {ref}",
            )
        # Verify every local ref resolves to an existing file under BASE
        for ref in self.p.local_refs:
            if not ref.startswith("#"):
                try:
                    resolved = (BASE / ref).resolve()
                    resolved.relative_to(BASE.resolve())
                    self.assertTrue(
                        resolved.is_file(),
                        f"Local reference {ref!r} must resolve to existing file under {BASE}",
                    )
                except ValueError:
                    self.fail(
                        f"Reference {ref!r} escapes BASE directory {BASE}"
                    )


# ── CSS ───────────────────────────────────────────────────────


class TestCSS(unittest.TestCase):
    def setUp(self):
        self.css = _css()

    def test_responsive_and_reduced_motion(self):
        self.assertIn("@media", self.css, "Must include media queries")
        self.assertIn("prefers-reduced-motion", self.css, "Must handle reduced motion")

    def test_focus_styling(self):
        self.assertTrue(":focus" in self.css, "Focus styling required")


# ── Integrity ─────────────────────────────────────────────────


class TestIntegrity(unittest.TestCase):
    def test_local_stylesheet(self):
        html = _html()
        self.assertIn(
            'href="styles.css"', html,
            "Must link styles.css via relative path",
        )
        # Parse full HTML to verify all local resource refs resolve
        p = _Parser()
        p.feed(html)
        for ref in p.local_refs:
            if not ref.startswith("#"):
                try:
                    resolved = (BASE / ref).resolve()
                    resolved.relative_to(BASE.resolve())
                    self.assertTrue(
                        resolved.is_file(),
                        f"Local reference {ref!r} must resolve to existing file under {BASE}",
                    )
                except ValueError:
                    self.fail(
                        f"Reference {ref!r} escapes BASE directory {BASE}"
                    )

    def test_no_forms(self):
        p = _Parser()
        p.feed(_html())
        self.assertFalse(p.has_form, "No forms permitted")
