"use strict";

// Calendar dates as strings: days "YYYY-MM-DD", months "YYYY-MM", always in the device's local time.
// Never new Date("YYYY-MM-DD"): that parses as UTC and shifts the day west of Greenwich.
// Month and weekday names come from I18n.
const Dates = (() => {
  const monthShort = (m) => I18n.t("request.months.short")[m - 1];
  const monthGenitiveShort = (m) => I18n.t("request.months.genitive")[m - 1];

  const pad = (n) => String(n).padStart(2, "0");

  function parse(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    return { y, m, d };
  }

  function iso(y, m, d) {
    return `${y}-${pad(m)}-${pad(d)}`;
  }

  function fromLocal(date) {
    return iso(date.getFullYear(), date.getMonth() + 1, date.getDate());
  }

  function today() {
    return fromLocal(new Date());
  }

  function addDays(day, n) {
    const { y, m, d } = parse(day);
    return fromLocal(new Date(y, m - 1, d + n));
  }

  // Whole days between two dates; UTC arithmetic keeps DST changes out of it.
  function daysBetween(from, to) {
    const a = parse(from), b = parse(to);
    return Math.round((Date.UTC(b.y, b.m - 1, b.d) - Date.UTC(a.y, a.m - 1, a.d)) / 86400000);
  }

  function month(y, m) {
    return `${y}-${pad(m)}`;
  }

  function monthOf(day) {
    return day.slice(0, 7);
  }

  function parseMonth(key) {
    const [y, m] = key.split("-").map(Number);
    return { y, m };
  }

  function addMonths(key, n) {
    const { y, m } = parseMonth(key);
    const index = y * 12 + (m - 1) + n;
    return month(Math.floor(index / 12), (index % 12) + 1);
  }

  function monthsBetween(from, to) {
    const a = parseMonth(from), b = parseMonth(to);
    return (b.y - a.y) * 12 + (b.m - a.m);
  }

  function daysInMonth(key) {
    const { y, m } = parseMonth(key);
    return new Date(y, m, 0).getDate();
  }

  // 0 = Monday … 6 = Sunday.
  function weekday(day) {
    const { y, m, d } = parse(day);
    return (new Date(y, m - 1, d).getDay() + 6) % 7;
  }

  function nightsText(low, high = low) {
    return I18n.tn("request.plurals.nights", high, { n: low === high ? low : `${low}–${high}` });
  }

  function monthTitle(key) {
    const { y, m } = parseMonth(key);
    return `${I18n.t("form.calendar.months.titles")[m - 1]} ${y}`;
  }

  function weekdaysShort() {
    return I18n.t("form.calendar.months.weekdays_short");
  }

  function dayLabel(day) {
    const { y, m, d } = parse(day);
    return I18n.t("form.calendar.months.day_label", {
      day: d, month: I18n.t("form.calendar.months.genitive")[m - 1], year: y,
      weekday: I18n.t("form.calendar.months.weekdays")[weekday(day)],
    });
  }

  // Same rules as hotel_form.dates_label on the backend (UI requirements D-2).
  function label(dates, todayIso = today()) {
    const currentYear = parse(todayIso).y;
    if (dates.flexible) {
      const months = dates.months.map(parseMonth);
      const names = months.map(({ m }) => monthShort(m));
      const lastYear = months[months.length - 1].y;
      let text = months[0].y === lastYear ? names.join("–") : `${names[0]} – ${names[names.length - 1]}`;
      if (lastYear !== currentYear) text += ` ${lastYear}`;
      return `${text} · ${nightsText(dates.nightsFrom, dates.nightsTo)}`;
    }
    const a = parse(dates.checkIn), b = parse(dates.checkOut);
    const endYear = b.y !== currentYear ? ` ${b.y}` : "";
    let text;
    if (a.y === b.y && a.m === b.m) {
      text = `${a.d}–${b.d} ${monthGenitiveShort(b.m)}${endYear}`;
    } else {
      const startYear = a.y !== b.y && a.y !== currentYear ? ` ${a.y}` : "";
      text = `${a.d} ${monthGenitiveShort(a.m)}${startYear} – ${b.d} ${monthGenitiveShort(b.m)}${endYear}`;
    }
    return `${text} · ${nightsText(daysBetween(dates.checkIn, dates.checkOut))}`;
  }

  return {
    monthShort, weekdaysShort, parse, iso, today, addDays, daysBetween, month, monthOf, parseMonth,
    addMonths, monthsBetween, daysInMonth, weekday, nightsText, monthTitle, dayLabel, label,
  };
})();
