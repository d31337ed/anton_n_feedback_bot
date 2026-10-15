"use strict";

// Summary rows that expand in place; at most one is open at a time (UI requirements P-3).
// Markup: <div data-accordion="name"><button data-accordion-toggle aria-expanded>…</button><div data-accordion-body hidden>…</div></div>
class Accordion {
  constructor(root, { onToggle = () => {} } = {}) {
    this.root = root;
    this.onToggle = onToggle;
    root.addEventListener("click", (event) => {
      const toggle = event.target.closest("[data-accordion-toggle]");
      if (!toggle || !root.contains(toggle)) return;
      // A control inside the row, like an (i) button, does its own thing.
      if (event.target.closest("button, [role=button]") !== toggle) return;
      const name = toggle.closest("[data-accordion]").dataset.accordion;
      this.toggle(name);
    });
  }

  items() {
    return Array.from(this.root.querySelectorAll("[data-accordion]"));
  }

  isOpen(name) {
    const item = this.root.querySelector(`[data-accordion="${name}"]`);
    return Boolean(item && !item.querySelector("[data-accordion-body]").hidden);
  }

  open(name) {
    for (const item of this.items()) this.set(item, item.dataset.accordion === name);
    this.onToggle(name);
  }

  close() {
    for (const item of this.items()) this.set(item, false);
    this.onToggle(null);
  }

  toggle(name) {
    if (this.isOpen(name)) this.close();
    else this.open(name);
  }

  set(item, open) {
    item.querySelector("[data-accordion-body]").hidden = !open;
    item.querySelector("[data-accordion-toggle]").setAttribute("aria-expanded", String(open));
    item.classList.toggle("open", open);
  }
}
