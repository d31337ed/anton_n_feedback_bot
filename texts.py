"""User-facing texts live in locales/<lang>.toml, admin chat texts in locales/admin.toml."""
import string
import tomllib
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LANG = "ru"
ADMIN_FILE = "admin"
PLURAL_FORMS = {"zero", "one", "two", "few", "many", "other"}


def _flatten(table: dict, prefix: str = "") -> dict[str, object]:
    flat = {}
    for key, value in table.items():
        path = f"{prefix}{key}"
        # A table of plural forms ({one, few, many, other}) is one text, not a section.
        if isinstance(value, dict) and not set(value) <= PLURAL_FORMS:
            flat.update(_flatten(value, f"{path}."))
        else:
            flat[path] = value
    return flat


def _clean(value):
    # Multi-line strings end with the newline before the closing quotes; it is not part of the text.
    if isinstance(value, str):
        return value.removesuffix("\n")
    if isinstance(value, dict):
        return {form: _clean(text) for form, text in value.items()}
    if isinstance(value, list):
        return [_clean(text) for text in value]
    return value


def _load(name: str) -> dict[str, object]:
    with open(LOCALES_DIR / f"{name}.toml", "rb") as file:
        return {key: _clean(value) for key, value in _flatten(tomllib.load(file)).items()}


def _fields(value) -> set[str]:
    texts = value.values() if isinstance(value, dict) else value if isinstance(value, list) else [value]
    return {name for text in texts for _, name, _, _ in string.Formatter().parse(text) if name}


def _validate(catalogs: dict[str, dict]) -> None:
    """Every language has the default's keys with the same placeholders, so a translation can't break a message."""
    base = catalogs[DEFAULT_LANG]
    problems = []
    for lang, catalog in catalogs.items():
        problems += [f"{lang}: missing {key}" for key in base.keys() - catalog.keys()]
        problems += [f"{lang}: unknown {key}" for key in catalog.keys() - base.keys()]
        problems += [f"{lang}: placeholders differ in {key}" for key in base.keys() & catalog.keys()
                     if _fields(base[key]) != _fields(catalog[key])]
    if problems:
        raise ValueError("Broken locale files:\n" + "\n".join(problems))


CATALOGS = {path.stem: _load(path.stem) for path in sorted(LOCALES_DIR.glob("*.toml")) if path.stem != ADMIN_FILE}
ADMIN = _load(ADMIN_FILE)
_validate(CATALOGS)


def lang_of(language_code: str | None) -> str:
    """Telegram's language code ("en", "pt-br") mapped to an available language."""
    lang = (language_code or "").split("-")[0].lower()
    return lang if lang in CATALOGS else DEFAULT_LANG


def t(key: str, lang: str = DEFAULT_LANG, **values) -> str:
    text = CATALOGS.get(lang, CATALOGS[DEFAULT_LANG])[key]
    return text.format(**values) if values else text


def plural_form(lang: str, number: int) -> str:
    """CLDR plural category of an integer; the mini app gets the same from Intl.PluralRules."""
    if lang == "ru":
        if number % 10 == 1 and number % 100 != 11:
            return "one"
        if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
            return "few"
        return "many"
    return "one" if number == 1 else "other"


def tn(key: str, number: int, lang: str = DEFAULT_LANG, **values) -> str:
    """A text with plural forms, e.g. tn("request.plurals.nights", 5) -> "5 ночей"; {n} defaults to the number."""
    forms = CATALOGS.get(lang, CATALOGS[DEFAULT_LANG])[key]
    values.setdefault("n", number)
    return forms.get(plural_form(lang, number), forms.get("other", "")).format(**values)


def admin_t(key: str, **values) -> str:
    text = ADMIN[key]
    return text.format(**values) if values else text


def section(prefix: str, lang: str = DEFAULT_LANG) -> dict[str, object]:
    """All texts under a prefix, keys relative to it."""
    return {key.removeprefix(prefix): value for key, value in CATALOGS.get(lang, CATALOGS[DEFAULT_LANG]).items()
            if key.startswith(prefix)}


def text_key(text: str | None, prefix: str) -> str | None:
    """The key under a prefix whose text in any language equals the given one, e.g. a pressed button."""
    for catalog in CATALOGS.values():
        for key, value in catalog.items():
            if key.startswith(prefix) and value == text:
                return key
    return None


def texts_under(prefix: str) -> set[str]:
    """Texts under a prefix in every language, e.g. all button labels."""
    return {value for catalog in CATALOGS.values() for key, value in catalog.items() if key.startswith(prefix)}
