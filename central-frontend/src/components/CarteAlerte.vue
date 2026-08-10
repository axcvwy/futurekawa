<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import BadgeNiveau from "./BadgeNiveau.vue";
import BadgeStatutAlerte from "./BadgeStatutAlerte.vue";
import { formaterDateHeure, formaterNombre } from "../lib/format";
import { useAuth, ROLES } from "../stores/auth";
import type { Alerte, StatutAlerte } from "../lib/types";

const props = defineProps<{
  alerte: Alerte;
  enCours: boolean;
}>();

const emit = defineEmits<{
  (e: "mettre-a-jour", statut: StatutAlerte, commentaire?: string): void;
}>();

const { role } = useAuth();

// Le responsable d'entrepôt ne peut qu'acquitter : il voit seulement « Prendre en compte ».
const estResponsableEntrepot = computed(() => role.value === ROLES.RESPONSABLE_ENTREPOT);

const commentaire = ref("");
const ouvert = ref(false);

function resoluer(): void {
  if (!ouvert.value) {
    ouvert.value = true;
    return;
  }
  emit("mettre-a-jour", "RESOLUE", commentaire.value || undefined);
}
</script>

<template>
  <li class="rounded-lg border border-border p-4">
    <div class="flex flex-wrap items-center gap-3">
      <span class="font-medium">{{ alerte.type_alerte.replaceAll("_", " ").toLowerCase() }}</span>
      <BadgeNiveau :niveau="alerte.niveau" />
      <BadgeStatutAlerte :statut="alerte.statut" />
      <span class="ml-auto text-xs text-muted-foreground">
        {{ formaterDateHeure(alerte.date_declenchement) }}
      </span>
    </div>
    <p class="mt-2 text-sm text-muted-foreground">{{ alerte.message }}</p>
    <p class="mt-1 text-xs text-muted-foreground">
      {{ alerte.pays?.nom ?? "Pays inconnu" }} · {{ alerte.entrepot?.nom ?? "Entrepôt inconnu" }} · valeur
      détectée {{ formaterNombre(alerte.valeur_detectee) }} (seuils
      {{ formaterNombre(alerte.seuil_minimum) }} – {{ formaterNombre(alerte.seuil_maximum) }})
      <template v-if="alerte.email_envoye"> · email envoyé le {{ formaterDateHeure(alerte.date_email) }}</template>
    </p>
    <RouterLink
      v-if="alerte.lot_id"
      :to="`/lots/${alerte.lot_id}`"
      class="mt-1 inline-block text-xs font-medium text-accent hover:underline"
    >
      Consulter le lot concerné
    </RouterLink>
    <p v-if="alerte.commentaire_resolution" class="mt-2 rounded-md bg-muted px-3 py-2 text-xs">
      Commentaire : {{ alerte.commentaire_resolution }}
    </p>

    <div v-if="alerte.statut !== 'RESOLUE' && alerte.statut !== 'IGNOREE'" class="mt-3 space-y-2">
      <textarea
        v-if="ouvert"
        v-model="commentaire"
        placeholder="Commentaire de résolution (facultatif)"
        rows="2"
        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
      ></textarea>
      <div class="flex flex-wrap gap-2">
        <button
          v-if="alerte.statut === 'ACTIVE'"
          class="inline-flex items-center rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted/50 disabled:opacity-50"
          :disabled="enCours"
          @click="emit('mettre-a-jour', 'PRISE_EN_COMPTE')"
        >
          Prendre en compte
        </button>
        <button
          v-if="!estResponsableEntrepot"
          class="inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          :disabled="enCours"
          @click="resoluer"
        >
          {{ ouvert ? "Confirmer la résolution" : "Résoudre" }}
        </button>
        <button
          v-if="!estResponsableEntrepot"
          class="inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/50 disabled:opacity-50"
          :disabled="enCours"
          @click="emit('mettre-a-jour', 'IGNOREE')"
        >
          Ignorer
        </button>
      </div>
    </div>
  </li>
</template>
