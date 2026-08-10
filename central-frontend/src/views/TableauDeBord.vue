<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { AlertTriangle, PackageSearch, Thermometer, Warehouse } from "lucide-vue-next";
import Section from "../components/Section.vue";
import Statistique from "../components/Statistique.vue";
import EtatChargement from "../components/EtatChargement.vue";
import EtatVide from "../components/EtatVide.vue";
import BadgeNiveau from "../components/BadgeNiveau.vue";
import BadgeStatutLot from "../components/BadgeStatutLot.vue";
import BadgeStatutSync from "../components/BadgeStatutSync.vue";
import { useSelection } from "../stores/selection";
import { useFetch } from "../lib/useFetch";
import { apiGet } from "../lib/api";
import { depuisMaintenant, formaterDate, formaterNombre, joursDepuis } from "../lib/format";
import type { Alerte, Entrepot, Lot, Sante } from "../lib/types";

const { paysId, exploitationId } = useSelection();

const lots = useFetch(
  () =>
    apiGet<Lot[]>("/lots", {
      pays_id: paysId.value,
      exploitation_id: exploitationId.value,
      ordre: "fifo",
    }),
  { watchSources: [paysId, exploitationId] },
);
const alertes = useFetch(
  () => apiGet<Alerte[]>("/alertes", { statut: "ACTIVE", pays_id: paysId.value }),
  { watchSources: [paysId] },
);
const entrepots = useFetch(
  () =>
    apiGet<Entrepot[]>("/entrepots", {
      pays_id: paysId.value,
      exploitation_id: exploitationId.value,
    }),
  { watchSources: [paysId, exploitationId] },
);
const sante = useFetch(() => apiGet<Sante>("/health"), { interval: 30_000 });

