from unittest.mock import patch, MagicMock
from tao.scouts.gemini import GeminiScout, ScoutQuery


def test_scout_query_expands_to_multiple_angles():
    q = ScoutQuery(topic="efficient fine-tuning", constraints=[])
    assert len(q.expand()) >= 3


def test_scout_query_appends_constraints():
    q = ScoutQuery(topic="LoRA", constraints=["has code", "top venue"])
    angles = q.expand()
    assert all("[has code, top venue]" in a for a in angles)


def test_scout_unavailable_returns_empty(tmp_path):
    scout = GeminiScout(bin_path="/nonexistent/bin/gemini-xyz-missing")
    assert scout.available() is False
    assert scout.search("topic") == []


def test_scout_parses_json_from_cli():
    scout = GeminiScout(bin_path="gemini")
    fake = MagicMock(stdout='{"papers":[{"title":"X","url":"https://arxiv.org/abs/1"}]}', returncode=0, stderr="")
    with patch("tao.scouts.gemini.shutil.which", return_value="/usr/bin/gemini"), \
         patch("tao.scouts.gemini.subprocess.run", return_value=fake):
        papers = scout.search("efficient fine-tuning", constraints=["has code"])
    assert len(papers) == 1
    assert papers[0]["title"] == "X"


def test_scout_nonzero_returncode_returns_empty():
    scout = GeminiScout(bin_path="gemini")
    fake = MagicMock(stdout="", returncode=2, stderr="auth failed")
    with patch("tao.scouts.gemini.shutil.which", return_value="/usr/bin/gemini"), \
         patch("tao.scouts.gemini.subprocess.run", return_value=fake):
        assert scout.search("topic") == []


def test_scout_invalid_json_returns_empty():
    scout = GeminiScout(bin_path="gemini")
    fake = MagicMock(stdout="not json", returncode=0, stderr="")
    with patch("tao.scouts.gemini.shutil.which", return_value="/usr/bin/gemini"), \
         patch("tao.scouts.gemini.subprocess.run", return_value=fake):
        assert scout.search("topic") == []


def test_scout_timeout_returns_empty():
    import subprocess as sp
    scout = GeminiScout(bin_path="gemini", timeout_sec=1)
    with patch("tao.scouts.gemini.shutil.which", return_value="/usr/bin/gemini"), \
         patch("tao.scouts.gemini.subprocess.run",
               side_effect=sp.TimeoutExpired(cmd="gemini", timeout=1)):
        assert scout.search("topic") == []


def test_scout_filters_non_dict_papers():
    scout = GeminiScout(bin_path="gemini")
    fake = MagicMock(
        stdout='{"papers":["oops", {"title":"Good","url":"u"}, 42]}',
        returncode=0, stderr="",
    )
    with patch("tao.scouts.gemini.shutil.which", return_value="/usr/bin/gemini"), \
         patch("tao.scouts.gemini.subprocess.run", return_value=fake):
        papers = scout.search("topic")
    assert papers == [{"title": "Good", "url": "u"}]
