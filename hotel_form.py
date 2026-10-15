"""Hotel request form: the data model shared with the mini app, its validation and its text rendering."""
import html
from datetime import date, timedelta

from texts import DEFAULT_LANG, t, tn

MODE_HOTEL, MODE_CITY = "hotel", "city"
# Allowed values; their labels are in locales under request.*.
ROOM_CATEGORIES = ("best_rate", "club", "view", "suite", "custom")
BEDS = ("any", "king", "twin")
CURRENCIES = ("USD", "EUR", "HOTEL", "RUB")
BUDGET_UNITS = ("night", "stay")
HOTEL_TYPES = ("any", "city", "beach")

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

# budget None means the choice is left to the agent.
DEFAULT_SEARCH = {"budget": None, "budgetCurrency": "USD", "budgetUnit": "night", "area": None, "freeNights": False, "chains": None,
                  "hotelType": "any"}
# What a returning user gets prefilled instead of the defaults.
PREFERENCE_FIELDS = ("adults", "childrenAges", "currency", "bed")



class Errors(dict):
    """Field path -> message in the user's language."""

    def __init__(self, lang: str):
        super().__init__()
        self.lang = lang

    def text(self, key: str, **values) -> str:
        return t(f"form.errors.{key}", self.lang, **values)


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__(errors)
        self.errors = errors


def nights_text(low: int, high: int | None = None, lang: str = DEFAULT_LANG) -> str:
    high = low if high is None else high
    return tn("request.plurals.nights", high, lang, n=low if low == high else f"{low}–{high}")


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


def dates_label(dates: dict, today: date, lang: str = DEFAULT_LANG) -> str:
    """Human-readable dates, the same as the mini app shows (UI requirements D-2)."""
    months_short, months_genitive = t("request.months.short", lang), t("request.months.genitive", lang)
    if dates["flexible"]:
        months = [(int(m[:4]), int(m[5:7])) for m in dates["months"]]
        names = [months_short[month - 1] for _, month in months]
        last_year = months[-1][0]
        text = "–".join(names) if months[0][0] == last_year else f"{names[0]} – {names[-1]}"
        if last_year != today.year:
            text += f" {last_year}"
        return f"{text} · {nights_text(dates['nightsFrom'], dates['nightsTo'], lang)}"
    check_in, check_out = date.fromisoformat(dates["checkIn"]), date.fromisoformat(dates["checkOut"])
    end_year = f" {check_out.year}" if check_out.year != today.year else ""
    if (check_in.year, check_in.month) == (check_out.year, check_out.month):
        text = f"{check_in.day}–{check_out.day} {months_genitive[check_out.month - 1]}{end_year}"
    else:
        start_year = f" {check_in.year}" if check_in.year != check_out.year and check_in.year != today.year else ""
        text = (f"{check_in.day} {months_genitive[check_in.month - 1]}{start_year} – "
                f"{check_out.day} {months_genitive[check_out.month - 1]}{end_year}")
    return f"{text} · {nights_text((check_out - check_in).days, lang=lang)}"


def _text(value, limit: int, errors: Errors, path: str, required: bool = False) -> str | None:
    text = str(value).strip() if value is not None else ""
    if not text:
        if required:
            errors[path] = errors.text("required")
        return None
    if len(text) > limit:
        errors[path] = errors.text("max_length", limit=limit)
    return text


