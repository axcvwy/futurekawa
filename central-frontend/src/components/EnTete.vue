<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { Coffee, Globe2, LogOut, RefreshCw } from "lucide-vue-next";
import BadgeStatutSync from "./BadgeStatutSync.vue";
import { useSelection } from "../stores/selection";
import { useAuth, ROLES } from "../stores/auth";
import { useFetch } from "../lib/useFetch";
import { apiGet } from "../lib/api";
import { depuisMaintenant } from "../lib/format";
import type { Exploitation, Pays, Sante } from "../lib/types";

const { paysId, exploitationId, definirPays, definirExploitation } = useSelection();
const { utilisateur, deconnecter } = useAuth();
const router = useRouter();

const pays = useFetch(() => apiGet<Pays[]>("/pays"));
const sante = useFetch(() => apiGet<Sante>("/health"), { interval: 30_000 });
const exploitations = useFetch(
  () => apiGet<Exploitation[]>("/exploitations", { pays_id: paysId.value }),
  { watchSources: [paysId] },
);

const enEchec = computed(() =>
  (sante.data?.pays ?? []).filter((p) => p.actif && p.dernier_statut_sync === "ECHEC"),
);

const derniereReussie = computed(() => {
  const dates = (sante.data?.pays ?? [])
    .map((p) => p.derniere_sync_reussie_le)
    .filter((v): v is string => Boolean(v))
    .sort();
  return dates.at(-1) ?? null;
});

const role = computed(() => utilisateur.value?.role);
const estAdmin = computed(() => role.value === ROLES.ADMIN_SIEGE);

const libellesRole: Record<string, string> = {
  ADMIN_SIEGE: "Administrateur siège",
  RESPONSABLE_EXPLOITATION: "Responsable exploitation",
  RESPONSABLE_ENTREPOT: "Responsable entrepôt",
  REFERENT_QUALITE: "Référent qualité",
};

// Visibilité des sections par rôle : les responsables d'entrepôt pilotent leur
// entrepôt (lots/alertes), les autres rôles accèdent au périmètre complet (pays compris).
const liens = computed(() => {
  const communs = [
    { to: "/", libelle: "Tableau de bord" },
    { to: "/lots", libelle: "Stocks et lots" },
    { to: "/alertes", libelle: "Alertes" },
  ];
  if (role.value === ROLES.RESPONSABLE_ENTREPOT) return communs;
  const etendus = [...communs, { to: "/pays", libelle: "Pilotage pays" }];
  if (role.value === ROLES.ADMIN_SIEGE) {
    etendus.push({ to: "/configuration", libelle: "Configuration" });
  }
  return etendus;
});

// Périmètre restreint affiché dans la bannière (pays / entrepôt de l'utilisateur).
const perimetreLibelle = computed(() => {
  if (!utilisateur.value) return "";
  if (utilisateur.value.role === ROLES.ADMIN_SIEGE) return "Tous les pays";
  const paysUtilisateur = pays.data?.find((p) => p.id === utilisateur.value?.pays_id);
  const base = paysUtilisateur ? `${paysUtilisateur.nom} (${paysUtilisateur.code_iso})` : "Pays assigné";
  if (utilisateur.value.role === ROLES.RESPONSABLE_ENTREPOT) return `${base} · entrepôt assigné`;
  return base;
});

