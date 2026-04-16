"""Prefer LaTeX/Markdown sources over rendered PDFs.

Rationale (`context_is_all_you_need.md`): feeding LLMs raw source lets them
read by section (abstract / method) rather than drowning in 30+ page PDFs.
Keep this helper tiny — it is a URL rewriter, not a fetcher.
"""
from __future__ import annotations
import re

_ARXIV_PDF = re.compile(
    r"^https?://arxiv\.org/pdf/(?P<id>[\w.\-/]+?)(?:\.pdf)?/?$",
    re.IGNORECASE,
)
_ARXIV_ABS = re.compile(
    r"^https?://arxiv\.org/abs/(?P<id>[\w.\-/]+?)/?$",
    re.IGNORECASE,
)


def is_pdf_url(url: str) -> bool:
    """Return True for URLs that obviously point at a PDF."""
    u = url.lower()
    return u.endswith(".pdf") or "/pdf/" in u


def prefer_source_url(url: str) -> str:
    """Map known PDF/abs URLs to source-form URLs when possible.

    Known rewrites:
      - arxiv.org/pdf/<id>[.pdf]       -> arxiv.org/e-print/<id>
      - arxiv.org/abs/<id>             -> arxiv.org/e-print/<id>

    Unknown URLs are returned unchanged.
    """
    m = _ARXIV_PDF.match(url) or _ARXIV_ABS.match(url)
    if m:
        return f"https://arxiv.org/e-print/{m.group('id')}"
    return url
