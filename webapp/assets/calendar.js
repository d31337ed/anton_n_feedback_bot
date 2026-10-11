"use strict";

// Date picker for exact dates or flexible months + nights (UI requirements, section 5).
// It knows nothing about Telegram: the host shows mainButton() and calls confirm()/cancel().
class Calendar {
  constructor(root, { maxNights, horizonMonths, flexNights, onChange = () => {}, onSelect = () => {} }) {
    this.root = root;
    this.maxNights = maxNights;
    this.horizonMonths = horizonMonths;
    this.flexNights = flexNights;
    this.onChange = onChange;
    // Called on every selection, e.g. for haptic feedback.
    this.onSelect = onSelect;
    this.confirmed = null;
    this.state = null;
    root.addEventListener("click", (event) => this.handleClick(event));
  }

  static defaultState() {
    return { flexible: false, visibleMonth: null, checkIn: null, checkOut: null, months: [], nightsFrom: 5, nightsTo: 7 };
  }

  // Seeds the calendar from a saved dates object (the edit form); both modes keep their own state.
  setValue(dates) {
    const state = Calendar.defaultState();
    if (dates && dates.flexible) {
      Object.assign(state, { flexible: true, months: [...dates.months], nightsFrom: dates.nightsFrom, nightsTo: dates.nightsTo });
    } else if (dates) {
      Object.assign(state, { checkIn: dates.checkIn, checkOut: dates.checkOut });
    }
    this.confirmed = dates ? state : null;
  }

  open() {
    this.today = Dates.today();
    this.firstMonth = Dates.monthOf(this.today);
    this.lastMonth = Dates.addMonths(this.firstMonth, this.horizonMonths - 1);
    this.state = JSON.parse(JSON.stringify(this.confirmed || Calendar.defaultState()));
    const anchor = this.state.flexible ? this.state.months[0] : this.state.checkIn && Dates.monthOf(this.state.checkIn);
    this.state.visibleMonth = this.clampMonth(anchor || this.firstMonth);
    this.render();
    this.scrollRibbon();
  }

  // Keeps the calendar's state; the host switches back to the form.
  confirm() {
    if (!this.mainButton().active) return null;
    this.confirmed = JSON.parse(JSON.stringify(this.state));
    return this.value();
  }

  value() {
    const s = this.confirmed;
    if (!s) return null;
    const dates = s.flexible
      ? { flexible: true, checkIn: null, checkOut: null, months: [...s.months], nightsFrom: s.nightsFrom, nightsTo: s.nightsTo }
      : { flexible: false, checkIn: s.checkIn, checkOut: s.checkOut, months: null, nightsFrom: null, nightsTo: null };
    dates.label = Dates.label(dates, Dates.today());
    return dates;
  }

  mainButton() {
    const s = this.state;
    if (s.flexible) {
      if (!s.months.length) return { text: "Выберите месяц", active: false };
      return { text: `Выбрать · ${Dates.nightsText(s.nightsFrom, s.nightsTo)}`, active: true };
    }
    if (!s.checkIn) return { text: "Выберите дату заезда", active: false };
    if (!s.checkOut) return { text: "Выберите дату выезда", active: false };
    return { text: `Выбрать · ${Dates.nightsText(Dates.daysBetween(s.checkIn, s.checkOut))}`, active: true };
  }

  clampMonth(key) {
    if (Dates.monthsBetween(this.firstMonth, key) < 0) return this.firstMonth;
    if (Dates.monthsBetween(key, this.lastMonth) < 0) return this.lastMonth;
    return key;
  }

  // ---------- state changes ----------

  handleClick(event) {
    const button = event.target.closest("button");
    if (!button || button.disabled || !this.root.contains(button)) return;
    const { action, value } = button.dataset;
    const s = this.state;
    if (action === "month") {
      if (s.flexible) this.toggleFlexibleMonth(value);
      else s.visibleMonth = value;
    } else if (action === "day") {
      this.pickDay(value);
    } else if (action === "flexible") {
      s.flexible = value === "on";
    } else if (action === "nights") {
      this.stepNights(value);
    } else {
      return;
    }
    this.onSelect();
    this.render();
    if (action === "flexible") this.scrollRibbon();
    this.onChange();
  }

  pickDay(day) {
    const s = this.state;
    if (s.checkIn && !s.checkOut && day > s.checkIn) {
      s.checkOut = day;
    } else {
      // First tap, a tap on or before check-in, or a tap after a full range starts over.
      s.checkIn = day;
      s.checkOut = null;
    }
  }

  toggleFlexibleMonth(key) {
    const s = this.state;
    if (s.months.includes(key)) {
      s.months = s.months.filter((m) => m !== key);
    } else if (s.months.length === 1 && Math.abs(Dates.monthsBetween(s.months[0], key)) === 1) {
      s.months = [s.months[0], key].sort();
    } else {
      s.months = [key];
    }
  }

  stepNights(step) {
    const s = this.state;
    const [low, high] = this.flexNights;
    const clamp = (n) => Math.min(high, Math.max(low, n));
    if (step === "from-") s.nightsFrom = clamp(s.nightsFrom - 1);
    if (step === "from+") { s.nightsFrom = clamp(s.nightsFrom + 1); s.nightsTo = Math.max(s.nightsTo, s.nightsFrom); }
    if (step === "to-") { s.nightsTo = clamp(s.nightsTo - 1); s.nightsFrom = Math.min(s.nightsFrom, s.nightsTo); }
    if (step === "to+") s.nightsTo = clamp(s.nightsTo + 1);
  }

