<script setup lang="ts">
import { computed, ref } from "vue";
import { toast } from "vue-sonner";
import { Pencil, PackagePlus, Plus, RotateCcw, Trash2, UserPlus, Warehouse, Radio } from "lucide-vue-next";
import Section from "../components/Section.vue";
import EtatChargement from "../components/EtatChargement.vue";
import EtatVide from "../components/EtatVide.vue";
import { useFetch } from "../lib/useFetch";
import { apiEnvoyer, apiGet } from "../lib/api";
import { ROLES } from "../stores/auth";
import type { Capteur, Entrepot, Exploitation, Pays, Utilisateur } from "../lib/types";

// Données
const pays = useFetch(() => apiGet<Pays[]>("/pays"));
const exploitations = useFetch(() => apiGet<Exploitation[]>("/exploitations"));
const entrepots = useFetch(() => apiGet<Entrepot[]>("/entrepots"));
const capteurs = useFetch(() => apiGet<Capteur[]>("/capteurs"));
const utilisateurs = useFetch(() => apiGet<Utilisateur[]>("/utilisateurs"));

const libellesRole: Record<string, string> = {
  ADMIN_SIEGE: "Admin siège",
  RESPONSABLE_EXPLOITATION: "Resp. exploitation",
  RESPONSABLE_ENTREPOT: "Resp. entrepôt",
  REFERENT_QUALITE: "Référent qualité",
};

const nomsPays = computed(() => Object.fromEntries((pays.data ?? []).map((p) => [p.id, `${p.nom} (${p.code_iso})`])));
const nomsEntrepots = computed(() => Object.fromEntries((entrepots.data ?? []).map((e) => [e.id, e.nom])));

function rechargerTout(): void {
  void pays.recharger();
  void exploitations.recharger();
  void entrepots.recharger();
  void capteurs.recharger();
  void utilisateurs.recharger();
}

// Utilisateurs
const formulaireUtilisateur = ref(false);
const enMutationUtilisateur = ref(false);
const utilisateurIdModifie = ref<string | null>(null);
const utilisateur = ref({
  email: "",
  nom: "",
  mot_de_passe: "",
  role: "RESPONSABLE_EXPLOITATION" as string,
  actif: true,
  pays_id: "",
  entrepot_id: "",
});

const estResponsableEntrepot = computed(() => utilisateur.value.role === ROLES.RESPONSABLE_ENTREPOT);

function ouvrirUtilisateur(): void {
  utilisateurIdModifie.value = null;
  utilisateur.value = {
    email: "",
    nom: "",
    mot_de_passe: "",
    role: "RESPONSABLE_EXPLOITATION",
    actif: true,
    pays_id: pays.data?.[0]?.id ?? "",
    entrepot_id: "",
  };
  formulaireUtilisateur.value = true;
}

function ouvrirModifUtilisateur(u: Utilisateur): void {
  utilisateurIdModifie.value = u.id;
  utilisateur.value = {
    email: u.email,
    nom: u.nom,
    mot_de_passe: "",
    role: u.role,
    actif: u.actif,
    pays_id: u.pays_id ?? "",
    entrepot_id: u.entrepot_id ?? "",
  };
  formulaireUtilisateur.value = true;
}

async function enregistrerUtilisateur(): Promise<void> {
  if (enMutationUtilisateur.value) return;
  enMutationUtilisateur.value = true;
  try {
    const corps = {
      email: utilisateur.value.email,
      nom: utilisateur.value.nom,
      role: utilisateur.value.role,
      actif: utilisateur.value.actif,
      pays_id: utilisateur.value.pays_id || null,
      entrepot_id: estResponsableEntrepot.value ? utilisateur.value.entrepot_id : null,
    } as { email: string; mot_de_passe?: string; [cle: string]: unknown };
    if (utilisateur.value.mot_de_passe) corps.mot_de_passe = utilisateur.value.mot_de_passe;
    if (utilisateurIdModifie.value) {
      await apiEnvoyer<Utilisateur>("PUT", `/utilisateurs/${utilisateurIdModifie.value}`, corps);
      toast.success("Utilisateur modifié");
    } else {
      if (!utilisateur.value.mot_de_passe) throw new Error("Un mot de passe est requis à la création");
      await apiEnvoyer<Utilisateur>("POST", "/utilisateurs", corps);
      toast.success("Utilisateur créé");
    }
    formulaireUtilisateur.value = false;
    void utilisateurs.recharger();
  } catch (e) {
    toast.error("Enregistrement impossible", {
      description: e instanceof Error ? e.message : "Erreur inconnue",
    });
  } finally {
    enMutationUtilisateur.value = false;
  }
}

