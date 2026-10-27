import disnake

def format_number(number: int) -> str:
    """Форматирует числа с разделителями (например, 1000000 -> 1 000 000)."""
    return f"{number:,}".replace(",", " ")