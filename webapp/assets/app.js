"use strict";

const tg = window.Telegram.WebApp;
const requestId = new URLSearchParams(location.search).get("request_id");

const STATUS_TEXT = {
  in_work: "Заявка уже в работе — напишите изменения в чат.",
  closed: "Заявка закрыта — начните новую через /start.",
  not_found: "Заявка не найдена — начните новую через /start.",
  unauthorized: "Не удалось подтвердить вход. Закройте форму и откройте её заново из чата с ботом.",
  network: "Не удалось связаться с сервером.",
};
const INFO_TEXT = {
  freeNights: "Акции вроде Stay 3 Pay 2: одна или несколько ночей в подарок.",
  local: "Local — валюта страны отеля, например иены в Японии или евро во Франции.",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

let config = { maxNights: 30, horizonMonths: 15, flexMonths: 12, flexNights: [1, 21], maxDatesComment: 500, adults: [1, 6], maxChildren: 6, maxChildAge: 17 };
let state = HotelModel.defaults();
let initialSnapshot = JSON.stringify(state);
const touched = new Set();
let screen = null;
let idempotencyKey = null;
let submitting = false;
let commentOpen = false;
let calendar = null;

const accordion = new Accordion($("#form-rows"), { onToggle: () => haptic() });

function haptic() {
  if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
}

function getPath(object, path) {
  return path.split(".").reduce((value, key) => value[key], object);
}

function setPath(object, path, value) {
  const keys = path.split(".");
  const last = keys.pop();
  keys.reduce((value, key) => value[key], object)[last] = value;
}

function el(tag, attributes = {}, ...children) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
  element.append(...children);
  return element;
}

// ---------- static controls ----------

function buildChoices(container, path, options, role) {
  container.replaceChildren(...Object.entries(options).map(([value, label]) =>
    el("button", { type: "button", role, "data-set": path, "data-value": value, class: container.classList.contains("chips") ? "chip" : "" }, label)));
}

buildChoices($("#category-chips"), "room.category", HotelModel.CATEGORIES, "radio");
buildChoices($("#bed-segmented"), "room.bed", HotelModel.BEDS, "radio");
buildChoices($("#hotel-type-segmented"), "search.hotelType", HotelModel.HOTEL_TYPES, "radio");
buildChoices($("#currency-chips"), "currency", HotelModel.CURRENCIES, "radio");
$("#budget-currency").replaceChildren(...Object.entries(HotelModel.CURRENCIES).map(([value, label]) => el("option", { value }, label)));

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

function renderChildrenAges() {
  const box = $("#children-ages");
  const selects = box.querySelectorAll("select");
  if (selects.length === state.childrenAges.length) {
    selects.forEach((select, i) => { select.value = state.childrenAges[i] === null ? "" : String(state.childrenAges[i]); });
    return;
  }
  box.replaceChildren(...state.childrenAges.map((age, i) => {
    const options = [el("option", { value: "" }, "Возраст"), el("option", { value: "0" }, "до 1")];
    for (let year = 1; year <= config.maxChildAge; year++) options.push(el("option", { value: String(year) }, `${year} ${Dates.plural(year, "год", "года", "лет")}`));
    const select = el("select", { "data-child": String(i), "aria-label": `Возраст ребёнка ${i + 1}` }, ...options);
    select.value = age === null ? "" : String(age);
    return el("div", { class: "row" }, el("span", {}, `Ребёнок ${i + 1}`), select);
  }));
}

