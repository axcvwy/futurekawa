import type { Mesure } from "./types";

export interface ConditionsConservation {
  temperature_cible_c?: number | null;
  humidite_cible_pct?: number | null;
  tolerance_temperature_c?: number | null;
  tolerance_humidite_pct?: number | null;
}

export interface AnalyseConformite {
  temperature: AnalyseSerie;
  humidite: AnalyseSerie;
}

export interface AnalyseSerie {
  total: number;
  dansPlage: number;
  horsPlage: number;
  pourcentageConforme: number | null;
  ecartMoyen: number | null;
  ecartMax: number | null;
  min: number | null;
  max: number | null;
  deriveLaPlusLongue: number;
}

function analyserSerie(
  valeurs: Array<{ valeur: number; cible: number; tolerance: number }>,
): AnalyseSerie {
  const total = valeurs.length;
  const min = total ? Math.min(...valeurs.map((v) => v.valeur)) : null;
  const max = total ? Math.max(...valeurs.map((v) => v.valeur)) : null;

  if (total === 0) {
    return { total: 0, dansPlage: 0, horsPlage: 0, pourcentageConforme: null, ecartMoyen: null, ecartMax: null, min: null, max: null, deriveLaPlusLongue: 0 };
  }

  const dansPlage = valeurs.filter((v) => Math.abs(v.valeur - v.cible) <= v.tolerance).length;
  const ecarts = valeurs.map((v) => Math.abs(v.valeur - v.cible));
  const deriveLaPlusLongue = valeurs.reduce(
    (acc, v) => {
      const conforme = Math.abs(v.valeur - v.cible) <= v.tolerance;
      const suite = conforme ? 0 : acc.suite + 1;
      return { suite, max: Math.max(acc.max, suite) };
    },
    { suite: 0, max: 0 },
  ).max;

  return {
    total,
    dansPlage,
    horsPlage: total - dansPlage,
    pourcentageConforme: Math.round((dansPlage / total) * 1000) / 10,
    ecartMoyen: ecarts.reduce((a, b) => a + b, 0) / total,
    ecartMax: Math.max(...ecarts),
    min,
    max,
    deriveLaPlusLongue,
  };
}

/**
 * Analyse la conformité d'un historique de mesures par rapport aux conditions
 * idéales du pays (cible ± tolérance). Retourne une analyse par série.
 */
export function analyserMesures(mesures: Mesure[], conditions: ConditionsConservation): AnalyseConformite {
  const temperature = mesures
    .map((m) => m.temperature_c)
    .filter((v): v is number => v != null && conditions.temperature_cible_c != null && conditions.tolerance_temperature_c != null)
    .map((v) => ({ valeur: v, cible: conditions.temperature_cible_c as number, tolerance: conditions.tolerance_temperature_c as number }));

  const humidite = mesures
    .map((m) => m.humidite_pct)
    .filter((v): v is number => v != null && conditions.humidite_cible_pct != null && conditions.tolerance_humidite_pct != null)
    .map((v) => ({ valeur: v, cible: conditions.humidite_cible_pct as number, tolerance: conditions.tolerance_humidite_pct as number }));

  return {
    temperature: analyserSerie(temperature),
    humidite: analyserSerie(humidite),
  };
}
