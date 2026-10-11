"""Hotel request form: the data model shared with the mini app, its validation and its text rendering."""
import html
from datetime import date, timedelta

MODE_HOTEL, MODE_CITY = "hotel", "city"
ROOM_CATEGORIES = {"best_rate": "Самый выгодный", "club": "С лаунжем", "view": "С видом", "suite": "Сьют",
                   "custom": "Пользовательский"}
BEDS = {"any": "любая кровать", "king": "King", "twin": "Twin"}
CURRENCIES = {"USD": "USD", "EUR": "EUR", "HOTEL": "Валюта отеля", "RUB": "RUB"}
HOTEL_TYPES = {"any": "любой", "city": "городской", "beach": "пляжный"}

MAX_NIGHTS = 30
HORIZON_MONTHS = 15
FLEX_MONTHS = 12
FLEX_NIGHTS = (1, 21)
ADULTS = (1, 6)
MAX_CHILDREN, MAX_CHILD_AGE = 6, 17
MAX_PLACE, MAX_CUSTOM_ROOM, MAX_AREA, MAX_CHAINS, MAX_COMMENT = 200, 200, 100, 200, 2000
MAX_DATES_COMMENT = 500
MAX_BUDGET = 1_000_000

# Sent to the mini app so both sides use the same limits.
CONFIG = {"maxNights": MAX_NIGHTS, "horizonMonths": HORIZON_MONTHS, "flexMonths": FLEX_MONTHS,
          "flexNights": list(FLEX_NIGHTS), "maxDatesComment": MAX_DATES_COMMENT, "adults": list(ADULTS), "maxChildren": MAX_CHILDREN, "maxChildAge": MAX_CHILD_AGE}

DEFAULT_ROOM = {"category": "best_rate", "customText": None, "bed": "any"}
DEFAULT_SEARCH = {"budgetPerNight": None, "budgetCurrency": "USD", "area": None, "freeNights": False, "chains": None,
                  "hotelType": "any"}
# What a returning user gets prefilled instead of the defaults.
PREFERENCE_FIELDS = ("adults", "childrenAges", "currency", "bed")

MONTHS_GENITIVE = ("янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек")
MONTHS_SHORT = ("Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек")


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__(errors)
        self.errors = errors


def plural(number: int, one: str, few: str, many: str) -> str:
    if number % 10 == 1 and number % 100 != 11:
        return one
    if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
        return few
    return many


def nights_text(low: int, high: int | None = None) -> str:
    high = low if high is None else high
    span = str(low) if low == high else f"{low}–{high}"
    return f"{span} {plural(high, 'ночь', 'ночи', 'ночей')}"


def month_index(value: date | str) -> int:
    """Months since year 0, from a date or a YYYY-MM string."""
    if isinstance(value, str):
        year, month = value.split("-")
        return int(year) * 12 + int(month) - 1
    return value.year * 12 + value.month - 1


