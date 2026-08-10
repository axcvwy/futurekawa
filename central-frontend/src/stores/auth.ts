import { ref, computed } from "vue";

const CLE_TOKEN = "futurekawa.token";
const CLE_UTILISATEUR = "futurekawa.utilisateur";

export const ROLES = {
  ADMIN_SIEGE: "ADMIN_SIEGE",
  RESPONSABLE_EXPLOITATION: "RESPONSABLE_EXPLOITATION",
  RESPONSABLE_ENTREPOT: "RESPONSABLE_ENTREPOT",
  REFERENT_QUALITE: "REFERENT_QUALITE",
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

export interface Utilisateur {
  id: string;
  email: string;
  nom: string;
  role: Role;
  actif: boolean;
  pays_id?: string | null;
  entrepot_id?: string | null;
  cree_le?: string;
  mis_a_jour_le?: string;
}

const token = ref<string | null>(null);
const utilisateur = ref<Utilisateur | null>(null);
const role = computed(() => utilisateur.value?.role);

function lireStockage(): void {
  try {
    token.value = window.localStorage.getItem(CLE_TOKEN);
    const brut = window.localStorage.getItem(CLE_UTILISATEUR);
    if (brut) utilisateur.value = JSON.parse(brut) as Utilisateur;
  } catch {
    /* stockage indisponible */
  }
}

function enregistrerStockage(): void {
  try {
    if (token.value) window.localStorage.setItem(CLE_TOKEN, token.value);
    else window.localStorage.removeItem(CLE_TOKEN);
    if (utilisateur.value) window.localStorage.setItem(CLE_UTILISATEUR, JSON.stringify(utilisateur.value));
    else window.localStorage.removeItem(CLE_UTILISATEUR);
  } catch {
    /* stockage indisponible */
  }
}

lireStockage();

export function useAuth() {
  return {
    token,
    utilisateur,
    connecter: (nouveauToken: string, profil: Utilisateur) => {
      token.value = nouveauToken;
      utilisateur.value = profil;
      enregistrerStockage();
    },
    deconnecter: () => {
      token.value = null;
      utilisateur.value = null;
      enregistrerStockage();
    },
    estConnecte: () => Boolean(token.value),
    estAdmin: () => utilisateur.value?.role === ROLES.ADMIN_SIEGE,
    role,
  };
}
