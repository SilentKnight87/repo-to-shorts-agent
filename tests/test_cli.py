from repo_to_shorts.cli import _slug


def test_slug_normalizes_text():
    assert _slug("Repo To Shorts!!!") == "repo-to-shorts"