  // ---------- rendering ----------

  render() {
    const s = this.state;
    const parts = [];
    if (s.flexible) {
      parts.push(this.el("button", { class: "cal-link accent", type: "button", "data-action": "flexible", "data-value": "off" }, "‹ Выбрать точные даты"));
      parts.push(this.el("h2", { class: "cal-subtitle" }, "Когда примерно?"));
      parts.push(this.renderRibbon());
      parts.push(this.renderNights());
    } else {
      parts.push(this.renderRibbon());
      parts.push(this.renderMonth(s.visibleMonth));
      const next = Dates.addMonths(s.visibleMonth, 1);
      parts.push(Dates.monthsBetween(next, this.lastMonth) >= 0
        ? this.renderMonth(next)
        : this.el("p", { class: "cal-easter-egg" }, "Завидую вашему горизонту планирования :)"));
      parts.push(this.el("button", { class: "cal-link muted", type: "button", "data-action": "flexible", "data-value": "on" }, "Не знаю точных дат"));
    }
    this.root.replaceChildren(...parts);
  }

  renderRibbon() {
    const s = this.state;
    const ribbon = this.el("div", { class: "cal-ribbon", role: "group", "aria-label": "Месяцы" });
    for (let i = 0; i < this.horizonMonths; i++) {
      const key = Dates.addMonths(this.firstMonth, i);
      const { y, m } = Dates.parseMonth(key);
      // The year is added to the first month of each new year.
      const text = Dates.MONTHS_SHORT[m - 1] + (m === 1 && i > 0 ? ` ${String(y).slice(2)}` : "");
      const pressed = s.flexible ? s.months.includes(key) : key === s.visibleMonth;
      ribbon.append(this.el("button", {
        class: "cal-chip", type: "button", "data-action": "month", "data-value": key,
        "aria-pressed": String(pressed), "aria-label": Dates.monthTitle(key),
      }, text));
    }
    return ribbon;
  }

  renderMonth(key) {
    const s = this.state;
    const panel = this.el("section", { class: "cal-month" });
    panel.append(this.el("h2", { class: "cal-title" }, Dates.monthTitle(key)));
    const grid = this.el("div", { class: "cal-grid", role: "group", "aria-label": Dates.monthTitle(key) });
    Dates.WEEKDAYS_SHORT.forEach((name, i) => grid.append(this.el("span", { class: `cal-weekday${i > 4 ? " weekend" : ""}`, "aria-hidden": "true" }, name)));
    const first = `${key}-01`;
    const offset = Dates.weekday(first);
    const length = Dates.daysInMonth(key);
    const latestCheckOut = s.checkIn && !s.checkOut ? Dates.addDays(s.checkIn, this.maxNights) : null;
    for (let cell = 0; cell < 42; cell++) {
      const dayNumber = cell - offset + 1;
      if (dayNumber < 1 || dayNumber > length) {
        grid.append(this.el("span", { class: "cal-empty", "aria-hidden": "true" }));
        continue;
      }
      const day = `${key}-${String(dayNumber).padStart(2, "0")}`;
      const classes = ["cal-day"];
      if (cell % 7 > 4) classes.push("weekend");
      if (day === this.today) classes.push("today");
      const isStart = day === s.checkIn, isEnd = day === s.checkOut;
      if (isStart) classes.push("range-start");
      if (isEnd) classes.push("range-end");
      if (s.checkIn && s.checkOut && day > s.checkIn && day < s.checkOut) classes.push("in-range");
      // Past days, and days beyond the longest stay while the check-out is being picked.
      const disabled = day < this.today || (latestCheckOut && day > latestCheckOut);
      grid.append(this.el("button", {
        class: classes.join(" "), type: "button", "data-action": "day", "data-value": day,
        "aria-label": Dates.dayLabel(day), "aria-pressed": String(isStart || isEnd), ...(disabled ? { disabled: "" } : {}),
      }, String(dayNumber)));
    }
    panel.append(grid);
    return panel;
  }

  renderNights() {
    const s = this.state;
    const [low, high] = this.flexNights;
    const stepper = (label, value, minus, plus, minusDisabled, plusDisabled) => this.el("div", { class: "cal-nights-item" },
      this.el("span", { class: "cal-nights-label" }, label),
      this.el("div", { class: "stepper" },
        this.el("button", { type: "button", "data-action": "nights", "data-value": minus, "aria-label": `${label}: меньше`, ...(minusDisabled ? { disabled: "" } : {}) }, "−"),
        this.el("output", {}, String(value)),
        this.el("button", { type: "button", "data-action": "nights", "data-value": plus, "aria-label": `${label}: больше`, ...(plusDisabled ? { disabled: "" } : {}) }, "+")));
    return this.el("div", { class: "cal-nights card" },
      this.el("span", { class: "cal-nights-title" }, "Ночей"),
      stepper("от", s.nightsFrom, "from-", "from+", s.nightsFrom <= low, s.nightsFrom >= high),
      stepper("до", s.nightsTo, "to-", "to+", s.nightsTo <= low, s.nightsTo >= high));
  }

  scrollRibbon() {
    const chip = this.root.querySelector('.cal-chip[aria-pressed="true"]');
    if (chip) chip.scrollIntoView({ block: "nearest", inline: "center" });
  }

  el(tag, attributes, ...children) {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
    element.append(...children);
    return element;
  }
}
