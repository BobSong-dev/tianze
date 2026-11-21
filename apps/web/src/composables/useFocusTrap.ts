import { nextTick, onBeforeUnmount, watch, type Ref } from "vue";

export function useFocusTrap(open: Ref<boolean>, container: Ref<HTMLElement | null>, close: () => void) {
  let previous: HTMLElement | null = null;
  const focusable = () => Array.from(container.value?.querySelectorAll<HTMLElement>(
    'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]',
  ) ?? []).filter(element => element.getClientRects().length > 0 && !element.closest("[inert]"));

  function onKey(event: KeyboardEvent) {
    if (!open.value || container.value?.closest("[inert]") || event.defaultPrevented) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== "Tab") return;
    const controls = focusable();
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (!first) { event.preventDefault(); return; }
    if (event.shiftKey && (document.activeElement === first || !container.value?.contains(document.activeElement))) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && (document.activeElement === last || !container.value?.contains(document.activeElement))) {
      event.preventDefault();
      first.focus();
    }
  }

  watch(open, async active => {
    if (active) {
      previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      document.addEventListener("keydown", onKey);
      await nextTick();
      if (open.value) focusable()[0]?.focus();
    } else {
      document.removeEventListener("keydown", onKey);
      await nextTick();
      if (previous?.isConnected && !previous.closest("[inert]") && previous.getClientRects().length) previous.focus();
    }
  });
  onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
}
