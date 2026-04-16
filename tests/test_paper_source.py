from tao.paper_source import is_pdf_url, prefer_source_url


def test_is_pdf_url_detects_pdf_suffix():
    assert is_pdf_url("https://foo.com/bar.pdf")


def test_is_pdf_url_detects_pdf_path_segment():
    assert is_pdf_url("https://arxiv.org/pdf/2401.12345")


def test_is_pdf_url_html_is_not_pdf():
    assert not is_pdf_url("https://foo.com/bar.html")


def test_prefer_source_rewrites_arxiv_pdf():
    assert prefer_source_url("https://arxiv.org/pdf/2401.12345v2") == "https://arxiv.org/e-print/2401.12345v2"


def test_prefer_source_rewrites_arxiv_pdf_with_suffix():
    assert prefer_source_url("https://arxiv.org/pdf/2401.12345v2.pdf") == "https://arxiv.org/e-print/2401.12345v2"


def test_prefer_source_rewrites_arxiv_abs():
    assert prefer_source_url("https://arxiv.org/abs/2401.12345") == "https://arxiv.org/e-print/2401.12345"


def test_prefer_source_preserves_subcategory_id():
    # Legacy arXiv ID format with slash (e.g. cs.CL/0501001)
    assert prefer_source_url("https://arxiv.org/abs/cs.CL/0501001") == "https://arxiv.org/e-print/cs.CL/0501001"


def test_prefer_source_unknown_url_passthrough():
    url = "https://example.com/paper.pdf"
    assert prefer_source_url(url) == url
