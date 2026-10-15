"use strict";

// Texts from locales/*.toml; the server puts them into the page as window.LOCALES (see miniapp_api.py).
// Static markup names its texts with data-t (text), data-t-placeholder and data-t-label (aria-label).
const I18n = (() => {
  const locales = window.LOCALES || {};
  const fallback = window.DEFAULT_LANG || "ru";
  let lang = fallback;

  // Telegram's language code ("en", "pt-br") mapped to an available language.
  function use(code) {
    const short = String(code || "").split("-")[0].toLowerCase();
    lang = locales[short] ? short : fallback;
    if (typeof document !== "undefined") document.documentElement.lang = lang;
  }

  function raw(key) {
    const value = (locales[lang] || {})[key];
    if (value !== undefined) return value;
    console.warn(`Missing text: ${key}`);
    return key;
  }

  function format(text, values) {
    return text.replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));
  }

  function t(key, values = {}) {
    const value = raw(key);
    return typeof value === "string" ? format(value, values) : value;
  }

  // Plural forms by CLDR category, the same as texts.plural_form on the backend; {n} defaults to the number.
  function tn(key, number, values = {}) {
    const forms = raw(key);
    const form = forms[new Intl.PluralRules(lang).select(number)] ?? forms.other;
    return format(form, { n: number, ...values });
  }

  function apply(root = document) {
    for (const node of root.querySelectorAll("[data-t]")) node.textContent = t(node.dataset.t);
    for (const node of root.querySelectorAll("[data-t-placeholder]")) node.placeholder = t(node.dataset.tPlaceholder);
    for (const node of root.querySelectorAll("[data-t-label]")) node.setAttribute("aria-label", t(node.dataset.tLabel));
  }

  return { use, t, tn, apply, get lang() { return lang; } };
})();
