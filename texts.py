"""User-facing texts live in locales/<lang>.toml, admin chat texts in locales/admin.toml."""
import re
import string
import tomllib
from html.parser import HTMLParser
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LANG = "ru"
ADMIN_FILE = "admin"
# Old labels of renamed buttons, still on users' keyboards: accepted, never shown. Optional in every language.
ALIASES_PREFIX = "aliases."
PLURAL_FORMS = {"zero", "one", "two", "few", "many", "other"}
# Texts shown in the mini app, which inserts them as plain text.
MINIAPP_PREFIXES = ("form.", "request.")
# Telegram's HTML: https://core.telegram.org/bots/api#html-style
TELEGRAM_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "span", "tg-spoiler", "a", "tg-emoji",
                 "code", "pre", "blockquote"}
TELEGRAM_ENTITIES = {"lt", "gt", "amp", "quot"}


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


def _is_plain(key: str) -> bool:
    """Texts Telegram or the mini app never parse as HTML: button labels, topic names, the mini app."""
    return key.startswith(MINIAPP_PREFIXES) or key.startswith(("buttons.", "topic.")) or key.endswith("_button")


class _MarkupChecker(HTMLParser):
    """Collects what Telegram would reject: unknown or unclosed tags, bare <, > or &."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.open_tags, self.problems, self.has_markup = [], [], False

    def handle_starttag(self, tag, attrs):
        self.has_markup = True
        if tag not in TELEGRAM_TAGS:
            self.problems.append(f"tag <{tag}> is not supported by Telegram")
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        self.has_markup = True
        if not self.open_tags or self.open_tags[-1] != tag:
            self.problems.append(f"</{tag}> does not close an open tag")
        else:
            self.open_tags.pop()

    # Ampersands are checked on the raw text in check(): the parser loses a trailing "&T".
    def handle_entityref(self, name):
        self.has_markup = True

    def handle_charref(self, name):
        self.has_markup = True

    def handle_data(self, data):
        for char, entity in (("<", "&lt;"), (">", "&gt;")):
            if char in data:
                self.problems.append(f"bare {char}, write {entity}")

    def check(self, text: str) -> list[str]:
        for match in re.finditer(r"&(?:(\w+);|#\d+;|#x[0-9a-fA-F]+;)?", text):
            if match.group(0) == "&":
                self.problems.append("bare &, write &amp;")
            elif match.group(1) and match.group(1) not in TELEGRAM_ENTITIES:
                self.problems.append(f"&{match.group(1)}; is not supported by Telegram")
        self.feed(text)
        self.close()
        # Whatever is left unparsed at the end (e.g. "<b") is a broken tag.
        if self.rawdata:
            self.problems.append(f"broken markup: {self.rawdata[:20]}")
        self.problems += [f"<{tag}> is not closed" for tag in self.open_tags]
        return self.problems


def _markup_problems(key: str, value) -> list[str]:
    texts = value.values() if isinstance(value, dict) else value if isinstance(value, list) else [value]
    problems = []
    for text in texts:
        checker = _MarkupChecker()
        found = checker.check(text)
        if _is_plain(key) and checker.has_markup:
            found = ["markup in a text that is shown as plain text"]
        problems += [f"{key}: {problem}" for problem in found]
    return problems


def _split_aliases(catalog: dict[str, object]) -> tuple[dict[str, object], dict[str, list]]:
    texts = {key: value for key, value in catalog.items() if not key.startswith(ALIASES_PREFIX)}
    aliases = {key.removeprefix(ALIASES_PREFIX): value for key, value in catalog.items()
               if key.startswith(ALIASES_PREFIX)}
    return texts, aliases


def _alias_problems(lang: str, catalog: dict, aliases: dict) -> list[str]:
    problems = []
    for key, old_texts in aliases.items():
        if not key.startswith("buttons.") or key not in catalog:
            problems.append(f"{lang}: alias for unknown button {key}")
        elif not isinstance(old_texts, list) or not all(isinstance(text, str) for text in old_texts):
            problems.append(f"{lang}: aliases of {key} must be a list of strings")
        else:
            problems += [f"{lang}: alias of {key} is a current button text: {text}" for text in old_texts
                         if text in catalog.values()]
            problems += [f"{lang}: alias {problem}" for text in old_texts for problem in _markup_problems(key, text)]
    return problems


def _validate(catalogs: dict[str, dict], admin: dict, aliases: dict[str, dict]) -> None:
    """Every language has the default's keys with the same placeholders, and its markup is what Telegram accepts,
    so an edit or a translation can't break a message."""
    base = catalogs[DEFAULT_LANG]
    problems = []
    for lang, catalog_aliases in aliases.items():
        problems += _alias_problems(lang, catalogs[lang], catalog_aliases)
    for lang, catalog in catalogs.items():
        problems += [f"{lang}: missing {key}" for key in base.keys() - catalog.keys()]
        problems += [f"{lang}: unknown {key}" for key in catalog.keys() - base.keys()]
        problems += [f"{lang}: placeholders differ in {key}" for key in base.keys() & catalog.keys()
                     if _fields(base[key]) != _fields(catalog[key])]
        problems += [f"{lang}: {problem}" for key, value in catalog.items() for problem in _markup_problems(key, value)]
    problems += [f"admin: {problem}" for key, value in admin.items() for problem in _markup_problems(key, value)]
    if problems:
        raise ValueError("Broken locale files:\n" + "\n".join(problems))


_SPLIT = {path.stem: _split_aliases(_load(path.stem)) for path in sorted(LOCALES_DIR.glob("*.toml"))
          if path.stem != ADMIN_FILE}
CATALOGS = {lang: texts for lang, (texts, _) in _SPLIT.items()}
ALIASES = {lang: aliases for lang, (_, aliases) in _SPLIT.items()}
ADMIN = _load(ADMIN_FILE)
_validate(CATALOGS, ADMIN, ALIASES)


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
    """The key under a prefix whose text or old alias in any language equals the given one, e.g. a pressed button."""
    for catalog in CATALOGS.values():
        for key, value in catalog.items():
            if key.startswith(prefix) and value == text:
                return key
    for aliases in ALIASES.values():
        for key, old_texts in aliases.items():
            if key.startswith(prefix) and text in old_texts:
                return key
    return None


def texts_under(prefix: str) -> set[str]:
    """Texts under a prefix in every language with their old aliases, e.g. all button labels."""
    current = {value for catalog in CATALOGS.values() for key, value in catalog.items() if key.startswith(prefix)}
    old = {text for aliases in ALIASES.values() for key, old_texts in aliases.items() if key.startswith(prefix)
           for text in old_texts}
    return current | old