async function activerUtilisateur(u: Utilisateur): Promise<void> {
  try {
    await apiEnvoyer<Utilisateur>("PUT", `/utilisateurs/${u.id}`, { actif: !u.actif });
    toast.success(u.actif ? "Compte désactivé" : "Compte activé");
    void utilisateurs.recharger();
  } catch (e) {
    toast.error("Mise à jour impossible", { description: e instanceof Error ? e.message : undefined });
  }
}

async function supprimerUtilisateur(u: Utilisateur): Promise<void> {
  if (!window.confirm(`Supprimer le compte ${u.email} ?`)) return;
  try {
    await apiEnvoyer<{ message: string }>("DELETE", `/utilisateurs/${u.id}`);
    toast.success("Utilisateur supprimé");
    void utilisateurs.recharger();
  } catch (e) {
    toast.error("Suppression impossible", { description: e instanceof Error ? e.message : undefined });
  }
}

// Entrepôt (création / modification)
const formulaireEntrepot = ref(false);
const enMutationEntrepot = ref(false);
const entrepotIdModifie = ref<string | null>(null);
const entrepot = ref({
  pays_id: "",
  nom: "",
  ville: "",
  nom_responsable: "",
  email_responsable: "",
  temperature_min_c: "",
  temperature_max_c: "",
  humidite_min_pct: "",
  humidite_max_pct: "",
});

function ouvrirEntrepot(): void {
  entrepotIdModifie.value = null;
  entrepot.value = {
    pays_id: pays.data?.[0]?.id ?? "",
    nom: "",
    ville: "",
    nom_responsable: "",
    email_responsable: "",
    temperature_min_c: "",
    temperature_max_c: "",
    humidite_min_pct: "",
    humidite_max_pct: "",
  };
  formulaireEntrepot.value = true;
}

function ouvrirModifEntrepot(e: Entrepot): void {
  entrepotIdModifie.value = e.id;
  entrepot.value = {
    pays_id: e.pays_id ?? "",
    nom: e.nom,
    ville: e.ville ?? "",
    nom_responsable: e.nom_responsable ?? "",
    email_responsable: e.email_responsable ?? "",
    temperature_min_c: e.temperature_min_c != null ? String(e.temperature_min_c) : "",
    temperature_max_c: e.temperature_max_c != null ? String(e.temperature_max_c) : "",
    humidite_min_pct: e.humidite_min_pct != null ? String(e.humidite_min_pct) : "",
    humidite_max_pct: e.humidite_max_pct != null ? String(e.humidite_max_pct) : "",
  };
  formulaireEntrepot.value = true;
}

async function enregistrerEntrepot(): Promise<void> {
  if (enMutationEntrepot.value) return;
  enMutationEntrepot.value = true;
  const corps = {
    pays_id: entrepot.value.pays_id,
    nom: entrepot.value.nom,
    ville: entrepot.value.ville,
    nom_responsable: entrepot.value.nom_responsable,
    email_responsable: entrepot.value.email_responsable,
    temperature_min_c: Number(entrepot.value.temperature_min_c),
    temperature_max_c: Number(entrepot.value.temperature_max_c),
    humidite_min_pct: Number(entrepot.value.humidite_min_pct),
    humidite_max_pct: Number(entrepot.value.humidite_max_pct),
  };
  try {
    if (entrepotIdModifie.value) {
      await apiEnvoyer<Entrepot>("PUT", `/entrepots/${entrepotIdModifie.value}`, corps);
      toast.success("Entrepôt modifié");
    } else {
      await apiEnvoyer<Entrepot>("POST", "/entrepots", corps);
      toast.success("Entrepôt créé");
    }
    formulaireEntrepot.value = false;
    void entrepots.recharger();
  } catch (e) {
    toast.error("Enregistrement impossible", {
      description: e instanceof Error ? e.message : "Erreur inconnue",
    });
  } finally {
    enMutationEntrepot.value = false;
  }
}

