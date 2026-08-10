<script setup lang="ts">
defineProps<{ titre: string; description?: string }>();
</script>

<template>
  <section class="surface-carte p-5">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="font-display text-lg font-semibold">{{ titre }}</h2>
        <p v-if="description" class="text-sm text-muted-foreground">{{ description }}</p>
      </div>
      <slot name="action" />
    </div>
    <slot />
  </section>
</template>
