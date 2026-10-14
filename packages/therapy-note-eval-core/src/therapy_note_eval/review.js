// Original bilingual interface. Source content is rendered only as text.
const cs = DATA.language === 'cs';
const tr = (en, cz) => cs ? cz : en;
document.documentElement.lang = DATA.language;
document.querySelector('#title').textContent = DATA.mode === 'adjudication'
  ? tr('Resolve disagreements', 'Posouzení neshod')
  : tr('Independent documentation review', 'Nezávislé hodnocení zápisu');
document.querySelector('#notice').textContent = tr(
  'Private review. Leave unassessed items blank. Save ratings in your private study folder.',
  'Neveřejné hodnocení. Nehodnocené položky nechte prázdné. Výsledky uložte do neveřejné složky studie.'
);
function text(parent, tag, value) {
  const element = document.createElement(tag);
  element.textContent = value; parent.append(element); return element;
}
const identity = document.querySelector('#identity');
const rater = document.createElement('input');
rater.placeholder = tr('Rater code', 'Kód hodnotitele');
rater.setAttribute('aria-label', rater.placeholder); identity.append(rater);
const role = document.createElement('select');
role.setAttribute('aria-label', tr('Your role', 'Vaše role'));
for (const [v, en, cz] of [
  ['', 'Select your role', 'Vyberte svoji roli'],
  ['therapist', 'Therapist', 'Terapeut'], ['supervisor', 'Supervisor', 'Supervizor'],
  ['client', 'Client reviewer', 'Klientský hodnotitel'],
  ['documentation_specialist', 'Documentation specialist', 'Odborník na dokumentaci'],
  ['native_speaker', 'Native speaker', 'Rodilý mluvčí'],
  ['researcher', 'Researcher', 'Výzkumník']
]) { const o = text(role, 'option', tr(en, cz)); o.value = v; }
identity.append(role);
const authorLabel = text(identity, 'label', tr('Did you help design this instrument?', 'Podílel/a jste se na návrhu tohoto nástroje?'));
const author = document.createElement('select'); authorLabel.append(author);
for (const [value, en, cz] of [['', 'Select', 'Vyberte'], ['yes', 'Yes', 'Ano'], ['no', 'No', 'Ne']]) {
  text(author, 'option', tr(en, cz)).value = value;
}
const app = document.querySelector('#app');
if (DATA.purpose_instructions) {
  text(app, 'h2', tr('Purpose and task specification', 'Účel a zadání zápisu'));
  text(app, 'p', DATA.purpose_instructions);
}
if (DATA.eligibility) {
  for (const [key, values] of Object.entries(DATA.eligibility)) {
    text(app, 'h3', key);
    for (const value of values) text(app, 'p', value);
  }
}
if (DATA.method_definitions?.length) {
  for (const method of DATA.method_definitions) {
    text(app, 'h3', method.id);
    text(app, 'p', method.definition);
    for (const [key, value] of Object.entries(method.severity_rules)) text(app, 'p', key + ': ' + value);
  }
} else if (DATA.stage !== 'registry_review' && DATA.stage !== 'literature_screening') text(app, 'p', tr('Severity: minor = limited correction; major = materially misleading documentation; critical = a plausible serious safety consequence. Rate severity only after identifying an error. These are development anchors.',
  'Závažnost: drobná = omezená oprava; závažná = podstatně zavádějící dokumentace; kritická = věrohodný závažný dopad na bezpečnost. Závažnost posuzujte až po zjištění chyby. Jde o vývojové kotvy.'));
