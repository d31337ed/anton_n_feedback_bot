"use strict";

// The hotel request as the form edits it, and the JSON it sends (UI requirements, section 6).
// Validation and summary texts mirror hotel_form.py on the backend; both read request.* from the locales.
const HotelModel = (() => {
  const CATEGORIES = ["best_rate", "club", "view", "suite", "custom"];
  const BEDS = ["any", "king", "twin"];
  const CURRENCIES = ["USD", "EUR", "HOTEL", "RUB"];
  const BUDGET_UNITS = ["night", "stay"];
  const HOTEL_TYPES = ["any", "city", "beach"];
  // Below these a per-night budget is very unlikely to find anything; there is no limit for the hotel's currency.
  const LOW_BUDGET = { USD: 100, EUR: 90, RUB: 8000 };
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
    if (!state[place].trim()) errors[place] = I18n.t("form.errors.required");
    if (!state.dates) errors.dates = I18n.t("form.errors.dates");
    if (state.room.category === "custom" && !state.room.customText.trim()) errors["room.customText"] = I18n.t("form.errors.custom_room");
    if (state.mode === "city" && state.search.budget.trim()) {
      const budget = Number(state.search.budget);
      if (!/^\d+$/.test(state.search.budget.trim()) || budget < 1 || budget > LIMITS.budget) {
        errors["search.budget"] = I18n.t("form.errors.budget");
      }
    }
    if (state.comment.length > LIMITS.comment) errors.comment = I18n.t("form.errors.max_length", { limit: LIMITS.comment });
    return errors;
  }

  // ---------- texts ----------

  // Choice labels for the form controls: { value: label }.
  function options(prefix, values) {
    return Object.fromEntries(values.map((value) => [value, I18n.t(`${prefix}.${value}`)]));
  }

  const choices = {
    categories: () => options("form.room.categories", CATEGORIES),
    beds: () => options("form.room.beds", BEDS),
    currencies: () => options("form.currencies", CURRENCIES),
    budgetUnits: () => options("form.search.units", BUDGET_UNITS),
    hotelTypes: () => options("form.search.hotel_types", HOTEL_TYPES),
  };

  function guestsText(adults, ages) {
    let result = I18n.tn("request.plurals.adults", adults);
    if (ages.length) {
      const listed = ages.map((age) => (age === null ? I18n.t("request.values.child_unknown")
        : age === 0 ? I18n.t("request.values.child_under_one") : String(age))).join(", ");
      result += `, ${I18n.tn("request.plurals.children", ages.length)} (${listed})`;
    }
    return result;
  }

  // The collapsed "Room" row: the custom text stands in for the category while it is typed.
  function roomText(room) {
    const category = room.category === "custom" ? (room.customText.trim() || I18n.t("form.room.categories.custom"))
      : I18n.t(`form.room.categories.${room.category}`);
    return `${category} · ${I18n.t(`request.beds.${room.bed}`)}`;
  }

  // S-2: the agent's own pick until any criterion is set.
  function searchText(state) {
    const search = state.search;
    const parts = [];
    const amount = budgetAmount(state);
    if (amount && /^\d+$/.test(search.budget.trim())) {
      parts.push(I18n.t("form.search.budget_short", {
        amount, currency: I18n.t(`form.currencies.${budgetCurrency(state)}`), unit: I18n.t(`form.search.unit_short_${search.budgetUnit}`),
      }));
    }
    if (search.chains.trim()) parts.push(search.chains.trim());
    if (search.area.trim()) parts.push(search.area.trim());
    if (search.hotelType !== "any") parts.push(I18n.t(`request.hotel_types.${search.hotelType}`));
    if (search.freeNights) parts.push(I18n.t("form.search.free_nights_short"));
    return parts.length ? parts.join(" · ") : I18n.t("form.search.default");
  }

  function budgetText(search, currency) {
    if (search.budget == null) return null;
    const unit = I18n.t(`request.budget.per_${search.budgetUnit}`);
    return currency === "HOTEL" ? I18n.t("request.budget.amount_hotel_currency", { amount: search.budget, unit })
      : I18n.t("request.budget.amount", { amount: search.budget, currency, unit });
  }

  // P-4: rows whose value differs from the default are highlighted.
  function changed(state) {
    return {
      guests: state.adults !== 2 || state.childrenAges.length > 0,
      room: state.room.category !== "best_rate" || state.room.bed !== "any",
      currency: state.currency !== "USD",
      search: searchText(state) !== I18n.t("form.search.default"),
    };
  }

  // Mirrors comments_text on the backend: one bullet per filled comment.
  const COMMENT_PARTS = [["dates", (d) => d.datesComment], ["room", (d) => d.room.customText], ["general", (d) => d.comment]];
  function commentsText(data) {
    return COMMENT_PARTS.filter(([, get]) => get(data))
      .map(([key, get]) => `• ${I18n.t(`request.comments.${key}`)}: ${get(data)}`).join("\n") || null;
  }

  // Review screen rows (FR-4.1) - the same as the summary the bot sends to the chat.
  function reviewRows(data) {
    const label = (key) => I18n.t(`request.labels.${key}`);
    const rows = [
      data.mode === "hotel" ? { key: "hotel", label: label("hotel"), value: data.hotel } : { key: "city", label: label("city"), value: data.city },
      { key: "dates", label: label("dates"), value: data.dates.label },
      { key: "guests", label: label("guests"), value: guestsText(data.adults, data.childrenAges) },
    ];
    const room = data.room;
    if (room.category !== "best_rate" || room.bed !== "any") {
      // The custom text itself is listed with the comments.
      rows.push({ key: "room", label: label("room"), value: `${I18n.t(`request.room_categories.${room.category}`)} · ${I18n.t(`request.beds.${room.bed}`)}` });
    }
    rows.push({ key: "currency", label: label("currency"), value: I18n.t(`request.currencies.${data.currency}`) });
    const search = data.search;
    if (search) {
      const budget = budgetText(search, search.budgetCurrency);
      if (budget) rows.push({ key: "budget", label: label("budget"), value: budget });
      if (search.area) rows.push({ key: "search", label: label("area"), value: search.area });
      if (search.freeNights) rows.push({ key: "search", label: label("free_nights"), value: I18n.t("request.values.yes") });
      if (search.chains) rows.push({ key: "search", label: label("chains"), value: search.chains });
      if (search.hotelType !== "any") rows.push({ key: "search", label: label("hotel_type"), value: I18n.t(`request.hotel_types.${search.hotelType}`) });
    }
    const comments = commentsText(data);
    if (comments) rows.push({ key: data.comment ? "comment" : data.room.customText ? "room" : "dates", label: label("comments"), value: comments });
    return rows;
  }

  return {
    choices, LIMITS, defaults, defaultSearch, fromRequest, applyPreferences,
    budgetCurrency, lowBudget, payload, validate, guestsText, roomText, searchText, changed, commentsText, reviewRows,
  };
})();
