(() => {
  "use strict";

  const tabs = [...document.querySelectorAll(".mode-tab")];
  const lookupPanel = document.querySelector("#lookup-panel");
  const practicePanel = document.querySelector("#practice-panel");
  const lookupForm = document.querySelector("#lookup-form");
  const practiceForm = document.querySelector("#practice-form");

  const lookupVerb = document.querySelector("#lookup-verb");
  const lookupTense = document.querySelector("#lookup-tense");
  const practiceVerb = document.querySelector("#practice-verb");
  const practiceTense = document.querySelector("#practice-tense");
  const practiceScope = document.querySelector("#practice-scope");
  const practiceConstruction = document.querySelector("#practice-construction");
  const practiceAuxiliary = document.querySelector("#practice-auxiliary");
  const practiceProfileHelp = document.querySelector("#practice-profile-help");
  const resetPractice = document.querySelector("#reset-practice");

  const lookupFeedback = createFeedback("lookup");
  const practiceFeedback = createFeedback("practice");
  let mode = "lookup";
  let practiceProfiles = {};
  let activePracticeProfile = null;
  let unlockedPracticeValues = null;

  const tenseLabels = new Map(
    [...lookupTense.options].map((option) => [option.value, option.textContent.trim()]),
  );
  const practiceTenseLabels = new Map(
    [...practiceTense.options].map((option) => [option.value, option.textContent.trim()]),
  );
  const scopeLabels = new Map(
    [...practiceScope.options].map((option) => [option.value, option.textContent.trim()]),
  );
  const constructionLabels = new Map([
    ["", "Todas las construcciones"],
    ["non_pronominal", "No pronominal"],
    ["pronominal", "Pronominal"],
  ]);
  const auxiliaryLabels = new Map([
    ["", "Todos los auxiliares"],
    ["avoir", "AVOIR"],
    ["etre", "ÊTRE"],
  ]);

  function createFeedback(prefix) {
    return {
      root: document.querySelector(`#${prefix}-feedback`),
      title: document.querySelector(`#${prefix}-feedback-title`),
      body: document.querySelector(`#${prefix}-feedback-body`),
      kind: document.querySelector(`#${prefix}-feedback-kind`),
      summary: document.querySelector(`#${prefix}-summary`),
    };
  }

  function showFeedback(target, title, body, kind, entries = []) {
    target.title.textContent = title;
    target.body.textContent = body;
    target.kind.textContent = kind;
    target.summary.replaceChildren();

    for (const [label, value] of entries) {
      const term = document.createElement("dt");
      const description = document.createElement("dd");
      term.textContent = label;
      description.textContent = value || "Sin filtro";
      target.summary.append(term, description);
    }

    target.summary.hidden = entries.length === 0;
    target.root.hidden = false;
  }

  function hideFeedback(target) {
    target.root.hidden = true;
    target.summary.hidden = true;
    target.summary.replaceChildren();
  }

  function setMode(nextMode) {
    mode = nextMode;
    const isLookup = mode === "lookup";
    tabs.forEach((tab) => {
      const active = tab.dataset.mode === mode;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    lookupPanel.hidden = !isLookup;
    practicePanel.hidden = isLookup;
    if (isLookup) lookupVerb.focus();
    else practiceVerb.focus();
  }

  function normalizeInfinitive(value) {
    // Only normalize casing and surrounding whitespace; do not discard diacritics.
    return value.trim().toLocaleLowerCase("fr-FR");
  }

  function captureUnlockedPracticeValues() {
    return {
      scope: practiceScope.value,
      construction: practiceConstruction.value,
      auxiliary: practiceAuxiliary.value,
    };
  }

  function restoreUnlockedPracticeValues() {
    if (unlockedPracticeValues) {
      practiceScope.value = unlockedPracticeValues.scope;
      practiceConstruction.value = unlockedPracticeValues.construction;
      practiceAuxiliary.value = unlockedPracticeValues.auxiliary;
    }
    practiceScope.disabled = false;
    practiceConstruction.disabled = false;
    practiceAuxiliary.disabled = false;
    unlockedPracticeValues = null;
    activePracticeProfile = null;
  }

  function applyPracticeProfile() {
    const verbKey = normalizeInfinitive(practiceVerb.value);
    const profile = practiceProfiles[verbKey];

    if (profile && activePracticeProfile !== verbKey) {
      if (!activePracticeProfile) unlockedPracticeValues = captureUnlockedPracticeValues();
      activePracticeProfile = verbKey;
      practiceScope.value = profile.scope;
      practiceConstruction.value = profile.construction;
      practiceAuxiliary.value = profile.auxiliary;
      practiceScope.disabled = true;
      practiceConstruction.disabled = true;
      practiceAuxiliary.disabled = true;
      practiceProfileHelp.textContent = `Perfil de demostración: ${profile.label}. Grupo, construcción y auxiliar se han completado y bloqueado; puedes seleccionar el tiempo verbal. Este perfil no sustituye al catálogo lingüístico.`;
      return;
    }

    if (!profile && activePracticeProfile) restoreUnlockedPracticeValues();

    if (!verbKey) {
      practiceProfileHelp.textContent = "Sin verbo específico: puedes elegir los filtros de práctica.";
    } else if (!profile) {
      practiceProfileHelp.textContent = "Este verbo aún no tiene un perfil en la demostración. No se infiere su grupo, construcción ni auxiliar; los filtros siguen editables hasta conectar el catálogo verificado.";
    } else {
      practiceProfileHelp.textContent = `Perfil de demostración: ${profile.label}. Grupo, construcción y auxiliar se han completado y bloqueado; puedes seleccionar el tiempo verbal. Este perfil no sustituye al catálogo lingüístico.`;
    }
  }

  function currentLookupSummary() {
    return [
      ["Verbo", lookupVerb.value.trim()],
      ["Tiempo o forma", tenseLabels.get(lookupTense.value) || "Todos los tiempos verbales"],
    ];
  }

  function currentPracticeSummary() {
    return [
      ["Verbo", practiceVerb.value.trim() || "No especificado"],
      ["Tiempo o forma", practiceTenseLabels.get(practiceTense.value) || "Todos los tiempos verbales"],
      ["Grupo o familia", scopeLabels.get(practiceScope.value) || "Todos los grupos y familias"],
      ["Construcción", constructionLabels.get(practiceConstruction.value) || "Todas las construcciones"],
      ["Auxiliar", auxiliaryLabels.get(practiceAuxiliary.value) || "Todos los auxiliares"],
    ];
  }

  tabs.forEach((tab) => tab.addEventListener("click", () => setMode(tab.dataset.mode)));

  lookupForm.addEventListener("input", () => hideFeedback(lookupFeedback));
  lookupForm.addEventListener("change", () => hideFeedback(lookupFeedback));
  lookupForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const verb = lookupVerb.value.trim();
    if (!verb) {
      showFeedback(lookupFeedback, "Falta el verbo", "Escribe el infinitivo que quieres consultar.", "Revisar datos");
      lookupVerb.focus();
      return;
    }

    showFeedback(
      lookupFeedback,
      "Consulta recibida correctamente",
      `La interfaz ha registrado la consulta de «${verb}» para «${tenseLabels.get(lookupTense.value) || "Todos los tiempos verbales"}». El catálogo y el motor Python aún no están implementados, por lo que todavía no se muestran conjugaciones reales.`,
      "Consulta",
      currentLookupSummary(),
    );
  });

  practiceVerb.addEventListener("input", () => {
    applyPracticeProfile();
    hideFeedback(practiceFeedback);
  });
  practiceForm.addEventListener("input", () => hideFeedback(practiceFeedback));
  practiceForm.addEventListener("change", () => hideFeedback(practiceFeedback));
  practiceForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const verb = normalizeInfinitive(practiceVerb.value);
    const scope = practiceScope.value;

    if (!verb && !scope && !practiceConstruction.value && !practiceAuxiliary.value) {
      showFeedback(
        practiceFeedback,
        "Define el conjunto de práctica",
        "Escribe un verbo o elige un grupo, una familia, una construcción o un auxiliar para acotar la práctica.",
        "Revisar datos",
        currentPracticeSummary(),
      );
      practiceScope.focus();
      return;
    }

    const profileNote = verb && !practiceProfiles[verb]
      ? " El verbo todavía no tiene un perfil verificado en el catálogo disponible; los filtros no se han deducido automáticamente."
      : "";
    showFeedback(
      practiceFeedback,
      "Configuración de práctica validada",
      `Los campos de práctica son independientes de «Ver conjugación». La sesión prevista contiene 20 preguntas; el generador y el corrector reales aún están pendientes.${profileNote}`,
      "Práctica · 20 preguntas",
      currentPracticeSummary(),
    );
  });

  resetPractice.addEventListener("click", () => {
    practiceForm.reset();
    // Reset means the form defaults, not the pre-profile values saved for an unlock.
    activePracticeProfile = null;
    unlockedPracticeValues = null;
    practiceScope.disabled = false;
    practiceConstruction.disabled = false;
    practiceAuxiliary.disabled = false;
    applyPracticeProfile();
    hideFeedback(practiceFeedback);
    practiceVerb.focus();
  });

  // This tiny file is a UX fixture, not the linguistic source of truth.
  fetch("./verb-profiles.demo.json")
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      practiceProfiles = data.profiles || {};
      applyPracticeProfile();
    })
    .catch(() => {
      practiceProfiles = {};
      practiceProfileHelp.textContent = "No se ha podido cargar el perfil de demostración. Los filtros permanecen editables; el catálogo verificado se incorporará más adelante.";
    });

  setMode("lookup");
})();
