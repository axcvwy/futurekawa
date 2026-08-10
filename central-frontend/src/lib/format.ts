export function formaterDateHeure(valeur?: string | null): string {
  if (!valeur) return "—";
  const date = new Date(valeur);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export function formaterDate(valeur?: string | null): string {
  if (!valeur) return "—";
  const date = new Date(valeur);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(date);
}

export function formaterNombre(valeur?: number | null, unite = ""): string {
  if (valeur === null || valeur === undefined) return "—";
  return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(valeur)}${unite}`;
}

export function joursDepuis(valeur?: string | null): number | null {
  if (!valeur) return null;
  const date = new Date(valeur);
  if (Number.isNaN(date.getTime())) return null;
  return Math.floor((Date.now() - date.getTime()) / 86400000);
}

export function depuisMaintenant(valeur?: string | null): string {
  if (!valeur) return "jamais";
  const date = new Date(valeur);
  if (Number.isNaN(date.getTime())) return "jamais";
  const secondes = Math.floor((Date.now() - date.getTime()) / 1000);
  if (secondes < 60) return "il y a quelques secondes";
  if (secondes < 3600) return `il y a ${Math.floor(secondes / 60)} min`;
  if (secondes < 86400) return `il y a ${Math.floor(secondes / 3600)} h`;
  return `il y a ${Math.floor(secondes / 86400)} j`;
}
