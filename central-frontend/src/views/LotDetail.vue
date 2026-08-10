<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import { toast } from "vue-sonner";
import { ArrowLeft, Droplets, Save, Thermometer } from "lucide-vue-next";
import Section from "../components/Section.vue";
import Statistique from "../components/Statistique.vue";
import EtatChargement from "../components/EtatChargement.vue";
import EtatErreur from "../components/EtatErreur.vue";
import EtatVide from "../components/EtatVide.vue";
import BadgeNiveau from "../components/BadgeNiveau.vue";
import BadgeStatutAlerte from "../components/BadgeStatutAlerte.vue";
import BadgeStatutLot from "../components/BadgeStatutLot.vue";
import CourbeMesures from "../components/CourbeMesures.vue";
import { useAuth, ROLES } from "../stores/auth";
import { useFetch } from "../lib/useFetch";
import { apiEnvoyer, apiGet } from "../lib/api";
import { formaterDate, formaterDateHeure, formaterNombre, joursDepuis } from "../lib/format";
import { analyserMesures, type ConditionsConservation } from "../lib/analyse";
import type { Alerte, Entrepot, Lot, Mesure, Pays } from "../lib/types";

const props = defineProps<{ lotId: string }>();

const { role } = useAuth();

const lot = useFetch(() => apiGet<Lot>(`/lots/${props.lotId}`));
const mesures = useFetch(() => apiGet<Mesure[]>(`/lots/${props.lotId}/mesures`));
const entrepot = useFetch(
  () => apiGet<Entrepot>(`/entrepots/${lot.data?.entrepot_id ?? ""}`),
  { watchSources: [() => lot.data?.entrepot_id] },
);
const pays = useFetch(() => apiGet<Pays[]>("/pays"));
const alertes = useFetch(
  () => apiGet<Alerte[]>("/alertes", { pays_id: lot.data?.pays_id, limite: 100 }),
  { watchSources: [() => lot.data?.pays_id] },
);

const paysDuLot = computed(() => (pays.data ?? []).find((p) => p.id === lot.data?.pays_id));

/** Bande cible affichée sur la courbe : conditions idéales du pays (cible ± tolérance),
 *  sinon plage de l'entrepôt en secours. */
const bande = computed(() => {
  const p = paysDuLot.value;
  if (p && p.temperature_cible_c != null && p.tolerance_temperature_c != null) {
    return {
      temperature_min_c: p.temperature_cible_c - p.tolerance_temperature_c,
      temperature_max_c: p.temperature_cible_c + p.tolerance_temperature_c,
      humidite_min_pct:
        p.humidite_cible_pct != null && p.tolerance_humidite_pct != null
          ? p.humidite_cible_pct - p.tolerance_humidite_pct
          : null,
      humidite_max_pct:
        p.humidite_cible_pct != null && p.tolerance_humidite_pct != null
          ? p.humidite_cible_pct + p.tolerance_humidite_pct
          : null,
    };
  }
  return {
    temperature_min_c: entrepot.data?.temperature_min_c ?? null,
    temperature_max_c: entrepot.data?.temperature_max_c ?? null,
    humidite_min_pct: entrepot.data?.humidite_min_pct ?? null,
    humidite_max_pct: entrepot.data?.humidite_max_pct ?? null,
  };
});

const conditions = computed<ConditionsConservation>(() => {
  const p = paysDuLot.value;
  return {
    temperature_cible_c: p?.temperature_cible_c ?? null,
    humidite_cible_pct: p?.humidite_cible_pct ?? null,
    tolerance_temperature_c: p?.tolerance_temperature_c ?? null,
    tolerance_humidite_pct: p?.tolerance_humidite_pct ?? null,
  };
});

const analyse = computed(() => analyserMesures(mesures.data ?? [], conditions.value));

function tonConformite(pourcentage: number | null): "succes" | "avertissement" | "alerte" {
  if (pourcentage === null) return "avertissement";
  if (pourcentage >= 90) return "succes";
  if (pourcentage >= 70) return "avertissement";
  return "alerte";
}

const temperatures = computed(() =>
  (mesures.data ?? []).map((m) => m.temperature_c).filter((v): v is number => v != null),
);
const humidites = computed(() =>
  (mesures.data ?? []).map((m) => m.humidite_pct).filter((v): v is number => v != null),
);