function renderForm() {
  const city = state.mode === "city";
  for (const button of $$("[data-set]")) button.setAttribute("aria-checked", String(String(getPath(state, button.dataset.set)) === button.dataset.value));
  for (const node of $$("[data-modes]")) node.hidden = node.dataset.modes !== state.mode;
  for (const input of $$("[data-input]")) {
    const value = getPath(state, input.dataset.input);
    if (input.value !== value) input.value = value;
  }

  const datesValue = $("#dates-value");
  datesValue.textContent = state.dates ? state.dates.label : "Выбрать ›";
  datesValue.classList.toggle("accent", !state.dates);

  const kids = state.childrenAges.length;
  const [minAdults, maxAdults] = config.adults;
  $("#guests-inline").hidden = kids > 0;
  $("#guests-toggle").hidden = kids === 0;
  $("#guests-value").textContent = HotelModel.guestsText(state.adults, state.childrenAges);
  $("[data-output=adults]").value = `${state.adults} ${Dates.plural(state.adults, "взрослый", "взрослых", "взрослых")}`;
  $("[data-output=adults]").classList.toggle("changed", state.adults !== 2);
  $("[data-output=adults-count]").value = state.adults;
  $("[data-output=children]").value = kids;
  for (const button of $$('[data-step="adults"]')) button.disabled = button.dataset.delta < 0 ? state.adults <= minAdults : state.adults >= maxAdults;
  for (const button of $$('[data-step="children"]')) button.disabled = button.dataset.delta < 0 ? kids <= 0 : kids >= config.maxChildren;
  $("#add-child").disabled = config.maxChildren === 0;
  renderChildrenAges();

  $("#room-value").textContent = HotelModel.roomText(state.room);
  $("#custom-room").hidden = state.room.category !== "custom";
  $("#search-value").textContent = HotelModel.searchText(state.search);
  $("#free-nights").checked = state.search.freeNights;
  $("#budget-currency").value = HotelModel.budgetCurrency(state);

  const changed = HotelModel.changed(state);
  $("#guests-value").classList.toggle("changed", changed.guests);
  $("#room-value").classList.toggle("changed", changed.room);
  $("#search-value").classList.toggle("changed", changed.search);

  $("#comment-box").hidden = !(commentOpen || state.comment);
  $("#comment-link").hidden = !$("#comment-box").hidden;

  const errors = HotelModel.validate(state);
  for (const node of $$("[data-error]")) {
    const name = node.dataset.error;
    node.textContent = touched.has(name) && errors[name] ? errors[name] : "";
  }
  for (const input of $$("[data-input]")) input.classList.toggle("invalid", touched.has(input.dataset.input) && Boolean(errors[input.dataset.input]));
  updateButtons();
  updateClosingConfirmation();
  return errors;
}

function renderReview() {
  const list = $("#review-list");
  list.replaceChildren(...HotelModel.reviewRows(HotelModel.payload(state)).map((row) => {
    const edit = el("button", { type: "button", class: "link-button" }, "Изменить");
    edit.addEventListener("click", () => editFromReview(row.key));
    return el("div", { class: "review-item" },
      el("div", {}, el("div", { class: "review-key" }, row.label), el("div", { class: "review-value" }, row.value)),
      edit);
  }));
  $("#review-error").hidden = true;
}

function mainButton(text, active) {
  tg.MainButton.setParams({
    text, is_visible: true, is_active: active,
    color: active ? tg.themeParams.button_color || "#2b6ca3" : tg.themeParams.hint_color || "#9aa5ad",
    text_color: tg.themeParams.button_text_color || "#ffffff",
  });
}

function updateButtons() {
  if (screen === "form") {
    mainButton("Проверить заявку", Object.keys(HotelModel.validate(state)).length === 0);
    tg.BackButton.hide();
  } else if (screen === "calendar") {
    const { text, active } = calendar.mainButton();
    mainButton(text, active);
    tg.BackButton.show();
  } else if (screen === "review") {
    mainButton("Отправить заявку", !submitting);
    tg.BackButton.show();
  } else {
    tg.MainButton.hide();
    tg.BackButton.hide();
  }
}

function updateClosingConfirmation() {
  if (JSON.stringify(state) !== initialSnapshot) tg.enableClosingConfirmation();
  else tg.disableClosingConfirmation();
}

// ---------- navigation ----------

function openForm() {
  showScreen("form");
  renderForm();
}

function openCalendar() {
  calendar.open();
  showScreen("calendar");
  calendar.scrollToSelection();
}

function focusOn(element) {
  if (!element) return;
  element.scrollIntoView({ block: "center" });
  element.focus({ preventScroll: true });
}

function editFromReview(key) {
  openForm();
  if (key === "dates") return openCalendar();
  if (key === "hotel" || key === "city") return focusOn(document.getElementById(key));
  if (key === "budget") return focusOn($("#budget"));
  if (key === "currency") return focusOn($("#currency-chips button[aria-checked=true]"));
  if (key === "comment") { commentOpen = true; renderForm(); return focusOn($("#comment")); }
  if (key === "guests" && !state.childrenAges.length) return focusOn($('[data-step="adults"]'));
  accordion.open(key);
  $(`[data-accordion="${key}"]`).scrollIntoView({ block: "start" });
}

function openReview() {
  for (const name of ["hotel", "city", "dates", "room.customText", "search.budgetPerNight", "comment"]) touched.add(name);
  const errors = renderForm();
  const first = Object.keys(errors)[0];
  if (first) {
    if (first === "room.customText") accordion.open("room");
    const target = $(`[data-input="${first}"]`) || $(`[data-error="${first}"]`);
    if (target) target.scrollIntoView({ block: "center" });
    return;
  }
  renderReview();
  showScreen("review");
}

