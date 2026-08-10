<script setup lang="ts">
import { Inbox } from "lucide-vue-next";

withDefaults(defineProps<{ libelle?: string }>(), { libelle: "Aucune donnée à afficher." });
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
    <Inbox class="size-5" />
    {{ libelle }}
  </div>
</template>
