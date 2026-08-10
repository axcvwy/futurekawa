<script setup lang="ts">
import type { NiveauAlerte } from "../lib/types";

const props = defineProps<{ niveau: NiveauAlerte }>();

const styles: Record<string, string> = {
  ELEVE: "border-destructive/40 bg-destructive/15 text-destructive",
  MOYEN: "border-warning/40 bg-warning/15 text-warning-foreground",
};

const libelles: Record<string, string> = { ELEVE: "Élevé", MOYEN: "Moyen" };
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap"
    :class="styles[props.niveau] ?? 'border-border bg-muted text-muted-foreground'"
  >
    {{ libelles[props.niveau] ?? props.niveau }}
  </span>
</template>
