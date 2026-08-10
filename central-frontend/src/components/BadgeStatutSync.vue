<script setup lang="ts">
import { computed } from "vue";
import type { StatutSync } from "../lib/types";

const props = defineProps<{ statut?: StatutSync | null }>();

const styles: Record<string, string> = {
  SUCCES: "border-success/30 bg-success/10 text-success",
  SUCCES_PARTIEL: "border-warning/40 bg-warning/15 text-warning-foreground",
  ECHEC: "border-destructive/30 bg-destructive/10 text-destructive",
};

const libelles: Record<string, string> = {
  SUCCES: "Synchronisé",
  SUCCES_PARTIEL: "Partiel",
  ECHEC: "Échec",
};

const cle = computed(() => props.statut ?? "");
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap"
    :class="styles[cle] ?? 'border-border bg-muted text-muted-foreground'"
  >
    {{ libelles[cle] ?? "Jamais synchronisé" }}
  </span>
</template>
