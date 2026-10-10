const DEFAULT_LOCAL_API_BASE_URL = "http://127.0.0.1:8000/api/v1";
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1"]);

function normalizeInfinitive(value) {
  return String(value ?? "").trim().normalize("NFC").toLocaleLowerCase("fr-FR");
}

function resolveBaseUrl(configuredBaseUrl, locationObject) {
  const configured = String(configuredBaseUrl ?? "").trim();
  if (configured) return configured.replace(/\/+$/, "");
  if (locationObject && LOCAL_HOSTS.has(locationObject.hostname)) {
    return DEFAULT_LOCAL_API_BASE_URL;
  }
  throw new CoqApiError(
    "La API de COQ no está configurada para este sitio. Define window.COQ_API_BASE_URL antes de cargar la interfaz.",
    { code: "API_BASE_URL_NOT_CONFIGURED", status: 0 },
  );
}

export class CoqApiError extends Error {
  constructor(message, { code = "API_ERROR", status = 0, details = {} } = {}) {
    super(message);
    this.name = "CoqApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/** Independent HTTP client for the regular COQ API, never the synthetic test server. */
export function createCoqApiClient({
  baseUrl,
  fetchImpl = globalThis.fetch,
  locationObject = globalThis.location,
} = {}) {
  if (typeof fetchImpl !== "function") {
    throw new TypeError("Este entorno no proporciona fetch().");
  }
  const apiBaseUrl = resolveBaseUrl(baseUrl, locationObject);

  async function request(path, { query = {}, method = "GET", body } = {}) {
    const url = new URL(`${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`);
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }

    let response;
    try {
      response = await fetchImpl(url.toString(), {
        method,
        headers: {
          Accept: "application/json",
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch {
      throw new CoqApiError(
        `No se pudo conectar con la API de COQ en ${apiBaseUrl}. Comprueba que el backend esté ejecutándose.`,
        { code: "API_UNREACHABLE", status: 0 },
      );
    }

    let payload = null;
    try {
      payload = await response.json();
    } catch {
      // Keep an HTTP-derived error below when the response has no JSON body.
    }

    if (!response.ok) {
      const fallback = `La API respondió con HTTP ${response.status}.`;
      throw new CoqApiError(
        typeof payload?.message === "string" ? payload.message : fallback,
        {
          code: typeof payload?.code === "string" ? payload.code : "API_ERROR",
          status: response.status,
          details: payload?.details && typeof payload.details === "object" ? payload.details : {},
        },
      );
    }

    if (payload === null || typeof payload !== "object") {
      throw new CoqApiError("La API devolvió una respuesta que no es un objeto JSON.", {
        code: "INVALID_API_RESPONSE",
        status: response.status,
      });
    }
    return payload;
  }

  async function getHealth() {
    return request("/health");
  }

  async function searchVerbs(query, limit = 10, { exact = false } = {}) {
    const normalized = normalizeInfinitive(query);
    if (!normalized) {
      throw new CoqApiError("Escribe el infinitivo francés que quieres consultar.", {
        code: "INVALID_REQUEST",
        status: 422,
      });
    }
    const payload = await request("/verbs/search", {
      query: { q: normalized, limit, exact },
    });
    if (!Array.isArray(payload.items) || typeof payload.query !== "string") {
      throw new CoqApiError("La respuesta de búsqueda no respeta el contrato de COQ.", {
        code: "INVALID_API_RESPONSE",
      });
    }
    return payload;
  }

  async function lookupConjugation(verbId, formId = "") {
    const normalizedId = String(verbId ?? "").trim();
    if (!normalizedId) {
      throw new CoqApiError("La consulta necesita un identificador de verbo aprobado.", {
        code: "INVALID_REQUEST",
        status: 422,
      });
    }
    const payload = await request(`/verbs/${encodeURIComponent(normalizedId)}/conjugation`, {
      query: { form_id: formId },
    });
    if (typeof payload.infinitive !== "string" || !Array.isArray(payload.tables)) {
      throw new CoqApiError("La respuesta de conjugación no respeta el contrato de COQ.", {
        code: "INVALID_API_RESPONSE",
      });
    }
    return payload;
  }

  async function lookupByInfinitive(infinitive, formId = "") {
    const query = normalizeInfinitive(infinitive);
    const search = await searchVerbs(query, 20, { exact: true });
    // exact=true means the server matched the canonical infinitive or a registered alias;
    // the frontend never infers IDs or chooses a prefix-only result.
    const canonicalMatch = search.items.find(
      (item) => normalizeInfinitive(item.infinitive) === query,
    );
    if (canonicalMatch) return lookupConjugation(canonicalMatch.verb_id, formId);

    if (search.items.length === 0) {
      throw new CoqApiError(`No se encontró un verbo aprobado con el infinitivo «${query}».`, {
        code: "VERB_NOT_FOUND",
        status: 404,
      });
    }
    if (search.items.length > 1) {
      throw new CoqApiError(`El término «${query}» coincide con varios alias. Consulta el infinitivo canónico.`, {
        code: "AMBIGUOUS_VERB_ALIAS",
        status: 409,
      });
    }
    return lookupConjugation(search.items[0].verb_id, formId);
  }

  return Object.freeze({
    baseUrl: apiBaseUrl,
    getHealth,
    searchVerbs,
    lookupConjugation,
    lookupByInfinitive,
  });
}
