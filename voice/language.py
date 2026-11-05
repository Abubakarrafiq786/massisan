def detect_text_language(text: str) -> str | None:
    if any(
        "\u0600" <= character <= "\u06ff"
        or "\u0750" <= character <= "\u077f"
        or "\u08a0" <= character <= "\u08ff"
        for character in text
    ):
        return "ur"
    return None
