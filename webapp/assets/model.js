"use strict";

// The hotel request as the form edits it, and the JSON it sends (UI requirements, section 6).
// Validation and summary texts mirror hotel_form.py on the backend.
const HotelModel = (() => {
  const CATEGORIES = { best_rate: "Самый выгодный", club: "С лаунжем", view: "С видом", suite: "Сьют", custom: "Свои предпочтения" };
  const BEDS = { any: "Не важно", king: "1 (King)", twin: "2 (Twin)" };
  const BEDS_SHORT = { any: "любая кровать", king: "King", twin: "Twin" };
  const CURRENCIES = { USD: "USD", EUR: "EUR", HOTEL: "Local", RUB: "RUB" };
  const CURRENCIES_SUMMARY = { USD: "USD", EUR: "EUR", HOTEL: "Валюта отеля", RUB: "RUB" };
  const BUDGET_UNITS = { night: "за ночь", stay: "за стей" };
  // Below these a per-night budget is very unlikely to find anything; there is no limit for the hotel's currency.
  const LOW_BUDGET = { USD: 100, EUR: 90, RUB: 8000 };
  const HOTEL_TYPES = { any: "Любой", city: "Городской", beach: "Пляжный" };
  const LIMITS = { place: 200, customRoom: 200, area: 100, chains: 200, comment: 2000, datesComment: 500, budget: 1000000 };

  function defaults() {
    return {
      mode: "hotel", hotel: "", city: "", dates: null,
      adults: 2, childrenAges: [],
      room: { category: "best_rate", customText: "", bed: "any" },
      currency: "USD",
      search: defaultSearch(),
      comment: "",
      // The comment written in the flexible dates view; it is not part of the dates object.
      datesComment: "",
    };
  }

  function defaultSearch() {
    // budgetCurrency null = follows the response currency until the user picks one.
    // An empty budget leaves the choice to the agent.
    return { budget: "", budgetCurrency: null, budgetUnit: "night", area: "", freeNights: false, chains: "", hotelType: "any" };
  }

  // A saved request (edit mode) back into form state.
  function fromRequest(form) {
    const state = defaults();
    state.mode = form.mode;
    state.hotel = form.hotel || "";
    state.city = form.city || "";
    state.dates = form.dates;
    state.adults = form.adults;
    state.childrenAges = [...form.childrenAges];
    state.room = { category: form.room.category, customText: form.room.customText || "", bed: form.room.bed };
    state.currency = form.currency;
    if (form.search) {
      state.search = {
        budget: form.search.budget == null ? "" : String(form.search.budget),
        budgetCurrency: form.search.budgetCurrency, budgetUnit: form.search.budgetUnit || "night", area: form.search.area || "",
        freeNights: form.search.freeNights, chains: form.search.chains || "", hotelType: form.search.hotelType,
      };
    }
    state.comment = form.comment || "";
    state.datesComment = form.datesComment || "";
    return state;
  }

  function applyPreferences(state, preferences) {
    if (preferences.adults) state.adults = preferences.adults;
    if (preferences.childrenAges) state.childrenAges = [...preferences.childrenAges];
    if (preferences.currency) state.currency = preferences.currency;
    if (preferences.bed) state.room.bed = preferences.bed;
    return state;
  }

  const text = (value) => (value.trim() ? value.trim() : null);

  function budgetCurrency(state) {
    return state.search.budgetCurrency || state.currency;
  }

  // The amount that is sent; none leaves the budget to the agent.
  function budgetAmount(state) {
    const value = state.search.budget.trim();
    return value ? Number(value) : null;
  }

  // The hint under the budget: the amount is valid but too low to find anything (per stay, divided by the nights).
  function lowBudget(state) {
    const amount = state.mode === "city" ? budgetAmount(state) : null;
    const limit = LOW_BUDGET[budgetCurrency(state)];
    if (!amount || !limit) return false;
    if (state.search.budgetUnit === "night") return amount < limit;
    const dates = state.dates;
    if (!dates) return false;
    const nights = dates.flexible ? dates.nightsFrom : Dates.daysBetween(dates.checkIn, dates.checkOut);
    return amount < limit * nights;
  }

  // Values of the hidden mode stay in the state but are not sent (FR-3.1, S-4).
  function payload(state) {
    const city = state.mode === "city";
    return {
      mode: state.mode,
      hotel: city ? null : text(state.hotel),
      city: city ? text(state.city) : null,
      dates: state.dates,
      adults: state.adults,
      childrenAges: [...state.childrenAges],
      room: {
        category: state.room.category,
        customText: state.room.category === "custom" ? text(state.room.customText) : null,
        bed: state.room.bed,
      },
      currency: state.currency,
      search: city ? {
        budget: budgetAmount(state),
        budgetCurrency: budgetCurrency(state),
        budgetUnit: state.search.budgetUnit,
        area: text(state.search.area),
        freeNights: state.search.freeNights,
        chains: text(state.search.chains),
        hotelType: state.search.hotelType,
      } : null,
      comment: text(state.comment),
      datesComment: state.dates && state.dates.flexible ? text(state.datesComment) : null,
    };
  }

  // Errors keyed like the backend's: "hotel", "dates", "room.customText", …
  function validate(state) {
    const errors = {};
    const place = state.mode === "city" ? "city" : "hotel";
    if (!state[place].trim()) errors[place] = "Обязательное поле";
    if (!state.dates) errors.dates = "Выберите даты";
    if (state.room.category === "custom" && !state.room.customText.trim()) errors["room.customText"] = "Опишите, что важно в номере";
    if (state.mode === "city" && state.search.budget.trim()) {
      const budget = Number(state.search.budget);
      if (!/^\d+$/.test(state.search.budget.trim()) || budget < 1 || budget > LIMITS.budget) {
        errors["search.budget"] = "Целое число больше нуля";
      }
    }
    if (state.comment.length > LIMITS.comment) errors.comment = `Не больше ${LIMITS.comment} символов`;
    return errors;
  }

  // ---------- texts ----------

  function guestsText(adults, ages) {
    let result = `${adults} ${Dates.plural(adults, "взрослый", "взрослых", "взрослых")}`;
    if (ages.length) {
      const listed = ages.map((age) => (age === null ? "?" : age === 0 ? "до 1" : String(age))).join(", ");
      result += `, ${ages.length} ${Dates.plural(ages.length, "ребёнок", "детей", "детей")} (${listed})`;
    }
    return result;
  }

  function roomText(room) {
    const category = room.category === "custom" ? (room.customText.trim() || CATEGORIES.custom) : CATEGORIES[room.category];
    return `${category} · ${BEDS_SHORT[room.bed]}`;
  }

  // S-2: the agent's own pick until any criterion is set.
  const DEFAULT_SEARCH_TEXT = "Выгодные на мой взгляд";
  function searchText(state) {
    const search = state.search;
    const parts = [];
    const amount = budgetAmount(state);
    if (amount && /^\d+$/.test(search.budget.trim())) {
      const currency = budgetCurrency(state);
      parts.push(`до ${amount} ${CURRENCIES[currency]}/${search.budgetUnit === "night" ? "ночь" : "стей"}`);
    }
    if (search.chains.trim()) parts.push(search.chains.trim());
    if (search.area.trim()) parts.push(search.area.trim());
    if (search.hotelType !== "any") parts.push(HOTEL_TYPES[search.hotelType].toLowerCase());
    if (search.freeNights) parts.push("с беспл. ночами");
    return parts.length ? parts.join(" · ") : DEFAULT_SEARCH_TEXT;
  }

  function budgetText(search, currency) {
    if (search.budget == null) return null;
    const unit = BUDGET_UNITS[search.budgetUnit];
    return currency === "HOTEL" ? `до ${search.budget} в валюте отеля ${unit}` : `до ${search.budget} ${currency} ${unit}`;
  }

  // P-4: rows whose value differs from the default are highlighted.
  function changed(state) {
    return {
      guests: state.adults !== 2 || state.childrenAges.length > 0,
      room: state.room.category !== "best_rate" || state.room.bed !== "any",
      currency: state.currency !== "USD",
      search: searchText(state) !== DEFAULT_SEARCH_TEXT,
    };
  }

  // Mirrors comments_text on the backend: one bullet per filled comment.
  const COMMENT_PARTS = [["По датам", (d) => d.datesComment], ["По номеру", (d) => d.room.customText], ["В целом", (d) => d.comment]];
  function commentsText(data) {
    return COMMENT_PARTS.filter(([, get]) => get(data)).map(([label, get]) => `• ${label}: ${get(data)}`).join("\n") || null;
  }

  // Review screen rows (FR-4.1) - the same as the summary the bot sends to the chat.
  function reviewRows(data) {
    const rows = [
      data.mode === "hotel" ? { key: "hotel", label: "Отель", value: data.hotel } : { key: "city", label: "Город или локация", value: data.city },
      { key: "dates", label: "Даты", value: data.dates.label },
      { key: "guests", label: "Гости", value: guestsText(data.adults, data.childrenAges) },
    ];
    const room = data.room;
    if (room.category !== "best_rate" || room.bed !== "any") {
      // The custom text itself is listed with the comments.
      const category = room.category === "custom" ? "Пользовательский" : CATEGORIES[room.category];
      rows.push({ key: "room", label: "Номер", value: `${category} · ${BEDS_SHORT[room.bed]}` });
    }
    rows.push({ key: "currency", label: "Валюта", value: CURRENCIES_SUMMARY[data.currency] });
    const search = data.search;
    if (search) {
      const budget = budgetText(search, search.budgetCurrency);
      if (budget) rows.push({ key: "budget", label: "Бюджет", value: budget });
      if (search.area) rows.push({ key: "search", label: "Район", value: search.area });
      if (search.freeNights) rows.push({ key: "search", label: "Бесплатные ночи", value: "да" });
      if (search.chains) rows.push({ key: "search", label: "Сети", value: search.chains });
      if (search.hotelType !== "any") rows.push({ key: "search", label: "Тип отеля", value: HOTEL_TYPES[search.hotelType].toLowerCase() });
    }
    const comments = commentsText(data);
    if (comments) rows.push({ key: data.comment ? "comment" : data.room.customText ? "room" : "dates", label: "Комментарии", value: comments });
    return rows;
  }

  return {
    CATEGORIES, BEDS, CURRENCIES, BUDGET_UNITS, HOTEL_TYPES, LIMITS, defaults, defaultSearch, fromRequest, applyPreferences,
    budgetCurrency, lowBudget, payload, validate, guestsText, roomText, searchText, changed, commentsText, reviewRows,
  };
})();
