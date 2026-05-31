import React, { useState, useEffect } from "react";

/* ──────────────────────────────────────────────────────────────────────────
   ANTAR · COMPAT  (compatibility · two-chart alignment)
   --------------------------------------------------------------------------
   Flow screen, not a destination board. Steps:
     1) Pick the connection type (Romantic / Business / Co-founder / Friend / Family)
     2) Pick / add the other chart
     3) See the verdict — score + headline + the layers where you meet vs. pull apart

   Visual centerpiece: the two-circle alignment diagram (the user + the other,
   overlap = where you meet). Calm, two-color, same as the rest.

   Layers (from the existing engine, plain-language):
     SOUL · CHEMISTRY · PUBLIC · LIFE PATH · COMMUNICATION · FRICTION
   Each shows passed/strained + a one-line read. Tap any → full detail.
   ────────────────────────────────────────────────────────────────────────── */

const T = {
  bg: "#060608", card: "#0C0C10", cardUp: "#101016", sheet: "#0C0C12",
  line: "rgba(255,255,255,0.05)", lineUp: "rgba(255,255,255,0.10)",
  teal: "#00D9B8", amber: "#E0A23B", red: "#EF4444",
  t1: "#F2F4F7", t2: "#9BA3AF", t3: "#5A626E", t4: "#363C45",
  mono: "'JetBrains Mono','SF Mono',monospace",
  sans: "'Inter',-apple-system,sans-serif",
};

/* ── DATA ──────────────────────────────────────────────────────────────── */
const RELATIONSHIP_TYPES = [
  { id: "romantic",   label: "Romantic Partner",    sub: "Emotional connection, attraction, long-term potential", icon: "♥" },
  { id: "business",   label: "Business Partner",    sub: "Work style, trust, financial alignment", icon: "◆" },
  { id: "cofounder",  label: "Co-Founder",          sub: "Personality fit, pressure handling, shared vision", icon: "△" },
  { id: "friend",     label: "Friend / Social",     sub: "Energy match, communication, mutual growth", icon: "◉" },
  { id: "family",     label: "Family",              sub: "Parents, children, siblings, family dynamics", icon: "⌂" },
  { id: "employee",   label: "Employee",            sub: "Role fit, work ethic, reliability — you evaluating a hire", icon: "▣", roles: true },
];

/* role sub-selector — only shown when reason === "employee" */
const EMPLOYEE_ROLES = [
  { id: "sales",            label: "Sales" },
  { id: "marketing",        label: "Marketing" },
  { id: "product",          label: "Product" },
  { id: "leadership",       label: "Leadership" },
  { id: "operations",       label: "Operations" },
  { id: "engineering",      label: "Engineering" },
  { id: "customer_support", label: "Customer Support" },
];

const SAVED_CHARTS = [
  { id: "andres",   name: "Andres",   initial: "A", relationship: "cofounder", born: "Cancer lagna · Colombia" },
  { id: "harleen",  name: "Harleen",  initial: "H", relationship: "business",  born: "Operating partner" },
];

/* mock verdict for Andres × cofounder */
const VERDICT = {
  score: 78, label: "Strong fit",
  headline: "A high-trust co-founder match — your edges complement.",
  detail: "You bring the engine and the urgency; they bring the steadying hand and emotional intelligence. The combination is naturally complementary for building.",
  layers: [
    { key: "soul",     name: "Soul Alignment",   passed: true,  badge: "Mutual Lock",     line: "Your deepest drives mutually see each other — a karmic resonance you can feel." },
    { key: "chem",     name: "Working Chemistry",passed: true,  badge: "Strong",           line: "Day-to-day collaboration flows. You finish each other's sentences in meetings." },
    { key: "public",   name: "Public Image",     passed: true,  badge: "Power Pair",       line: "The world reads you as a credible duo. Your visible styles amplify each other." },
    { key: "path",     name: "Life Path",        passed: true,  badge: "Aligned",          line: "Your dasha periods are running in the same direction for the next several years." },
    { key: "comm",     name: "Communication",    passed: false, badge: "Asymmetric",       line: "You move faster than they do. Hold space for processing or it strains." },
    { key: "friction", name: "Friction Points",  passed: false, badge: "Watch this",       line: "When stress hits, you push; they withdraw. Name the pattern early." },
  ],
};