function source(parent, sources) {
  for (const s of sources || []) {
    text(parent, 'h3', tr('Source: ', 'Zdroj: ') + s.id);
    for (const t of s.turns) {
      text(parent, 'pre', `${t.id} · ${t.speaker}: ${t.text}`).id = `source-${s.id}-${t.id}`;
    }
  }
}
function evidence(parent, values) {
  for (const value of values || []) {
    const span = value.span || value;
    text(parent, 'blockquote', span.quote || value.text || '');
    if (value.source_id) {
      const link = text(parent, 'a', tr('Show source passage', 'Zobrazit pasáž ve zdroji'));
      link.href = `#source-${value.source_id}-${span.unit_id}`;
    }
  }
}
source(app, DATA.sources);
if (DATA.note) { text(app, 'h2', tr('Note', 'Zápis')); text(app, 'pre', DATA.note); }
const names = {
  supported:'Podpořeno', contradicted:'V rozporu', unsupported:'Nepodloženo',
  unassessable:'Nelze posoudit', preserved:'Zachováno', partial:'Částečně zachováno',
  not_applicable:'Nevztahuje se', answered:'Odpověď doložena', not_in_note:'Informace v zápisu chybí',
  failed:'Odpověď se nepodařilo získat',
  eligibility:'Výběr zdroje', include:'Zařadit', exclude:'Vyřadit', uncertain:'Nejisté',
  omitted:'Vynecháno',
  mandatory:'Povinné', mandatory_in_certain_circumstances:'Povinné za určitých okolností',
  highly_recommended:'Silně doporučené', good_to_have:'Dobré mít', optional:'Volitelné',
  retain:'Zachovat', generalize:'Zobecnit', omit:'Vynechat',
  complete_atomic:'Úplné, jednotlivé výroky', missing_claim:'Chybí tvrzení',
  compound_claim:'Spojená tvrzení', incorrect_split:'Chybné rozdělení',
  pass:'Splněno', fail:'Nesplněno', appropriate:'Vhodná', leading:'Návodná',
  ambiguous:'Nejasná', irrelevant:'Nepodstatná', wrong_answer:'Chybná odpověď',
  a_better:'Lepší A', b_better:'Lepší B', both_acceptable:'Oba přijatelné',
  both_unacceptable:'Oba nepřijatelné', cannot_decide:'Nelze rozhodnout',
  none:'Žádná', minor:'Drobná', major:'Závažná', critical:'Kritická',
  claim:'Tvrzení', qa:'Zachování informace', importance:'Důležitost',
  disclosure:'Zacházení s detailem', segmentation:'Rozdělení tvrzení',
  dimension:'Vlastnost zápisu', question:'Kvalita otázky', pair:'Porovnání zápisů',
  severity:'Závažnost chyby', continuity:'Kontinuita péče', supervision:'Supervize',
  client:'Komunikace s klientem', audit:'Dokumentační audit', all:'Všechny účely',
  clinical:'Klinická přiměřenost', privacy:'Citlivé informace',
  language:'Jazyk a srozumitelnost', instructions:'Dodržení zadání'
};
const label = value => cs ? (names[value] || value) : value.replaceAll('_', ' ');
const controls = new Map();
const reasons = new Map();
for (const item of DATA.items) {
  const box = document.createElement('article'); app.append(box);
  text(box, 'small', label(item.kind) + ' · ' + label(item.profile));
  text(box, 'h3', item.kind === 'dimension' ? label(item.text) : item.text);
  if (item.definition) {
    text(box, 'p', item.definition.definition);
    for (const [key, value] of Object.entries(item.definition.anchors || {})) text(box, 'p', label(key) + ': ' + value);
    for (const [key, value] of Object.entries(item.definition.examples || {})) text(box, 'p', key + ': ' + value);
  }
  const ctx = item.context || {};
  if (ctx.research_content) text(box, 'pre', JSON.stringify(ctx.research_content, null, 2));
  if (ctx.abstract) text(box, 'p', ctx.abstract);
  if (ctx.doi) text(box, 'p', 'DOI: ' + ctx.doi);
  if (item.kind === 'pair') {
    text(box, 'h4', 'A'); text(box, 'pre', ctx.A);
    text(box, 'h4', 'B'); text(box, 'pre', ctx.B); source(box, ctx.sources);
  } else if (Array.isArray(ctx)) { evidence(box, ctx); }
  else {
    if (ctx.source_answer) {
      text(box, 'h4', tr('Source answer to check', 'Zdrojová odpověď ke kontrole'));
      text(box, 'p', ctx.source_answer);
    }
    evidence(box, ctx.source_evidence || ctx.evidence);
    if ('note_answer' in ctx) {
      text(box, 'h4', tr('Answer from the note', 'Odpověď ze zápisu'));
      text(box, 'p', ctx.note_answer ? label(ctx.note_answer.status) : tr('Not measured', 'Dosud neměřeno'));
      if (ctx.note_answer?.text) text(box, 'p', ctx.note_answer.text);
      evidence(box, ctx.note_answer?.evidence);
    }
  }
  if (item.human_votes) {
    text(box, 'h4', tr('Initial human ratings', 'Původní lidská hodnocení'));
    for (const vote of item.human_votes) text(box, 'p', label(vote.value || 'unassessable'));
  }
  if (item.kind === 'task') {
    const answer = document.createElement('textarea');
    answer.setAttribute('aria-label', item.text);
    box.append(answer); controls.set(item.id, answer); continue;
  }
  const select = document.createElement('select');
  select.setAttribute('aria-label', label(item.kind) + ': ' + item.text);
  text(select, 'option', tr('Not rated', 'Nehodnoceno')).value = '';
  for (const value of item.choices) text(select, 'option', label(value)).value = value;
  box.append(select); controls.set(item.id, select);
  if (item.require_reason) {
    text(box, 'label', tr('Decision reason (required)', 'Důvod rozhodnutí (povinný)'));
    const reason = document.createElement('textarea'); box.append(reason); reasons.set(item.id, reason);
  }
}
document.querySelector('#missingTitle').textContent = tr(DATA.missing_information_prompt,
  DATA.stage === 'note_only_task'
    ? 'Odpovídejte pouze ze zápisu. Uveďte, pokud odpověď chybí. Popište obtíže, čas a věcné opravy.'
    : DATA.stage === 'source_bank'
      ? 'Jaké důležité informace chybí ve zdrojové bance? Zkontrolujte otázky, význam a jazyk.'
      : DATA.mode === 'adjudication'
        ? 'Zdůvodněte řešení neshod. Nehodnocené položky nejsou shodou.'
        : 'Jaká důležitá informace nebo otázka chybí? Uveďte také důvody svého hodnocení.');
