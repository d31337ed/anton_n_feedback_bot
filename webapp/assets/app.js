"use strict";

const tg = window.Telegram.WebApp;
const requestId = new URLSearchParams(location.search).get("request_id");

// Request statuses the server may answer with; each has a notice under form.status.
const NOTICE_STATUSES = ["in_work", "closed", "not_found"];
const statusText = (code) => I18n.t(`form.status.${code}`);

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

// Texts first: everything below renders in the user's language.
I18n.use(tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code);
I18n.apply();

let config = { maxNights: 30, horizonMonths: 15, flexMonths: 12, flexNights: [1, 21], maxDatesComment: 500, adults: [1, 6], maxChildren: 6, maxChildAge: 17 };
let state = HotelModel.defaults();
let initialSnapshot = JSON.stringify(state);
const touched = new Set();
let screen = null;
let idempotencyKey = null;
let submitting = false;
let commentOpen = false;
let calendar = null;

// The root is the whole form: the city block and the main rows share one open-at-a-time accordion.
const accordion = new Accordion($("#screen-form"), { onToggle: () => haptic() });

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

buildChoices($("#category-chips"), "room.category", HotelModel.choices.categories(), "radio");
buildChoices($("#bed-segmented"), "room.bed", HotelModel.choices.beds(), "radio");
buildChoices($("#hotel-type-segmented"), "search.hotelType", HotelModel.choices.hotelTypes(), "radio");
buildChoices($("#currency-chips"), "currency", HotelModel.choices.currencies(), "radio");
$("#budget-unit").replaceChildren(...Object.entries(HotelModel.choices.budgetUnits()).map(([value, label]) => el("option", { value }, label)));
$("#budget-currency").replaceChildren(...Object.entries(HotelModel.choices.currencies()).map(([value, label]) => el("option", { value }, label)));

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
    const options = [el("option", { value: "" }, I18n.t("form.guests.age")), el("option", { value: "0" }, I18n.t("form.guests.age_under_one"))];
    for (let year = 1; year <= config.maxChildAge; year++) options.push(el("option", { value: String(year) }, I18n.tn("form.guests.years", year)));
    const select = el("select", { "data-child": String(i), "aria-label": I18n.t("form.guests.age_label", { n: i + 1 }) }, ...options);
    select.value = age === null ? "" : String(age);
    return el("div", { class: "row" }, el("span", { class: "hint" }, I18n.t("form.guests.child", { n: i + 1 })), select);
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
  datesValue.textContent = state.dates ? state.dates.label : I18n.t("form.dates.choose");
  datesValue.classList.toggle("accent", !state.dates);

  const kids = state.childrenAges.length;
  const [minAdults, maxAdults] = config.adults;
  $("[data-output=adults]").value = state.adults;
  $("[data-output=adults]").classList.toggle("changed", state.adults !== 2);
  $("[data-output=children]").value = kids;
  $("[data-output=children]").classList.toggle("changed", kids > 0);
  for (const button of $$('[data-step="adults"]')) button.disabled = button.dataset.delta < 0 ? state.adults <= minAdults : state.adults >= maxAdults;
  for (const button of $$('[data-step="children"]')) button.disabled = button.dataset.delta < 0 ? kids <= 0 : kids >= config.maxChildren;
  renderChildrenAges();

  $("#room-value").textContent = HotelModel.roomText(state.room);
  $("#custom-room").hidden = state.room.category !== "custom";
  $("#search-value").textContent = HotelModel.searchText(state);
  $("#free-nights").checked = state.search.freeNights;
  $("#budget-currency").value = HotelModel.budgetCurrency(state);
  $("#budget-unit").value = state.search.budgetUnit;

  const changed = HotelModel.changed(state);
  $("#room-value").classList.toggle("changed", changed.room);
  $("#search-value").classList.toggle("changed", changed.search);

  $("#comment-box").hidden = !(commentOpen || state.comment);
  $("#comment-link").hidden = !$("#comment-box").hidden;

  const errors = HotelModel.validate(state);
  for (const node of $$("[data-error]")) {
    const name = node.dataset.error;
    node.textContent = touched.has(name) && errors[name] ? errors[name] : "";
  }
  // A warning, not an error: shown once the user has left the field, and it does not block sending.
  $("#budget-low").hidden = !(touched.has("search.budget") && !errors["search.budget"] && HotelModel.lowBudget(state));
  for (const input of $$("[data-input]")) input.classList.toggle("invalid", touched.has(input.dataset.input) && Boolean(errors[input.dataset.input]));
  updateButtons();
  updateClosingConfirmation();
  return errors;
}

