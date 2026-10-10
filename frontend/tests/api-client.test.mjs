import test from "node:test";
import assert from "node:assert/strict";
import { createCoqApiClient, CoqApiError } from "../api-client.mjs";

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() { return payload; },
  };
}

const localLocation = { hostname: "localhost" };

test("lookup by infinitive searches approved catalog before conjugation", async () => {
  const calls = [];
  const client = createCoqApiClient({
    baseUrl: "http://127.0.0.1:8000/api/v1",
    locationObject: localLocation,
    fetchImpl: async (url) => {
      calls.push(url);
      if (url.includes("/verbs/search?")) {
        return jsonResponse({
          query: "parler",
          limit: 20,
          items: [{
            verb_id: "v_parler",
            infinitive: "parler",
            label: "parler",
            group_id: "first",
            family_ids: ["first_regular"],
            default_construction_id: "parler.non_pronominal",
          }],
        });
      }
      return jsonResponse({
        verb_id: "v_parler",
        infinitive: "parler",
        construction_id: "parler.non_pronominal",
        tables: [{ form_id: "present_indicatif", label_fr: "Présent de l’indicatif", rows: [] }],
      });
    },
  });

  const result = await client.lookupByInfinitive(" PARLER ", "present_indicatif");
  assert.equal(result.infinitive, "parler");
  assert.equal(calls.length, 2);
  assert.match(calls[0], /\/verbs\/search\?q=parler&limit=20&exact=true$/);
  assert.match(calls[1], /\/verbs\/v_parler\/conjugation\?form_id=present_indicatif$/);
});

test("catalog-not-ready errors keep the stable API error code and message", async () => {
  const client = createCoqApiClient({
    baseUrl: "http://127.0.0.1:8000/api/v1",
    locationObject: localLocation,
    fetchImpl: async () => jsonResponse({
      code: "CATALOG_NOT_READY",
      message: "El catálogo de conjugación todavía no está listo para consultas.",
      details: {},
    }, 503),
  });

  await assert.rejects(
    client.lookupByInfinitive("parler"),
    (error) => error instanceof CoqApiError
      && error.code === "CATALOG_NOT_READY"
      && error.status === 503
      && error.message.includes("todavía no está listo"),
  );
});

test("lookup refuses a prefix-only query when exact search finds no approved infinitive", async () => {
  const client = createCoqApiClient({
    baseUrl: "http://127.0.0.1:8000/api/v1",
    locationObject: localLocation,
    fetchImpl: async (url) => {
      assert.match(url, /exact=true$/);
      return jsonResponse({ query: "parl", limit: 20, items: [] });
    },
  });

  await assert.rejects(
    client.lookupByInfinitive("parl"),
    (error) => error instanceof CoqApiError && error.code === "VERB_NOT_FOUND",
  );
});

test("remote pages require an explicit API base URL instead of calling localhost", () => {
  assert.throws(
    () => createCoqApiClient({ fetchImpl: async () => {}, locationObject: { hostname: "coq.example" } }),
    (error) => error instanceof CoqApiError && error.code === "API_BASE_URL_NOT_CONFIGURED",
  );
});

test("exact registered alias resolves to its canonical approved verb", async () => {
  const calls = [];
  const client = createCoqApiClient({
    baseUrl: "http://127.0.0.1:8000/api/v1",
    locationObject: localLocation,
    fetchImpl: async (url) => {
      calls.push(url);
      if (url.includes("/verbs/search?")) {
        return jsonResponse({
          query: "parlo",
          limit: 20,
          items: [{
            verb_id: "v_parler",
            infinitive: "parler",
            label: "parler",
            group_id: "first",
            family_ids: ["first_regular"],
            default_construction_id: "parler.non_pronominal",
          }],
        });
      }
      return jsonResponse({
        verb_id: "v_parler",
        infinitive: "parler",
        construction_id: "parler.non_pronominal",
        tables: [{ form_id: "present_indicatif", label_fr: "Présent", rows: [] }],
      });
    },
  });

  const result = await client.lookupByInfinitive("parlo");
  assert.equal(result.infinitive, "parler");
  assert.equal(calls.length, 2);
});

test("ambiguous exact aliases fail closed instead of selecting an arbitrary verb", async () => {
  const client = createCoqApiClient({
    baseUrl: "http://127.0.0.1:8000/api/v1",
    locationObject: localLocation,
    fetchImpl: async () => jsonResponse({
      query: "alias",
      limit: 20,
      items: [
        { verb_id: "v_aller", infinitive: "aller", label: "aller", group_id: "third", family_ids: [], default_construction_id: "aller.non_pronominal" },
        { verb_id: "v_parler", infinitive: "parler", label: "parler", group_id: "first", family_ids: ["first_regular"], default_construction_id: "parler.non_pronominal" },
      ],
    }),
  });

  await assert.rejects(
    client.lookupByInfinitive("alias"),
    (error) => error instanceof CoqApiError && error.code === "AMBIGUOUS_VERB_ALIAS",
  );
});
