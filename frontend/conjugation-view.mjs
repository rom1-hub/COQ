const SUBJUNCTIVE_FORMS = new Set(["subjonctif_present", "subjonctif_passe"]);
const NON_PERSONAL_FORMS = new Set(["participe_present", "gerondif_present"]);
const PERSONAL_FORMS = new Set([
  "present_indicatif",
  "imperatif_present",
  "imparfait",
  "conditionnel_present",
  "futur_simple",
  "subjonctif_present",
  "passe_compose",
  "plus_que_parfait",
  "conditionnel_passe",
  "futur_anterieur",
  "subjonctif_passe",
]);
const ELIDABLE_QUE_SUBJECTS = new Set(["il", "elle", "on", "ils", "elles"]);
const FRENCH_VOWEL_START = /^[aeiouyàâäéèêëîïôöùûüœ]/iu;

function uniqueForms(values) {
  return [...new Set((Array.isArray(values) ? values : [])
    .filter((value) => typeof value === "string")
    .map((value) => value.trim())
    .filter(Boolean))];
}

function commonPrefix(values) {
  if (!values.length) return "";
  let prefix = values[0];
  for (const value of values.slice(1)) {
    while (prefix && !value.startsWith(prefix)) prefix = prefix.slice(0, -1);
    if (!prefix) break;
  }
  return prefix;
}

/** Condense reviewed agreement variants without exposing gender/number rows. */
export function formatVariantForms(values) {
  const forms = uniqueForms(values);
  if (forms.length <= 1) return forms[0] || "";

  const prefix = commonPrefix(forms);
  if (prefix) {
    const endings = forms.map((form) => form.slice(prefix.length));
    if (endings.every((ending) => ["", "e", "s", "es"].includes(ending))) {
      const hasE = endings.some((ending) => ending.includes("e"));
      const hasNoE = endings.some((ending) => !ending.includes("e"));
      const hasS = endings.some((ending) => ending.includes("s"));
      const hasNoS = endings.some((ending) => !ending.includes("s"));
      const feminine = !hasE ? "" : hasNoE ? "(e)" : "e";
      const plural = !hasS ? "" : hasNoS ? "(s)" : "s";
      const condensed = `${prefix}${feminine}${plural}`;
      // Avoid inventing an unattested combination for unusual suffix subsets.
      const feminineChoices = hasE ? (hasNoE ? ["", "e"] : ["e"]) : [""];
      const pluralChoices = hasS ? (hasNoS ? ["", "s"] : ["s"]) : [""];
      const representedEndings = new Set(
        feminineChoices.flatMap((feminineEnding) =>
          pluralChoices.map((pluralEnding) => `${feminineEnding}${pluralEnding}`),
        ),
      );
      const exactRepresentation = representedEndings.size === endings.length
        && endings.every((ending) => representedEndings.has(ending));
      if (exactRepresentation && condensed) return condensed;
    }
  }

  return forms.join(" / ");
}

/** Render only the subject text; agreement metadata remains in the API model. */
export function formatSubjectLabel(person, formId, forms) {
  if (!person) return "Forma no personal";
  const firstForm = uniqueForms(forms)[0] || "";
  const elideJe = person === "je" && FRENCH_VOWEL_START.test(firstForm);

  if (SUBJUNCTIVE_FORMS.has(formId)) {
    if (elideJe) return "que j'";
    if (ELIDABLE_QUE_SUBJECTS.has(person)) return `qu'${person}`;
    return `que ${person}`;
  }

  return elideJe ? "j'" : person;
}

function groupPersonalRows(table) {
  const groups = new Map();
  for (const row of table.rows || []) {
    const person = row.person || row.context?.person || null;
    if (!groups.has(person)) groups.set(person, []);
    groups.get(person).push(row);
  }

  return [...groups.entries()].map(([person, rows]) => {
    const forms = uniqueForms(rows.flatMap((row) => row.display_forms || []));
    return {
      subject: formatSubjectLabel(person, table.form_id, forms),
      conjugation: formatVariantForms(forms),
      person,
    };
  });
}

export function buildPresentationRows(table) {
  if (!table || !Array.isArray(table.rows)) return [];
  if (PERSONAL_FORMS.has(table.form_id) && !NON_PERSONAL_FORMS.has(table.form_id)) {
    return groupPersonalRows(table);
  }

  return table.rows.map((row) => ({
    subject: row.display_subject || "Forma no personal",
    conjugation: formatVariantForms(row.display_forms || []),
    person: null,
  }));
}

export function renderConjugationTables(host, tables) {
  if (!host) throw new TypeError("Falta el contenedor de resultados de conjugación.");
  host.replaceChildren();
  const fragment = document.createDocumentFragment();

  for (const item of Array.isArray(tables) ? tables : []) {
    const section = document.createElement("section");
    section.className = "conjugation-result";

    const heading = document.createElement("h3");
    heading.textContent = item.label_fr || item.form_id || "Conjugación";
    section.appendChild(heading);

    const scroll = document.createElement("div");
    scroll.className = "conjugation-table-scroll";
    const table = document.createElement("table");
    table.className = "conjugation-table";
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");

    for (const label of ["Sujeto", "Conjugación"]) {
      const th = document.createElement("th");
      th.scope = "col";
      th.textContent = label;
      headerRow.appendChild(th);
    }

    thead.appendChild(headerRow);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");

    for (const row of buildPresentationRows(item)) {
      const tr = document.createElement("tr");
      const subjectCell = document.createElement("td");
      const formCell = document.createElement("td");
      subjectCell.textContent = row.subject;
      formCell.textContent = row.conjugation;
      tr.append(subjectCell, formCell);
      tbody.appendChild(tr);
    }

    table.appendChild(tbody);
    scroll.appendChild(table);
    section.appendChild(scroll);
    fragment.appendChild(section);
  }

  host.appendChild(fragment);
  host.hidden = !Array.isArray(tables) || tables.length === 0;
}
