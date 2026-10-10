"use strict";

const tg = window.Telegram.WebApp;
const requestId = new URLSearchParams(location.search).get("request_id");

const ROOM_TYPES = ["Стандартный", "Делюкс", "Люкс"];
const DEFAULTS = {
  mode: "hotel", hotel: "", city: "", price_cap: "", check_in: "", check_out: "",
  adults: 2, children: 0, room_type: ROOM_TYPES[0], comment: "",
};
const MODE_LABELS = { hotel: "Конкретный отель", city: "Подбор в городе" };
// Same order and labels as the summary the bot sends to the chat.
const FIELD_LABELS = [
  ["mode", "Режим"], ["hotel", "Отель"], ["city", "Город"], ["price_cap", "Потолок цены за ночь"],
  ["check_in", "Заезд"], ["check_out", "Выезд"], ["adults", "Взрослые"], ["children", "Дети"],
  ["room_type", "Тип номера"], ["comment", "Комментарий"],
];
const MODE_FIELDS = { hotel: ["hotel"], city: ["city", "price_cap"] };
const LIMITS = { adults: [1, 20], children: [0, 20] };
const STATUS_TEXT = {
  in_work: "Заявка уже в работе — напишите изменения в чат.",
  closed: "Заявка закрыта — начните новую через /start.",
  not_found: "Заявка не найдена — начните новую через /start.",
  unauthorized: "Не удалось подтвердить вход. Закройте форму и откройте её заново из чата с ботом.",
  network: "Не удалось связаться с сервером.",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

let values = { ...DEFAULTS };
let initialValues = JSON.stringify(values);
let errors = {};
const touched = new Set();
let screen = null;
let idempotencyKey = null;
let submitting = false;

// ---------- helpers ----------

function todayIso() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function addDays(iso, days) {
  const date = new Date(iso + "T00:00:00Z");
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function nightsBetween(checkIn, checkOut) {
  return Math.round((Date.parse(checkOut) - Date.parse(checkIn)) / 86400000);
}

function plural(number, one, few, many) {
  const n10 = number % 10, n100 = number % 100;
  if (n10 === 1 && n100 !== 11) return one;
  if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return few;
  return many;
}

function formatDate(iso) {
  const [year, month, day] = iso.split("-");
  return `${day}.${month}.${year}`;
}

function activeFields() {
  const hidden = MODE_FIELDS[values.mode === "hotel" ? "city" : "hotel"];
  return FIELD_LABELS.map(([name]) => name).filter((name) => !hidden.includes(name));
}

// Fields of the other mode keep their values while hidden but are not submitted.
function payload() {
  const result = {};
  for (const name of activeFields()) {
    const value = typeof values[name] === "string" ? values[name].trim() : values[name];
    if (value !== "" && value !== null && !(name === "children" && value === 0)) result[name] = value;
  }
  return result;
}

function formatValue(name, data) {
  const value = data[name];
  if (name === "mode") return MODE_LABELS[value];
  if (name === "check_in") return formatDate(value);
  if (name === "check_out") {
    const nights = nightsBetween(data.check_in, value);
    return `${formatDate(value)} (${nights} ${plural(nights, "ночь", "ночи", "ночей")})`;
  }
  if (name === "price_cap") return `до $${value}`;
  return String(value);
}

// ---------- validation (the server re-checks everything) ----------

function validate() {
  const result = {};
  const required = values.mode === "hotel" ? ["hotel"] : ["city"];
  for (const name of required) {
    if (!values[name].trim()) result[name] = "Обязательное поле";
  }
  if (values.mode === "city" && values.price_cap !== "") {
    const price = Number(values.price_cap);
    if (!Number.isInteger(price) || price < 1) result.price_cap = "Нужно целое число больше нуля";
  }
  if (!values.check_in) result.check_in = "Укажите дату заезда";
  else if (values.check_in < todayIso()) result.check_in = "Дата заезда уже прошла";
  if (!values.check_out) result.check_out = "Укажите дату выезда";
  else if (values.check_in && values.check_out <= values.check_in) result.check_out = "Выезд должен быть позже заезда";
  return result;
}

// ---------- rendering ----------

function showScreen(name) {
  screen = name;
  for (const section of $$(".screen")) section.hidden = section.id !== `screen-${name}`;
  window.scrollTo(0, 0);
  updateButtons();
}

function showNotice(text, retry) {
  $("#notice-text").textContent = text;
  const retryButton = $("#notice-retry");
  retryButton.hidden = !retry;
  retryButton.onclick = retry || null;
  tg.disableClosingConfirmation();
  showScreen("notice");
}

function renderForm() {
  for (const button of $$("[data-mode]")) button.setAttribute("aria-checked", String(button.dataset.mode === values.mode));
  for (const field of $$("[data-modes]")) field.hidden = field.dataset.modes !== values.mode;
  for (const button of $$("[data-room]")) button.setAttribute("aria-checked", String(button.dataset.room === values.room_type));
  for (const name of ["hotel", "city", "price_cap", "check_in", "check_out", "comment"]) {
    const input = document.getElementById(name);
    if (input.value !== String(values[name])) input.value = values[name];
  }
  $("#check_in").min = todayIso();
  $("#check_out").min = values.check_in ? addDays(values.check_in, 1) : todayIso();
  for (const name of ["adults", "children"]) {
    document.getElementById(name).value = values[name];
    const [low, high] = LIMITS[name];
    $(`[data-step="${name}"][data-delta="-1"]`).disabled = values[name] <= low;
    $(`[data-step="${name}"][data-delta="1"]`).disabled = values[name] >= high;
  }
  const nights = values.check_in && values.check_out ? nightsBetween(values.check_in, values.check_out) : 0;
  $("#nights").textContent = nights > 0 ? `· ${nights} ${plural(nights, "ночь", "ночи", "ночей")}` : "";
  errors = validate();
  for (const element of $$("[data-error]")) {
    const name = element.dataset.error;
    element.textContent = touched.has(name) && errors[name] ? errors[name] : "";
  }
  updateButtons();
  updateClosingConfirmation();
}

function renderReview() {
  const data = payload();
  const list = $("#review-list");
  list.replaceChildren();
  for (const [name, label] of FIELD_LABELS) {
    if (!(name in data)) continue;
    const item = document.createElement("div");
    item.className = "review-item";
    const text = document.createElement("div");
    const key = document.createElement("div");
    key.className = "review-key";
    key.textContent = label;
    const value = document.createElement("div");
    value.className = "review-value";
    value.textContent = formatValue(name, data);
    text.append(key, value);
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "link-button";
    edit.textContent = "Изменить";
    edit.addEventListener("click", () => openForm(name === "mode" ? null : name));
    item.append(text, edit);
    list.append(item);
  }
  $("#review-error").hidden = true;
}

function updateButtons() {
  const main = tg.MainButton;
  if (screen === "form") {
    const ready = Object.keys(validate()).length === 0;
    main.setParams({
      text: "Проверить заявку",
      is_visible: true,
      is_active: ready,
      color: ready ? tg.themeParams.button_color || "#2b6ca3" : tg.themeParams.hint_color || "#9aa5ad",
      text_color: tg.themeParams.button_text_color || "#ffffff",
    });
    tg.BackButton.hide();
  } else if (screen === "review") {
    main.setParams({
      text: "Отправить заявку",
      is_visible: true,
      is_active: !submitting,
      color: tg.themeParams.button_color || "#2b6ca3",
      text_color: tg.themeParams.button_text_color || "#ffffff",
    });
    tg.BackButton.show();
  } else {
    main.hide();
    tg.BackButton.hide();
  }
}

function updateClosingConfirmation() {
  if (JSON.stringify(values) !== initialValues) tg.enableClosingConfirmation();
  else tg.disableClosingConfirmation();
}

// ---------- navigation ----------

function openForm(focusName) {
  showScreen("form");
  renderForm();
  if (focusName) {
    const target = document.getElementById(focusName) || document.querySelector(`[data-step="${focusName}"]`);
    if (target) {
      target.scrollIntoView({ block: "center" });
      target.focus({ preventScroll: true });
    }
  }
}

function openReview() {
  for (const name of activeFields()) touched.add(name);
  renderForm();
  if (Object.keys(errors).length) {
    const first = activeFields().find((name) => errors[name]);
    document.getElementById(first)?.scrollIntoView({ block: "center" });
    return;
  }
  renderReview();
  showScreen("review");
}

function setValue(name, value) {
  values[name] = value;
  // Changed data is a new submission, so it gets a new idempotency key.
  idempotencyKey = null;
  renderForm();
}

// ---------- server ----------

async function api(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: { "Authorization": `tma ${tg.initData}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await response.json(); } catch (e) { /* non-JSON error page */ }
  return { status: response.status, data };
}

async function load() {
  showScreen("loading");
  let response;
  try {
    response = await api("GET", `api/request${requestId ? `?request_id=${encodeURIComponent(requestId)}` : ""}`);
  } catch (e) {
    showNotice(STATUS_TEXT.network, load);
    return;
  }
  const { status, data } = response;
  if (status === 401 || status === 403) return showNotice(STATUS_TEXT.unauthorized);
  if (status === 404) return showNotice(STATUS_TEXT.not_found);
  if (status !== 200) return showNotice(STATUS_TEXT.network, load);
  if (data.status === "in_work" || data.status === "closed") return showNotice(STATUS_TEXT[data.status]);
  values = { ...DEFAULTS, ...data.fields };
  initialValues = JSON.stringify(values);
  openForm(null);
}

async function submit() {
  if (submitting) return;
  submitting = true;
  idempotencyKey = idempotencyKey || crypto.randomUUID();
  tg.MainButton.showProgress(false);
  updateButtons();
  let response;
  try {
    response = await api("POST", "api/request", { request_id: requestId, idempotency_key: idempotencyKey, fields: payload() });
  } catch (e) {
    response = null;
  }
  submitting = false;
  tg.MainButton.hideProgress();
  updateButtons();
  if (response && response.status === 200) {
    tg.disableClosingConfirmation();
    tg.close();
    return;
  }
  const code = response && response.data.error;
  if (response && response.status === 409 && STATUS_TEXT[code]) return showNotice(STATUS_TEXT[code]);
  if (response && (response.status === 401 || response.status === 403)) return showNotice(STATUS_TEXT.unauthorized);
  if (response && response.status === 422) {
    // The server disagrees with client-side validation: show its messages on the form.
    for (const name of Object.keys(response.data.fields || {})) touched.add(name);
    openForm(null);
    for (const [name, message] of Object.entries(response.data.fields || {})) {
      const element = document.querySelector(`[data-error="${name}"]`);
      if (element) element.textContent = message;
    }
    return;
  }
  const banner = $("#review-error");
  banner.textContent = code === "in_progress"
    ? "Заявка ещё отправляется, подождите пару секунд и нажмите ещё раз."
    : "Не удалось отправить заявку. Данные сохранены — попробуйте ещё раз.";
  banner.hidden = false;
}

// ---------- events ----------

for (const button of $$("[data-mode]")) button.addEventListener("click", () => setValue("mode", button.dataset.mode));
for (const button of $$("[data-room]")) button.addEventListener("click", () => setValue("room_type", button.dataset.room));
for (const button of $$("[data-step]")) {
  button.addEventListener("click", () => {
    const name = button.dataset.step;
    const [low, high] = LIMITS[name];
    setValue(name, Math.min(high, Math.max(low, values[name] + Number(button.dataset.delta))));
  });
}
for (const name of ["hotel", "city", "price_cap", "check_in", "check_out", "comment"]) {
  const input = document.getElementById(name);
  input.addEventListener("input", () => setValue(name, input.value));
  input.addEventListener("blur", () => { touched.add(name); renderForm(); });
}
// Date pickers commit on change and often never blur.
for (const name of ["check_in", "check_out"]) {
  document.getElementById(name).addEventListener("change", () => { touched.add(name); renderForm(); });
}
$("#screen-form").addEventListener("submit", (event) => event.preventDefault());

tg.MainButton.onClick(() => {
  if (screen === "form") openReview();
  else if (screen === "review") submit();
});
tg.BackButton.onClick(() => {
  if (screen === "review" && !submitting) openForm(null);
});

tg.ready();
tg.expand();
load();
