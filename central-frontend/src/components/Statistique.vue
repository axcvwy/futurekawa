<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  libelle: string;
  valeur: string | number;
  detail?: string;
  ton?: "neutre" | "alerte" | "succes" | "avertissement";
}>();

const tons: Record<string, string> = {
  neutre: "text-foreground",
  alerte: "text-destructive",
  succes: "text-accent",
  avertissement: "text-warning-foreground",
};

const classeValeur = computed(() => tons[props.ton ?? "neutre"] ?? "text-foreground");
</script>

<template>
  <div class="surface-carte p-4">
    <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ libelle }}</p>
    <p class="mt-1 font-display text-3xl font-semibold" :class="classeValeur">{{ valeur }}</p>
    <p v-if="detail" class="mt-1 text-xs text-muted-foreground">{{ detail }}</p>
  </div>
</template>