const Mono = ({ children, size = 8, color = T.t3, weight = 600, ls = "0.16em", style = {} }) => (
  <span style={{ fontSize: size, fontWeight: weight, letterSpacing: ls, color, fontFamily: T.mono, ...style }}>{children}</span>
);

/* ── ALIGNMENT DIAGRAM · two overlapping circles (Venn) ────────────────── */
const AlignmentDiagram = ({ score, leftInitial = "R", rightInitial = "A" }) => {
  // overlap width grows with score 0..100
  const overlap = 30 + (score / 100) * 50;
  return (
    <div style={{ position: "relative", width: "100%", display: "flex", justifyContent: "center", padding: "8px 0 12px" }}>
      <svg viewBox="0 0 360 200" width="100%" style={{ maxWidth: 360 }} xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="leftG" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={T.teal} stopOpacity="0.18" />
            <stop offset="70%" stopColor={T.teal} stopOpacity="0.04" />
            <stop offset="100%" stopColor={T.teal} stopOpacity="0" />
          </radialGradient>
          <radialGradient id="rightG" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={T.teal} stopOpacity="0.18" />
            <stop offset="70%" stopColor={T.teal} stopOpacity="0.04" />
            <stop offset="100%" stopColor={T.teal} stopOpacity="0" />
          </radialGradient>
        </defs>
        {/* left circle */}
        <circle cx={180 - overlap/2} cy="100" r="70" fill="url(#leftG)" stroke={T.teal} strokeWidth="1" strokeOpacity="0.7" />
        {/* right circle */}
        <circle cx={180 + overlap/2} cy="100" r="70" fill="url(#rightG)" stroke={T.teal} strokeWidth="1" strokeOpacity="0.7" />
        {/* initials */}
        <text x={180 - overlap/2 - 38} y="106" textAnchor="middle"
          fontFamily="'JetBrains Mono',monospace" fontSize="22" fontWeight="700" fill={T.t1}>{leftInitial}</text>
        <text x={180 + overlap/2 + 38} y="106" textAnchor="middle"
          fontFamily="'JetBrains Mono',monospace" fontSize="22" fontWeight="700" fill={T.t1}>{rightInitial}</text>
        {/* score in overlap */}
        <text x="180" y="98" textAnchor="middle"
          fontFamily="'JetBrains Mono',monospace" fontSize="28" fontWeight="800" fill={T.teal}
          style={{ filter: `drop-shadow(0 0 8px ${T.teal}80)` }}>{score}</text>
        <text x="180" y="118" textAnchor="middle"
          fontFamily="'JetBrains Mono',monospace" fontSize="8" fontWeight="600" fill={T.t3} letterSpacing="0.14em">ALIGNMENT</text>
      </svg>
    </div>
  );
};

/* ── HEADER / SHEET / NAV ──────────────────────────────────────────────── */
const Header = ({ onBack, title }) => (
  <div style={{ padding: "14px 18px 12px", background: T.bg, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      {onBack && (
        <button onClick={onBack} style={{ width: 30, height: 30, borderRadius: "50%", background: T.card, border: `1px solid ${T.lineUp}`,
          color: T.t2, cursor: "pointer", fontSize: 14 }}>‹</button>
      )}
      <div style={{ fontSize: 16, fontWeight: 800, color: T.t1, letterSpacing: "-0.02em" }}>ANTAR</div>
    </div>
    <button style={{ width: 30, height: 30, borderRadius: "50%", background: T.card, border: `1px solid ${T.lineUp}`,
      color: T.t1, fontFamily: T.mono, fontSize: 11, fontWeight: 700, cursor: "pointer" }}>R</button>
  </div>
);

const Sheet = ({ open, onClose, children }) => {
  useEffect(() => { document.body.style.overflow = open ? "hidden" : ""; return () => { document.body.style.overflow = ""; }; }, [open]);
  return (
    <>
      <div onClick={onClose} style={{ position: "absolute", inset: 0,
        background: open ? "rgba(0,0,0,0.6)" : "transparent", backdropFilter: open ? "blur(4px)" : "none",
        pointerEvents: open ? "auto" : "none", transition: "all 0.28s", zIndex: 30 }} />
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, maxHeight: "84vh",
        background: T.sheet, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderTop: `1px solid ${T.lineUp}`,
        boxShadow: "0 -16px 48px rgba(0,0,0,0.5)", transform: open ? "translateY(0)" : "translateY(100%)",
        transition: "transform 0.32s cubic-bezier(0.32,0.72,0,1)", zIndex: 31, display: "flex", flexDirection: "column" }}>
        <div onClick={onClose} style={{ padding: "12px 0 8px", cursor: "pointer" }}>
          <div style={{ width: 36, height: 4, borderRadius: 2, background: T.t4, margin: "0 auto" }} />
        </div>
        <div style={{ overflowY: "auto", padding: "8px 20px 30px", flex: 1, scrollbarWidth: "none" }}>{children}</div>
      </div>
    </>
  );
};

