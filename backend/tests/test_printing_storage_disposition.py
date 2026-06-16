import pytest

from apps.printing.storage import _download_disposition


def assert_attachment_header(header):
    assert isinstance(header, str)
    assert header.startswith("attachment")


def test_download_disposition_uses_normal_filename():
    header = _download_disposition("part.3mf", "model/3mf")

    assert_attachment_header(header)
    assert "part.3mf" in header


@pytest.mark.parametrize(
    ("filename", "basename"),
    [
        ("../../etc/passwd", "passwd"),
        ("C:\\Windows\\evil.stl", "evil.stl"),
    ],
)
def test_download_disposition_keeps_only_basename(filename, basename):
    header = _download_disposition(filename, "model/stl")

    assert_attachment_header(header)
    assert basename in header
    assert "/" not in header
    assert "\\" not in header


def test_download_disposition_strips_unsafe_control_chars_and_quote():
    header = _download_disposition('a"b\r\n.stl', "model/stl")

    assert_attachment_header(header)
    assert "\r" not in header
    assert "\n" not in header
    assert 'a"b' not in header
    assert "ab.stl" in header


@pytest.mark.parametrize(
    ("filename", "content_type", "download_name"),
    [
        ("", "model/stl", "download.stl"),
        ("", "not/a-real-type", "download"),
    ],
)
def test_download_disposition_falls_back_to_download_name(
    filename,
    content_type,
    download_name,
):
    header = _download_disposition(filename, content_type)

    assert_attachment_header(header)
    assert download_name in header