function renderReview() {
  const list = $("#review-list");
  list.replaceChildren(...HotelModel.reviewRows(HotelModel.payload(state)).map((row) => {
    const edit = el("button", { type: "button", class: "link-button" }, I18n.t("form.review.edit"));
    edit.addEventListener("click", () => editFromReview(row.key));
    return el("div", { class: "review-item" },
      el("div", {}, ...(row.label ? [el("div", { class: "review-key" }, row.label)] : []),
        el("div", { class: `review-value${row.label ? "" : " standalone"}${row.isDefault ? " default" : ""}` }, row.value)),
      edit);
  }));
  $("#review-error").hidden = true;
}

function cssColor(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// The page has one dark palette whatever Telegram's scheme; Telegram's chrome is repainted to match.
function applyTheme() {
  const bg = cssColor("--bg");
  if (tg.isVersionAtLeast("6.9")) {
    tg.setHeaderColor(bg);
    tg.setBackgroundColor(bg);
  }
  if (tg.isVersionAtLeast("7.10")) tg.setBottomBarColor(bg);
}

function mainButton(text, active) {
  tg.MainButton.setParams({
    text, is_visible: true, is_active: active,
    color: cssColor(active ? "--accent" : "--hint"),
    text_color: cssColor("--accent-text"),
  });
}

function updateButtons() {
  if (screen === "form") {
    mainButton(I18n.t("form.buttons.check"), Object.keys(HotelModel.validate(state)).length === 0);
    tg.BackButton.hide();
  } else if (screen === "calendar") {
    const { text, active } = calendar.mainButton();
    mainButton(text, active);
    tg.BackButton.show();
  } else if (screen === "review") {
    mainButton(I18n.t("form.buttons.send"), !submitting);
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
  if (key === "budget") { accordion.open("search"); return focusOn($("#budget")); }
  if (key === "currency") return focusOn($("#currency-chips button[aria-checked=true]"));
  if (key === "comment") { commentOpen = true; renderForm(); return focusOn($("#comment")); }
  if (key === "guests") return focusOn($('[data-step="adults"]'));
  accordion.open(key);
  $(`[data-accordion="${key}"]`).scrollIntoView({ block: "start" });
}

function openReview() {
  for (const name of ["hotel", "city", "dates", "room.customText", "search.budget", "comment"]) touched.add(name);
  const errors = renderForm();
  const first = Object.keys(errors)[0];
  if (first) {
    if (first === "room.customText") accordion.open("room");
    if (first === "search.budget") accordion.open("search");
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
    return showNotice(statusText("network"), load);
  }
  const { status, data } = response;
  if (status === 401 || status === 403) return showNotice(statusText("unauthorized"));
  if (status === 404) return showNotice(statusText("not_found"));
  if (status !== 200) return showNotice(statusText("network"), load);
  if (data.status === "in_work" || data.status === "closed") return showNotice(statusText(data.status));
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
  if (response && response.status === 409 && NOTICE_STATUSES.includes(code)) return showNotice(statusText(code));
  if (response && (response.status === 401 || response.status === 403)) return showNotice(statusText("unauthorized"));
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
    ? statusText("sending")
    : statusText("send_failed");
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
        state.childrenAges.pop();
      }
    });
    return;
  }
  const info = event.target.closest("[data-info]");
  if (info) {
    const message = I18n.t(`form.info.${info.dataset.info}`);
    if (tg.showPopup) tg.showPopup({ message, buttons: [{ type: "ok" }] });
    else window.alert(message);
  }
});

$("#dates-row").addEventListener("click", openCalendar);
$("#comment-link").addEventListener("click", () => {
  commentOpen = true;
  renderForm();
  $("#comment").focus();
});
$("#free-nights").addEventListener("change", (event) => {
  haptic();
  changeState(() => { state.search.freeNights = event.target.checked; });
});
$("#budget-unit").addEventListener("change", (event) => {
  haptic();
  changeState(() => { state.search.budgetUnit = event.target.value; });
});
$("#budget-currency").addEventListener("change", (event) => {
  haptic();
  changeState(() => { state.search.budgetCurrency = event.target.value; });
});
$("#search-reset").addEventListener("click", () => {
  haptic();
  changeState(() => {
    state.search = HotelModel.defaultSearch();
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

// Pinch zoom on iOS ignores the viewport meta in some web views.
document.addEventListener("gesturestart", (event) => event.preventDefault());
applyTheme();
tg.ready();
tg.expand();
load();
