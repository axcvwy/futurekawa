export type StatutSync = "SUCCES" | "ECHEC" | "SUCCES_PARTIEL" | string;
export type StatutAlerte = "ACTIVE" | "PRISE_EN_COMPTE" | "RESOLUE" | "IGNOREE";
export type NiveauAlerte = "MOYEN" | "ELEVE" | string;

export interface Pays {
  id: string;
  nom: string;
  code_iso: string;
  api_base_url?: string;
  actif: boolean;
  mock?: boolean;
  intervalle_sync_secondes?: number;
  temperature_cible_c?: number | null;
  humidite_cible_pct?: number | null;
  tolerance_temperature_c?: number | null;
  tolerance_humidite_pct?: number | null;
  derniere_sync_reussie_le?: string | null;
  dernier_statut_sync?: StatutSync | null;
  derniere_erreur_sync?: string | null;
}

export interface Sante {
  status: string;
  base_de_donnees?: string;
  pays: Array<{
    code_iso: string;
    nom: string;
    actif: boolean;
    mock?: boolean;
    dernier_statut_sync?: StatutSync | null;
    derniere_sync_reussie_le?: string | null;
    derniere_erreur_sync?: string | null;
  }>;
}

export interface Exploitation {
  id: string;
  pays_id: string;
  source_id?: string | null;
  nom: string;
  code?: string | null;
  ville?: string | null;
  actif: boolean;
  cree_le?: string;
  mis_a_jour_le?: string;
}

export interface Entrepot {
  id: string;
  pays_id: string;
  exploitation_id?: string | null;
  nom: string;
  ville?: string | null;
  code_pays?: string | null;
  nom_responsable?: string | null;
  email_responsable?: string | null;
  temperature_min_c?: number | null;
  temperature_max_c?: number | null;
  humidite_min_pct?: number | null;
  humidite_max_pct?: number | null;
  pays?: { id: string; nom: string; code_iso?: string };
  exploitation?: { id: string; nom: string; code?: string | null };
}

export interface Capteur {
  id: string;
  pays_id: string;
  entrepot_id: string;
  reference: string;
  topic_mqtt?: string | null;
  type_capteur?: string | null;
  statut?: string | null;
  frequence_mesure_secondes?: number | null;
  derniere_communication?: string | null;
}

export interface Lot {
  id: string;
  pays_id: string;
  entrepot_id: string;
  source_id?: string | null;
  code_lot: string;
  produit?: string | null;
  quantite_kg?: number | null;
  date_stockage: string;
  statut?: string | null;
  entrepot?: { id: string; nom: string; ville?: string | null };
  pays?: { id: string; nom: string };
  exploitation?: { id: string; nom: string; code?: string | null };
}

export interface Mesure {
  id: string;
  pays_id: string;
  entrepot_id?: string | null;
  capteur_id?: string | null;
  lot_id?: string | null;
  source?: string | null;
  topic_mqtt?: string | null;
  date_mesure: string;
  date_reception?: string | null;
  temperature_c?: number | null;
  humidite_pct?: number | null;
}

export interface Alerte {
  id: string;
  pays_id: string;
  entrepot_id?: string | null;
  lot_id?: string | null;
  capteur_id?: string | null;
  type_alerte: string;
  niveau: NiveauAlerte;
  statut: StatutAlerte;
  message?: string | null;
  valeur_detectee?: number | null;
  seuil_minimum?: number | null;
  seuil_maximum?: number | null;
  date_declenchement: string;
  date_resolution?: string | null;
  resolue_par?: string | null;
  commentaire_resolution?: string | null;
  email_envoye?: boolean | null;
  date_email?: string | null;
  pays?: { id: string; nom: string; code_iso?: string };
  entrepot?: { id: string; nom: string; ville?: string | null };
  transfert_local?: string;
}

export interface Synchronisation {
  id: string;
  pays_id: string;
  declencheur?: string;
  statut?: StatutSync;
  demarree_le?: string;
  terminee_le?: string | null;
  entrepots_lus?: number;
  entrepots_ecrits?: number;
  capteurs_lus?: number;
  capteurs_ecrits?: number;
  lots_lus?: number;
  lots_ecrits?: number;
  mesures_lues?: number;
  mesures_ecrites?: number;
  alertes_lues?: number;
  alertes_ecrites?: number;
  erreur?: string | null;
}

export interface Utilisateur {
  id: string;
  email: string;
  nom: string;
  role: string;
  actif: boolean;
  pays_id?: string | null;
  entrepot_id?: string | null;
  cree_le?: string;
  mis_a_jour_le?: string;
}
