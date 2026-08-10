<script setup lang="ts">
import { Loader2 } from "lucide-vue-next";

withDefaults(defineProps<{ libelle?: string }>(), { libelle: "Chargement des données…" });
</script>

<template>
  <div class="flex items-center justify-center gap-3 py-12 text-sm text-muted-foreground">
    <Loader2 class="size-4 animate-spin" />
    {{ libelle }}
  </div>
</template>
