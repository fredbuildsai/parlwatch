from pathlib import Path

from parlwatch.countries.fr.media import decode_srt, parse_nvs, parse_page, parse_uid

FIX = Path(__file__).parent / "fixtures"


def test_parse_uid():
    assert parse_uid("https://videos.assemblee-nationale.fr/video.19502241_6ac548b948b27.slug") == "19502241_6ac548b948b27"


def test_parse_page():
    p = parse_page((FIX / "an_video_page.html").read_text())
    assert p["caption_url"].endswith("/Datas/an/19502241_6ac548b948b27/files/hemi_20261006211505_1.srt")
    assert p["report_url"].endswith("CRSANR5L17S2027O1N010")
    assert "violences sexuelles" in p["title"]


def test_parse_nvs():
    audio, hls, chapters, speakers = parse_nvs((FIX / "an_data.nvs").read_text())
    assert audio == "http://anorigin.vodalys.com/vod/mp4/ida/domain1/2026/10/hemi_20261006211505.mp3"
    assert hls.endswith("2026/10/hemi_20261006211505_1.mp4/master.m3u8")
    assert len(chapters) == 26 or len(chapters) > 20
    assert speakers["19502264"].name == "M. Sébastien Chenu"
    assert speakers["19502264"].deputy_id == "720468"


def test_decode_srt_latin1():
    assert "Présidence" in decode_srt((FIX / "an_sample.srt").read_bytes())
