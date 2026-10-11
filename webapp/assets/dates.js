"use strict";

// Calendar dates as strings: days "YYYY-MM-DD", months "YYYY-MM", always in the device's local time.
// Never new Date("YYYY-MM-DD"): that parses as UTC and shifts the day west of Greenwich.
const Dates = (() => {
  const MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
  const MONTHS_SHORT = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"];
  const MONTHS_GENITIVE = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
  const MONTHS_GENITIVE_SHORT = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
  const WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"];
  const WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

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

  function plural(number, one, few, many) {
    const n10 = number % 10, n100 = number % 100;
    if (n10 === 1 && n100 !== 11) return one;
    if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return few;
    return many;
  }

  function nightsText(low, high = low) {
    const span = low === high ? String(low) : `${low}–${high}`;
    return `${span} ${plural(high, "ночь", "ночи", "ночей")}`;
  }

  function monthTitle(key) {
    const { y, m } = parseMonth(key);
    return `${MONTHS[m - 1]} ${y}`;
  }

  function dayLabel(day) {
    const { y, m, d } = parse(day);
    return `${d} ${MONTHS_GENITIVE[m - 1]} ${y}, ${WEEKDAYS[weekday(day)]}`;
  }

  // Same rules as hotel_form.dates_label on the backend (UI requirements D-2).
  function label(dates, todayIso = today()) {
    const currentYear = parse(todayIso).y;
    if (dates.flexible) {
      const months = dates.months.map(parseMonth);
      const names = months.map(({ m }) => MONTHS_SHORT[m - 1]);
      const lastYear = months[months.length - 1].y;
      let text = months[0].y === lastYear ? names.join("–") : `${names[0]} – ${names[names.length - 1]}`;
      if (lastYear !== currentYear) text += ` ${lastYear}`;
      return `${text} · ${nightsText(dates.nightsFrom, dates.nightsTo)}`;
    }
    const a = parse(dates.checkIn), b = parse(dates.checkOut);
    const endYear = b.y !== currentYear ? ` ${b.y}` : "";
    let text;
    if (a.y === b.y && a.m === b.m) {
      text = `${a.d}–${b.d} ${MONTHS_GENITIVE_SHORT[b.m - 1]}${endYear}`;
    } else {
      const startYear = a.y !== b.y && a.y !== currentYear ? ` ${a.y}` : "";
      text = `${a.d} ${MONTHS_GENITIVE_SHORT[a.m - 1]}${startYear} – ${b.d} ${MONTHS_GENITIVE_SHORT[b.m - 1]}${endYear}`;
    }
    return `${text} · ${nightsText(daysBetween(dates.checkIn, dates.checkOut))}`;
  }

  return {
    MONTHS_SHORT, WEEKDAYS_SHORT, parse, iso, today, addDays, daysBetween, month, monthOf, parseMonth,
    addMonths, monthsBetween, daysInMonth, weekday, plural, nightsText, monthTitle, dayLabel, label,
  };
})();
