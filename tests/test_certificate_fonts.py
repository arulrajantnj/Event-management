from pathlib import Path

import freetype

from certificate_generator import font_path_by_family, shape_text


def test_noto_sans_tamil_uses_bundled_unicode_font():
    font_path = Path(font_path_by_family("Noto Sans Tamil"))

    assert font_path.name == "NotoSansTamil-VariableFont_wdth,wght.ttf"
    assert font_path.is_file()

    face = freetype.Face(str(font_path))
    assert all(face.get_char_index(ord(character)) for character in "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd")


def test_uppercase_tamil_font_extension_is_found_and_shaped():
    assert Path(font_path_by_family("TAU ANJN")).name == "TAU_ANJN.TTF"

    shaped = shape_text("\u0ba4\u0bae\u0bbf\u0bb4\u0bcd", "TAU ANJN", 36)
    assert shaped is not None
    assert len({info.codepoint for info in shaped[1]}) > 1