async function supprimerEntrepot(e: Entrepot): Promise<void> {
  if (!window.confirm(`Supprimer l'entrepôt « ${e.nom} » ?`)) return;
  try {
    await apiEnvoyer<{ message: string }>("DELETE", `/entrepots/${e.id}`);
    toast.success("Entrepôt supprimé");
    void entrepots.recharger();
    void capteurs.recharger();
  } catch (err) {
    toast.error("Suppression impossible", {
      description: err instanceof Error ? err.message : undefined,
    });
  }
}

// Capteur (création / modification)
const formulaireCapteur = ref(false);
const enMutationCapteur = ref(false);
const capteurIdModifie = ref<string | null>(null);
const capteur = ref({
  entrepot_id: "",
  reference: "",
  topic_mqtt: "",
  type_capteur: "DHT22",
  statut: "ACTIF",
  frequence_mesure_secondes: "60",
});

function ouvrirCapteur(): void {
  capteurIdModifie.value = null;
  capteur.value = {
    entrepot_id: entrepots.data?.[0]?.id ?? "",
    reference: "",
    topic_mqtt: "",
    type_capteur: "DHT22",
    statut: "ACTIF",
    frequence_mesure_secondes: "60",
  };
  formulaireCapteur.value = true;
}

function ouvrirModifCapteur(c: Capteur): void {
  capteurIdModifie.value = c.id;
  capteur.value = {
    entrepot_id: c.entrepot_id ?? "",
    reference: c.reference,
    topic_mqtt: c.topic_mqtt ?? "",
    type_capteur: c.type_capteur ?? "",
    statut: c.statut ?? "ACTIF",
    frequence_mesure_secondes: c.frequence_mesure_secondes != null ? String(c.frequence_mesure_secondes) : "60",
  };
  formulaireCapteur.value = true;
}

async function enregistrerCapteur(): Promise<void> {
  if (enMutationCapteur.value) return;
  enMutationCapteur.value = true;
  const corps = {
    entrepot_id: capteur.value.entrepot_id,
    reference: capteur.value.reference,
    topic_mqtt: capteur.value.topic_mqtt,
    type_capteur: capteur.value.type_capteur,
    statut: capteur.value.statut,
    frequence_mesure_secondes: Number(capteur.value.frequence_mesure_secondes),
  };
  try {
    if (capteurIdModifie.value) {
      await apiEnvoyer<Capteur>("PUT", `/capteurs/${capteurIdModifie.value}`, corps);
      toast.success("Capteur modifié");
    } else {
      await apiEnvoyer<Capteur>("POST", "/capteurs", corps);
      toast.success("Capteur créé");
    }
    formulaireCapteur.value = false;
    void capteurs.recharger();
  } catch (e) {
    toast.error("Enregistrement impossible", {
      description: e instanceof Error ? e.message : "Erreur inconnue",
    });
  } finally {
    enMutationCapteur.value = false;
  }
}

async function supprimerCapteur(c: Capteur): Promise<void> {
  if (!window.confirm(`Supprimer le capteur « ${c.reference} » ?`)) return;
  try {
    await apiEnvoyer<{ message: string }>("DELETE", `/capteurs/${c.id}`);
    toast.success("Capteur supprimé");
    void capteurs.recharger();
  } catch (err) {
    toast.error("Suppression impossible", {
      description: err instanceof Error ? err.message : undefined,
    });
  }
}