const observations = {};
for (const [key, en, cz] of [
  ['review_seconds', 'Review time (seconds)', 'Čas kontroly (sekundy)'],
  ['factual_edits', 'Number of factual edits', 'Počet věcných oprav'],
  ['style_edits', 'Number of style edits', 'Počet stylistických úprav'],
  ['information_found_seconds', 'Time to find information (seconds)', 'Čas nalezení informace (sekundy)']
]) {
  const field = text(document.querySelector('#observations'), 'label', tr(en, cz));
  const input = document.createElement('input'); input.type = 'number'; input.min = '0';
  field.append(input); observations[key] = input;
}
const save = document.querySelector('#save');
save.textContent = tr('Download ratings', 'Stáhnout hodnocení');
save.onclick = () => {
  if (!rater.value.trim() || !role.value || !author.value) {
    alert(tr('Enter your rater code and role.', 'Vyplňte kód hodnotitele a svoji roli.')); return;
  }
  const answers = [...controls].filter(([_, c]) => c.value)
    .map(([id, c]) => ({id, value: c.value}));
  for (const answer of answers) {
    const item = DATA.items.find(item => item.id === answer.id);
    if (DATA.mode === 'adjudication' && item.supersedes) answer.supersedes = item.supersedes;
    if (reasons.has(answer.id)) {
      answer.reason = reasons.get(answer.id).value.trim();
      if (!answer.reason) {
        alert(tr('Give a reason for each decision.', 'U každého rozhodnutí uveďte důvod.')); return;
      }
    }
  }
  const out = {version: DATA.version, sheet_id: DATA.id, rater_id: rater.value.trim(),
    role: role.value, mode: DATA.mode, instrument_author: author.value === 'yes', answers,
    submitted_at: new Date().toISOString(),
    missing_information: document.querySelector('#missing').value};
  for (const [key, input] of Object.entries(observations)) {
    out[key] = input.value === '' ? null : Number(input.value);
    if (out[key] !== null && (!Number.isFinite(out[key]) || out[key] < 0)) {
      alert(tr('Enter non-negative measurements.', 'Vyplňte nezáporné hodnoty měření.')); return;
    }
  }
  const url = URL.createObjectURL(new Blob([JSON.stringify(out, null, 2)], {type:'application/json'}));
  const link = document.createElement('a');
  link.href = url; link.download = 'gen2-ratings-' + DATA.id.slice(0, 12) + '.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  document.querySelector('#progress').textContent = answers.length + ' / ' + DATA.items.length;
};
