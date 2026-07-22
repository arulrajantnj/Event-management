from pathlib import Path

import freetype

from certificate_generator import font_path_by_family


def test_noto_sans_tamil_uses_bundled_unicode_font():
    font_path = Path(font_path_by_family("Noto Sans Tamil"))

    assert font_path.name == "NotoSansTamil-VariableFont_wdth,wght.ttf"
    assert font_path.is_file()

    face = freetype.Face(str(font_path))
    assert all(face.get_char_index(ord(character)) for character in "தமிழ்")