function formaterTemperature(valeur: unknown): string {
  return typeof valeur === "number" ? `${valeur}°` : "—";
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="font-display text-2xl font-semibold">Configuration</h1>
      <p class="text-sm text-muted-foreground">
        Comptes utilisateurs, entrepôts et capteurs — réservé à l'administrateur siège.
      </p>
    </div>

    <Section
      titre="Utilisateurs & rôles"
      description="Créez les comptes selon le rôle métier ; le périmètre pays/entrepôt est restreint automatiquement."
    >
      <template #action>
        <button
          class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          @click="ouvrirUtilisateur"
        >
          <UserPlus class="size-4" /> Nouvel utilisateur
        </button>
      </template>

      <form
        v-if="formulaireUtilisateur"
        class="mb-4 rounded-lg border border-border bg-muted/30 p-4"
        @submit.prevent="enregistrerUtilisateur"
      >
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">E-mail</span>
            <input v-model="utilisateur.email" type="email" required class="champ" :disabled="utilisateurIdModifie !== null" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Nom</span>
            <input v-model="utilisateur.nom" required class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">
              {{ utilisateurIdModifie ? "Mot de passe (laisser vide pour conserver)" : "Mot de passe" }}
            </span>
            <input v-model="utilisateur.mot_de_passe" type="password" :required="utilisateurIdModifie === null" class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Rôle</span>
            <select v-model="utilisateur.role" class="champ">
              <option v-for="r in Object.values(ROLES)" :key="r" :value="r">{{ libellesRole[r] }}</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Pays</span>
            <select v-model="utilisateur.pays_id" class="champ">
              <option value="">—</option>
              <option v-for="p in pays.data ?? []" :key="p.id" :value="p.id">{{ nomsPays[p.id] }}</option>
            </select>
          </label>
          <label v-if="estResponsableEntrepot" class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Entrepôt</span>
            <select v-model="utilisateur.entrepot_id" class="champ">
              <option value="">—</option>
              <option v-for="e in entrepots.data ?? []" :key="e.id" :value="e.id">
                {{ e.nom }}{{ nomsPays[e.pays_id] ? ` · ${nomsPays[e.pays_id]}` : "" }}
              </option>
            </select>
          </label>
          <label class="flex items-end gap-2 pb-2 text-sm">
            <input v-model="utilisateur.actif" type="checkbox" class="h-4 w-4" />
            Compte actif
          </label>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button type="button" class="bouton-secondaire" @click="formulaireUtilisateur = false">Annuler</button>
          <button type="submit" :disabled="enMutationUtilisateur" class="bouton-primaire">
            <Plus class="size-4" />
            {{ enMutationUtilisateur ? "Enregistrement…" : utilisateurIdModifie ? "Enregistrer les modifications" : "Créer le compte" }}
          </button>
        </div>
      </form>

      <EtatChargement v-if="utilisateurs.isLoading" />
      <EtatVide v-else-if="(utilisateurs.data?.length ?? 0) === 0" libelle="Aucun utilisateur." />
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th class="py-2 pr-4 font-medium">Utilisateur</th>
              <th class="py-2 pr-4 font-medium">Rôle</th>
              <th class="py-2 pr-4 font-medium">Périmètre</th>
              <th class="py-2 pr-4 font-medium">Actif</th>
              <th class="py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in utilisateurs.data ?? []" :key="u.id" class="border-b border-border/60">
              <td class="py-2.5 pr-4">
                <span class="font-medium">{{ u.nom }}</span>
                <span class="block text-xs text-muted-foreground">{{ u.email }}</span>
              </td>
              <td class="py-2.5 pr-4">{{ libellesRole[u.role] ?? u.role }}</td>
              <td class="py-2.5 pr-4 text-xs text-muted-foreground">
                {{ u.pays_id ? nomsPays[u.pays_id] : "Tous les pays" }}
                <template v-if="u.entrepot_id"> · {{ nomsEntrepots[u.entrepot_id] }}</template>
              </td>
              <td class="py-2.5 pr-4">
                <button
                  class="rounded-md px-2 py-1 text-xs font-medium transition-colors"
                  :class="u.actif ? 'bg-success/15 text-success' : 'bg-destructive/15 text-destructive'"
                  @click="activerUtilisateur(u)"
                >
                  {{ u.actif ? "Actif" : "Inactif" }}
                </button>
              </td>
              <td class="py-2.5 text-right">
                <button
                  class="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted"
                  title="Modifier"
                  @click="ouvrirModifUtilisateur(u)"
                >
                  <Pencil class="size-4" />
                </button>
                <button
                  class="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                  title="Supprimer"
                  @click="supprimerUtilisateur(u)"
                >
                  <Trash2 class="size-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Section>

    <Section
      titre="Entrepôts"
      description="Créez un entrepôt pour chaque site physique de stockage. Les capteurs IoT seront rattachés à un entrepôt."
    >
      <template #action>
        <button
          class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          @click="ouvrirEntrepot"
        >
          <Warehouse class="size-4" /> Nouvel entrepôt
        </button>
      </template>

      <form
        v-if="formulaireEntrepot"
        class="mb-4 rounded-lg border border-border bg-muted/30 p-4"
        @submit.prevent="enregistrerEntrepot"
      >
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Pays</span>
            <select v-model="entrepot.pays_id" required class="champ" :disabled="entrepotIdModifie !== null">
              <option v-for="p in pays.data ?? []" :key="p.id" :value="p.id">{{ nomsPays[p.id] }}</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Nom</span>
            <input v-model="entrepot.nom" required class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Ville</span>
            <input v-model="entrepot.ville" class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Responsable</span>
            <input v-model="entrepot.nom_responsable" required class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">E-mail responsable</span>
            <input v-model="entrepot.email_responsable" type="email" required class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Température min (°C)</span>
            <input v-model="entrepot.temperature_min_c" type="number" step="0.5" class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Température max (°C)</span>
            <input v-model="entrepot.temperature_max_c" type="number" step="0.5" class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Humidité min (%)</span>
            <input v-model="entrepot.humidite_min_pct" type="number" step="1" class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Humidité max (%)</span>
            <input v-model="entrepot.humidite_max_pct" type="number" step="1" class="champ" />
          </label>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button type="button" class="bouton-secondaire" @click="formulaireEntrepot = false">Annuler</button>
          <button type="submit" :disabled="enMutationEntrepot" class="bouton-primaire">
            <PackagePlus class="size-4" />
            {{ enMutationEntrepot ? "Enregistrement…" : entrepotIdModifie ? "Enregistrer les modifications" : "Créer l'entrepôt" }}
          </button>
        </div>
      </form>

      <EtatChargement v-if="entrepots.isLoading" />
      <EtatVide v-else-if="(entrepots.data?.length ?? 0) === 0" libelle="Aucun entrepôt consolidé." />
      <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="e in entrepots.data ?? []" :key="e.id" class="rounded-lg border border-border p-3">
          <div class="flex items-center gap-2">
            <Warehouse class="size-4 text-muted-foreground" />
            <span class="font-medium">{{ e.nom }}</span>
            <span class="ml-auto flex gap-1">
              <button
                class="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted"
                title="Modifier"
                @click="ouvrirModifEntrepot(e)"
              >
                <Pencil class="size-4" />
              </button>
              <button
                class="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                title="Supprimer"
                @click="supprimerEntrepot(e)"
              >
                <Trash2 class="size-4" />
              </button>
            </span>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">
            {{ e.ville ?? "—" }} · {{ nomsPays[e.pays_id] ?? "—" }}
          </p>
          <p class="mt-1 text-xs text-muted-foreground">
            {{ formaterTemperature(e.temperature_min_c) }} – {{ formaterTemperature(e.temperature_max_c) }} · H
            {{ formaterTemperature(e.humidite_min_pct) }} – {{ formaterTemperature(e.humidite_max_pct) }}
          </p>
        </div>
      </div>
    </Section>

    <Section
      titre="Capteurs IoT"
      description="Créez un capteur rattaché à un entrepôt."
    >
      <template #action>
        <button
          class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          @click="ouvrirCapteur"
        >
          <Radio class="size-4" /> Nouveau capteur
        </button>
      </template>

      <form
        v-if="formulaireCapteur"
        class="mb-4 rounded-lg border border-border bg-muted/30 p-4"
        @submit.prevent="enregistrerCapteur"
      >
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Entrepôt</span>
            <select v-model="capteur.entrepot_id" required class="champ">
              <option v-for="e in entrepots.data ?? []" :key="e.id" :value="e.id">
                {{ e.nom }}{{ nomsPays[e.pays_id] ? ` · ${nomsPays[e.pays_id]}` : "" }}
              </option>
            </select>
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Référence</span>
            <input v-model="capteur.reference" required class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Topic MQTT</span>
            <input v-model="capteur.topic_mqtt" required class="champ" placeholder="futurekawa/pays/…" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Type</span>
            <input v-model="capteur.type_capteur" required class="champ" />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Fréquence (s)</span>
            <input v-model="capteur.frequence_mesure_secondes" type="number" min="5" class="champ" />
          </label>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button type="button" class="bouton-secondaire" @click="formulaireCapteur = false">Annuler</button>
          <button type="submit" :disabled="enMutationCapteur" class="bouton-primaire">
            <Plus class="size-4" />
            {{ enMutationCapteur ? "Enregistrement…" : capteurIdModifie ? "Enregistrer les modifications" : "Créer le capteur" }}
          </button>
        </div>
      </form>

      <EtatChargement v-if="capteurs.isLoading" />
      <EtatVide v-else-if="(capteurs.data?.length ?? 0) === 0" libelle="Aucun capteur consolidé." />
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th class="py-2 pr-4 font-medium">Référence</th>
              <th class="py-2 pr-4 font-medium">Type</th>
              <th class="py-2 pr-4 font-medium">Entrepôt</th>
              <th class="py-2 pr-4 font-medium">Topic</th>
              <th class="py-2 pr-4 font-medium">Statut</th>
              <th class="py-2 pr-4 font-medium">Fréquence</th>
              <th class="py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in capteurs.data ?? []" :key="c.id" class="border-b border-border/60">
              <td class="py-2.5 pr-4 font-mono">{{ c.reference }}</td>
              <td class="py-2.5 pr-4">{{ c.type_capteur ?? "—" }}</td>
              <td class="py-2.5 pr-4">{{ nomsEntrepots[c.entrepot_id] ?? "—" }}</td>
              <td class="py-2.5 pr-4 font-mono text-xs text-muted-foreground">{{ c.topic_mqtt ?? "—" }}</td>
              <td class="py-2.5 pr-4">{{ c.statut ?? "—" }}</td>
              <td class="py-2.5 pr-4">{{ c.frequence_mesure_secondes ?? "—" }} s</td>
              <td class="py-2.5 text-right">
                <button
                  class="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted"
                  title="Modifier"
                  @click="ouvrirModifCapteur(c)"
                >
                  <Pencil class="size-4" />
                </button>
                <button
                  class="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                  title="Supprimer"
                  @click="supprimerCapteur(c)"
                >
                  <Trash2 class="size-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Section>

    <div class="flex justify-end">
      <button
        class="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted/50"
        @click="rechargerTout"
      >
        <RotateCcw class="size-4" /> Actualiser
      </button>
    </div>
  </div>
</template>

<style scoped>
.champ {
  height: 2.25rem;
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border);
  background: var(--color-background);
  padding: 0 0.75rem;
  font-size: 0.875rem;
  outline: none;
}
.champ:focus {
  box-shadow: 0 0 0 2px var(--color-ring);
}
.bouton-primaire {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  border-radius: 0.5rem;
  background: var(--color-primary);
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-primary-foreground);
  transition: opacity 0.15s;
}
.bouton-primaire:hover {
  opacity: 0.9;
}
.bouton-primaire:disabled {
  opacity: 0.5;
}
.bouton-secondaire {
  border-radius: 0.5rem;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  color: var(--color-muted-foreground);
  transition: background 0.15s;
}
.bouton-secondaire:hover {
  background: var(--color-muted);
}
</style>