<script setup lang="ts">
import { computed, ref } from "vue";
import { toast } from "vue-sonner";
import Section from "../components/Section.vue";
import Statistique from "../components/Statistique.vue";
import EtatChargement from "../components/EtatChargement.vue";
import EtatErreur from "../components/EtatErreur.vue";
import EtatVide from "../components/EtatVide.vue";
import CarteAlerte from "../components/CarteAlerte.vue";
import { useSelection } from "../stores/selection";
import { useFetch } from "../lib/useFetch";
import { apiEnvoyer, apiGet } from "../lib/api";
import type { Alerte, StatutAlerte } from "../lib/types";

const { paysId } = useSelection();

const statut = ref<string | undefined>("ACTIVE");
const type = ref<string | undefined>(undefined);

const alertes = useFetch(
  () =>
    apiGet<Alerte[]>("/alertes", {
      statut: statut.value === "tous" ? undefined : statut.value,
      pays_id: paysId.value,
      type_alerte: type.value === "tous" ? undefined : type.value,
    }),
  { watchSources: [statut, type, paysId] },
);

const toutes = useFetch(
  () => apiGet<Alerte[]>("/alertes", { pays_id: paysId.value, limite: 200 }),
  { watchSources: [paysId] },
);

const types = computed(() => Array.from(new Set((toutes.data ?? []).map((a) => a.type_alerte))));

const enCours = ref(false);

async function mettreAJour(id: string, nouveauStatut: StatutAlerte, commentaire?: string): Promise<void> {
  enCours.value = true;
  try {
    const donnees = await apiEnvoyer<Alerte>("PATCH", `/alertes/${id}`, {
      statut: nouveauStatut,
      commentaire_resolution: commentaire ?? null,
    });
    toast.success("Alerte mise à jour", {
      description: donnees.transfert_local
        ? `Transfert vers le backend pays : ${donnees.transfert_local}`
        : undefined,
    });
    void alertes.recharger();
    void toutes.recharger();
  } catch (e) {
    toast.error("Échec de la mise à jour", {
      description: e instanceof Error ? e.message : "Erreur inconnue",
    });
  } finally {
    enCours.value = false;
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="font-display text-2xl font-semibold">Supervision des alertes</h1>
      <p class="text-sm text-muted-foreground">
        Prise en compte, résolution et historique des dépassements de seuils.
      </p>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Statistique
        libelle="Actives"
        :valeur="(toutes.data ?? []).filter((a) => a.statut === 'ACTIVE').length"
        ton="alerte"
      />
      <Statistique
        libelle="Prises en compte"
        :valeur="(toutes.data ?? []).filter((a) => a.statut === 'PRISE_EN_COMPTE').length"
        ton="avertissement"
      />
      <Statistique
        libelle="Résolues"
        :valeur="(toutes.data ?? []).filter((a) => a.statut === 'RESOLUE').length"
        ton="succes"
      />
      <Statistique
        libelle="Emails envoyés"
        :valeur="(toutes.data ?? []).filter((a) => a.email_envoye).length"
        detail="notifications responsables"
      />
    </div>

    <Section titre="Alertes" description="Filtrez par statut et par type d'alerte.">
      <div class="mb-4 grid gap-3 sm:grid-cols-2 lg:w-2/3">
        <select
          v-model="statut"
          class="h-9 rounded-md border border-input bg-background px-2 text-sm outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="tous">Tous les statuts</option>
          <option value="ACTIVE">Active</option>
          <option value="PRISE_EN_COMPTE">Prise en compte</option>
          <option value="RESOLUE">Résolue</option>
          <option value="IGNOREE">Ignorée</option>
        </select>
        <select
          v-model="type"
          class="h-9 rounded-md border border-input bg-background px-2 text-sm outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="tous">Tous les types</option>
          <option v-for="t in types" :key="t" :value="t">
            {{ t.replaceAll("_", " ").toLowerCase() }}
          </option>
        </select>
      </div>

      <EtatErreur v-if="alertes.isError" :erreur="alertes.error" />
      <EtatChargement v-else-if="alertes.isLoading" />
      <EtatVide v-else-if="(alertes.data?.length ?? 0) === 0" libelle="Aucune alerte pour ces filtres." />
      <ul v-else class="space-y-3">
        <CarteAlerte
          v-for="alerte in alertes.data ?? []"
          :key="alerte.id"
          :alerte="alerte"
          :en-cours="enCours"
          @mettre-a-jour="(s, c) => mettreAJour(alerte.id, s, c)"
        />
      </ul>
    </Section>
  </div>
</template>