const BottomNav = ({ active, onChange }) => {
  const tabs = [
    { id: "home", label: "TODAY", icon: "◎" }, { id: "ask", label: "ASK", icon: "✦" },
    { id: "places", label: "PLACES", icon: "◬" }, { id: "balance", label: "BALANCE", icon: "◯" },
    { id: "compat", label: "COMPAT", icon: "◈" },
  ];
  return (
    <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, display: "flex",
      background: `${T.bg}F5`, backdropFilter: "blur(12px)", borderTop: `1px solid ${T.line}`, padding: "5px 0 14px", zIndex: 25 }}>
      {tabs.map(t => (
        <button key={t.id} onClick={() => onChange(t.id)} style={{ flex: 1, border: "none", background: "none",
          cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 3, padding: "5px 0" }}>
          <span style={{ fontSize: 15, color: active === t.id ? T.teal : T.t4, filter: active === t.id ? `drop-shadow(0 0 4px ${T.teal}50)` : "none" }}>{t.icon}</span>
          <Mono size={7} color={active === t.id ? T.teal : T.t4} ls="0.1em">{t.label}</Mono>
        </button>
      ))}
    </div>
  );
};

/* ── STEP 1 · PICK RELATIONSHIP TYPE ───────────────────────────────────── */
const StepRelationship = ({ onPick }) => (
  <div style={{ padding: "8px 16px 24px" }}>
    <Mono size={8} color={T.teal} style={{ display: "block", marginBottom: 14 }}>COMPATIBILITY · NEW</Mono>
    <div style={{ fontSize: 22, fontWeight: 700, color: T.t1, letterSpacing: "-0.02em", marginBottom: 8 }}>
      What kind of connection is this?
    </div>
    <div style={{ fontSize: 13, color: T.t2, lineHeight: 1.5, marginBottom: 18 }}>
      Different relationships read different layers of the chart. Choose the closest fit.
    </div>
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {RELATIONSHIP_TYPES.map(r => (
        <button key={r.id} onClick={() => onPick(r.id)} style={{ width: "100%", textAlign: "left", cursor: "pointer",
          padding: "14px 16px", background: T.card, border: `1px solid ${T.line}`, borderRadius: 11,
          display: "flex", alignItems: "center", gap: 14 }}>
          <span style={{ fontSize: 18, color: T.teal, width: 24, textAlign: "center" }}>{r.icon}</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 600, color: T.t1 }}>{r.label}</div>
            <div style={{ fontSize: 12, color: T.t2, marginTop: 3, lineHeight: 1.4 }}>{r.sub}</div>
          </div>
          <span style={{ color: T.t4, fontSize: 14 }}>›</span>
        </button>
      ))}
    </div>
  </div>
);

/* ── STEP 2 · PICK / ADD THE OTHER CHART ───────────────────────────────── */
const StepChart = ({ relationship, onPick, onAdd }) => {
  const r = RELATIONSHIP_TYPES.find(x => x.id === relationship);
  return (
    <div style={{ padding: "8px 16px 24px" }}>
      <Mono size={8} color={T.teal} style={{ display: "block", marginBottom: 10 }}>
        STEP 2 · {r.label.toUpperCase()}
      </Mono>
      <div style={{ fontSize: 21, fontWeight: 700, color: T.t1, letterSpacing: "-0.02em", marginBottom: 16 }}>
        Choose a chart, or add one.
      </div>

      {SAVED_CHARTS.length > 0 && (
        <>
          <Mono size={7} color={T.t3} style={{ display: "block", marginBottom: 10 }}>SAVED CHARTS</Mono>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 18 }}>
            {SAVED_CHARTS.map(c => (
              <button key={c.id} onClick={() => onPick(c.id)} style={{ width: "100%", textAlign: "left", cursor: "pointer",
                padding: "12px 14px", background: T.card, border: `1px solid ${T.line}`, borderRadius: 10,
                display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 36, height: 36, borderRadius: "50%", background: T.cardUp,
                  border: `1px solid ${T.lineUp}`, display: "flex", alignItems: "center", justifyContent: "center",
                  color: T.t1, fontFamily: T.mono, fontSize: 14, fontWeight: 700 }}>{c.initial}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: T.t1 }}>{c.name}</div>
                  <Mono size={8} color={T.t3} weight={500} ls="0.04em" style={{ display: "block", marginTop: 2 }}>{c.born.toUpperCase()}</Mono>
                </div>
                <span style={{ color: T.t4, fontSize: 13 }}>›</span>
              </button>
            ))}
          </div>
        </>
      )}

      <button onClick={onAdd} style={{ width: "100%", padding: "13px", background: "transparent",
        border: `1px dashed ${T.lineUp}`, borderRadius: 10, color: T.teal,
        fontFamily: T.mono, fontSize: 10, fontWeight: 800, letterSpacing: "0.14em", cursor: "pointer" }}>
        + ADD A NEW CHART
      </button>
    </div>
  );
};