function moyenne(valeurs: number[]): number | null {
  return valeurs.length === 0 ? null : valeurs.reduce((a, b) => a + b, 0) / valeurs.length;
}

const alertesLot = computed(() => {
  const liste = alertes.data ?? [];
  const specifiques = liste.filter((a) => a.lot_id === props.lotId);
  if (specifiques.length > 0) return specifiques;
  return liste.filter((a) => a.entrepot_id === lot.data?.entrepot_id);
});
const dernierReleve = computed(() => (mesures.data ?? []).at(-1));

const descriptionCourbe = computed(() => {
  const p = paysDuLot.value;
  if (p && p.temperature_cible_c != null) {
    return `Conditions idéales ${p.nom} : ${formaterNombre(p.temperature_cible_c, " °C")} ± ${formaterNombre(p.tolerance_temperature_c, " °C")} · ${formaterNombre(p.humidite_cible_pct, " %")} ± ${formaterNombre(p.tolerance_humidite_pct, " %")} (bande cible en vert, points hors bande en rouge)`;
  }
  if (entrepot.data?.temperature_min_c != null) {
    return `Plage de l'entrepôt : ${formaterNombre(entrepot.data.temperature_min_c, " °C")} – ${formaterNombre(entrepot.data.temperature_max_c, " °C")} et ${formaterNombre(entrepot.data.humidite_min_pct, " %")} – ${formaterNombre(entrepot.data.humidite_max_pct, " %")}`;
  }
  return "Relevés IoT transmis par MQTT puis consolidés par le siège.";
});

// Changement de statut d'un lot 
const statutForm = ref("");
const enMajStatut = ref(false);

// Le référent qualité ne modifie QUE le statut ; les autres rôles opérationnels
// (admin, exploitation, entrepôt) peuvent aussi ajuster quantité/produit via le proxy.
const peutChangerStatut = computed(() => {
  const r = role.value;
  return (
    r === ROLES.ADMIN_SIEGE ||
    r === ROLES.RESPONSABLE_EXPLOITATION ||
    r === ROLES.RESPONSABLE_ENTREPOT ||
    r === ROLES.REFERENT_QUALITE
  );
});

const statutsQualite = ["EN_ALERTE", "CONFORME", "A_VERIFIER"];
const statutsOperationnels = ["EN_STOCK", "EN_ALERTE", "CONFORME", "A_VERIFIER", "EXPORTE"];

const statutsDisponibles = computed(() =>
  role.value === ROLES.REFERENT_QUALITE ? statutsQualite : statutsOperationnels,
);

async function changerStatut(): Promise<void> {
  if (enMajStatut.value || !statutForm.value) return;
  enMajStatut.value = true;
  try {
    await apiEnvoyer<Lot>("PUT", `/lots/${props.lotId}`, { statut: statutForm.value });
    toast.success("Statut du lot mis à jour");
    statutForm.value = "";
    void lot.recharger();
  } catch (e) {
    toast.error("Mise à jour impossible", {
      description: e instanceof Error ? e.message : "Erreur inconnue",
    });
  } finally {
    enMajStatut.value = false;
  }
}
</script>

