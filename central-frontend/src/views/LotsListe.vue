<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import { toast } from "vue-sonner";
import { ArrowDownUp, PackagePlus, X } from "lucide-vue-next";
import Section from "../components/Section.vue";
import EtatChargement from "../components/EtatChargement.vue";
import EtatErreur from "../components/EtatErreur.vue";
import EtatVide from "../components/EtatVide.vue";
import BadgeStatutLot from "../components/BadgeStatutLot.vue";
import { useSelection } from "../stores/selection";
import { useAuth, ROLES } from "../stores/auth";
import { useFetch } from "../lib/useFetch";
import { apiEnvoyer, apiGet } from "../lib/api";
import { formaterDate, formaterNombre, joursDepuis } from "../lib/format";
import type { Entrepot, Lot } from "../lib/types";

const { paysId, exploitationId } = useSelection();
const { role, utilisateur } = useAuth();

const entrepotId = ref<string | undefined>(undefined);
const statut = ref<string | undefined>(undefined);
const ordre = ref<"fifo" | "desc">("fifo");
const recherche = ref("");

// Les rôles opérationnels peuvent créer un lot ; le référent qualité non.
const peutCreerLot = computed(() => {
  const r = role.value;
  return (
    r === ROLES.ADMIN_SIEGE ||
    r === ROLES.RESPONSABLE_EXPLOITATION ||
    r === ROLES.RESPONSABLE_ENTREPOT
  );
});

const entrepots = useFetch(
  () =>
    apiGet<Entrepot[]>("/entrepots", {
      pays_id: paysId.value,
      exploitation_id: exploitationId.value,
    }),
  { watchSources: [paysId, exploitationId] },
);

const lots = useFetch(
  () =>
    apiGet<Lot[]>("/lots", {
      pays_id: paysId.value,
      exploitation_id: exploitationId.value,
      entrepot_id: entrepotId.value,
      statut: statut.value,
      ordre: ordre.value,
    }),
  { watchSources: [paysId, exploitationId, entrepotId, statut, ordre] },
);

const liste = computed(() => {
  const rechercheMin = recherche.value.trim().toLowerCase();
  return (lots.data ?? []).filter(
    (l) =>
      rechercheMin === "" ||
      `${l.code_lot} ${l.produit ?? ""}`.toLowerCase().includes(rechercheMin),
  );
});

// Formulaire de création de lot
const formulaireOuvert = ref(false);
const enCreation = ref(false);

const nouveauLot = ref({
  code_lot: "",
  entrepot_id: "",
  produit: "",
  quantite_kg: "",
  date_stockage: new Date().toISOString().slice(0, 10),
});

// Le responsable d'entrepôt ne peut créer que dans SON entrepôt.
const entrepotsAutorises = computed(() => {
  if (role.value === ROLES.RESPONSABLE_ENTREPOT) {
    return (entrepots.data ?? []).filter((e) => e.id === utilisateur.value?.entrepot_id);
  }
  return entrepots.data ?? [];
});

function ouvrirFormulaire(): void {
  nouveauLot.value = {
    code_lot: "",
    entrepot_id: entrepotsAutorises.value[0]?.id ?? "",
    produit: "Café vert Arabica",
    quantite_kg: "",
    date_stockage: new Date().toISOString().slice(0, 10),
  };
  formulaireOuvert.value = true;
}