function changeState(mutate) {
  mutate();
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
    return showNotice(STATUS_TEXT.network, load);
  }
  const { status, data } = response;
  if (status === 401 || status === 403) return showNotice(STATUS_TEXT.unauthorized);
  if (status === 404) return showNotice(STATUS_TEXT.not_found);
  if (status !== 200) return showNotice(STATUS_TEXT.network, load);
  if (data.status === "in_work" || data.status === "closed") return showNotice(STATUS_TEXT[data.status]);
  config = { ...config, ...data.config };
  state = data.form ? HotelModel.fromRequest(data.form) : HotelModel.applyPreferences(HotelModel.defaults(), data.preferences || {});
  initialSnapshot = JSON.stringify(state);
  calendar = new Calendar($("#screen-calendar"), {
    maxNights: config.maxNights, horizonMonths: config.horizonMonths, flexMonths: config.flexMonths,
    flexNights: config.flexNights, maxComment: config.maxDatesComment,
    onChange: updateButtons, onSelect: haptic,
  });
  calendar.setValue(state.dates, state.datesComment);
  openForm();
}

async function submit() {
  if (submitting) return;
  submitting = true;
  idempotencyKey = idempotencyKey || crypto.randomUUID();
  tg.MainButton.showProgress(false);
  updateButtons();
  let response = null;
  try {
    response = await api("POST", "api/request", { request_id: requestId, idempotency_key: idempotencyKey, form: HotelModel.payload(state) });
  } catch (e) { /* shown below */ }
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
    // The server disagrees with the client-side checks: show its messages on the form.
    openForm();
    for (const [name, message] of Object.entries(response.data.fields || {})) {
      const node = $(`[data-error="${name}"]`) || $(`[data-error="${name.split(".")[0]}"]`);
      if (node) node.textContent = message;
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

$("#screen-form").addEventListener("submit", (event) => event.preventDefault());

$("#screen-form").addEventListener("click", (event) => {
  const choice = event.target.closest("[data-set]");
  if (choice) {
    haptic();
    changeState(() => setPath(state, choice.dataset.set, choice.dataset.value));
    return;
  }
  const step = event.target.closest("[data-step]");
  if (step && !step.disabled) {
    haptic();
    const delta = Number(step.dataset.delta);
    changeState(() => {
      if (step.dataset.step === "adults") {
        state.adults = Math.min(config.adults[1], Math.max(config.adults[0], state.adults + delta));
      } else if (delta > 0) {
        state.childrenAges.push(null);
      } else {
        // The last child is removed; with no children the block folds back into the "+ Дети" chip.
        state.childrenAges.pop();
        if (!state.childrenAges.length) accordion.close();
      }
    });
    return;
  }
  const info = event.target.closest("[data-info]");
  if (info) {
    const message = INFO_TEXT[info.dataset.info];
    if (tg.showPopup) tg.showPopup({ message, buttons: [{ type: "ok" }] });
    else window.alert(message);
  }
});

$("#dates-row").addEventListener("click", openCalendar);
$("#add-child").addEventListener("click", () => {
  haptic();
  changeState(() => state.childrenAges.push(null));
  accordion.open("guests");
});
$("#comment-link").addEventListener("click", () => {
  commentOpen = true;
  renderForm();
  $("#comment").focus();
});
$("#free-nights").addEventListener("change", (event) => {
  haptic();
  changeState(() => { state.search.freeNights = event.target.checked; });
});
$("#budget-currency").addEventListener("change", (event) => {
  haptic();
  changeState(() => { state.search.budgetCurrency = event.target.value; });
});
$("#search-reset").addEventListener("click", () => {
  haptic();
  changeState(() => {
    const { budgetPerNight, budgetCurrency } = state.search;
    state.search = { ...HotelModel.defaultSearch(), budgetPerNight, budgetCurrency };
  });
});
$("#children-ages").addEventListener("change", (event) => {
  const select = event.target.closest("[data-child]");
  if (!select) return;
  haptic();
  changeState(() => { state.childrenAges[Number(select.dataset.child)] = select.value === "" ? null : Number(select.value); });
});
for (const input of $$("[data-input]")) {
  input.addEventListener("input", () => changeState(() => setPath(state, input.dataset.input, input.value)));
  input.addEventListener("blur", () => { touched.add(input.dataset.input); renderForm(); });
}

tg.MainButton.onClick(() => {
  if (screen === "form") {
    openReview();
  } else if (screen === "calendar") {
    const dates = calendar.confirm();
    if (!dates) return;
    changeState(() => { state.dates = dates; state.datesComment = calendar.comment(); });
    touched.add("dates");
    openForm();
  } else if (screen === "review") {
    submit();
  }
});
tg.BackButton.onClick(() => {
  // The calendar keeps the last confirmed dates when closed with Back (D-14).
  if (screen === "calendar" || (screen === "review" && !submitting)) openForm();
});

tg.ready();
tg.expand();
load();
