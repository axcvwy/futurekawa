/**
 * Client HTTP du backend central (siège) FutureKawa.
 * Le frontend ne communique JAMAIS directement avec les backends pays.
 */

import { useAuth } from "../stores/auth";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:5001";

export class ApiError extends Error {
  statut: number;

  constructor(message: string, statut: number) {
    super(message);
    this.name = "ApiError";
    this.statut = statut;
  }
}

export type Params = Record<string, string | number | boolean | null | undefined>;

function construireUrl(chemin: string, params?: Params): string {
  const url = new URL(API_BASE_URL + chemin);
  if (params) {
    for (const [cle, valeur] of Object.entries(params)) {
      if (valeur === undefined || valeur === null || valeur === "") continue;
      url.searchParams.set(cle, String(valeur));
    }
  }
  return url.toString();
}

function entetes(avecContenu: boolean): HeadersInit {
  const { token } = useAuth();
  const entetes: Record<string, string> = { Accept: "application/json" };
  if (avecContenu) entetes["Content-Type"] = "application/json";
  if (token.value) entetes["Authorization"] = `Bearer ${token.value}`;
  return entetes;
}

export async function apiGet<T>(chemin: string, params?: Params): Promise<T> {
  const reponse = await fetch(construireUrl(chemin, params), {
    headers: entetes(false),
  });
  if (!reponse.ok) {
    throw new ApiError(`Échec de la requête ${chemin} (${reponse.status})`, reponse.status);
  }
  return (await reponse.json()) as T;
}

export async function apiEnvoyer<T>(
  methode: "POST" | "PUT" | "PATCH" | "DELETE",
  chemin: string,
  corps?: unknown,
  params?: Params,
): Promise<T> {
  const reponse = await fetch(construireUrl(chemin, params), {
    method: methode,
    headers: entetes(true),
    body: corps === undefined ? null : JSON.stringify(corps),
  });
  if (!reponse.ok) {
    let detail = `Échec de la requête ${chemin} (${reponse.status})`;
    try {
      const donnees = (await reponse.json()) as { detail?: string };
      if (donnees?.detail) detail = donnees.detail;
    } catch {
      /* réponse non JSON */
    }
    throw new ApiError(detail, reponse.status);
  }
  return (await reponse.json()) as T;
}
