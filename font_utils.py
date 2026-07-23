import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FONT_DIR = os.path.join(BASE_DIR, "static", "fonts")
SUPPORTED_WEB_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
BUILT_IN_WEB_FONTS = ("Poppins", "Arial", "Times New Roman", "Verdana", "Georgia")


def font_display_name(filename):
    name = os.path.splitext(filename)[0].replace("_", " ")
    if name == "NotoSansTamil-VariableFont wdth,wght":
        return "Noto Sans Tamil"
    return name


def available_web_fonts():
    fonts = [{"name": name, "filename": None} for name in BUILT_IN_WEB_FONTS]
    if not os.path.isdir(FONT_DIR):
        return fonts

    names = {font["name"].casefold() for font in fonts}
    for filename in sorted(os.listdir(FONT_DIR)):
        _, extension = os.path.splitext(filename)
        if extension.lower() not in SUPPORTED_WEB_FONT_EXTENSIONS:
            continue
        name = font_display_name(filename)
        if name.casefold() in names:
            continue
        fonts.append({"name": name, "filename": filename})
        names.add(name.casefold())
    return fonts


def valid_web_font_name(value, default="Poppins"):
    requested = (value or "").strip()
    names = {font["name"].casefold(): font["name"] for font in available_web_fonts()}
    return names.get(requested.casefold(), default)