def _int(value, low: int, high: int, errors: Errors, path: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        errors[path] = errors.text("integer")
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        errors[path] = errors.text("integer")
        return None
    if number != value and str(number) != str(value).strip():
        errors[path] = errors.text("integer")
    elif not low <= number <= high:
        errors[path] = errors.text("range", low=low, high=high)
    return number


def _choice(value, options: tuple, default: str, errors: Errors, path: str) -> str:
    if value is None:
        return default
    if value not in options:
        errors[path] = errors.text("invalid")
    return value


def _clean_dates(raw, errors: Errors, today: date) -> dict | None:
    if not isinstance(raw, dict):
        errors["dates"] = errors.text("dates")
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
            errors["dates.months"] = errors.text("months_count")
        elif len(indexes) == 2 and indexes[1] - indexes[0] != 1:
            errors["dates.months"] = errors.text("months_in_a_row")
        elif not all(first_month <= i <= last_month for i in indexes):
            errors["dates.months"] = errors.text("month_out_of_range")
        if nights_from is None or nights_to is None:
            errors.setdefault("dates.nightsFrom", errors.text("nights"))
        elif nights_from > nights_to:
            errors["dates.nightsFrom"] = errors.text("nights_order")
        return {"flexible": True, "checkIn": None, "checkOut": None, "months": months,
                "nightsFrom": nights_from, "nightsTo": nights_to}
    try:
        check_in = date.fromisoformat(str(raw.get("checkIn")))
        check_out = date.fromisoformat(str(raw.get("checkOut")))
    except ValueError:
        errors["dates"] = errors.text("exact_dates")
        return None
    if check_in < today - timedelta(days=1):
        errors["dates.checkIn"] = errors.text("check_in_past")
    elif check_in > last_day:
        errors["dates.checkIn"] = errors.text("check_in_out_of_range")
    if check_out <= check_in:
        errors["dates.checkOut"] = errors.text("check_out_before_check_in")
    elif (check_out - check_in).days > MAX_NIGHTS:
        errors["dates.checkOut"] = errors.text("max_nights", max=MAX_NIGHTS)
    elif check_out > last_day:
        errors["dates.checkOut"] = errors.text("check_out_out_of_range")
    return {"flexible": False, "checkIn": check_in.isoformat(), "checkOut": check_out.isoformat(),
            "months": None, "nightsFrom": None, "nightsTo": None}


def _clean_children(raw, errors: Errors) -> list:
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_CHILDREN:
        errors["childrenAges"] = errors.text("children_count", max=MAX_CHILDREN)
        return []
    # The age is optional: None means it was not specified.
    return [_int(age, 0, MAX_CHILD_AGE, errors, f"childrenAges.{i}") for i, age in enumerate(raw)]


def clean_request(raw: dict, today: date | None = None, lang: str = DEFAULT_LANG) -> dict:
    """Validates the submitted form; returns the full data model with explicit defaults. Errors are in `lang`."""
    today = today or date.today()
    errors = Errors(lang)
    mode = raw.get("mode")
    if mode not in (MODE_HOTEL, MODE_CITY):
        raise ValidationError({"mode": errors.text("mode")})
    request = {
        "mode": mode,
        "hotel": _text(raw.get("hotel"), MAX_PLACE, errors, "hotel", required=True) if mode == MODE_HOTEL else None,
        "city": _text(raw.get("city"), MAX_PLACE, errors, "city", required=True) if mode == MODE_CITY else None,
        "dates": _clean_dates(raw.get("dates"), errors, today),
        "adults": _int(raw.get("adults", 2), *ADULTS, errors, "adults"),
        "childrenAges": _clean_children(raw.get("childrenAges"), errors),
    }
    if request["adults"] is None:
        errors["adults"] = errors.text("adults")
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
            "budget": _int(search.get("budget"), 1, MAX_BUDGET, errors, "search.budget"),
            # The budget has its own currency; it follows the response currency until changed.
            "budgetCurrency": _choice(search.get("budgetCurrency"), CURRENCIES, request["currency"], errors,
                                      "search.budgetCurrency"),
            "budgetUnit": _choice(search.get("budgetUnit"), BUDGET_UNITS, "night", errors, "search.budgetUnit"),
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
    # It is stored in the default language, the one of the admin chat.
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


def guests_text(adults: int, ages: list, lang: str = DEFAULT_LANG) -> str:
    text = tn("request.plurals.adults", adults, lang)
    if ages:
        listed = ", ".join(t("request.values.child_unknown", lang) if age is None
                           else t("request.values.child_under_one", lang) if age == 0 else str(age) for age in ages)
        text += f", {tn('request.plurals.children', len(ages), lang)} ({listed})"
    return text


def room_text(room: dict, lang: str = DEFAULT_LANG) -> str:
    # The custom text itself is listed with the comments.
    return f"{t(f'request.room_categories.{room['category']}', lang)} · {t(f'request.beds.{room['bed']}', lang)}"


def budget_text(request: dict, lang: str = DEFAULT_LANG) -> str:
    search = request["search"]
    # Requests saved before the budget unit existed have budgetPerNight.
    budget = search.get("budget", search.get("budgetPerNight"))
    if budget is None:
        return t("request.budget.none", lang)
    unit = t(f"request.budget.per_{search.get('budgetUnit', 'night')}", lang)
    if search["budgetCurrency"] == "HOTEL":
        return t("request.budget.amount_hotel_currency", lang, amount=budget, unit=unit)
    return t("request.budget.amount", lang, amount=budget, currency=search["budgetCurrency"], unit=unit)


# Text of each search criterion's default value, for criteria missing from one of two diffed versions.
SEARCH_DEFAULTS = {"budget": "request.budget.none", "area": "request.values.empty", "free_nights": "request.values.no",
                   "chains": "request.values.any_chains", "hotel_type": "request.hotel_types.any"}


def search_rows(request: dict, lang: str = DEFAULT_LANG) -> list[tuple[str, str]]:
    """(key, value) of each search criterion."""
    search = request["search"]
    value = lambda key: t(f"request.values.{key}", lang)
    return [("budget", budget_text(request, lang)),
            ("area", search["area"] or value("empty")),
            ("free_nights", value("yes" if search["freeNights"] else "no")),
            ("chains", search["chains"] or value("any_chains")),
            ("hotel_type", t(f"request.hotel_types.{search['hotelType']}", lang))]


# Comments from different parts of the form, in the order they are shown.
COMMENT_PARTS = (("dates", lambda r: r.get("datesComment")),
                 ("room", lambda r: r["room"]["customText"]),
                 ("general", lambda r: r.get("comment")))


def comments_text(request: dict, lang: str = DEFAULT_LANG) -> str | None:
    """One bullet per filled comment, e.g. "• По датам: любые выходные"."""
    lines = [f"• {t(f'request.comments.{key}', lang)}: {text}" for key, get in COMMENT_PARTS if (text := get(request))]
    return "\n".join(lines) or None


def rows(request: dict, full: bool = False, lang: str = DEFAULT_LANG) -> list[tuple[str, str]]:
    """(label, plain value) pairs; a row with an empty label is a line on its own.
    Defaults are listed too, except an empty area and free nights that are off.
    full=True lists everything, free nights as yes/no and each comment separately - used to diff two versions."""
    label = lambda key: t(f"request.labels.{key}", lang)
    place = ("hotel", request["hotel"]) if request["mode"] == MODE_HOTEL else ("city", request["city"])
    result = [(label(place[0]), place[1]),
              (label("dates"), request["dates"]["label"]),
              (label("guests"), guests_text(request["adults"], request["childrenAges"], lang))]
    result.append((label("room"), room_text(request["room"], lang)))
    result.append((label("currency"), t(f"request.currencies.{request['currency']}", lang)))
    if request["search"] is not None:
        search = request["search"]
        for key, value in search_rows(request, lang):
            if full:
                result.append((label(key), value))
            elif key == "free_nights":
                if search["freeNights"]:
                    result.append(("", t("request.values.free_nights_only", lang)))
            elif key != "area" or search["area"]:
                result.append((label(key), value))
    if full:
        result.extend((f"{label('comments')} · {t(f'request.comments.{key}', lang)}", get(request) or t("request.values.empty", lang))
                      for key, get in COMMENT_PARTS)
    elif comments := comments_text(request, lang):
        result.append((label("comments"), comments))
    return result


def format_request(request: dict, lang: str = DEFAULT_LANG) -> str:
    lines = []
    for label, value in rows(request, lang=lang):
        # The comments are a list of bullets, so they start on a new line.
        if not label:
            lines.append(html.escape(value))
            continue
        separator = "\n" if label == t("request.labels.comments", lang) else " "
        lines.append(f"<b>{label}</b>:{separator}{html.escape(value)}")
    return "\n".join(lines)


def format_changes(old: dict, new: dict) -> str:
    """What changed between two versions, for the admin chat (default language)."""
    before, after = dict(rows(old, full=True)), dict(rows(new, full=True))
    # Search rows exist only in city mode; switching modes should not list their defaults as changes.
    search_defaults = {t(f"request.labels.{key}"): t(text) for key, text in SEARCH_DEFAULTS.items()}
    lines = []
    for label in dict.fromkeys([*before, *after]):
        missing = search_defaults.get(label, t("request.values.empty"))
        old_value, new_value = before.get(label, missing), after.get(label, missing)
        if old_value != new_value:
            lines.append(f"<b>{label}</b>: {html.escape(old_value)} → {html.escape(new_value)}")
    return "\n".join(lines)
