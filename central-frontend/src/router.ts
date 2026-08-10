import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "./stores/auth";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/connexion",
      name: "connexion",
      component: () => import("./views/Connexion.vue"),
      meta: { public: true },
    },
    {
      path: "/",
      name: "tableau-de-bord",
      component: () => import("./views/TableauDeBord.vue"),
    },
    {
      path: "/lots",
      name: "lots",
      component: () => import("./views/LotsListe.vue"),
    },
    {
      path: "/lots/:lotId",
      name: "lot-detail",
      component: () => import("./views/LotDetail.vue"),
      props: true,
    },
    {
      path: "/alertes",
      name: "alertes",
      component: () => import("./views/Alertes.vue"),
    },
    {
      path: "/pays",
      name: "pays",
      component: () => import("./views/PaysPilotage.vue"),
    },
    {
      path: "/configuration",
      name: "configuration",
      component: () => import("./views/Configuration.vue"),
      meta: { adminOnly: true },
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach((destination) => {
  const { estConnecte, estAdmin } = useAuth();
  if (!destination.meta.public && !estConnecte()) {
    return { name: "connexion", query: { retour: destination.fullPath } };
  }
  if (destination.meta.adminOnly && !estAdmin()) {
    return { name: "tableau-de-bord" };
  }
  if (destination.name === "connexion" && estConnecte()) {
    return { name: "tableau-de-bord" };
  }
  return true;
});
