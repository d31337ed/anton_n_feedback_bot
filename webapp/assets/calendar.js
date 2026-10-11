"use strict";

// Date picker for exact dates or flexible months + nights (UI requirements, section 5).
// It knows nothing about Telegram: the host shows mainButton() and calls confirm()/cancel().
class Calendar {
  constructor(root, { maxNights, horizonMonths, flexMonths, flexNights, maxComment, onChange = () => {}, onSelect = () => {} }) {
    this.root = root;
    this.maxNights = maxNights;
    this.horizonMonths = horizonMonths;
    this.flexMonths = flexMonths;
    this.flexNights = flexNights;
    this.maxComment = maxComment;
    this.onChange = onChange;
    // Called on every selection, e.g. for haptic feedback.
    this.onSelect = onSelect;
    this.confirmed = null;
    this.state = null;
    root.addEventListener("click", (event) => this.handleClick(event));
    root.addEventListener("input", (event) => {
      if (event.target.dataset.action === "comment") this.state.comment = event.target.value;
    });
  }

  static defaultState() {
    return { flexible: false, checkIn: null, checkOut: null, months: [], nightsFrom: 5, nightsTo: 7, comment: "" };
  }

  // Seeds the calendar from a saved dates object (the edit form); both modes keep their own state.
  setValue(dates, comment = "") {
    const state = Calendar.defaultState();
    state.comment = comment || "";
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
    // Flexible dates offer flexMonths months; exact dates run up to the same day horizonMonths later.
    const lastExactMonth = Dates.addMonths(this.firstMonth, this.horizonMonths);
    const day = Math.min(Dates.parse(this.today).d, Dates.daysInMonth(lastExactMonth));
    this.lastDay = `${lastExactMonth}-${String(day).padStart(2, "0")}`;
    this.state = JSON.parse(JSON.stringify(this.confirmed || Calendar.defaultState()));
    this.render();
  }

  // Called once the calendar is on screen: shows the selected month (exact) or chip (flexible).
  scrollToSelection() {
    const s = this.state;
    if (s.flexible) return window.scrollTo(0, 0);
    const panel = s.checkIn && this.root.querySelector(`.cal-month[data-month="${Dates.monthOf(s.checkIn)}"]`);
    if (panel) panel.scrollIntoView({ block: "start" });
    else window.scrollTo(0, 0);
  }

  // Keeps the calendar's state; the host switches back to the form.
  confirm() {
    if (!this.mainButton().active) return null;
    this.confirmed = JSON.parse(JSON.stringify(this.state));
    return this.value();
  }

  // The comment from the flexible view; it is not part of the dates and only goes with flexible dates.
  comment() {
    const s = this.confirmed;
    return s && s.flexible ? s.comment.trim() : "";
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

  // ---------- state changes ----------

  handleClick(event) {
    const button = event.target.closest("button");
    if (!button || button.disabled || !this.root.contains(button)) return;
    const { action, value } = button.dataset;
    const s = this.state;
    if (action === "month") {
      this.toggleFlexibleMonth(value);
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
    if (action === "flexible") this.scrollToSelection();
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
      parts.push(this.renderMonthChips());
      parts.push(this.renderNights());
      const comment = this.el("textarea", {
        class: "card input", id: "dates-comment", "data-action": "comment", rows: "3", maxlength: String(this.maxComment),
        placeholder: "Например: любые выходные, кроме праздников",
      });
      comment.value = s.comment;
      parts.push(this.el("div", { class: "field" }, this.el("label", { class: "label", for: "dates-comment" }, "Комментарий"), comment));
    } else {
      // The link stays on top: the months below scroll for more than a year.
      parts.push(this.el("button", { class: "cal-link muted", type: "button", "data-action": "flexible", "data-value": "on" }, "Не знаю точных дат"));
      const lastMonth = Dates.monthOf(this.lastDay);
      for (let key = this.firstMonth; Dates.monthsBetween(key, lastMonth) >= 0; key = Dates.addMonths(key, 1)) {
        parts.push(this.renderMonth(key));
      }
      parts.push(this.el("p", { class: "cal-easter-egg" }, "Завидую вашему горизонту планирования :)"));
    }
    this.root.replaceChildren(...parts);
  }

  // All flexible months fit on one screen, so there is no scrolling.
  renderMonthChips() {
    const s = this.state;
    const grid = this.el("div", { class: "cal-months", role: "group", "aria-label": "Месяцы" });
    for (let i = 0; i < this.flexMonths; i++) {
      const key = Dates.addMonths(this.firstMonth, i);
      const { y, m } = Dates.parseMonth(key);
      const text = `${Dates.MONTHS_SHORT[m - 1]} ${String(y).slice(2)}`;
      const pressed = s.months.includes(key);
      grid.append(this.el("button", {
        class: "cal-chip", type: "button", "data-action": "month", "data-value": key,
        "aria-pressed": String(pressed), "aria-label": Dates.monthTitle(key),
      }, text));
    }
    return grid;
  }

  renderMonth(key) {
    const s = this.state;
    const panel = this.el("section", { class: "cal-month", "data-month": key });
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
      if (cell % 7 === 0 || dayNumber === 1) classes.push("week-start");
      if (cell % 7 === 6 || dayNumber === length) classes.push("week-end");
      if (day === this.today) classes.push("today");
      const isStart = day === s.checkIn, isEnd = day === s.checkOut;
      if (isStart) classes.push("range-start");
      // The band between the two circles starts only once the range is complete.
      if (isStart && s.checkOut) classes.push("with-range");
      if (isEnd) classes.push("range-end");
      if (s.checkIn && s.checkOut && day > s.checkIn && day < s.checkOut) classes.push("in-range");
      // Past days, days past the horizon, and days beyond the longest stay while the check-out is being picked.
      const disabled = day < this.today || day > this.lastDay || (latestCheckOut && day > latestCheckOut);
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

  el(tag, attributes, ...children) {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
    element.append(...children);
    return element;
  }
}
