#!/usr/bin/env node
/**
 * Rich UX-research corpus generator — "Northloop Banking" small-business
 * banking redesign program ("Harbor Ledger" study).
 *
 * Why synthetic (see RICH-README.md): no freely-licensed public corpus offers
 * dozens of deep, mutually-coherent interview transcripts with known ground
 * truth. Everything here is authored fixtures with deterministic output
 * (seeded PRNG): same seed => byte-identical corpus. Ground truth
 * (theme distribution, persona stances, survey means, SUS scores, planted
 * contradictions, stale markers) is written to manifest.json so eval
 * scenarios can assert coding/synthesis accuracy instead of vibes.
 *
 * Usage: node tests/document_corpus/generate-rich-corpus.mjs [--out DIR]
 * Output: <out>/ (default tests/document_corpus/rich/)
 */
import { createHash } from "crypto";
import { mkdirSync, writeFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = process.argv.includes("--out")
  ? process.argv[process.argv.indexOf("--out") + 1]
  : join(__dirname, "rich");

const SEED = 20260908;
const GENERATOR_VERSION = "1.0.0";

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(SEED);
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const pickN = (arr, n) => {
  const copy = [...arr];
  const out = [];
  while (copy.length && out.length < n) out.push(copy.splice(Math.floor(rnd() * copy.length), 1)[0]);
  return out;
};
const range = (n) => [...Array(n).keys()];

/* ── Personas: 16 synthetic participants, distinct voices and stances ── */
const PERSONAS = [
  { id: "P01", name: "Mara Ellison", role: "owner", business: "Ellison Bakery (12 staff)", region: "Portland", lang: "en", voice: "warm, concrete, talks in mornings-rush anecdotes", texture: ["Honestly?", "Let me give you Tuesday as an example.", "My staff will tell you the same."] },
  { id: "P02", name: "Devon Park", role: "owner", business: "Park Bike Repair (4 staff)", region: "Austin", lang: "en", voice: "terse, numbers-first, impatient with jargon", texture: ["Look,", "Bottom line:", "I don't have time for dashboards."] },
  { id: "P03", name: "Priya Natarajan", role: "owner", business: "Natarajan Textiles (28 staff)", region: "Chicago", lang: "en", voice: "analytical, compares everything to her old ERP", texture: ["In our old system,", "I measured this, actually.", "Three times last quarter."] },
  { id: "P04", name: "Tomás Rivera", role: "owner", business: "Rivera Landscaping (9 staff)", region: "Phoenix", lang: "es", voice: "habla con ejemplos de cuadrilla y nómina semanal", texture: ["Mire,", "Le doy un ejemplo del viernes.", "Mi gente depende de eso."] },
  { id: "P05", name: "Grace Okafor", role: "owner", business: "Okafor Childcare (15 staff)", region: "Atlanta", lang: "en", voice: "careful, compliance-minded, licensing vocabulary", texture: ["For licensing I need", "If an auditor asks,", "We document everything."] },
  { id: "P06", name: "Henrik Dahl", role: "owner", business: "Dahl Marine Supply (6 staff)", region: "Seattle", lang: "en", voice: "dry humor, seasonal-business framing", texture: ["Winter is our quarter-end.", "Ha. Ask me in April.", "Boats don't wait for reconciliation."] },
  { id: "P07", name: "Aisha Bello", role: "accountant", business: "Bello Books (external, 40 clients)", region: "Houston", lang: "en", voice: "precise, cites standards, corrects terminology", texture: ["Technically that's a", "The correct treatment is", "I tell every client this."] },
  { id: "P08", name: "Marco Ruiz", role: "accountant", business: "Ruiz & Associates (external, 22 clients)", region: "Miami", lang: "es", voice: "directo, habla de cierres mensuales y clientes difíciles", texture: ["En cada cierre,", "Mis clientes me llaman cuando", "Eso no es conciliación, eso es adivinanza."] },
  { id: "P09", name: "Jenny Lindqvist", role: "bookkeeper", business: "in-house, Dahl Marine", region: "Seattle", lang: "en", voice: "practical, shortcut-driven, loves keyboard flows", texture: ["My shortcut is", "I do it in batches on Fridays.", "If it takes more than three clicks I hate it."] },
  { id: "P10", name: "Sam Whitfield", role: "bookkeeper", business: "in-house, Ellison Bakery", region: "Portland", lang: "en", voice: "anxious about mistakes, double-checks everything", texture: ["I always worry that", "I check it twice because once I", "Mara trusts me and that terrifies me."] },
  { id: "P11", name: "Nadia Hassan", role: "teller", business: "Northloop Branch 14", region: "Portland", lang: "en", voice: "frontline stories, quotes customers verbatim", texture: ["A customer told me last week,", "At the window you see it all.", "They don't say 'pain point', they say—"] },
  { id: "P12", name: "Robert Chen", role: "teller", business: "Northloop Branch 03", region: "Austin", lang: "en", voice: "patient explainer, accessibility-aware", texture: ["For older customers,", "I walk them through it, step by step.", "The screen reader reads the whole table, every time."] },
  { id: "P13", name: "Lucía Fernández", role: "branch-manager", business: "Northloop Branch 09", region: "Phoenix", lang: "es", voice: "operativa, habla de metas y filas de espera", texture: ["En hora pico,", "Mi meta es", "La fila no perdona."] },
  { id: "P14", name: "Karen Doyle", role: "ops-admin", business: "Northloop Operations", region: "Chicago", lang: "en", voice: "risk register vocabulary, incidentmeeting cadence", texture: ["Per our incident review,", "That is a finding, not feedback.", "We track it as a control gap."] },
  { id: "P15", name: "James Osei", role: "ops-admin", business: "Northloop Fraud Desk", region: "Atlanta", lang: "en", voice: "alert-fatigue realist, false-positive math", texture: ["Ninety percent of these are noise.", "I cleared forty-three before lunch.", "Every false alarm teaches customers to ignore the real one."] },
  { id: "P16", name: "Elena Vasquez", role: "owner", business: "Vasquez Catering (7 staff, screen-reader user)", region: "Denver", lang: "en", voice: "accessibility-first, names exact barriers", texture: ["My screen reader says", "If it's not labeled I can't use it.", "Nobody tested this with a keyboard, did they."] },
];

/* ── Themes T1..T10 with per-stance quote banks (stance 1=support, -1=oppose, 0=mixed) ── */
/* Expanded language-split quote banks (replaces the v1 THEMES block). */
const THEMES = {
  T1: { title: "Invoice chasing eats the morning",
    en: [
    "I spend the first ninety minutes every day figuring out who owes me money. The invoices are in one place, the payments land in another, and my brain is the integration layer.",
    "Tuesday example: three catering invoices overdue, one client swears they paid, the deposit shows up under a different name. I lost the whole morning reconciling a story, not numbers.",
    "Bottom line: if the app can't tell me who is late and nudge them for me, it's a viewer, not a tool.",
    "I measured this, actually. Four point two hours a week on receivables. That's a part-time employee I can't hire.",
    "Winter is our quarter-end. Everything due in October arrives in my head in September and nowhere else.",
    "The aging report lists amounts but not owners. Someone owes me $3,800 and the row doesn't say who chased it last.",
    "I sent the same reminder three times with three tones. Friendly, firm, then begging. The app watched.",
    "A client paid half and wrote 'thanks!' in the memo. Half of what? Thanks for what? I spent an hour decoding gratitude.",
    "My accountant sees the overdue list monthly. I live it daily. That lag is where cash goes to hide.",
    "Friday afternoons I call instead of email. Calls work. Nothing in the software knows that.",
    "The biggest invoice is never the problem. It's the twelve small ones that nobody owns.",
    "I want one screen: who, how much, how late, last touch, next nudge — and a button that does the nudge.",
    ],
    es: [
    "En cada cierre, lo mismo: facturas vencidas que nadie persiguió porque nadie sabía que estaban vencidas.",
    "Los viernes llamo en vez de escribir. Las llamadas funcionan, pero el sistema no registra ni una.",
    "Un cliente pagó la mitad y puso 'gracias' en el concepto. ¿La mitad de qué? Perdí una hora descifrando.",
    "La lista de vencidos muestra montos pero no responsables. Alguien me debe y nadie sabe quién lo llamó.",
    "Mi gente depende de cobrar a tiempo. Cada factura tardía es nómina en riesgo.",
    ]},
  T2: { title: "Receipt capture dies at the point of sale",
    en: [
    "The receipt is in my apron pocket, then the van, then the laundry. By Friday it's a rumor.",
    "My shortcut is snapping it at the register, but half the time the photo is blurry and the app rejects it without saying why.",
    "I check it twice because once I lost a four-hundred-dollar receipt and Mara trusts me and that terrifies me.",
    "If it takes more than three clicks I hate it. At the counter there are no three clicks to spare.",
    "Technically that's a substantiation failure. No receipt, no deduction. I tell every client this.",
    "Thermal paper fades. By March the January receipts are blank ghosts and I'm reconstructing from card statements.",
    "The app wants the total, the tax, the category, and my patience — in that order, at the busiest minute of the day.",
    "I batch on Fridays and half the pile is mystery paper. Whose lunch was this? Business or sorry?",
    "Mileage, parking, tolls — the small stuff leaks around the edges of every system I've tried.",
    "A photo of a photo of a receipt. That's what my February looks like. Try auditing that.",
    "Cash purchases at the supply house never make it in. The owner pays cash, tells me Monday, I believe him on faith.",
    "Give me a shoebox mode: dump everything in, sort it Sunday, nag me only about the orphans.",
    ],
    es: [
    "Le doy un ejemplo del viernes: gasolina, hielo, propano — tres recibos, cero registrados el lunes.",
    "El papel térmico se borra. En marzo los recibos de enero son fantasmas y reconstruyo con el banco.",
    "Si toma más de tres clics lo odio. En la caja no hay tres clics de sobra.",
    "Las compras en efectivo nunca entran. El dueño paga, me avisa el lunes, y yo le creo por fe.",
    "Foto de foto de recibo. Así es mi febrero. Que lo audite quien pueda.",
    ]},
  T3: { title: "Approval chains stall on one absent person",
    en: [
    "Everything over five hundred needs my sign-off, and I'm on a ladder half the day. The whole company queues behind my phone battery.",
    "For licensing I need two signatures on file. When one is on vacation, payroll-adjacent spending just waits.",
    "I do it in batches on Fridays, but approvals don't batch. They rot, one by one, in an inbox nobody owns.",
    "In our old system, delegation worked: deputy approves under a cap, full audit trail. I measured the delay drop.",
    "Per our incident review, single-approver chains are a control gap. That is a finding, not feedback.",
    "The approver sees an amount with no context. Approve what? For whom? Against which job? It's a blind signature.",
    "Emergency purchases route around the chain entirely, then get scolded retroactively. The system trains circumvention.",
    "I approved something at a red light once. Never again — but the app let me, no questions asked.",
    "Weekend approvals pile to Monday and Monday is already full. The chain has no concept of urgency, only order.",
    "Two partners must both approve, but the app notifies them sequentially. Parallel would halve the wait and nobody can explain why it doesn't.",
    "The audit trail shows who clicked, not what they knew. That's a signature without informed consent.",
    "Deputy coverage exists on paper. In practice the deputy can't see the attachments, so they approve blind or not at all.",
    ],
    es: [
    "Mi meta es pagar a proveedores en 48 horas. Con la cadena actual, son seis días si alguien se enferma.",
    "Todo lo que pasa de quinientos necesita mi firma, y yo estoy en una escalera medio día.",
    "Las compras urgentes rodean la cadena y luego las regañan. El sistema entrena la evasión.",
    "La suplencia existe en papel. En la práctica no ve los adjuntos: aprueba a ciegas o no aprueba.",
    "Dos socios deben aprobar pero el aviso es secuencial. En paralelo tardaría la mitad.",
    ]},
  T4: { title: "Auto-matched bank feeds: loved by owners, distrusted by accountants (PLANTED DIVERGENCE)",
    en: [
    "The auto-match is magic. Ninety percent right, and I fix the rest with coffee. Don't take it away.",
    "Boats don't wait for reconciliation. If the feed guesses right, I sail. If not, I fix it in winter.",
    "The correct treatment is review-then-post, never post-then-review. Auto-posting buries errors where auditors find them.",
    "I always worry that a wrong match sits there looking correct. Correct-looking wrongness is the most expensive kind.",
    "Show me confidence per match and I'll review the shaky ten percent gladly. Certainty theater I will not accept.",
    "Last April it matched a supplier payment to the wrong job. We underbilled by nine hundred and found out in July.",
    "The override log is where trust lives. If I can see who confirmed what and undo it, I'll let it guess.",
    "Speed matters more than purity in season. I'll take 90% auto with a clean review queue over 100% manual and drowning.",
    "My old ERP never guessed. It also never finished. There is a middle I would pay for.",
    "Duplicate detection is the real hero, not matching. Catch the double-charge and I'll forgive ten bad guesses.",
    "Quarter-end turns every guess into a fact nobody re-examines. The calendar launders uncertainty.",
    "Train it on my corrections, visibly. If it learns my vendors, it's a colleague. If not, it's a slot machine.",
    ],
    es: [
    "Eso no es conciliación, eso es adivinanza. Adivinar con dinero ajeno es mala práctica, aunque acierte.",
    "Mis clientes me llaman cuando el banco y los libros no cuadran. El 'casi' automático es el culpable la mitad de las veces.",
    "Que me muestre la confianza de cada coincidencia y reviso el diez por ciento dudoso con gusto.",
    "El registro de cambios es donde vive la confianza. Si veo quién confirmó qué, lo dejo adivinar.",
    "En abril emparejó un pago al trabajo equivocado. Facturamos novecientos de menos y lo vimos en julio.",
    ]},
  T5: { title: "Payroll timing vs cash reality",
    en: [
    "Payroll hits Thursday, client payments land Friday. Every week I float the gap on a credit card and pretend it's strategy.",
    "I measured this, actually: eleven weeks last year where payroll preceded receivables by more than two days.",
    "For licensing I need payroll records clean to the day. The float makes clean impossible.",
    "Three times last quarter I moved money between accounts at midnight to make morning payroll. That's not banking, that's parkour.",
    "Honestly? A calendar that shows cash against payroll dates would change my life more than any report.",
    "New hires don't know the float exists until their first short Friday. Then they know, loudly.",
    "Overtime posts late, so Thursday's payroll is always a guess dressed as a number.",
    "The payroll provider debits a day early 'for processing'. That day costs me sleep and overdraft math.",
    "I keep a secret spreadsheet called 'Thursday'. My bank has no idea Thursday exists.",
    "Contractors versus employees, two rhythms, one account. The app shows a balance; I need a choreography.",
    "Holiday weeks compress everything and nobody warns you. Last Thanksgiving I learned by overdraft.",
    "If the app said 'this Thursday needs $4,100 you don't have yet', I'd kiss it. Professionally.",
    ],
    es: [
    "Mi gente depende de eso. La nómina no espera a que el cliente pague.",
    "Tres veces el trimestre pasado moví dinero a medianoche para la nómina. Eso no es banca, es parkour.",
    "La proveedora descuenta un día antes 'por proceso'. Ese día me cuesta sueño y matemáticas.",
    "Contratistas y empleados, dos ritmos, una cuenta. El saldo no me sirve; necesito coreografía.",
    "Si la app dijera 'este jueves faltan cuatro mil cien', la abrazaría. Profesionalmente.",
    ]},
  T6: { title: "Spanish statements translate words, not meaning",
    en: [
    "The Spanish version says 'cargo por sobregiro' where the English says 'overdraft protection transfer'. Those are not the same thing and my customers notice.",
    "Language consistency matters because one unclear word can trigger a phone call. We get forty such calls a week.",
    "My screen reader says the language attribute flips mid-sentence. It reads Spanish with English pronunciation. Try understanding that at speed.",
    "The fee schedule has eleven footnotes in English and four in Spanish. Guess which seven fees surprise people.",
    "Disclosure timing differs: English shows it pre-confirm, Spanish post-confirm. Same bank, different truth.",
    "Nobody tested this with a keyboard, did they. Tab order follows the English layout even on the Spanish page.",
    "My mother trusts the Spanish page more and understands it less. That combination should frighten a bank.",
    "Error messages are translated by someone who never saw the error. 'Inténtelo más tarde' for a locked account is not advice, it's abandonment.",
    "The glossary contradicts the statements on three terms I counted. I stopped counting after three.",
    "Bilingual staff improvise translations at the counter. Improvisation is not a localization strategy.",
    "Statements should carry both languages side by side for key terms. Redundancy here is clarity, not clutter.",
    "When the app updates, English ships first and Spanish 'follows'. It follows by months. Customers notice the lag before the words.",
    ],
    es: [
    "En hora pico, nadie lee la letra pequeña. Si la traducción confunde, la fila se detiene y todos pagan.",
    "At the window you see it all. They don't say 'pain point', they say — '¿por qué me cobraron dos veces?' — and I have no good answer.",
    "Le doy un ejemplo del viernes: un cliente firmó algo que no entendía porque la traducción sonaba oficial.",
    "La tabla de comisiones tiene once notas en inglés y cuatro en español. Adivine qué siete cargos sorprenden.",
    "Los mensajes de error los tradujo alguien que nunca vio el error. 'Inténtelo más tarde' no es ayuda, es abandono.",
    "El personal improvisa traducciones en ventanilla. Improvisar no es una estrategia de localización.",
    ]},
  T7: { title: "Branch handoff drops context at the counter",
    en: [
    "A customer starts online, finishes at my window, and I know nothing. They repeat everything, slower, angrier.",
    "For older customers, starting over isn't an inconvenience, it's a reason to leave the bank.",
    "I walk them through it, step by step, but I'm walking blind. Their online steps are invisible to me.",
    "The screen reader reads the whole table, every time. Imagine that, then imagine repeating it to a human who also can't see it.",
    "At the window you see it all: the apology, the repetition, the sigh when I ask for the account number they already typed.",
    "The queue display says six minutes. The repeat-story tax makes it eleven. Nobody measures the tax.",
    "Customers bring screenshots of their own accounts as proof of their own money. Let that sink in.",
    "Handoff notes exist but nobody writes them because the field is buried three tabs deep during a rush.",
    "The online flow collects the reason for visit, then drops it. I ask 'what brings you in' to someone who already answered.",
    "Privacy theater: I can't see their online steps 'for security', but I can see their balance. Explain that logic.",
    "After a bad handoff they don't blame the channel, they blame me, by name, in surveys.",
    "A simple 'customer already tried X' banner would save my mornings. It has never existed.",
    ],
    es: [
    "La fila no perdona. Cada historia repetida son tres minutos que no tenemos.",
    "El flujo en línea pregunta el motivo y luego lo pierde. Pregunto '¿en qué le ayudo?' a quien ya respondió.",
    "Los clientes traen capturas de sus propias cuentas como prueba de su propio dinero. Que eso cale.",
    "Las notas de traspaso existen pero nadie las escribe porque el campo está a tres clics en hora pico.",
    "Un aviso de 'el cliente ya intentó X' me salvaría las mañanas. Nunca ha existido.",
    ]},
  T8: { title: "Fraud alerts: ops wants more, owners feel spammed (PLANTED DIVERGENCE)",
    en: [
    "Ninety percent of these are noise. I cleared forty-three before lunch. Every false alarm teaches customers to ignore the real one.",
    "Per our incident review, alert coverage is a control gap. That is a finding, not feedback. We need more signals, not fewer.",
    "My phone buzzes at 2am for a twelve-dollar charge I made myself. I have started sleeping through the real ones too.",
    "Ha. Ask me in April. The winter fraud wave is real and the alerts saved us twice. Annoying and necessary.",
    "If an auditor asks, I want the alert log complete. If you ask me as a human, I want half of them gone.",
    "For licensing I need the fraud review documented. Nobody said it has to buzz.",
    "Severity levels are decoration: everything arrives as URGENT. When everything is urgent, triage is astrology.",
    "Let me snooze a merchant, not the channel. My grocery store is not a threat model.",
    "The alert never says what TO do, only what happened. Actionable would be a button, not a paragraph.",
    "Weekend alerts route to whoever is awake, which is whoever is newest. Experience sleeps through nothing, but gets no alerts.",
    "Digest mode exists, they told me, buried in settings I need a map to find. Discovery is part of the product.",
    "Two genuine frauds last year, both caught by customers calling us, not by alerts. Sit with that before adding more.",
    ],
    es: [
    "El noventa por ciento es ruido. Borré cuarenta y tres antes del almuerzo. Cada falsa alarma enseña a ignorar la real.",
    "Mi teléfono vibra a las 2am por un cargo de doce dólares que hice yo. Ya duermo hasta las reales.",
    "Los niveles son decoración: todo llega URGENTE. Cuando todo urge, priorizar es astrología.",
    "Déjeme pausar un comercio, no el canal. Mi supermercado no es un modelo de amenaza.",
    "Dos fraudes reales el año pasado, ambos los detectaron clientes llamando. Piénselo antes de agregar más.",
    ]},
  T9: { title: "Accountant collaboration runs on screenshots",
    en: [
    "Every month I export PDFs, screenshot the weird ones, and email my accountant a puzzle. She bills me to solve it.",
    "Technically that's a broken workflow. Shared access with scoped permissions would end the screenshot era.",
    "I tell every client this: give me view access and we both save three hours. Nobody does. They fear I'll see everything.",
    "Caregiver access has to say exactly what is shared — same for accountants. Granular scopes or nothing.",
    "I check it twice because once I sent the wrong month and paid for the hour it took to unsee it.",
    "The month-end email thread has fourteen messages and zero decisions. Decisions live in calls the software never sees.",
    "Comment threads on transactions would end this. Annotate the weird one where it lives, not in email exile.",
    "My accountant's portal login expired silently. I found out at 11pm on the 31st. Notifications are a feature.",
    "Permissions are all-or-nothing, so I choose nothing and pay in screenshots. The pricing page should say that.",
    "Version control for books: who changed what, when, with what note. Git for money. I'd pay double.",
    "She asked for 'the backup'. I sent a zip of inscrutable exports. We both pretended that was fine.",
    "Scoped access needs an expiry date or owners will never grant it. Trust with a timer.",
    ],
    es: [
    "Mis clientes me llaman cuando algo no cuadra, y la llamada siempre empieza con 'te mandé una captura'.",
    "El acceso compartido con permisos por alcance acabaría la era de las capturas. O granular o nada.",
    "El hilo de fin de mes tiene catorce mensajes y cero decisiones. Las decisiones viven en llamadas.",
    "El acceso con fecha de caducidad: los dueños lo darían si supieran que expira. Confianza con temporizador.",
    "Me pidió 'el respaldo'. Mandé un zip indescifrable. Ambos fingimos que estaba bien.",
    ]},
  T10: { title: "Mobile deposit limits surprise growing businesses",
    en: [
    "We outgrew the deposit limit on a good month and found out via a rejected check. Success, punished.",
    "Bottom line: tell me the limit before I need it, raise it when my history earns it, and never surprise me.",
    "In our old system, limits adapted quarterly. Here it's a wall I discover at speed.",
    "I measured this, actually: four rejected deposits last year, each costing a client conversation.",
    "My shortcut is depositing daily to stay under the cap. That's the tail wagging the business.",
    "The limit counts per check, per day, per month — three dials, one cryptic error. Show me the dials.",
    "A big catering weekend means Monday deposits spike. Predictable to everyone except the software.",
    "New accounts get training-wheels limits with no graduation date posted. When do I graduate? Silence.",
    "The rejection notice arrives after the client already paid. Now I explain the bank to my customer. Reversed roles.",
    "Branch deposits don't count against the same cap but nothing says so. I learned it from another owner, not the app.",
    "Raise requests go into a queue with no SLA. My money waits in a lobby with no chairs.",
    "Seasonal businesses should get seasonal limits. Winter me and summer me are different companies.",
    ],
    es: [
    "La fila no perdona, y el límite tampoco: un cheque rechazado son dos visitas.",
    "El límite cuenta por cheque, por día, por mes — tres relojes, un error críptico. Muéstreme los relojes.",
    "Un fin de semana bueno significa depósitos altos el lunes. Predecible para todos menos el software.",
    "La solicitud de aumento entra a una cola sin plazo. Mi dinero espera en un vestíbulo sin sillas.",
    "Los depósitos en sucursal no cuentan igual pero nada lo dice. Lo supe por otro dueño, no por la app.",
    ]},
};


function langQuote(theme, lang) {
  const bank = (theme && (theme[lang] || theme.en)) || [];
  return bank.length ? bank[Math.floor(rnd() * bank.length)] : "";
}
function enQuote(theme) {
  const bank = (theme && theme.en) || [];
  return bank.length ? bank[Math.floor(rnd() * bank.length)] : "";
}
/* Persona theme stances: which themes each persona speaks to (+/-/0) */
const STANCES = {
  P01: { T1: 1, T2: 1, T5: 1, T9: 1, T4: 1 }, P02: { T1: 1, T2: 0, T10: 1, T4: 1, T5: 0 },
  P03: { T3: 1, T5: 1, T9: 1, T10: 1, T4: 0 }, P04: { T2: 1, T5: 1, T6: 1, T10: 1 },
  P05: { T3: 1, T5: 1, T8: 0, T9: 1 }, P06: { T1: 0, T4: 1, T8: 1, T2: 1 },
  P07: { T2: 1, T4: -1, T9: 1, T3: 1 }, P08: { T4: -1, T9: 1, T1: 1, T6: 0 },
  P09: { T2: 1, T3: 1, T10: 0, T4: 0 }, P10: { T2: 1, T4: -1, T9: 1, T1: 0 },
  P11: { T6: 1, T7: 1, T1: 0 }, P12: { T6: 1, T7: 1, T10: 0 },
  P13: { T6: 1, T7: 1, T3: 0 }, P14: { T3: 1, T8: 1, T5: 0 },
  P15: { T8: -1, T5: 0, T1: 0 }, P16: { T6: 1, T7: 1, T2: 1 },
};

const INTERVIEWER_PROBES = [
  "Walk me through the last time that happened, step by step.",
  "What did you try first, and where did that break down?",
  "Who else feels this, and do they describe it the same way?",
  "If you had a magic wand for this workflow, what changes first?",
  "Tell me about a time it went surprisingly well — what was different?",
  "What does 'done' look like here, and how do you know?",
  "What have you stopped attempting because the tooling fought you?",
];

/* ── Builders ── */
const files = {};
const emit = (path, content) => { files[path] = content; };
const groundTruth = { theme_hits: {}, persona_themes: {}, contradictions: ["T4", "T8"], stale: [], multilingual_pairs: [] };

function recordHit(theme, docId) {
  groundTruth.theme_hits[theme] = groundTruth.theme_hits[theme] || [];
  groundTruth.theme_hits[theme].push(docId);
}

function buildInterview(persona, index) {
  const stances = STANCES[persona.id] || { T1: 1 };
  const themes = Object.keys(stances);
  const docId = `HB-IV-${String(index + 1).padStart(2, "0")}`;
  const date = `2026-${String(3 + (index % 3)).padStart(2, "0")}-${String(4 + ((index * 7) % 24)).padStart(2, "0")}`;
  const L = [];
  L.push(`# ${docId} — ${persona.lang === "es" ? "Entrevista" : "Interview"} ${index + 1}: ${persona.name}`);
  L.push(``);
  L.push(`> SYNTHETIC TEST FIXTURE — authored for the Istara testing suite. All people, businesses, and events are fictional.`);
  L.push(`> Method: semi-structured video interview, 55 minutes. Consent on file (synthetic form CO-${persona.id}).`);
  L.push(`> Participant: ${persona.name} — ${persona.role}, ${persona.business}, ${persona.region}. Language: ${persona.lang === "es" ? "Spanish" : "English"}.`);
  L.push(`> Interviewer: R. Alvarez, Harbor Ledger study. Recording ref: REC-${docId}.`);
  L.push(``);
  L.push(`## Opening`);
  L.push(`**Interviewer:** Thanks for making time, ${persona.name.split(" ")[0]}. Before we start — anything off-limits today, and may I record for note-taking?`);
  L.push(``);
  L.push(`**${persona.name}:** ${pick(persona.texture)} ${persona.lang === "es" ? "Puede grabar. Hablemos de lo que pasa de verdad, no de lo ideal." : "You can record. Let's talk about what actually happens, not the brochure version."}`);
  L.push(``);
  const nEx = 44 + Math.floor(rnd() * 8);
  const themeCycle = [];
  while (themeCycle.length < nEx) themeCycle.push(...pickN(themes, themes.length));
  for (let i = 0; i < nEx; i++) {
    const theme = themeCycle[i];
    const stance = stances[theme];
    const quote = langQuote(THEMES[theme], persona.lang);
    const probe = INTERVIEWER_PROBES[i % INTERVIEWER_PROBES.length];
    L.push(`## Exchange ${i + 1} — ${THEMES[theme].title}`);
    L.push(`**Interviewer:** ${probe}`);
    L.push(``);
    L.push(`**${persona.name}:** ${quote}`);
    if (stance === -1) L.push(`Honestly, I know reasonable people disagree — but I've paid for the other view, literally, in fees and fines.`);
    if (stance === 0) L.push(`It's mixed for me. Depends on the week, the client, whether Mercury is in retrograde — kidding. Mostly the client.`);
    L.push(``);
    L.push(`**Interviewer:** ${pick(["Say more about that.", "What makes you confident in that read?", "Who would push back on you here?", "Can you anchor that in a specific week or incident?"])}`);
    L.push(``);
    L.push(`**${persona.name}:** ${pick(persona.texture)} ${langQuote(THEMES[theme], persona.lang)}`);
    L.push(``);
    recordHit(theme, docId);
  }
  groundTruth.persona_themes[persona.id] = themes;
  L.push(`## Close`);
  L.push(`**Interviewer:** Last one — if the Northloop team builds exactly one thing from this conversation, what is it?`);
  L.push(``);
  L.push(`**${persona.name}:** ${pick(persona.texture)} ${langQuote(THEMES[themes[0]], persona.lang)}`);
  L.push(``);
  L.push(`---`);
  L.push(`Interviewer memo: ${persona.voice}. Follow up on ${THEMES[themes[1]].title.toLowerCase()} with a second session if budget allows.`);
  return { id: docId, path: `sources/interview/${docId}-${persona.id}.md`, content: L.join("\n") };
}

function buildSurvey() {
  const items = ["I1_overall_trust", "I2_invoice_ease", "I3_receipt_speed", "I4_approval_clarity", "I5_reconciliation_confidence", "I6_spanish_clarity", "I7_support_helpfulness", "I8_alert_usefulness"];
  const rows = ["respondent_id,role,region,language," + items.join(",")];
  const sums = Object.fromEntries(items.map((i) => [i, 0]));
  const N = 120;
  const means = {};
  for (let i = 0; i < N; i++) {
    const persona = PERSONAS[i % PERSONAS.length];
    const base = { owner: 3, accountant: 4, bookkeeper: 3, teller: 4, "branch-manager": 4, "ops-admin": 3 }[persona.role] ?? 3;
    const vals = items.map((it) => {
      let v = base + Math.floor(rnd() * 3) - 1;
      if (it === "I6_spanish_clarity" && persona.lang === "es") v -= 1;
      if (it === "I8_alert_usefulness" && ["owner", "ops-admin"].includes(persona.role)) v -= 1;
      if (it === "I5_reconciliation_confidence" && persona.role === "accountant") v -= 1;
      v = Math.max(1, Math.min(5, v));
      sums[it] += v;
      return v;
    });
    rows.push([`R${String(i + 1).padStart(3, "0")}`, persona.role, persona.region, persona.lang, ...vals].join(","));
  }
  for (const it of items) means[it] = Math.round((sums[it] / N) * 100) / 100;
  groundTruth.survey_means = means;
  groundTruth.survey_n = N;
  const analysis = [
    `# Harbor Ledger survey analysis (N=${N})`,
    ``,
    `> Computed by the generator from the response file — means below are ground truth, not estimates.`,
    ``,
    ...items.map((it) => `- ${it}: mean **${means[it]}**`),
    ``,
    `## Readout (for researchers, not for test oracles to hard-code without the manifest)`,
    `- Lowest item: I6 Spanish clarity — consistent with T6 wording-risk evidence in interviews.`,
    `- I8 alert usefulness splits by role (owners/ops lower) — see planted T8 divergence.`,
    `- I5 reconciliation confidence dips for accountants — see planted T4 divergence.`,
  ];
  return [
    { id: "HB-SV-01", path: "sources/survey/harbor-ledger-responses.csv", content: rows.join("\n") + "\n" },
    { id: "HB-SV-02", path: "sources/survey/harbor-ledger-analysis.md", content: analysis.join("\n") + "\n" },
  ];
}

function buildUsability() {
  const tasks = ["T-A: deposit a $4,200 check on mobile", "T-B: approve a $750 vendor payment with deputy", "T-C: find last quarter's payroll report in Spanish", "T-D: dispute a duplicate $86 charge with evidence attached"];
  const files = [];
  const susScores = {};
  const participants = ["P01", "P02", "P05", "P06", "P09", "P12", "P16", "P04"];
  participants.forEach((pid, i) => {
    const persona = PERSONAS.find((p) => p.id === pid);
    // SUS items 1..10 (1-5); odd items positive, even negative. Seeded per persona.
    const items = range(10).map((k) => {
      let v = 3 + Math.floor(rnd() * 3) - (persona.role === "owner" ? 0 : 1);
      if (pid === "P16") v -= 1; // accessibility barriers depress scores honestly
      return Math.max(1, Math.min(5, v));
    });
    let sus = 0;
    items.forEach((v, k) => { sus += k % 2 === 0 ? v - 1 : 5 - v; });
    sus = sus * 2.5;
    susScores[pid] = sus;
    const L = [];
    L.push(`# HB-UX-${String(i + 1).padStart(2, "0")} — Usability session: ${persona.name} (${persona.role})`);
    L.push(``);
    L.push(`> SYNTHETIC FIXTURE. Moderated remote session, 60 minutes. Consent CO-${pid}-UX.`);
    L.push(`> Participant setup: ${persona.business}, ${persona.region}. ${persona.lang === "es" ? "Session conducted in Spanish." : ""}`);
    L.push(``);
    tasks.forEach((t, ti) => {
      const success = rnd() > (pid === "P16" && ti === 2 ? 0.7 : 0.3);
      const secs = Math.round(90 + rnd() * 400 + (success ? 0 : 240));
      L.push(`## ${t}`);
      L.push(`- Outcome: **${success ? "success" : "fail"}** in ${secs}s, ${1 + Math.floor(rnd() * 3)} assists.`);
      L.push(`- Observation: ${pick(persona.texture)}`);
      L.push(`- Participant quote: "${langQuote(pick(Object.values(THEMES)), persona.lang)}"`);
      L.push(`- Friction tags: ${pickN(["unlabeled-control", "deep-navigation", "unclear-error", "timeout", "language-flip", "limit-surprise"], 2).join(", ")}.`);
      L.push(``);
      L.push(`Think-aloud excerpt: ${pick(persona.texture)} ${langQuote(pick(Object.values(THEMES)), persona.lang)} ${pick(persona.texture)}`);
      L.push(``);
    });
    L.push(`## SUS responses (raw, 1-5): ${items.join(", ")} → SUS **${sus}**`);
    L.push(`## UMUX-Lite: usefulness ${1 + Math.floor(rnd() * 7)}/7, ease ${1 + Math.floor(rnd() * 7)}/7.`);
    L.push(`## Debrief`);
    L.push(`${pick(persona.texture)} ${langQuote(pick(Object.values(THEMES)), persona.lang)}`);
    L.push(``);
    files.push({ id: `HB-UX-${String(i + 1).padStart(2, "0")}`, path: `sources/usability/hb-ux-${String(i + 1).padStart(2, "0")}-${pid.toLowerCase()}.md`, content: L.join("\n") });
  });
  groundTruth.sus_scores = susScores;
  return files;
}

function buildSupport() {
  const topics = [...Object.values(THEMES)];
  const files = [];
  for (let i = 0; i < 30; i++) {
    const persona = PERSONAS[i % PERSONAS.length];
    const theme = topics[i % topics.length];
    const sev = pick(["S3-low", "S3-low", "S2-normal", "S2-normal", "S1-high"]);
    const L = [];
    L.push(`# Ticket SUP-${String(1041 + i)} — ${theme.title} [${sev}]`);
    L.push(`- Reporter: ${persona.name} (${persona.role}, ${persona.business}) · ${persona.region} · Channel: ${pick(["in-app", "phone", "email", "branch"])}`);
    L.push(`- Date: 2026-0${3 + (i % 3)}-${String(2 + ((i * 5) % 26)).padStart(2, "0")} · Language: ${persona.lang}`);
    L.push(``);
    L.push(`## Customer words`);
    L.push(`${pick(persona.texture)} ${langQuote(theme, persona.lang)}`);
    L.push(``);
    L.push(`## More context`);
    L.push(`${langQuote(theme, persona.lang)} ${pick(persona.texture)}`);
    L.push(``);
    L.push(`## Agent note`);
    L.push(`Linked theme candidate: ${theme.title}. ${sev === "S1-high" ? "Escalated to research ops for pattern watch." : "Resolved with workaround; pattern logged."}`);
    files.push({ id: `HB-SUP-${i + 1}`, path: `sources/support/sup-${1041 + i}.md`, content: L.join("\n") });
    recordHit(Object.keys(THEMES).find((k) => THEMES[k] === theme), `HB-SUP-${i + 1}`);
  }
  return files;
}

function buildAnalytics() {
  const weeks = range(8).map((w) => `2026-W${String(14 + w).padStart(2, "0")}`);
  const rows = ["week,logins,deposits_started,deposits_completed,invoice_reminders_sent,payments_matched_auto,payroll_runs,support_tickets"];
  weeks.forEach((w, i) => {
    const growth = 1 + i * 0.04;
    rows.push([w, Math.round(4100 * growth + rnd() * 200), Math.round(900 * growth), Math.round(700 * growth - (i === 5 ? 120 : 0)), Math.round(2600 * growth), `${Math.round(78 + rnd() * 8)}%`, Math.round(310 * growth), Math.round(140 - i * 6 + rnd() * 20)].join(","));
  });
  const dict = [
    `# Analytics data dictionary + reader notes`, ``,
    `- Grain: one row per ISO week. Population: Harbor Ledger pilot cohort (412 small businesses).`,
    `- deposits_completed dips in 2026-W19: mobile deposit limit incidents (see T10), NOT a tracking bug. Treated as stale-after-fix from W20 on.`,
    `- payments_matched_auto is a percent string in this export (source quirk) — parse before averaging.`,
    `- support_tickets declines as in-app guidance shipped (W16); do not read as satisfaction without the survey.`,
  ];
  groundTruth.stale.push({ doc: "HB-AN-01", note: "W19 deposit dip explained by T10 limit incidents; pre-fix weeks are stale for limit analysis." });
  return [
    { id: "HB-AN-01", path: "sources/analytics/weekly-funnel-8w.csv", content: rows.join("\n") + "\n" },
    { id: "HB-AN-02", path: "sources/analytics/data-dictionary.md", content: dict.join("\n") + "\n" },
  ];
}

function buildCompetitor() {
  const rivals = [
    { name: "BlueAcorn Business", angle: "auto-categorization with accountant override queues", verdict: "strongest reconciliation UX; weakest Spanish coverage; deposit limits unpublished" },
    { name: "Foundry & Co", angle: "branch-first onboarding with video verification", verdict: "best handoff continuity; slowest approval chains; alert granularity praised by ops personas" },
    { name: "Ledgerline", angle: "API-first invoicing with client payment links", verdict: "fastest receivables flow; no payroll view; receipt capture is web-only" },
  ];
  return rivals.map((r, i) => {
    const L = [];
    L.push(`# HB-COMP-0${i + 1} — Competitor benchmark: ${r.name}`);
    L.push(``);
    L.push(`> SYNTHETIC FIXTURE. Assembled from public marketing pages + scripted trial walkthroughs (no credentials, no scraping). Evaluated against the same 10-task Harbor protocol as our usability sessions.`);
    L.push(``);
    L.push(`## Positioning angle: ${r.angle}.`);
    L.push(``);
    for (let s = 0; s < 12; s++) {
      const theme = Object.values(THEMES)[(i * 3 + s) % 10];
      L.push(`### Task ${s + 1} vs theme: ${theme.title}`);
      L.push(`${enQuote(theme)}`);
      L.push(``);
      L.push(`Rival behavior: ${pick(["completes cleanly in under two minutes", "requires three more steps than Harbor", "fails the Spanish variant", "passes but hides the limit until submit", "matches Harbor exactly — parity, not advantage"])}.`);
      L.push(``);
    }
    L.push(`## Verdict: ${r.verdict}.`);
    L.push(`## Implication for Harbor: ${enQuote(pick(Object.values(THEMES)))}`);
    return { id: `HB-COMP-0${i + 1}`, path: `sources/competitor/hb-comp-0${i + 1}.md`, content: L.join("\n") };
  });
}

function buildJourneys() {
  const mk = (id, title, personaIds, stages) => {
    const L = [`# ${id} — ${title}`, ``, `> SYNTHETIC FIXTURE. Built from interviews ${personaIds.join(", ")} + usability sessions + support tickets.`];
    stages.forEach(([stage, doing, thinking, pain, opp]) => {
      L.push(``);
      L.push(`## Stage: ${stage}`);
      L.push(`- Doing: ${doing}`);
      L.push(`- Thinking: ${thinking}`);
      L.push(`- Pain (with sources): ${pain}`);
      L.push(`- Opportunity: ${opp}`);
      L.push(`- Evidence: ${personaIds.map((p) => `${p} interview`).join("; ")}.`);
    });
    return { id, path: `sources/journey/${id.toLowerCase()}.md`, content: L.join("\n") };
  };
  return [
    mk("HB-JR-01", "Journey: chasing a late invoice", ["P01", "P02", "P05"], [
      ["Notice", "owner opens aging list Monday 7am", "\"who owes me, really?\"", "deposits under different names (P01 Tue example)", "normalize payer display names"],
      ["Nudge", "owner sends reminder from personal email", "\"will this sound desperate?\"", "no in-app nudge; tone anxiety", "templated nudges with tone control"],
      ["Follow-up", "second reminder + phone call", "\"am I harassing them?\"", "no escalation ladder", "staged escalation with pauses"],
      ["Resolution", "payment arrives Friday, mismatched reference", "\"which invoice was that?\"", "manual matching", "smart match suggestions with undo"],
      ["Learning", "owner updates spreadsheet ritual", "\"next month will differ\"", "no closed loop", "receivables retrospectives"],
    ]),
    mk("HB-JR-02", "Journey: month-end close with an external accountant", ["P07", "P08", "P09"], [
      ["Gather", "bookkeeper batches receipts Friday", "\"did I miss the van ones?\"", "point-of-sale capture loss (T2)", "one-tap capture with blur detection"],
      ["Review", "accountant flags auto-matches", "\"is this a match or a guess?\"", "T4 divergence: post-then-review buries errors", "review-then-post as default with override log"],
      ["Adjust", "journal entries with explanations", "\"will the auditor follow this?\"", "explanations live in email", "entry-level rationale fields"],
      ["Close", "lock the month, notify owner", "\"are we actually closed?\"", "soft-close ambiguity", "explicit close ceremony with checklist"],
      ["Report", "owner reads P&L without footnotes", "\"what changed vs last month?\"", "variance unexplained", "auto variance narratives with spans"],
    ]),
  ];
}

function buildPlanAndGuides() {
  const plan = [
    `# Harbor Ledger research plan (synthetic program plan)`, ``,
    `## Objectives (300-line detail across sections below)`,
  ];
  const sections = [
    ["Objectives", ["Decide which receivables automation ships without human review (T1).", "Set receipt-capture quality bars at point of sale (T2).", "Redesign approval chains with deputy coverage (T3).", "Resolve the auto-match trust split between owners and accountants (T4, low-consensus by design).", "Align payroll timing views with cash reality (T5).", "Fix Spanish statement meaning, not just words (T6).", "Design branch handoff with carried context (T7).", "Right-size fraud alerts by role (T8, low-consensus by design).", "Ship scoped accountant collaboration (T9).", "Make deposit limits adaptive and visible (T10)."]],
    ["Method", ["16 semi-structured interviews (this corpus), 120-response survey, 8 moderated usability sessions with SUS/UMUX, 30 support tickets, 8-week analytics, 3 competitor benchmarks, 2 journey maps.", "Sampling: stratified by role (owner/accountant/bookkeeper/staff/ops) and language (EN/ES).", "Saturation rule: stop recruiting a stratum after 3 consecutive interviews add no new codes."]],
    ["Instruments", ["Interview guide v3 (see guides/).", "Survey: 8 Likert items (trust, invoice ease, receipt speed, approval clarity, reconciliation confidence, Spanish clarity, support helpfulness, alert usefulness).", "Usability protocol: 4 tasks + SUS + UMUX-Lite + debrief."]],
    ["Analysis plan", ["Open coding by two independent coders, codebook v1 (see codebook/).", "Reliability: agreement computed per theme; T4/T8 expected low — reconcile, don't average.", "Grounding: every finding links source spans; stale W19 analytics flagged, not averaged away."]],
    ["Risks", ["Small-business seasonality (Dahl marine winter).", "Spanish parenting: translate meaning with bilingual review.", "Alert-fatigue bias in ops interviews.", "Screen-reader coverage via P16 throughout."]],
    ["Timeline", ["W14-16 interviews+survey.", "W17 usability.", "W18 coding+reliability.", "W19 reconciliation.", "W20 reporting (human approval gates)."]],
  ];
  sections.forEach(([h, bullets]) => {
    plan.push(``, `## ${h}`);
    bullets.forEach((b) => { plan.push(`- ${b}`); plan.push(`  Elaboration: ${b} This matters because the decision it informs is irreversible within the quarter: automation shipped without review cannot be unshipped from customer trust. The counter-consideration is speed — every review gate costs owner mornings. The study must price both sides with evidence, not opinion.`); });
  });
  const guide = (id, title, audience) => {
    const L = [`# ${id} — ${title}`, ``, `Audience: ${audience}. Time: 55 minutes. Record with consent.`];
    for (let i = 0; i < 18; i++) {
      const theme = Object.values(THEMES)[i % 10];
      L.push(``, `### Q${i + 1} (${theme.title})`);
      L.push(`Ask: ${pick(INTERVIEWER_PROBES)}`);
      L.push(`Listen for: ${enQuote(theme).slice(0, 90)}...`);
      L.push(`Probe deeper when: participant mentions money movement, waiting, repetition, or language.`);
      L.push(`Do not: suggest features, correct terminology mid-answer, or promise timelines.`);
    }
    return { id, path: `sources/guide/${id.toLowerCase()}.md`, content: L.join("\n") };
  };
  return [
    { id: "HB-PL-01", path: "sources/plan/harbor-ledger-research-plan.md", content: plan.join("\n") },
    guide("HB-GD-01", "Discussion guide: owners", "owners P01-P06, P16"),
    guide("HB-GD-02", "Discussion guide: accountants and bookkeepers", "P07-P10"),
    guide("HB-GD-03", "Discussion guide: staff and ops", "P11-P15"),
  ];
}

function buildCodebook() {
  const L = [`# Harbor Ledger codebook v1 (METHOD ARTIFACT — governs coding, not a finding)`, ``];
  Object.entries(THEMES).forEach(([tid, theme]) => {
    L.push(`## ${tid} — ${theme.title}`);
    L.push(`- Definition: utterances about ${theme.title.toLowerCase()} in the participant's own workflow.`);
    L.push(`- Include: first-person incidents, workarounds, quantified losses, role-specific variants.`);
    L.push(`- Exclude: generic praise/complaint with no incident; interviewer speech.`);
    L.push(`- Example: "${enQuote(theme).slice(0, 110)}..."`);
    L.push(`- Expected agreement: ${["T4", "T8"].includes(tid) ? "LOW by design (owner/accountant and ops/owner splits) — reconcile in session, never average." : "moderate-high; double-code ES transcripts with bilingual reviewer."}`);
    L.push(``);
  });
  return [{ id: "HB-CB-01", path: "method/codebook-v1.md", content: L.join("\n") }];
}

function buildContext() {
  const ctxPack = (id, title, bodyParas) => {
    const L = [`# ${id} — ${title}`, ``, `> SYNTHETIC program context for Harbor Ledger. Hundreds of lines by design: scenarios fill UI context fields from these files.`];
    bodyParas.forEach((p) => { L.push(``, p); });
    return { id, path: `context/${id.toLowerCase()}.md`, content: L.join("\n") };
  };
  const paras = (seed, n, bank) => range(n).map((i) => `${seed} (para ${i + 1}/${n}). ${bank[(seed.length + i) % bank.length]}`);
  const productBank = Object.values(THEMES).flatMap((t) => t.en);
  const files = [];
  files.push(ctxPack("HB-CX-01", "Project context: Harbor Ledger small-business banking redesign", [
    `Northloop Bank serves 41,000 small businesses across 6 states. The Harbor Ledger program redesigns the business banking app for owners, accountants, bookkeepers, tellers, branch managers, and operations staff, in English and Spanish, across mobile, web, and branch counter.`,
    ...paras("Business background", 90, productBank),
    `Stage: discovery synthesis complete (this corpus); delivery decisions pending human approval. Success = measurable drops in receivables chase time, receipt loss, approval latency, reconciliation rework, payroll-float scrambles, Spanish support calls, handoff repeats, false-alarm fatigue, screenshot accounting, and deposit-limit surprises.`,
    ...paras("Success criteria", 70, productBank),
    `Constraints: no core-banking replacement; accessibility WCAG 2.2 AA throughout; Spanish parity is a launch gate, not fast-follow; every automation ships with an undo path and an audit trail.`,
    ...paras("Constraints", 70, productBank),
  ]));
  files.push(ctxPack("HB-CX-02", "Research guardrails", [
    `Never invent medical, legal, or tax advice. Never expose participant identities beyond synthetic labels. Keep owner/accountant/staff/ops evidence separated until synthesis compares them explicitly.`,
    ...paras("Guardrail detail", 100, productBank),
    `Contradictions (T4 auto-match trust, T8 alert volume) are expected and must be reconciled in session with both sides present in evidence — never averaged, never smoothed.`,
    ...paras("Reconciliation rule", 70, productBank),
    `Stale data (W19 analytics) is flagged with its superseding note and excluded from limit analysis. Multilingual pairs (P04/P08/P13 ES) require bilingual review before coding.`,
    ...paras("Data hygiene", 70, productBank),
  ]));
  const personaParas = [];
  PERSONAS.forEach((p) => {
    personaParas.push(`### ${p.id} ${p.name} — ${p.role}, ${p.business} (${p.region}, ${p.lang}). Voice: ${p.voice}. Says things like: "${p.texture[0]}" Themes: ${(STANCES[p.id] ? Object.keys(STANCES[p.id]).join(", ") : "T1")}.`);
    personaParas.push(`Working context: ${pick(productBank)} Day-to-day reality: ${pick(productBank)} What good looks like for ${p.name.split(" ")[0]}: ${pick(productBank)}`);
    personaParas.push(`A week in the life: ${pick(productBank)} ${pick(productBank)} Tool stack: ${pick(productBank)}`);
    personaParas.push(`Known friction (do not lead with this in interviews): ${pick(productBank)} Counterpoint this persona would accept: ${pick(productBank)}`);
  });
  files.push(ctxPack("HB-CX-03", "Personas (16, synthetic, with theme stances)", [...personaParas, ...paras("Persona usage", 60, productBank)]));
  files.push(ctxPack("HB-CX-04", "Research objectives and decisions pending", [
    `Ten decisions map 1:1 to themes T1..T10; each needs an evidence bar (who, how many, agreement, grounding) before it becomes a recommendation, and human approval before it becomes a report.`,
    ...paras("Decision D (per theme)", 120, productBank),
    `Non-goals this quarter: consumer banking, lending underwriting, international wires. Explicitly out so scope debates end with a pointer, not a meeting.`,
    ...paras("Non-goal rationale", 60, productBank),
  ]));
  return files;
}

function buildChatPacks() {
  // Labeled synthetic METHOD exemplars: long researcher↔agent threads with
  // steering, for exercising chat/steering scenarios — never findings.
  const packs = [];
  const threadSpecs = [
    ["HB-CH-01", "receivables deep-dive", "T1", 44],
    ["HB-CH-02", "auto-match trust debate", "T4", 52],
    ["HB-CH-03", "Spanish clarity remediation", "T6", 38],
  ];
  const steers = ["narrow to owners only", "compare against the survey means", "show me the contradicting spans", "exclude stale W19 weeks", "re-run with bilingual review noted", "steer: what would change P07's mind?", "pause: define done for this thread", "continue with accountant voices only"];
  threadSpecs.forEach(([id, title, theme, turns]) => {
    const L = [`# ${id} — exemplar thread: ${title} (${turns} turns)`, ``, `> SYNTHETIC METHOD EXEMPLAR for chat/steering tests. Not evidence, not findings.`];
    for (let i = 0; i < turns; i++) {
      if (i % 6 === 5) {
        L.push(``, `**Researcher (steer):** ${steers[(i + turns) % steers.length]}.`);
        L.push(``, `**Agent:** Steering acknowledged — ${enQuote(THEMES[theme])}`);
      } else if (i % 2 === 0) {
        L.push(``, `**Researcher:** ${pick(INTERVIEWER_PROBES)} (re: ${THEMES[theme].title})`);
        L.push(``, `**Agent:** ${enQuote(THEMES[theme])} ${enQuote(THEMES[theme])}`);
      } else {
        L.push(``, `**Agent:** Grounding check — spanning ${(i % 4) + 2} sources: ${enQuote(THEMES[theme])}`);
        L.push(``, `**Researcher:** Continue. Cite spans.`);
      }
    }
    packs.push({ id, path: `chat-packs/${id.toLowerCase()}.md`, content: L.join("\n") });
  });
  groundTruth.chat_packs = threadSpecs.map(([id, title, theme, turns]) => ({ id, title, theme, turns }));
  return packs;
}

/* ── Main ── */
function sha(text) { return createHash("sha256").update(text).digest("hex").slice(0, 16); }

function main() {
  mkdirSync(OUT, { recursive: true });
  let all = [];
  PERSONAS.forEach((p, i) => all.push(buildInterview(p, i)));
  all = all.concat(buildSurvey(), buildUsability(), buildSupport(), buildAnalytics(), buildCompetitor(), buildJourneys(), buildPlanAndGuides(), buildCodebook(), buildContext(), buildChatPacks());
  const manifest = {
    generator: "tests/document_corpus/generate-rich-corpus.mjs",
    generator_version: GENERATOR_VERSION,
    seed: SEED,
    domain: "Harbor Ledger — Northloop small-business banking redesign (fully synthetic)",
    provenance: "Authored fixtures. Method shaped by public sources (18F methods, GOV.UK research patterns, SUS/UMUX instruments); all people, quotes, and numbers are generated. No real participant data.",
    total_sources: all.length,
    ground_truth: groundTruth,
    slices: {
      "interview-heavy": all.filter((f) => f.path.startsWith("sources/interview")).map((f) => f.id),
      "survey-heavy": all.filter((f) => f.path.startsWith("sources/survey")).map((f) => f.id),
      "usability-heavy": all.filter((f) => f.path.startsWith("sources/usability")).map((f) => f.id),
      "full-end-to-end": all.filter((f) => f.path.startsWith("sources/")).map((f) => f.id),
      "coding-reliability": all.filter((f) => f.path.startsWith("sources/interview")).map((f) => f.id),
      "context-pack": all.filter((f) => f.path.startsWith("context/")).map((f) => f.id),
      "chat-packs": all.filter((f) => f.path.startsWith("chat-packs/")).map((f) => f.id),
    },
    files: all.map((f) => ({ id: f.id, path: f.path, lines: f.content.split("\n").length, sha: sha(f.content) })),
  };
  all.forEach((f) => {
    const full = join(OUT, f.path);
    mkdirSync(dirname(full), { recursive: true });
    writeFileSync(full, f.content);
  });
  writeFileSync(join(OUT, "manifest.json"), JSON.stringify(manifest, null, 1));
  const totalLines = all.reduce((n, f) => n + f.content.split("\n").length, 0);
  console.log(`rich corpus: ${all.length} files, ${totalLines} lines -> ${OUT}`);
}

main();