async function creerLot(): Promise<void> {
  if (enCreation.value) return;
  enCreation.value = true;
  try {
    await apiEnvoyer<Lot>("POST", "/lots", {
      code_lot: nouveauLot.value.code_lot,
      entrepot_id: nouveauLot.value.entrepot_id,
      produit: nouveauLot.value.produit,
      quantite_kg: Number(nouveauLot.value.quantite_kg),
      date_stockage: nouveauLot.value.date_stockage,
    });
    toast.success("Lot créé", { description: `Le lot ${nouveauLot.value.code_lot} a été enregistré.` });
    formulaireOuvert.value = false;
    void lots.recharger();
  } catch (e) {
    toast.error("Création impossible", {
      description: e instanceof Error ? e.message : "Erreur inconnue",
    });
  } finally {
    enCreation.value = false;
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="font-display text-2xl font-semibold">Stocks et lots</h1>
      <p class="text-sm text-muted-foreground">
        Tri par défaut FIFO : le lot le plus ancien apparaît en premier.
      </p>
    </div>

    <Section
      :titre="`${liste.length} lot(s)`"
      description="Sélectionnez un lot pour consulter ses courbes température / humidité."
    >
      <template #action>
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-if="peutCreerLot"
            class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            @click="ouvrirFormulaire"
          >
            <PackagePlus class="size-4" />
            Nouveau lot
          </button>
          <button
            class="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted/50"
            @click="ordre = ordre === 'fifo' ? 'desc' : 'fifo'"
          >
            <ArrowDownUp class="size-4" />
            {{ ordre === "fifo" ? "Plus ancien d'abord (FIFO)" : "Plus récent d'abord" }}
          </button>
        </div>
      </template>

      <form
        v-if="formulaireOuvert"
        class="mb-6 rounded-lg border border-border bg-muted/30 p-4"
        @submit.prevent="creerLot"
      >
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold">Nouveau lot (écriture directe vers le pays)</h3>
          <button
            type="button"
            class="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted"
            title="Fermer"
            @click="formulaireOuvert = false"
          >
            <X class="size-4" />
          </button>
        </div>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Code lot</span>
            <input
              v-model="nouveauLot.code_lot"
              required
              placeholder="LOT-2026-…"
              class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Produit</span>
            <input
              v-model="nouveauLot.produit"
              required
              class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Quantité (kg)</span>
            <input
              v-model="nouveauLot.quantite_kg"
              required
              type="number"
              min="0"
              step="0.5"
              class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Date de stockage</span>
            <input
              v-model="nouveauLot.date_stockage"
              required
              type="date"
              class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Entrepôt</span>
            <select
              v-model="nouveauLot.entrepot_id"
              required
              class="h-9 w-full rounded-md border border-input bg-background px-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              <option v-for="e in entrepotsAutorises" :key="e.id" :value="e.id">
                {{ e.nom }}{{ e.ville ? ` · ${e.ville}` : "" }}
              </option>
            </select>
          </label>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/50"
            @click="formulaireOuvert = false"
          >
            Annuler
          </button>
          <button
            type="submit"
            :disabled="enCreation || entrepotsAutorises.length === 0"
            class="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            <PackagePlus class="size-4" />
            {{ enCreation ? "Enregistrement…" : "Enregistrer le lot" }}
          </button>
        </div>
      </form>

      <div class="mb-4 grid gap-3 sm:grid-cols-3">
        <input
          v-model="recherche"
          placeholder="Rechercher un code lot ou produit…"
          class="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
        <select
          v-model="entrepotId"
          class="h-9 rounded-md border border-input bg-background px-2 text-sm outline-none focus:ring-2 focus:ring-ring"
        >
          <option :value="undefined">Tous les entrepôts</option>
          <option v-for="e in entrepots.data ?? []" :key="e.id" :value="e.id">
            {{ e.nom }}{{ e.ville ? ` · ${e.ville}` : "" }}
          </option>
        </select>
        <select
          v-model="statut"
          class="h-9 rounded-md border border-input bg-background px-2 text-sm outline-none focus:ring-2 focus:ring-ring"
        >
          <option :value="undefined">Tous les statuts</option>
          <option value="EN_STOCK">En stock</option>
          <option value="EXPEDIE">Expédié</option>
          <option value="PERDU">Perdu</option>
        </select>
      </div>

      <EtatErreur v-if="lots.isError" :erreur="lots.error" />
      <EtatChargement v-else-if="lots.isLoading" />
      <EtatVide v-else-if="liste.length === 0" libelle="Aucun lot ne correspond aux filtres." />
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th class="py-2 pr-4 font-medium">Code lot</th>
              <th class="py-2 pr-4 font-medium">Produit</th>
              <th class="py-2 pr-4 font-medium">Quantité</th>
              <th class="py-2 pr-4 font-medium">Date de stockage</th>
              <th class="py-2 pr-4 font-medium">Ancienneté</th>
              <th class="py-2 pr-4 font-medium">Statut</th>
              <th class="py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="lot in liste" :key="lot.id" class="border-b border-border/60 hover:bg-muted/40">
              <td class="py-2.5 pr-4 font-mono font-medium">{{ lot.code_lot }}</td>
              <td class="py-2.5 pr-4 text-muted-foreground">{{ lot.produit ?? "—" }}</td>
              <td class="py-2.5 pr-4">{{ formaterNombre(lot.quantite_kg, " kg") }}</td>
              <td class="py-2.5 pr-4">{{ formaterDate(lot.date_stockage) }}</td>
              <td class="py-2.5 pr-4 text-muted-foreground">{{ joursDepuis(lot.date_stockage) ?? "—" }} j</td>
              <td class="py-2.5 pr-4"><BadgeStatutLot :statut="lot.statut" /></td>
              <td class="py-2.5 text-right">
                <RouterLink :to="`/lots/${lot.id}`" class="font-medium text-accent hover:underline">
                  Consulter
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Section>
  </div>
</template>
