<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: number }>(), { size: 20 });

const paths: Record<string, string> = {
  overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  strength: "M4 20V10 M12 20V4 M20 20v-7 M2 20h20",
  pattern: "m12 3 9 5-9 5-9-5z M3 12l9 5 9-5 M3 16l9 5 9-5",
  relations: "M8 6h8 M6 8v8 M8 18h8 M18 8v8 M8 8l8 8 M4 4h4v4H4z M16 4h4v4h-4z M4 16h4v4H4z M16 16h4v4h-4z",
  structure: "M9 3h6v5H9z M3 16h6v5H3z M15 16h6v5h-6z M12 8v4 M6 16v-4h12v4",
  tiaohou: "M12 3v2 M12 19v2 M3 12h2 M19 12h2 M5.5 5.5 7 7 M17 17l1.5 1.5 M5.5 18.5 7 17 M17 7l1.5-1.5 M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  advanced: "m12 3 9 9-9 9-9-9z M12 7v10 M7 12h10",
  temporal: "M21 12a9 9 0 1 1-9-9 M12 7v5l4 2 M17 3h4v4",
  knowledge: "M8 5h8 M6 8l5 8 M18 8l-5 8 M8 5a2 2 0 1 1-4 0 2 2 0 0 1 4 0 M20 5a2 2 0 1 1-4 0 2 2 0 0 1 4 0 M14 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0",
  ai: "M4 4h16v13H9l-5 4z M8 9h8 M8 13h5",
  report: "M5 3h10l4 4v14H5z M14 3v5h5 M9 12h6 M9 16h6",
  menu: "M4 6h16 M4 12h16 M4 18h16",
  close: "m6 6 12 12 M6 18 18 6",
  settings: "M4 7h16 M4 17h16 M8 4v6 M16 14v6",
  home: "m3 10 9-7 9 7 M5 9v12h14V9 M9 21v-7h6v7",
  compass: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M16 8l-3 5-5 3 3-5z",
};
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="ui-icon">
    <path :d="paths[name] ?? paths.compass" />
  </svg>
</template>