/* ── STEP 3 · THE VERDICT ──────────────────────────────────────────────── */
const StepVerdict = ({ chartId, relationship, onOpenLayer }) => {
  const v = VERDICT;
  const chart = SAVED_CHARTS.find(c => c.id === chartId);
  return (
    <div style={{ padding: "4px 16px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <Mono size={8} color={T.teal}>COMPATIBILITY VERDICT</Mono>
        <Mono size={7} color={T.t3}>{RELATIONSHIP_TYPES.find(r=>r.id===relationship).label.toUpperCase()}</Mono>
      </div>

      <AlignmentDiagram score={v.score} leftInitial="R" rightInitial={chart?.initial || "A"} />

      <div style={{ textAlign: "center", marginBottom: 18 }}>
        <Mono size={9} color={T.teal} weight={800}>{v.label.toUpperCase()}</Mono>
        <div style={{ fontSize: 17, fontWeight: 600, color: T.t1, lineHeight: 1.35, letterSpacing: "-0.01em", margin: "8px 16px 0" }}>
          {v.headline}
        </div>
      </div>

      <div style={{ padding: "13px 14px", background: T.card, border: `1px solid ${T.line}`, borderRadius: 11, marginBottom: 18 }}>
        <div style={{ fontSize: 13, color: T.t2, lineHeight: 1.55 }}>{v.detail}</div>
      </div>

      {/* layer breakdown */}
      <Mono size={7} color={T.t3} style={{ display: "block", marginBottom: 10 }}>WHERE YOU MEET · WHERE YOU PULL APART</Mono>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {v.layers.map(l => (
          <button key={l.key} onClick={() => onOpenLayer(l)} style={{ width: "100%", textAlign: "left", cursor: "pointer",
            padding: "12px 14px", background: T.card,
            border: `1px solid ${T.line}`, borderLeft: `2px solid ${l.passed ? T.teal : T.amber}`,
            borderRadius: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: l.passed ? T.teal : T.amber,
                  boxShadow: l.passed ? `0 0 6px ${T.teal}` : "none" }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: T.t1 }}>{l.name}</span>
              </div>
              <Mono size={7} color={l.passed ? T.teal : T.amber}>{l.badge.toUpperCase()}</Mono>
            </div>
            <div style={{ fontSize: 12, color: T.t2, lineHeight: 1.45 }}>{l.line}</div>
          </button>
        ))}
      </div>
    </div>
  );
};

/* ── LIST: existing compatibility checks (when not in a flow) ──────────── */
const CompatList = ({ onNew, onOpen }) => (
  <div style={{ padding: "8px 16px 24px" }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
      <Mono size={8} color={T.teal}>COMPATIBILITY</Mono>
      <button onClick={onNew} style={{ padding: "6px 12px", background: T.teal, color: T.bg, border: "none", borderRadius: 16,
        fontFamily: T.mono, fontSize: 9, fontWeight: 800, letterSpacing: "0.12em", cursor: "pointer" }}>+ NEW</button>
    </div>
    <Mono size={7} color={T.t3} style={{ display: "block", marginBottom: 10 }}>YOUR CHARTS</Mono>
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {SAVED_CHARTS.map(c => {
        const r = RELATIONSHIP_TYPES.find(x => x.id === c.relationship);
        return (
          <button key={c.id} onClick={() => onOpen(c.id)} style={{ width: "100%", textAlign: "left", cursor: "pointer",
            padding: "12px 14px", background: T.card, border: `1px solid ${T.line}`, borderRadius: 10,
            display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: "50%", background: T.cardUp,
              border: `1px solid ${T.lineUp}`, display: "flex", alignItems: "center", justifyContent: "center",
              color: T.t1, fontFamily: T.mono, fontSize: 14, fontWeight: 700 }}>{c.initial}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: T.t1 }}>{c.name}</div>
              <Mono size={8} color={T.t3} weight={500} ls="0.04em" style={{ display: "block", marginTop: 2 }}>{r.label.toUpperCase()}</Mono>
            </div>
            <span style={{ color: T.t4, fontSize: 13 }}>›</span>
          </button>
        );
      })}
    </div>
  </div>
);

