import unicodedata


def normalize_text(value: str | None) -> str | None:
    """Normaliza texto para busca: sem acentos e sem distinção de maiúsculas.

    Também é registrada como função SQL no SQLite (``normalize_text``), para que
    o banco e a aplicação comparem termos exatamente da mesma forma.
    """

    if value is None:
        return None
    # Caminho rápido: ~95% dos textos são ASCII e dispensam a decomposição Unicode.
    # Importa porque a função roda linha a linha dentro das consultas do SQLite.
    if value.isascii():
        return value.lower()
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold()


def escape_like(value: str, escape: str = "\\") -> str:
    """Escapa os curingas do LIKE para que o termo seja buscado literalmente."""

    return value.replace(escape, escape * 2).replace("%", f"{escape}%").replace("_", f"{escape}_")