const enStock = computed(() => (lots.data ?? []).filter((l) => (l.statut ?? "EN_STOCK") === "EN_STOCK"));
const quantite = computed(() => enStock.value.reduce((total, l) => total + (l.quantite_kg ?? 0), 0));
const plusAncien = computed(() => enStock.value[0]);
const paysActifs = computed(() => (sante.data?.pays ?? []).filter((p) => p.actif));
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="font-display text-2xl font-semibold">Tableau de bord consolidé</h1>
      <p class="text-sm text-muted-foreground">
        Stocks, conditions de conservation et alertes.
      </p>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Statistique
        libelle="Lots en stock"
        :valeur="lots.isLoading ? '…' : enStock.length"
        :detail="`${lots.data?.length ?? 0} lots consolidés`"
      />
      <Statistique
        libelle="Quantité stockée"
        :valeur="lots.isLoading ? '…' : formaterNombre(quantite)"
        detail="kilogrammes de café vert"
      />
      <Statistique
        libelle="Alertes actives"
        :valeur="alertes.isLoading ? '…' : (alertes.data?.length ?? 0)"
        detail="à traiter par la supervision"
        :ton="(alertes.data?.length ?? 0) > 0 ? 'alerte' : 'succes'"
      />
      <Statistique
        libelle="Entrepôts suivis"
        :valeur="entrepots.isLoading ? '…' : (entrepots.data?.length ?? 0)"
        :detail="`${paysActifs.length} pays actifs`"
      />
    </div>

    <div class="grid gap-6 lg:grid-cols-3">
      <Section
        titre="Rotation FIFO — lots les plus anciens"
        description="Les lots à sortir en priorité, triés par date de stockage croissante."
        class="lg:col-span-2"
      >
        <template #action>
          <RouterLink to="/lots" class="text-sm font-medium text-accent hover:underline">
            Voir tous les lots
          </RouterLink>
        </template>

        <EtatChargement v-if="lots.isLoading" />
        <EtatVide v-else-if="enStock.length === 0" libelle="Aucun lot en stock pour cette sélection." />
        <ul v-else class="divide-y divide-border">
          <li v-for="lot in enStock.slice(0, 6)" :key="lot.id">
            <RouterLink
              :to="`/lots/${lot.id}`"
              class="flex flex-wrap items-center gap-3 py-3 transition-colors hover:bg-muted/50"
            >
              <PackageSearch class="size-4 text-muted-foreground" />
              <span class="font-mono text-sm font-medium">{{ lot.code_lot }}</span>
              <span class="text-sm text-muted-foreground">{{ lot.produit ?? "Café" }}</span>
              <BadgeStatutLot :statut="lot.statut" />
              <span class="ml-auto text-sm text-muted-foreground">
                {{ formaterNombre(lot.quantite_kg, " kg") }}
              </span>
              <span class="w-40 text-right text-sm">
                {{ formaterDate(lot.date_stockage) }}
                <span v-if="joursDepuis(lot.date_stockage) !== null" class="ml-2 text-xs text-muted-foreground">
                  {{ joursDepuis(lot.date_stockage) }} j
                </span>
              </span>
            </RouterLink>
          </li>
        </ul>

        <p v-if="plusAncien" class="mt-3 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
          <Warehouse class="mr-1 inline size-3.5" />
          Lot bloquant la sortie FIFO : <strong>{{ plusAncien.code_lot }}</strong> stocké le
          {{ formaterDate(plusAncien.date_stockage) }}.
        </p>
      </Section>

      <Section
        titre="Fil d'alertes"
        description="Alertes actives remontées par les capteurs."
      >
        <template #action>
          <RouterLink to="/alertes" class="text-sm font-medium text-accent hover:underline">
            Superviser
          </RouterLink>
        </template>

        <EtatChargement v-if="alertes.isLoading" />
        <EtatVide v-else-if="(alertes.data?.length ?? 0) === 0" libelle="Aucune alerte active. Conditions nominales." />
        <ul v-else class="space-y-3">
          <li
            v-for="alerte in (alertes.data ?? []).slice(0, 6)"
            :key="alerte.id"
            class="rounded-lg border border-border p-3"
          >
            <div class="flex items-center gap-2">
              <AlertTriangle class="size-4 text-destructive" />
              <span class="text-sm font-medium">
                {{ alerte.type_alerte.replaceAll("_", " ").toLowerCase() }}
              </span>
              <span class="ml-auto"><BadgeNiveau :niveau="alerte.niveau" /></span>
            </div>
            <p class="mt-1 text-xs text-muted-foreground">{{ alerte.message }}</p>
            <p class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              <Thermometer class="size-3.5" />
              {{ alerte.entrepot?.nom ?? "Entrepôt inconnu" }} · {{ depuisMaintenant(alerte.date_declenchement) }}
            </p>
          </li>
        </ul>
      </Section>
    </div>

    <Section
      titre="État des connexions pays"
      description="Statut de la dernière synchronisation du siège avec chaque backend pays."
    >
      <template #action>
        <RouterLink to="/pays" class="text-sm font-medium text-accent hover:underline">
          Pilotage
        </RouterLink>
      </template>

      <EtatChargement v-if="sante.isLoading" />
      <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="p in sante.data?.pays ?? []" :key="p.code_iso" class="rounded-lg border border-border p-3">
          <div class="flex items-center gap-2">
            <span class="font-medium">{{ p.nom }}</span>
            <span class="font-mono text-xs text-muted-foreground">{{ p.code_iso }}</span>
            <span class="ml-auto"><BadgeStatutSync :statut="p.dernier_statut_sync" /></span>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">
            Dernière réussite : {{ depuisMaintenant(p.derniere_sync_reussie_le) }}
            <template v-if="p.mock"> · source simulée</template>
          </p>
          <p v-if="p.derniere_erreur_sync" class="mt-1 text-xs text-destructive">
            {{ p.derniere_erreur_sync }}
          </p>
        </div>
      </div>
    </Section>
  </div>
</template>
