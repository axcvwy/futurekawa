import { ref, watch } from "vue";

const CLE_STOCKAGE = "futurekawa.selection";

const paysId = ref<string | undefined>(undefined);
const exploitationId = ref<string | undefined>(undefined);

try {
  const brut = window.localStorage.getItem(CLE_STOCKAGE);
  if (brut) {
    const donnees = JSON.parse(brut) as { paysId?: string; exploitationId?: string };
    if (donnees.paysId) paysId.value = donnees.paysId;
    if (donnees.exploitationId) exploitationId.value = donnees.exploitationId;
  }
} catch {
  /* stockage indisponible */
}

watch(
  [paysId, exploitationId],
  ([p, e]) => {
    try {
      window.localStorage.setItem(CLE_STOCKAGE, JSON.stringify({ paysId: p, exploitationId: e }));
    } catch {
      /* stockage indisponible */
    }
  },
  { deep: true },
);

export function useSelection() {
  return {
    paysId,
    exploitationId,
    definirPays: (id?: string) => {
      paysId.value = id;
      exploitationId.value = undefined;
    },
    definirExploitation: (id?: string) => {
      exploitationId.value = id;
    },
  };
}
