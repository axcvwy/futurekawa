<script setup lang="ts">
import { computed, ref } from "vue";
import { toast } from "vue-sonner";
import { RefreshCw } from "lucide-vue-next";
import Section from "../components/Section.vue";
import EtatChargement from "../components/EtatChargement.vue";
import EtatErreur from "../components/EtatErreur.vue";
import EtatVide from "../components/EtatVide.vue";
import BadgeStatutSync from "../components/BadgeStatutSync.vue";
import { useSelection } from "../stores/selection";
import { useAuth, ROLES } from "../stores/auth";
import { useFetch } from "../lib/useFetch";
import { apiEnvoyer, apiGet } from "../lib/api";
import { depuisMaintenant, formaterDateHeure } from "../lib/format";
import type { Pays, Synchronisation } from "../lib/types";

const { paysId } = useSelection();
const { role } = useAuth();

// Configuration des pays (activation, intervalle, URL) : réservée à l'administrateur siège.
const peutConfigurer = computed(() => role.value === ROLES.ADMIN_SIEGE);
// Le bouton « Synchroniser maintenant » est disponible pour l'admin et le responsable
// d'exploitation (le backend restreint déjà au pays assigné).
const peutSynchroniser = computed(() =>
  role.value === ROLES.ADMIN_SIEGE || role.value === ROLES.RESPONSABLE_EXPLOITATION,
);

const pays = useFetch(() => apiGet<Pays[]>("/pays"));
const syncs = useFetch(
  () => apiGet<Synchronisation[]>("/synchronisations", { pays_id: paysId.value, limite: 50 }),
  { watchSources: [paysId] },
);

const enMutation = ref(false);
const syncEnCours = ref<string | null>(null);

async function majPays(id: string, corps: Record<string, unknown>): Promise<void> {
  enMutation.value = true;
  try {
    await apiEnvoyer<Pays>("PUT", `/pays/${id}`, corps);
    toast.success("Configuration du pays mise à jour");
    void pays.recharger();
  } catch (e) {
    toast.error("Mise à jour impossible", {
      description: e instanceof Error ? e.message : "Erreur inconnue",
    });
  } finally {
    enMutation.value = false;
  }
}

async function lancerSync(id: string): Promise<void> {
  syncEnCours.value = id;
  try {
    const donnees = await apiEnvoyer<Synchronisation>("POST", `/synchronisations/pays/${id}`);
    toast.success("Synchronisation lancée", {
      description: `Statut : ${donnees.statut ?? "en cours"} · ${donnees.lots_ecrits ?? 0} lot(s), ${donnees.mesures_ecrites ?? 0} mesure(s)`,
    });
    void pays.recharger();
    void syncs.recharger();
  } catch (e) {
    toast.error("Synchronisation en échec", {
      description: e instanceof Error ? e.message : "Erreur inconnue",
    });
  } finally {
    syncEnCours.value = null;
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="font-display text-2xl font-semibold">Pilotage des pays</h1>
      <p class="text-sm text-muted-foreground">
        Activez les backends pays, déclenchez une synchronisation et consultez le journal.
      </p>
    </div>

    <Section titre="Backends pays" description="Chaque pays expose son API locale au siège.">
      <EtatErreur v-if="pays.isError" :erreur="pays.error" />
      <EtatChargement v-else-if="pays.isLoading" />
      <div v-else class="grid gap-4 md:grid-cols-2">
        <div v-for="p in pays.data ?? []" :key="p.id" class="rounded-lg border border-border p-4">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="font-display text-base font-semibold">{{ p.nom }}</h3>
            <span class="font-mono text-xs text-muted-foreground">{{ p.code_iso }}</span>
            <span class="ml-auto"><BadgeStatutSync :statut="p.dernier_statut_sync" /></span>
          </div>
          <p class="mt-1 break-all font-mono text-xs text-muted-foreground">
            {{ p.api_base_url ?? "URL non renseignée" }}
          </p>
          <p class="mt-1 text-xs text-muted-foreground">
            Dernière réussite : {{ depuisMaintenant(p.derniere_sync_reussie_le) }} · intervalle
            {{ p.intervalle_sync_secondes ?? "—" }} s<template v-if="p.mock"> · source simulée</template>
          </p>
          <p v-if="p.derniere_erreur_sync" class="mt-1 text-xs text-destructive">
            {{ p.derniere_erreur_sync }}
          </p>
          <div class="mt-3 flex flex-wrap items-center gap-3">
            <label v-if="peutConfigurer" class="inline-flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                class="peer sr-only"
                :checked="p.actif"
                :disabled="enMutation"
                @change="(e) => majPays(p.id, { actif: (e.target as HTMLInputElement).checked })"
              />
              <span class="relative h-6 w-11 rounded-full bg-muted-foreground/30 transition peer-checked:bg-accent"></span>
              {{ p.actif ? "Actif" : "Inactif" }}
            </label>
            <span v-else class="text-xs text-muted-foreground">
              {{ p.actif ? "Pays actif" : "Pays inactif" }}<template v-if="p.mock"> · source simulée</template>
            </span>
            <button
              v-if="peutSynchroniser"
              class="ml-auto inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
              :disabled="syncEnCours !== null"
              @click="lancerSync(p.id)"
            >
              <RefreshCw :class="`mr-1.5 size-4 ${syncEnCours === p.id ? 'animate-spin' : ''}`" />
              Synchroniser maintenant
            </button>
          </div>
        </div>
      </div>
    </Section>

    <Section
      titre="Journal des synchronisations"
      description="Volumétrie lue et écrite lors des derniers échanges siège / pays."
    >
      <EtatErreur v-if="syncs.isError" :erreur="syncs.error" />
      <EtatChargement v-else-if="syncs.isLoading" />
      <EtatVide v-else-if="(syncs.data?.length ?? 0) === 0" libelle="Aucune synchronisation enregistrée." />
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th class="py-2 pr-4 font-medium">Démarrée le</th>
              <th class="py-2 pr-4 font-medium">Déclencheur</th>
              <th class="py-2 pr-4 font-medium">Statut</th>
              <th class="py-2 pr-4 font-medium">Lots</th>
              <th class="py-2 pr-4 font-medium">Mesures</th>
              <th class="py-2 pr-4 font-medium">Alertes</th>
              <th class="py-2 font-medium">Erreur</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in syncs.data ?? []" :key="s.id" class="border-b border-border/60">
              <td class="py-2.5 pr-4">{{ formaterDateHeure(s.demarree_le) }}</td>
              <td class="py-2.5 pr-4 text-muted-foreground">
                {{ s.declencheur === "MANUEL" ? "Manuel" : "Automatique" }}
              </td>
              <td class="py-2.5 pr-4"><BadgeStatutSync :statut="s.statut" /></td>
              <td class="py-2.5 pr-4">{{ s.lots_ecrits ?? 0 }}/{{ s.lots_lus ?? 0 }}</td>
              <td class="py-2.5 pr-4">{{ s.mesures_ecrites ?? 0 }}/{{ s.mesures_lues ?? 0 }}</td>
              <td class="py-2.5 pr-4">{{ s.alertes_ecrites ?? 0 }}/{{ s.alertes_lues ?? 0 }}</td>
              <td class="py-2.5 text-xs text-destructive">{{ s.erreur ?? "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Section>
  </div>
</template>
