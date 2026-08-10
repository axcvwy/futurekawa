<script setup lang="ts">
import type { StatutAlerte } from "../lib/types";

const props = defineProps<{ statut: StatutAlerte | string }>();

const styles: Record<string, string> = {
  ACTIVE: "border-destructive/30 bg-destructive/10 text-destructive",
  PRISE_EN_COMPTE: "border-warning/40 bg-warning/15 text-warning-foreground",
  RESOLUE: "border-success/30 bg-success/10 text-success",
  IGNOREE: "border-border bg-muted text-muted-foreground",
};

const libelles: Record<string, string> = {
  ACTIVE: "Active",
  PRISE_EN_COMPTE: "Prise en compte",
  RESOLUE: "Résolue",
  IGNOREE: "Ignorée",
};
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap"
    :class="styles[props.statut] ?? 'border-border bg-muted text-muted-foreground'"
  >
    {{ libelles[props.statut] ?? props.statut }}
  </span>
</template>
