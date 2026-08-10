<script setup lang="ts">
import { computed } from "vue";
import { RouterView, useRoute } from "vue-router";
import { Toaster } from "vue-sonner";
import EnTete from "./components/EnTete.vue";

const route = useRoute();
const pagePublique = computed(() => Boolean(route.meta.public));
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background">
    <EnTete v-if="!pagePublique" />
    <main class="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
      <RouterView />
    </main>
    <footer class="border-t border-border py-4 text-center text-xs text-muted-foreground">
      FutureKawa · Console siège
    </footer>
  </div>
  <Toaster position="top-right" rich-colors />
</template>
