import test from "node:test";
import assert from "node:assert/strict";

import {
  buildPresentationRows,
  formatSubjectLabel,
  formatVariantForms,
} from "../conjugation-view.mjs";

test("identical compound forms are rendered once for each subject", () => {
  const table = {
    form_id: "passe_compose",
    rows: [
      { person: "je", context: { person: "je", gender: "masculine", number: "singular" }, display_forms: ["ai parlé"] },
      { person: "je", context: { person: "je", gender: "feminine", number: "singular" }, display_forms: ["ai parlé"] },
    ],
  };
  assert.deepEqual(buildPresentationRows(table), [
    { subject: "j'", conjugation: "ai parlé", person: "je" },
  ]);
});

test("être agreement variants are grouped into compact parenthetical notation", () => {
  assert.equal(formatVariantForms(["suis sorti", "suis sortie"]), "suis sorti(e)");
  assert.equal(formatVariantForms(["sommes sortis", "sommes sorties"]), "sommes sorti(e)s");
  assert.equal(
    formatVariantForms(["êtes sorti", "êtes sortie", "êtes sortis", "êtes sorties"]),
    "êtes sorti(e)(s)",
  );
});

test("does not imply unavailable agreement combinations in the compact display", () => {
  assert.equal(
    formatVariantForms(["est sorti", "est sortis", "est sorties"]),
    "est sorti / est sortis / est sorties",
  );
});

test("subjunctive subjects include que and use French elision", () => {
  assert.equal(formatSubjectLabel("je", "subjonctif_present", ["parle"]), "que je");
  assert.equal(formatSubjectLabel("je", "subjonctif_passe", ["aie parlé"]), "que j'");
  assert.equal(formatSubjectLabel("il", "subjonctif_present", ["parle"]), "qu'il");
  assert.equal(formatSubjectLabel("on", "subjonctif_passe", ["ait parlé"]), "qu'on");
});

test("presentation never adds courtesy or standard usage explanations", () => {
  const table = {
    form_id: "passe_compose",
    rows: [
      { person: "vous", context: { person: "vous", usage: "courtesy", gender: "masculine", number: "singular" }, display_forms: ["avez parlé"] },
      { person: "vous", context: { person: "vous", usage: "standard", gender: "feminine", number: "plural" }, display_forms: ["avez parlé"] },
    ],
  };
  assert.deepEqual(buildPresentationRows(table), [
    { subject: "vous", conjugation: "avez parlé", person: "vous" },
  ]);
});
