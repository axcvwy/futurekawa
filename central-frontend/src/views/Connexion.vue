<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { toast } from "vue-sonner";
import { Coffee, Lock, Mail, UserRound } from "lucide-vue-next";
import { apiEnvoyer, ApiError } from "../lib/api";
import { useAuth, type Utilisateur } from "../stores/auth";

const { connecter } = useAuth();
const router = useRouter();

const email = ref("");
const motDePasse = ref("");
const enCours = ref(false);

async function seConnecter(): Promise<void> {
  if (enCours.value) return;
  enCours.value = true;
  try {
    const reponse = await apiEnvoyer<{ access_token: string; utilisateur: Utilisateur }>(
      "POST",
      "/auth/login",
      { email: email.value, mot_de_passe: motDePasse.value },
    );
    connecter(reponse.access_token, reponse.utilisateur);
    toast.success("Connexion réussie", { description: `Bienvenue, ${reponse.utilisateur.nom}.` });
    void router.push("/");
  } catch (e) {
    const message = e instanceof ApiError ? e.message : "Impossible de se connecter";
    toast.error("Échec de la connexion", { description: message });
  } finally {
    enCours.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex min-h-[70vh] w-full max-w-md flex-col justify-center py-10">
    <div class="mb-8 flex flex-col items-center gap-3 text-center">
      <span class="flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
        <Coffee class="size-7" />
      </span>
      <h1 class="font-display text-2xl font-semibold">FutureKawa — Console siège</h1>
      <p class="text-sm text-muted-foreground">Identifiez-vous pour accéder aux données consolidées.</p>
    </div>

    <form
      class="space-y-4 rounded-xl border border-border bg-card p-6 shadow-sm"
      @submit.prevent="seConnecter"
    >
      <label class="block">
        <span class="mb-1.5 flex items-center gap-1.5 text-sm font-medium">
          <Mail class="size-4" /> Adresse e-mail
        </span>
        <input
          v-model="email"
          type="email"
          autocomplete="username"
          required
          placeholder="vous@futurekawa.com"
          class="h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </label>

      <label class="block">
        <span class="mb-1.5 flex items-center gap-1.5 text-sm font-medium">
          <Lock class="size-4" /> Mot de passe
        </span>
        <input
          v-model="motDePasse"
          type="password"
          autocomplete="current-password"
          required
          placeholder="••••••••"
          class="h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </label>

      <button
        type="submit"
        :disabled="enCours"
        class="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
      >
        <UserRound class="size-4" />
        {{ enCours ? "Connexion…" : "Se connecter" }}
      </button>
    </form>

    <p class="mt-4 text-center text-xs text-muted-foreground">
      Accès par rôle : ADMIN_SIEGE, RESPONSABLE_EXPLOITATION, RESPONSABLE_ENTREPOT, REFERENT_QUALITE.
    </p>
  </div>
</template>