function seDeconnecter(): void {
  deconnecter();
  void router.push({ name: "connexion" });
}
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
    <div class="banniere-cafe">
      <div class="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3">
        <RouterLink to="/" class="flex items-center gap-2.5">
          <span class="flex size-9 items-center justify-center rounded-lg bg-primary-foreground/15">
            <Coffee class="size-5" />
          </span>
          <span class="leading-tight">
            <span class="block font-display text-lg font-semibold">FutureKawa</span>
            <span class="block text-[11px] uppercase tracking-widest opacity-80">Supervision siège</span>
          </span>
        </RouterLink>

        <div class="ml-auto flex flex-wrap items-center gap-2">
          <template v-if="estAdmin">
            <Globe2 class="size-4 opacity-80" />
            <select
              class="h-9 w-[190px] rounded-md border border-primary-foreground/25 bg-primary-foreground/10 px-2 text-sm text-primary-foreground outline-none focus:border-primary-foreground/50"
              :value="paysId ?? 'tous'"
              @change="(e) => definirPays((e.target as HTMLSelectElement).value === 'tous' ? undefined : (e.target as HTMLSelectElement).value)"
            >
              <option value="tous" class="text-foreground">Tous les pays</option>
              <option
                v-for="p in pays.data ?? []"
                :key="p.id"
                :value="p.id"
                class="text-foreground"
              >
                {{ p.nom }} ({{ p.code_iso }})
              </option>
            </select>

            <select
              class="h-9 w-[210px] rounded-md border border-primary-foreground/25 bg-primary-foreground/10 px-2 text-sm text-primary-foreground outline-none focus:border-primary-foreground/50"
              :value="exploitationId ?? 'toutes'"
              @change="(e) => definirExploitation((e.target as HTMLSelectElement).value === 'toutes' ? undefined : (e.target as HTMLSelectElement).value)"
            >
              <option value="toutes" class="text-foreground">Toutes les exploitations</option>
              <option
                v-for="e in exploitations.data ?? []"
                :key="e.id"
                :value="e.id"
                class="text-foreground"
              >
                {{ e.nom }}{{ e.code ? ` · ${e.code}` : "" }}
              </option>
            </select>
          </template>

          <span
            v-else
            class="flex h-9 items-center gap-1.5 rounded-md border border-primary-foreground/25 bg-primary-foreground/10 px-3 text-sm text-primary-foreground"
          >
            <Globe2 class="size-4 opacity-80" />
            {{ perimetreLibelle }}
          </span>

          <span class="flex h-9 items-center gap-2 rounded-md border border-primary-foreground/25 bg-primary-foreground/10 px-3 text-sm text-primary-foreground">
            <span class="flex size-6 items-center justify-center rounded-full bg-primary-foreground/20 text-xs font-semibold">
              {{ (utilisateur?.nom ?? "?").trim().charAt(0).toUpperCase() }}
            </span>
            <span class="leading-tight">
              <span class="block max-w-[180px] truncate font-medium">{{ utilisateur?.nom }}</span>
              <span class="block text-[10px] uppercase tracking-wider opacity-80">
                {{ libellesRole[utilisateur?.role ?? ""] ?? utilisateur?.role }}
              </span>
            </span>
            <button
              type="button"
              title="Se déconnecter"
              class="rounded-md p-1.5 transition-colors hover:bg-primary-foreground/15"
              @click="seDeconnecter"
            >
              <LogOut class="size-4" />
            </button>
          </span>
        </div>
      </div>
    </div>

    <nav class="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4">
      <RouterLink
        v-for="lien in liens"
        :key="lien.to"
        :to="lien.to"
        class="border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
        :exact-active-class="lien.to === '/' ? 'border-accent text-foreground' : undefined"
        :active-class="lien.to === '/' ? undefined : 'border-accent text-foreground'"
      >
        {{ lien.libelle }}
      </RouterLink>
      <span class="ml-auto hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
        <RefreshCw class="size-3.5" />
        Données fraîches {{ depuisMaintenant(derniereReussie) }}
      </span>
    </nav>

    <div v-if="enEchec.length > 0" class="border-t border-destructive/25 bg-destructive/10">
      <div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-2 text-xs text-destructive">
        <BadgeStatutSync statut="ECHEC" />
        <span>
          Synchronisation en échec :
          {{ enEchec.map((p) => `${p.nom} (${p.derniere_erreur_sync ?? "erreur inconnue"})`).join(" · ") }}
        </span>
      </div>
    </div>
  </header>
</template>