<template>
  <div class="space-y-6">
    <RouterLink to="/lots" class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeft class="size-4" /> Retour aux stocks
    </RouterLink>

    <EtatErreur v-if="lot.isError" :erreur="lot.error" />
    <EtatChargement v-else-if="lot.isLoading || !lot.data" libelle="Chargement du lot…" />

    <template v-else>
      <div class="surface-carte p-5">
        <div class="flex flex-wrap items-center gap-3">
          <h1 class="font-display text-2xl font-semibold">Lot {{ lot.data.code_lot }}</h1>
          <BadgeStatutLot :statut="lot.data.statut" />
        </div>

        <form
          v-if="peutChangerStatut"
          class="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-border bg-muted/30 p-3"
          @submit.prevent="changerStatut"
        >
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Nouveau statut</span>
            <select
              v-model="statutForm"
              class="h-9 w-[220px] rounded-md border border-input bg-background px-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="" disabled>Choisir un statut…</option>
              <option v-for="s in statutsDisponibles" :key="s" :value="s">
                {{ s.replaceAll("_", " ").toLowerCase() }}
              </option>
            </select>
          </label>
          <button
            type="submit"
            :disabled="enMajStatut || !statutForm"
            class="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            <Save class="size-4" />
            {{ enMajStatut ? "Enregistrement…" : "Appliquer" }}
          </button>
          <p class="w-full text-xs text-muted-foreground">
            <template v-if="role === ROLES.REFERENT_QUALITE">
              Le référent qualité peut valider la conformité (EN_ALERTE, CONFORME, A_VERIFIER).
            </template>
            <template v-else>Choisissez un statut pour mettre à jour le lot.</template>
          </p>
        </form>

        <dl class="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt class="text-xs uppercase tracking-wide text-muted-foreground">Produit</dt>
            <dd>{{ lot.data.produit ?? "—" }}</dd>
          </div>
          <div>
            <dt class="text-xs uppercase tracking-wide text-muted-foreground">Quantité</dt>
            <dd>{{ formaterNombre(lot.data.quantite_kg, " kg") }}</dd>
          </div>
          <div>
            <dt class="text-xs uppercase tracking-wide text-muted-foreground">Date de stockage</dt>
            <dd>
              {{ formaterDate(lot.data.date_stockage) }}
              <span class="text-muted-foreground">({{ joursDepuis(lot.data.date_stockage) ?? "—" }} j)</span>
            </dd>
          </div>
          <div>
            <dt class="text-xs uppercase tracking-wide text-muted-foreground">Localisation</dt>
            <dd>
              {{ lot.data.entrepot?.nom ?? "—" }}
              <template v-if="lot.data.entrepot?.ville"> · {{ lot.data.entrepot.ville }}</template>
              <template v-if="lot.data.pays?.nom"> · {{ lot.data.pays.nom }}</template>
            </dd>
          </div>
          <div>
            <dt class="text-xs uppercase tracking-wide text-muted-foreground">Exploitation</dt>
            <dd>{{ lot.data.exploitation?.nom ?? "—" }}</dd>
          </div>
          <div>
            <dt class="text-xs uppercase tracking-wide text-muted-foreground">Identifiant source</dt>
            <dd class="font-mono text-xs">{{ lot.data.source_id ?? "N/A" }}</dd>
          </div>
        </dl>
      </div>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Statistique
          libelle="Température moyenne"
          :valeur="formaterNombre(moyenne(temperatures), ' °C')"
          :detail="`min ${formaterNombre(temperatures.length ? Math.min(...temperatures) : null, ' °C')} · max ${formaterNombre(temperatures.length ? Math.max(...temperatures) : null, ' °C')}`"
        />
        <Statistique
          libelle="Humidité moyenne"
          :valeur="formaterNombre(moyenne(humidites), ' %')"
          :detail="`min ${formaterNombre(humidites.length ? Math.min(...humidites) : null, ' %')} · max ${formaterNombre(humidites.length ? Math.max(...humidites) : null, ' %')}`"
        />
        <Statistique libelle="Mesures reçues" :valeur="(mesures.data ?? []).length" detail="500 dernières mesures" />
        <Statistique
          libelle="Alertes du lot"
          :valeur="alertesLot.length"
          :ton="alertesLot.some((a) => a.statut === 'ACTIVE') ? 'alerte' : 'succes'"
          :detail="`${alertesLot.filter((a) => a.statut === 'ACTIVE').length} active(s)`"
        />
      </div>

      <Section
        titre="Courbes température / humidité"
        :description="descriptionCourbe"
      >
        <EtatErreur v-if="mesures.isError" :erreur="mesures.error" />
        <EtatChargement v-else-if="mesures.isLoading" libelle="Chargement des mesures…" />
        <EtatVide v-else-if="(mesures.data ?? []).length === 0" libelle="Aucune mesure disponible pour ce lot." />
        <template v-else>
          <CourbeMesures
            :mesures="mesures.data ?? []"
            :seuils="bande"
          />
          <p class="mt-2 text-xs text-muted-foreground">
            <Thermometer class="mr-1 inline size-3.5" />
            Dernier relevé : {{ formaterDateHeure(dernierReleve?.date_mesure) }}
            <Droplets class="ml-3 mr-1 inline size-3.5" />
            Source : {{ dernierReleve?.source ?? "capteur IoT" }}
          </p>
        </template>
      </Section>

      <Section
        titre="Analyse de conformité & dérives"
        description="Mesures comparées aux conditions idéales du pays (cible ± tolérance) pour justifier la traçabilité."
      >
        <div v-if="(mesures.data ?? []).length === 0" class="text-sm text-muted-foreground">
          Aucune mesure à analyser.
        </div>
        <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Statistique
            libelle="Température dans la plage"
            :valeur="analyse.temperature.pourcentageConforme === null ? '—' : `${analyse.temperature.pourcentageConforme} %`"
            :detail="`${analyse.temperature.dansPlage}/${analyse.temperature.total} mesures dans la bande cible`"
            :ton="tonConformite(analyse.temperature.pourcentageConforme)"
          />
          <Statistique
            libelle="Écart température (moy.)"
            :valeur="formaterNombre(analyse.temperature.ecartMoyen, ' °C')"
            :detail="`max ${formaterNombre(analyse.temperature.ecartMax, ' °C')} · plage observée ${formaterNombre(analyse.temperature.min, ' °C')} – ${formaterNombre(analyse.temperature.max, ' °C')}`"
          />
          <Statistique
            libelle="Humidité dans la plage"
            :valeur="analyse.humidite.pourcentageConforme === null ? '—' : `${analyse.humidite.pourcentageConforme} %`"
            :detail="`${analyse.humidite.dansPlage}/${analyse.humidite.total} mesures dans la bande cible`"
            :ton="tonConformite(analyse.humidite.pourcentageConforme)"
          />
          <Statistique
            libelle="Écart humidité (moy.)"
            :valeur="formaterNombre(analyse.humidite.ecartMoyen, ' %')"
            :detail="`max ${formaterNombre(analyse.humidite.ecartMax, ' %')} · plage observée ${formaterNombre(analyse.humidite.min, ' %')} – ${formaterNombre(analyse.humidite.max, ' %')}`"
          />
        </div>

        <div class="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div class="rounded-lg border border-border p-3">
            <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">Dérive la plus longue</p>
            <p class="mt-1 font-display text-2xl font-semibold">
              {{ Math.max(analyse.temperature.deriveLaPlusLongue, analyse.humidite.deriveLaPlusLongue) }}
              <span class="text-sm font-normal text-muted-foreground">relevé(s) consécutif(s) hors bande</span>
            </p>
            <p class="mt-1 text-xs text-muted-foreground">
              Température : {{ analyse.temperature.deriveLaPlusLongue }} · Humidité : {{ analyse.humidite.deriveLaPlusLongue }}
            </p>
          </div>
          <div class="rounded-lg border border-border p-3">
            <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">Cible du pays</p>
            <p v-if="paysDuLot?.temperature_cible_c != null" class="mt-1 font-display text-2xl font-semibold">
              {{ formaterNombre(paysDuLot.temperature_cible_c, " °C") }} · {{ formaterNombre(paysDuLot.humidite_cible_pct, " %") }}
            </p>
            <p v-else class="mt-1 text-sm text-muted-foreground">Non renseignée pour ce pays.</p>
            <p class="mt-1 text-xs text-muted-foreground">
              <template v-if="paysDuLot?.tolerance_temperature_c != null">
                Tolérance : ±{{ formaterNombre(paysDuLot.tolerance_temperature_c, " °C") }} · ±{{ formaterNombre(paysDuLot.tolerance_humidite_pct, " %") }}
              </template>
              <template v-else>Référence = plage de l'entrepôt</template>
            </p>
          </div>
        </div>
      </Section>

      <Section titre="Alertes liées à ce lot" description="Historique complet des dépassements de seuils.">
        <EtatVide v-if="alertesLot.length === 0" libelle="Aucune alerte enregistrée pour ce lot." />
        <ul v-else class="divide-y divide-border">
          <li
            v-for="alerte in alertesLot"
            :key="alerte.id"
            class="flex flex-wrap items-center gap-3 py-3 text-sm"
          >
            <span class="font-medium">{{ alerte.type_alerte.replaceAll("_", " ").toLowerCase() }}</span>
            <BadgeNiveau :niveau="alerte.niveau" />
            <BadgeStatutAlerte :statut="alerte.statut" />
            <span class="text-muted-foreground">{{ alerte.message }}</span>
            <span class="ml-auto text-xs text-muted-foreground">
              {{ formaterDateHeure(alerte.date_declenchement) }}
            </span>
          </li>
        </ul>
      </Section>
    </template>
  </div>
</template>