/* ── MAIN ──────────────────────────────────────────────────────────────── */
export default function AntarCompat() {
  const [tab, setTab] = useState("compat");
  const [step, setStep] = useState("list"); // list | type | pick | verdict
  const [relationship, setRelationship] = useState(null);
  const [chartId, setChartId] = useState(null);
  const [layer, setLayer] = useState(null);

  const back = () => {
    if (step === "verdict") setStep("pick");
    else if (step === "pick") setStep("type");
    else if (step === "type") setStep("list");
  };

  return (
    <div style={{ width: "100%", maxWidth: 430, margin: "0 auto", background: T.bg, color: T.t1,
      fontFamily: T.sans, height: "100vh", position: "relative", overflow: "hidden",
      border: `1px solid ${T.line}`, borderRadius: 16 }}>
      <style>{`::-webkit-scrollbar{display:none}`}</style>

      <Header onBack={step !== "list" ? back : null} />

      <div style={{ height: "calc(100vh - 50px - 56px)", overflowY: "auto", scrollbarWidth: "none" }}>
        {tab === "compat" && step === "list" && (
          <CompatList
            onNew={() => setStep("type")}
            onOpen={(id) => { setChartId(id); setRelationship(SAVED_CHARTS.find(c=>c.id===id).relationship); setStep("verdict"); }} />
        )}
        {tab === "compat" && step === "type" && (
          <StepRelationship onPick={(id) => { setRelationship(id); setStep("pick"); }} />
        )}
        {tab === "compat" && step === "pick" && (
          <StepChart relationship={relationship}
            onPick={(id) => { setChartId(id); setStep("verdict"); }}
            onAdd={() => alert("Add-chart flow not implemented in mockup")} />
        )}
        {tab === "compat" && step === "verdict" && (
          <StepVerdict chartId={chartId} relationship={relationship} onOpenLayer={setLayer} />
        )}

        {tab !== "compat" && (
          <div style={{ padding: "60px 28px", textAlign: "center" }}>
            <Mono size={8} color={T.teal} style={{ display: "block", marginBottom: 12 }}>{tab.toUpperCase()}</Mono>
            <div style={{ fontSize: 15, color: T.t2, lineHeight: 1.5 }}>This screen is built separately.</div>
          </div>
        )}
      </div>

      <BottomNav active={tab} onChange={setTab} />

      <Sheet open={!!layer} onClose={() => setLayer(null)}>
        {layer && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: layer.passed ? T.teal : T.amber,
                boxShadow: layer.passed ? `0 0 8px ${T.teal}` : "none" }} />
              <Mono size={8} color={layer.passed ? T.teal : T.amber}>{layer.badge.toUpperCase()}</Mono>
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: T.t1, letterSpacing: "-0.02em", marginBottom: 14 }}>{layer.name}</div>
            <div style={{ fontSize: 14, color: T.t1, lineHeight: 1.6, marginBottom: 14 }}>{layer.line}</div>
            <div style={{ padding: "13px 14px", background: T.card, border: `1px solid ${T.line}`, borderRadius: 11 }}>
              <Mono size={7} color={layer.passed ? T.teal : T.amber} style={{ display: "block", marginBottom: 6 }}>
                {layer.passed ? "HOW TO USE IT" : "HOW TO WORK WITH IT"}
              </Mono>
              <div style={{ fontSize: 13, color: T.t2, lineHeight: 1.55 }}>
                {layer.passed
                  ? "This layer is naturally aligned — you don't need to manage it. Lean into it when the relationship gets tested elsewhere."
                  : "This is where conscious effort matters. Naming the pattern out loud, before stress hits, prevents most of the friction."}
              </div>
            </div>
          </>
        )}
      </Sheet>
    </div>
  );
}
