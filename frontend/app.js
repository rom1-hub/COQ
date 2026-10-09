(() => {
  "use strict";

  const tabs = [...document.querySelectorAll(".mode-tab")];
  const form = document.querySelector("#search-form");
  const panel = document.querySelector("#panel");
  const hint = document.querySelector("#mode-hint");
  const submit = document.querySelector("#submit-search");
  const feedback = document.querySelector("#feedback");
  const feedbackTitle = document.querySelector("#feedback-title");
  const feedbackBody = document.querySelector("#feedback-body");
  const feedbackKind = document.querySelector("#feedback-kind");
  const summary = document.querySelector("#selection-summary");
  const reset = document.querySelector("#reset-all");
  const verbInput = document.querySelector("#verb-search");
  const verbHelp = document.querySelector("#verb-help");
  const tenseSelect = document.querySelector("#tense");
  const groupSelect = document.querySelector("#group");
  const familyField = document.querySelector("#family-field");
  const familySelect = document.querySelector("#family");
  const auxiliarySelect = document.querySelector("#auxiliary");
  let mode = "lookup";

  const compoundTenses = new Set([
    "passe_compose",
    "plus_que_parfait",
    "conditionnel_passe",
    "futur_anterieur",
    "subjonctif_passe",
  ]);
  const nonPersonalForms = new Set(["participe_present", "gerondif_present"]);
  const tenseLabels = new Map(
    [...tenseSelect.options].map((option) => [option.value, option.textContent.trim()]),
  );
  const groupLabels = new Map(
    [...groupSelect.options].map((option) => [option.value, option.textContent.trim()]),
  );
  const familyLabels = new Map(
    [...familySelect.options].map((option) => [option.value, option.textContent.trim()]),
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

  function showFeedback(title, body, kind = mode === "lookup" ? "Consulta" : "Práctica", entries = []) {
    feedbackTitle.textContent = title;
    feedbackBody.textContent = body;
    feedbackKind.textContent = kind;
    summary.replaceChildren();

    for (const [label, value] of entries) {
      const term = document.createElement("dt");
      const description = document.createElement("dd");
      term.textContent = label;
      description.textContent = value || "Sin filtro";
      summary.append(term, description);
    }

    summary.hidden = entries.length === 0;
    feedback.hidden = false;
  }

  function hideFeedback() {
    feedback.hidden = true;
    summary.hidden = true;
    summary.replaceChildren();
  }

  function updateFamilyControl() {
    const isFamilyMode = groupSelect.value === "family";
    familyField.hidden = !isFamilyMode;
    familySelect.disabled = !isFamilyMode;
    if (!isFamilyMode) familySelect.value = "";
  }

  function updateAuxiliaryControl() {
    const tense = tenseSelect.value;
    const isUnavailable = nonPersonalForms.has(tense) || (tense !== "" && !compoundTenses.has(tense));
    auxiliarySelect.disabled = isUnavailable;
    if (isUnavailable) auxiliarySelect.value = "";
    document.querySelector("#auxiliary-help").textContent = isUnavailable
      ? "El auxiliar solo se filtra para tiempos compuestos."
      : "El filtro de auxiliar se aplica a los tiempos compuestos.";
  }

  function setMode(nextMode) {
    mode = nextMode;
    tabs.forEach((tab) => {
      const active = tab.dataset.mode === mode;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panel.setAttribute("aria-labelledby", mode === "lookup" ? "tab-lookup" : "tab-practice");
    form.dataset.mode = mode;
    reset.hidden = mode === "lookup";

    if (mode === "lookup") {
      hint.textContent = "Busca un verbo y elige qué tiempos o formas quieres consultar.";
      verbHelp.textContent = "Introduce el infinitivo francés que quieres consultar.";
      submit.textContent = "Consultar conjugación";
      verbInput.required = true;
    } else {
      hint.textContent = "Práctica: selecciona un verbo, un grupo o una familia. El objetivo previsto es una sesión de 20 preguntas.";
      verbHelp.textContent = "Puedes elegir un verbo concreto o definir un conjunto con los filtros.";
      submit.textContent = "Preparar práctica";
      verbInput.required = false;
    }
    hideFeedback();
  }

  function selectedSummary() {
    const data = new FormData(form);
    const selectedGroup = String(data.get("group") || "");
    const selectedTense = String(data.get("tense") || "");
    const selectedFamily = String(data.get("family") || "");
    const selectedConstruction = String(data.get("construction") || "");
    const selectedAuxiliary = String(data.get("auxiliary") || "");

    const commonEntries = [
      ["Verbo", String(data.get("verb") || "").trim() || "No especificado"],
      ["Tiempo o forma", tenseLabels.get(selectedTense) || "Todos los tiempos verbales"],
    ];

    if (mode === "lookup") return commonEntries;

    return [
      ...commonEntries,
      ["Grupo", groupLabels.get(selectedGroup) || "Todos los grupos"],
      ...(selectedGroup === "family" ? [["Familia", familyLabels.get(selectedFamily) || "No seleccionada"]] : []),
      ["Construcción", constructionLabels.get(selectedConstruction) || "Todas las construcciones"],
      ["Auxiliar", auxiliaryLabels.get(selectedAuxiliary) || "Todos los auxiliares"],
    ];
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => setMode(tab.dataset.mode));
  });

  groupSelect.addEventListener("change", () => {
    updateFamilyControl();
    hideFeedback();
  });

  tenseSelect.addEventListener("change", () => {
    updateAuxiliaryControl();
    hideFeedback();
  });

  form.addEventListener("input", hideFeedback);
  form.addEventListener("change", hideFeedback);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const verb = verbInput.value.trim();
    const selectedFamily = familySelect.value;

    if (mode === "lookup" && !verb) {
      showFeedback("Falta el verbo", "Escribe el infinitivo que quieres consultar.", "Revisar datos");
      verbInput.focus();
      return;
    }

    if (mode === "practice" && groupSelect.value === "family" && !selectedFamily) {
      showFeedback("Selecciona una familia", "Has elegido el filtro por familia morfológica; selecciona también la familia concreta.", "Revisar datos");
      familySelect.focus();
      return;
    }

    if (mode === "practice" && !verb && !groupSelect.value && !selectedFamily) {
      showFeedback("Define el conjunto de práctica", "Para preparar una sesión, introduce un verbo o selecciona un grupo o una familia verbal.", "Revisar datos");
      groupSelect.focus();
      return;
    }

    const entries = selectedSummary();
    if (mode === "lookup") {
      showFeedback(
        "Consulta recibida correctamente",
        `La interfaz ha registrado la consulta de «${verb}» para «${tenseLabels.get(tenseSelect.value) || "Todos los tiempos verbales"}». Todavía no puede mostrar las conjugaciones porque el catálogo de verbos y el motor Python no están implementados. No se han inventado formas verbales.`,
        "Consulta",
        entries,
      );
    } else {
      showFeedback(
        "Configuración de práctica validada",
        "Los filtros están preparados para una sesión prevista de 20 preguntas. El generador y el corrector no se ejecutan todavía porque el catálogo y el motor lingüístico están pendientes.",
        "Práctica · 20 preguntas",
        entries,
      );
    }
  });

  reset.addEventListener("click", () => {
    form.reset();
    setMode("lookup");
    updateFamilyControl();
    updateAuxiliaryControl();
    hideFeedback();
    verbInput.focus();
  });

  // Estado inicial explícito: los filtros dependientes empiezan sincronizados.
  updateFamilyControl();
  updateAuxiliaryControl();
  setMode("lookup");
})();
