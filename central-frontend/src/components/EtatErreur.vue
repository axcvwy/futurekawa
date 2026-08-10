<script setup lang="ts">
import { computed } from "vue";
import { AlertTriangle } from "lucide-vue-next";
import { API_BASE_URL } from "../lib/api";

const props = defineProps<{ erreur?: unknown }>();

const message = computed(() =>
  props.erreur instanceof Error ? props.erreur.message : "Erreur inconnue",
);
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-10 text-center">
    <AlertTriangle class="size-5 text-destructive" />
    <p class="text-sm font-medium text-destructive">Impossible de contacter le backend central</p>
    <p class="max-w-md text-xs text-muted-foreground">{{ message }}</p>
    <p class="text-xs text-muted-foreground">
      API attendue sur <code class="font-mono">{{ API_BASE_URL }}</code> — vérifiez que le service siège est démarré.
    </p>
  </div>
</template>
