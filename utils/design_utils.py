from dataclasses import dataclass

@dataclass
class ColorPalette:
    PRIMARY: str = "#935073"        # Plum - for navbars, highlights
    BACKGROUND: str = "#efefef"     # Light gray - background
    BUTTON: str = "#bfee90"         # Lime green - for buttons
    BUTTON_TEXT: str = "#ffffff"    # White - button text
    TEXT_HEADING: str = "#000000"   # Black - headings
    TEXT_BODY: str = "#555555"      # Dark gray - secondary text
    TEXT_HIGHLIGHT: str = "#935073" # Plum - for highlighted text

@dataclass
class FontStyle:
    PRIMARY_FONT: str = "Segoe UI, sans-serif"
    HEADING_SIZE: str = "24px"
    BODY_SIZE: str = "16px"
    SMALL_SIZE: str = "14px"
    FONT_WEIGHT_BOLD: str = "bold"
    FONT_WEIGHT_NORMAL: str = "normal"

@dataclass
class ButtonStyle:
    BACKGROUND: str = ColorPalette.BUTTON
    TEXT_COLOR: str = ColorPalette.BUTTON_TEXT
    BORDER_RADIUS: str = "6px"
    PADDING: str = "10px 20px"
    FONT: str = FontStyle.PRIMARY_FONT
    FONT_SIZE: str = FontStyle.BODY_SIZE
    HOVER_EFFECT: str = "filter: brightness(0.95);"


def get_styles():
    return {
        "colors": ColorPalette(),
        "fonts": FontStyle(),
        "buttons": ButtonStyle(),
    }


def inject_global_styles():
    styles = get_styles()
    colors = styles["colors"]
    fonts = styles["fonts"]
    buttons = styles["buttons"]

    style_block = f"""
    <style>
        body {{
            background-color: {colors.BACKGROUND};
            font-family: {fonts.PRIMARY_FONT};
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: {colors.TEXT_HEADING};
            font-weight: {fonts.FONT_WEIGHT_BOLD};
        }}

        p, span, div {{
            color: {colors.TEXT_BODY};
            font-size: {fonts.BODY_SIZE};
        }}

        .highlight {{
            color: {colors.TEXT_HIGHLIGHT};
            font-weight: {fonts.FONT_WEIGHT_BOLD};
        }}

        .custom-button {{
            background-color: {buttons.BACKGROUND};
            color: {buttons.TEXT_COLOR};
            border: none;
            border-radius: {buttons.BORDER_RADIUS};
            padding: {buttons.PADDING};
            font-family: {buttons.FONT};
            font-size: {buttons.FONT_SIZE};
            cursor: pointer;
        }}

        .custom-button:hover {{
            {buttons.HOVER_EFFECT}
        }}
    </style>
    """
    return style_block
