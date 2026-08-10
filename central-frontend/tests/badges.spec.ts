import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import BadgeNiveau from "../src/components/BadgeNiveau.vue";
import BadgeStatutLot from "../src/components/BadgeStatutLot.vue";

describe("BadgeNiveau", () => {
  it("affiche le libellé français d'un niveau ELEVE", () => {
    const wrapper = mount(BadgeNiveau, { props: { niveau: "ELEVE" } });
    expect(wrapper.text()).toContain("Élevé");
  });

  it("affiche le libellé français d'un niveau MOYEN", () => {
    const wrapper = mount(BadgeNiveau, { props: { niveau: "MOYEN" } });
    expect(wrapper.text()).toContain("Moyen");
  });

  it("repli gracieux si le niveau est inconnu", () => {
    const wrapper = mount(BadgeNiveau, { props: { niveau: "INCONNU" } });
    expect(wrapper.text()).toBe("INCONNU");
  });
});

describe("BadgeStatutLot", () => {
  it("traduit un statut de lot en libellé lisible", () => {
    const wrapper = mount(BadgeStatutLot, { props: { statut: "EN_STOCK" } });
    expect(wrapper.text().toLowerCase()).toContain("en stock");
  });

  it("affiche un repli pour un statut absent", () => {
    const wrapper = mount(BadgeStatutLot, { props: { statut: undefined } });
    expect(wrapper.text().toLowerCase()).toContain("inconnu");
  });
});