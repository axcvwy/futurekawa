<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ statut?: string | null }>();

const styles: Record<string, string> = {
  EN_STOCK: "border-accent/30 bg-accent/10 text-accent",
  EXPEDIE: "border-border bg-muted text-muted-foreground",
  PERDU: "border-destructive/30 bg-destructive/10 text-destructive",
};

const cle = computed(() => props.statut ?? "");
const libelle = computed(() =>
  (props.statut ?? "inconnu").replaceAll("_", " ").toLowerCase(),
);
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap"
    :class="styles[cle] ?? 'border-border bg-muted text-muted-foreground'"
  >
    {{ libelle }}
  </span>
</template>