def add_months(day: date, months: int) -> date:
    """The same day of the month `months` later, clamped to the month's length."""
    index = month_index(day) + months
    year, month = divmod(index, 12)
    month += 1
    next_month = date(year + month // 12, month % 12 + 1, 1)
    return date(year, month, min(day.day, (next_month - timedelta(days=1)).day))


def dates_label(dates: dict, today: date) -> str:
    """Human-readable dates, the same as the mini app shows (UI requirements D-2)."""
    if dates["flexible"]:
        months = [(int(m[:4]), int(m[5:7])) for m in dates["months"]]
        names = [MONTHS_SHORT[month - 1] for _, month in months]
        last_year = months[-1][0]
        text = "–".join(names) if months[0][0] == last_year else f"{names[0]} – {names[-1]}"
        if last_year != today.year:
            text += f" {last_year}"
        return f"{text} · {nights_text(dates['nightsFrom'], dates['nightsTo'])}"
    check_in, check_out = date.fromisoformat(dates["checkIn"]), date.fromisoformat(dates["checkOut"])
    end_year = f" {check_out.year}" if check_out.year != today.year else ""
    if (check_in.year, check_in.month) == (check_out.year, check_out.month):
        text = f"{check_in.day}–{check_out.day} {MONTHS_GENITIVE[check_out.month - 1]}{end_year}"
    else:
        start_year = f" {check_in.year}" if check_in.year != check_out.year and check_in.year != today.year else ""
        text = (f"{check_in.day} {MONTHS_GENITIVE[check_in.month - 1]}{start_year} – "
                f"{check_out.day} {MONTHS_GENITIVE[check_out.month - 1]}{end_year}")
    return f"{text} · {nights_text((check_out - check_in).days)}"


def _text(value, limit: int, errors: dict, path: str, required: bool = False) -> str | None:
    text = str(value).strip() if value is not None else ""
    if not text:
        if required:
            errors[path] = "Обязательное поле"
        return None
    if len(text) > limit:
        errors[path] = f"Не больше {limit} символов"
    return text


def _int(value, low: int, high: int, errors: dict, path: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        errors[path] = "Нужно целое число"
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        errors[path] = "Нужно целое число"
        return None
    if number != value and str(number) != str(value).strip():
        errors[path] = "Нужно целое число"
    elif not low <= number <= high:
        errors[path] = f"От {low} до {high}"
    return number


def _choice(value, options: dict, default: str, errors: dict, path: str) -> str:
    if value is None:
        return default
    if value not in options:
        errors[path] = "Недопустимое значение"
    return value


def _clean_dates(raw, errors: dict, today: date) -> dict | None:
    if not isinstance(raw, dict):
        errors["dates"] = "Выберите даты"
        return None
    # The client's "today" may differ from the server's by a day either way.
    first_month = month_index(today - timedelta(days=1))
    last_month = month_index(today + timedelta(days=1)) + FLEX_MONTHS - 1
    # Exact dates may go up to the same day HORIZON_MONTHS later.
    last_day = add_months(today + timedelta(days=1), HORIZON_MONTHS)
    if raw.get("flexible"):
        months = raw.get("months")
        nights_from = _int(raw.get("nightsFrom"), *FLEX_NIGHTS, errors, "dates.nightsFrom")
        nights_to = _int(raw.get("nightsTo"), *FLEX_NIGHTS, errors, "dates.nightsTo")
        try:
            indexes = [month_index(m) for m in months if len(m) == 7 and m[4] == "-"]
        except (TypeError, ValueError):
            indexes = []
        if not isinstance(months, list) or not 1 <= len(months) <= 2 or len(indexes) != len(months):
            errors["dates.months"] = "Выберите один или два месяца"
        elif len(indexes) == 2 and indexes[1] - indexes[0] != 1:
            errors["dates.months"] = "Месяцы должны идти подряд"
        elif not all(first_month <= i <= last_month for i in indexes):
            errors["dates.months"] = "Месяц вне доступного периода"
        if nights_from is None or nights_to is None:
            errors.setdefault("dates.nightsFrom", "Укажите число ночей")
        elif nights_from > nights_to:
            errors["dates.nightsFrom"] = "«От» не может быть больше «До»"
        return {"flexible": True, "checkIn": None, "checkOut": None, "months": months,
                "nightsFrom": nights_from, "nightsTo": nights_to}
    try:
        check_in = date.fromisoformat(str(raw.get("checkIn")))
        check_out = date.fromisoformat(str(raw.get("checkOut")))
    except ValueError:
        errors["dates"] = "Выберите даты заезда и выезда"
        return None
    if check_in < today - timedelta(days=1):
        errors["dates.checkIn"] = "Дата заезда уже прошла"
    elif check_in > last_day:
        errors["dates.checkIn"] = "Дата заезда вне доступного периода"
    if check_out <= check_in:
        errors["dates.checkOut"] = "Выезд должен быть позже заезда"
    elif (check_out - check_in).days > MAX_NIGHTS:
        errors["dates.checkOut"] = f"Не больше {MAX_NIGHTS} ночей"
    elif check_out > last_day:
        errors["dates.checkOut"] = "Дата выезда вне доступного периода"
    return {"flexible": False, "checkIn": check_in.isoformat(), "checkOut": check_out.isoformat(),
            "months": None, "nightsFrom": None, "nightsTo": None}


def _clean_children(raw, errors: dict) -> list:
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_CHILDREN:
        errors["childrenAges"] = f"От 0 до {MAX_CHILDREN} детей"
        return []
    # The age is optional: None means it was not specified.
    return [_int(age, 0, MAX_CHILD_AGE, errors, f"childrenAges.{i}") for i, age in enumerate(raw)]


def clean_request(raw: dict, today: date | None = None) -> dict:
    """Validates the submitted form; returns the full data model with explicit defaults."""
    today = today or date.today()
    errors: dict[str, str] = {}
    mode = raw.get("mode")
    if mode not in (MODE_HOTEL, MODE_CITY):
        raise ValidationError({"mode": "Выберите режим"})
    request = {
        "mode": mode,
        "hotel": _text(raw.get("hotel"), MAX_PLACE, errors, "hotel", required=True) if mode == MODE_HOTEL else None,
        "city": _text(raw.get("city"), MAX_PLACE, errors, "city", required=True) if mode == MODE_CITY else None,
        "dates": _clean_dates(raw.get("dates"), errors, today),
        "adults": _int(raw.get("adults", 2), *ADULTS, errors, "adults"),
        "childrenAges": _clean_children(raw.get("childrenAges"), errors),
    }
    if request["adults"] is None:
        errors["adults"] = "Укажите число взрослых"
    room = raw.get("room") if isinstance(raw.get("room"), dict) else {}
    category = _choice(room.get("category"), ROOM_CATEGORIES, "best_rate", errors, "room.category")
    request["room"] = {
        "category": category,
        "customText": _text(room.get("customText"), MAX_CUSTOM_ROOM, errors, "room.customText", required=True)
        if category == "custom" else None,
        "bed": _choice(room.get("bed"), BEDS, "any", errors, "room.bed"),
    }
    request["currency"] = _choice(raw.get("currency"), CURRENCIES, "USD", errors, "currency")
    if mode == MODE_CITY:
        search = raw.get("search") if isinstance(raw.get("search"), dict) else {}
        request["search"] = {
            "budgetPerNight": _int(search.get("budgetPerNight"), 1, MAX_BUDGET, errors, "search.budgetPerNight"),
            # The budget has its own currency; it follows the response currency until changed.
            "budgetCurrency": _choice(search.get("budgetCurrency"), CURRENCIES, request["currency"], errors,
                                      "search.budgetCurrency"),
            "area": _text(search.get("area"), MAX_AREA, errors, "search.area"),
            "freeNights": search.get("freeNights") is True,
            "chains": _text(search.get("chains"), MAX_CHAINS, errors, "search.chains"),
            "hotelType": _choice(search.get("hotelType"), HOTEL_TYPES, "any", errors, "search.hotelType"),
        }
    else:
        request["search"] = None
    request["comment"] = _text(raw.get("comment"), MAX_COMMENT, errors, "comment")
    # Written next to flexible dates, kept apart from them and glued to the comment only for display.
    flexible = bool(request["dates"] and request["dates"]["flexible"])
    request["datesComment"] = _text(raw.get("datesComment"), MAX_DATES_COMMENT, errors, "datesComment") if flexible else None
    if errors:
        raise ValidationError(errors)
    # The label is always rebuilt here, so the chat never shows text that disagrees with the dates.
    request["dates"]["label"] = dates_label(request["dates"], today)
    return request


def clean_preferences(raw) -> dict:
    """Keeps only valid preference values; anything broken falls back to the defaults on the client."""
    if not isinstance(raw, dict):
        return {}
    preferences = {}
    if isinstance(raw.get("adults"), int) and ADULTS[0] <= raw["adults"] <= ADULTS[1]:
        preferences["adults"] = raw["adults"]
    ages = raw.get("childrenAges")
    if isinstance(ages, list) and len(ages) <= MAX_CHILDREN and all(
            age is None or (isinstance(age, int) and 0 <= age <= MAX_CHILD_AGE) for age in ages):
        preferences["childrenAges"] = ages
    if raw.get("currency") in CURRENCIES:
        preferences["currency"] = raw["currency"]
    if raw.get("bed") in BEDS:
        preferences["bed"] = raw["bed"]
    return preferences


def preferences_of(request: dict) -> dict:
    return {"adults": request["adults"], "childrenAges": request["childrenAges"],
            "currency": request["currency"], "bed": request["room"]["bed"]}


def guests_text(adults: int, ages: list) -> str:
    text = f"{adults} {plural(adults, 'взрослый', 'взрослых', 'взрослых')}"
    if ages:
        listed = ", ".join("?" if age is None else "до 1" if age == 0 else str(age) for age in ages)
        text += f", {len(ages)} {plural(len(ages), 'ребёнок', 'детей', 'детей')} ({listed})"
    return text


def room_text(room: dict) -> str:
    # The custom text itself is listed with the comments.
    return f"{ROOM_CATEGORIES[room['category']]} · {BEDS[room['bed']]}"


def budget_text(request: dict) -> str:
    search = request["search"]
    if search["budgetPerNight"] is None:
        return "—"
    if search["budgetCurrency"] == "HOTEL":
        return f"до {search['budgetPerNight']} в валюте отеля за ночь"
    return f"до {search['budgetPerNight']} {search['budgetCurrency']}/ночь"


SEARCH_ROW_DEFAULTS = {"Бюджет": "—", "Район": "—", "Бесплатные ночи": "нет", "Сети": "любые", "Тип отеля": HOTEL_TYPES["any"]}


# Comments from different parts of the form, in the order they are shown.
COMMENT_PARTS = (("По датам", lambda r: r.get("datesComment")),
                 ("По номеру", lambda r: r["room"]["customText"]),
                 ("В целом", lambda r: r.get("comment")))
COMMENTS_LABEL = "Комментарии"


def comments_text(request: dict) -> str | None:
    """One bullet per filled comment, e.g. "• По датам: любые выходные"."""
    lines = [f"• {label}: {text}" for label, get in COMMENT_PARTS if (text := get(request))]
    return "\n".join(lines) or None


def rows(request: dict, full: bool = False) -> list[tuple[str, str]]:
    """(label, plain value) pairs. full=True also lists default values and each comment separately - used to diff two versions."""
    result = [("Отель", request["hotel"]) if request["mode"] == MODE_HOTEL else ("Город", request["city"]),
              ("Даты", request["dates"]["label"]),
              ("Гости", guests_text(request["adults"], request["childrenAges"]))]
    if full or request["room"] != DEFAULT_ROOM:
        result.append(("Номер", room_text(request["room"])))
    result.append(("Валюта", CURRENCIES[request["currency"]]))
    search = request["search"]
    if search is not None:
        for label, value in (("Бюджет", budget_text(request)),
                             ("Район", search["area"] or "—"),
                             ("Бесплатные ночи", "да" if search["freeNights"] else "нет"),
                             ("Сети", search["chains"] or "любые"),
                             ("Тип отеля", HOTEL_TYPES[search["hotelType"]])):
            if full or value != SEARCH_ROW_DEFAULTS[label]:
                result.append((label, value))
    if full:
        result.extend((f"{COMMENTS_LABEL} · {label}", get(request) or "—") for label, get in COMMENT_PARTS)
    elif comments := comments_text(request):
        result.append((COMMENTS_LABEL, comments))
    return result


def format_request(request: dict) -> str:
    lines = []
    for label, value in rows(request):
        # The comments are a list of bullets, so they start on a new line.
        separator = "\n" if label == COMMENTS_LABEL else " "
        lines.append(f"<b>{label}</b>:{separator}{html.escape(value)}")
    return "\n".join(lines)


def format_changes(old: dict, new: dict) -> str:
    before, after = dict(rows(old, full=True)), dict(rows(new, full=True))
    lines = []
    for label in dict.fromkeys([*before, *after]):
        # Search rows exist only in city mode; switching modes should not list their defaults as changes.
        missing = SEARCH_ROW_DEFAULTS.get(label, "—")
        old_value, new_value = before.get(label, missing), after.get(label, missing)
        if old_value != new_value:
            lines.append(f"<b>{label}</b>: {html.escape(old_value)} → {html.escape(new_value)}")
    return "\n".join(lines)
