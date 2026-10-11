"""[working-agreement 2026-10-11] A TEMPLATE working agreement for two people building something together — not a legal agreement.

Looks like a proper working agreement (parties, scope, roles, decisions, communication, IP, equity, confidentiality, changes and exit, signatures) so the
two people have a real document to sit down with. What the product knows is filled in; everything personal or legal is left blank on purpose:

  FILLED   roles and responsibilities (from the who-leads-what read), the open areas to assign, shared areas, the disagreement protocol (from the
           friction the reading found), a check-in rhythm, who decides what
  BLANK    parties' names, ID numbers, addresses, the venture, hours, spending limits, ownership of work, EQUITY, vesting, pay, expenses,
           confidentiality terms, exit terms, review date, signatures — we do not suggest numbers or legal wording

It says plainly, at the top and again at the end, that it is a template to talk from and not legal advice. Deterministic (no LLM): the document is the
same every time from the same reading; the people's edits are stored separately as `values` and merged over it. en + es. Partners (cofounder / business)
today; employee, boss and advisor get their own sheets later (build() returns None for them)."""
from __future__ import annotations

from typing import Dict, List, Optional

from antar_engine import partner_roles as P

VERSION = "working-agreement-1"
KINDS = ("cofounder", "business")

_RESP = {
    "en": {
        "tech": ["Owns the product roadmap and technical decisions", "Chooses tools, architecture and technical hires", "Reports progress and risks on the agreed rhythm"],
        "ops": ["Owns day-to-day execution and delivery", "Keeps processes, deadlines and quality in place", "Flags capacity problems early"],
        "sales": ["Owns the sales pipeline and client relationships", "Leads pricing conversations with clients", "Reports on pipeline and commitments made"],
        "vision": ["Sets direction and priorities", "Carries the venture's story and long-term plan", "Calls the priority when areas compete"],
        "finance": ["Owns budgeting, bookkeeping and reporting", "Prepares the numbers behind decisions and funding", "Tracks cash and obligations"],
        "creative": ["Owns brand, voice and presentation", "Approves public-facing materials", "Keeps messaging consistent"],
    },
    "es": {
        "tech": ["Lleva la hoja de ruta del producto y las decisiones técnicas", "Elige herramientas, arquitectura y contrataciones técnicas", "Informa avances y riesgos con el ritmo acordado"],
        "ops": ["Lleva la ejecución y la entrega del día a día", "Mantiene procesos, plazos y calidad", "Avisa pronto de problemas de capacidad"],
        "sales": ["Lleva el embudo de ventas y la relación con clientes", "Dirige las conversaciones de precios con clientes", "Informa del embudo y de los compromisos asumidos"],
        "vision": ["Define la dirección y las prioridades", "Sostiene la historia y el plan a largo plazo del proyecto", "Decide la prioridad cuando las áreas compiten"],
        "finance": ["Lleva el presupuesto, la contabilidad y los informes", "Prepara las cifras detrás de las decisiones y el financiamiento", "Sigue el flujo de caja y las obligaciones"],
        "creative": ["Lleva la marca, la voz y la presentación", "Aprueba los materiales públicos", "Mantiene el mensaje coherente"],
    },
}
_TX = {
    "en": {
        "title": "Working agreement (template)",
        "disclaimer": "This is a template to help you talk and write things down together. It is not a legal agreement and it is not legal advice. Change anything, "
                      "and have a lawyer review it before you rely on it.",
        "s_parties": "Parties", "s_purpose": "Purpose and scope", "s_roles": "Roles and responsibilities", "s_time": "Time and commitment",
        "s_decisions": "Decision-making", "s_comm": "Communication and record-keeping", "s_ip": "Ownership of work", "s_equity": "Equity, pay and expenses",
        "s_conf": "Confidentiality", "s_changes": "Changes, review and exit", "s_sign": "Signatures",
        "party_a": "Party A", "party_b": "Party B", "name": "Full name", "idn": "ID or passport number", "addr": "Address", "eff": "Effective date",
        "venture": "Name of the venture", "venture_d": "What you are building together",
        "scope_hint": "Describe the venture and what is in and out of scope.",
        "owner_of": "{who} owns", "who_owns": "Owner for {lane}", "pick": "Choose: Party A, Party B or shared",
        "opts_owner": ["Party A", "Party B", "Shared"], "assign": "Not yet assigned. Agree an owner together.",
        "shared_h": "Shared areas", "shared_t": "Both parties decide together: {lanes}.",
        "gap_t": "Neither party is the natural owner of {lanes}. Agree to hire, partner or outsource it, or assign it on purpose.",
        "hours": "Hours per week committed", "others": "Other work or commitments each party may keep", "full": "Full-time or part-time",
        "dec_own": "Each owner decides in their own area and writes the decision down: what was decided, by whom, and by when.",
        "dec_joint": "These need both parties to agree first, in writing: hiring and dismissals, contracts, fundraising, public statements, and changes to this agreement.",
        "spend": "Spending that needs both parties' approval above", "deadlock_f": "If a decision is still open after this many days",
        "deadlock_t": "Who helps decide (a named advisor or mediator)",
        "disagree": "When you disagree: say it within a day, in one sentence. Agree a time to talk. If it is still open, the owner of the area decides and the other "
                    "party's view is written beside the decision.",
        "solo": "Because one party does their best work owning an area outright, each owner's scope is written narrowly and agreed in writing.",
        "cadence": "Check-in rhythm", "cadence_o": ["Weekly", "Twice a week", "Fortnightly", "Monthly"], "channels": "Channel for what",
        "channels_v": "Urgent: call. Decisions: a shared document. Updates: chat.", "record": "Every key decision is written down with who decided it and by when.",
        "ip_f": "Who owns the work created for the venture", "ip_hint": "Agree this with a lawyer; write the intent here.",
        "eq_h": "Left blank on purpose: only the two of you can decide these.", "eq": "Equity structure", "vest": "Vesting", "pay": "Pay or draw", "exp": "Expenses",
        "conf": "How confidential information is handled", "conf_hint": "Agree what is private and for how long.",
        "review": "Review this agreement on", "review_hint": "About six months from the effective date.", "roles_change": "Roles change only when both parties agree, in writing.",
        "exit": "If one party leaves: notice period, and what happens to the work and to ownership", "exit_hint": "Agree this with a lawyer.",
        "sig_n": "Name", "sig_d": "Date", "sig_s": "Signature", "foot": "A template, not a legal agreement. Have a lawyer review before relying on it.",
        "blank": "________", "reading": "from your reading",
    },
    "es": {
        "title": "Acuerdo de trabajo (plantilla)",
        "disclaimer": "Esta es una plantilla para ayudarles a conversar y dejar las cosas por escrito. No es un acuerdo legal ni es asesoría legal. Cambien lo que quieran "
                      "y pidan a un abogado que la revise antes de apoyarse en ella.",
        "s_parties": "Partes", "s_purpose": "Propósito y alcance", "s_roles": "Roles y responsabilidades", "s_time": "Tiempo y dedicación",
        "s_decisions": "Toma de decisiones", "s_comm": "Comunicación y registro", "s_ip": "Propiedad del trabajo", "s_equity": "Participación, pago y gastos",
        "s_conf": "Confidencialidad", "s_changes": "Cambios, revisión y salida", "s_sign": "Firmas",
        "party_a": "Parte A", "party_b": "Parte B", "name": "Nombre completo", "idn": "Número de documento o pasaporte", "addr": "Domicilio", "eff": "Fecha de inicio",
        "venture": "Nombre del proyecto", "venture_d": "Lo que están construyendo juntos",
        "scope_hint": "Describan el proyecto y qué entra y qué no entra en el alcance.",
        "owner_of": "{who} lleva", "who_owns": "Responsable de {lane}", "pick": "Elijan: Parte A, Parte B o compartido",
        "opts_owner": ["Parte A", "Parte B", "Compartido"], "assign": "Aún sin asignar. Acuerden un responsable juntos.",
        "shared_h": "Áreas compartidas", "shared_t": "Ambas partes deciden juntas: {lanes}.",
        "gap_t": "Ninguna de las partes es la responsable natural de {lanes}. Acuerden contratar, asociarse o externalizarlo, o asignarlo a propósito.",
        "hours": "Horas por semana comprometidas", "others": "Otros trabajos o compromisos que cada parte puede mantener", "full": "Tiempo completo o parcial",
        "dec_own": "Cada responsable decide en su propia área y deja la decisión por escrito: qué se decidió, quién y para cuándo.",
        "dec_joint": "Estas decisiones requieren el acuerdo previo de ambas partes, por escrito: contrataciones y despidos, contratos, financiamiento, declaraciones públicas y cambios a este acuerdo.",
        "spend": "Gastos que requieren la aprobación de ambas partes por encima de", "deadlock_f": "Si una decisión sigue abierta después de este número de días",
        "deadlock_t": "Quién ayuda a decidir (un asesor o mediador con nombre)",
        "disagree": "Cuando no estén de acuerdo: díganlo en un día, en una frase. Acuerden un momento para hablar. Si sigue abierto, decide quien lleva el área y "
                    "la opinión de la otra parte queda escrita junto a la decisión.",
        "solo": "Como una de las partes rinde mejor llevando un área por completo, el alcance de cada responsable se escribe de forma acotada y se acuerda por escrito.",
        "cadence": "Ritmo de revisión", "cadence_o": ["Semanal", "Dos veces por semana", "Quincenal", "Mensual"], "channels": "Canal para cada cosa",
        "channels_v": "Urgente: llamada. Decisiones: un documento compartido. Novedades: chat.", "record": "Toda decisión clave queda escrita con quién la tomó y para cuándo.",
        "ip_f": "Quién es dueño del trabajo creado para el proyecto", "ip_hint": "Acuérdenlo con un abogado; escriban aquí la intención.",
        "eq_h": "Se deja en blanco a propósito: solo ustedes dos pueden decidirlo.", "eq": "Estructura de participación", "vest": "Consolidación (vesting)", "pay": "Pago o retiro", "exp": "Gastos",
        "conf": "Cómo se maneja la información confidencial", "conf_hint": "Acuerden qué es privado y por cuánto tiempo.",
        "review": "Revisar este acuerdo el", "review_hint": "Unos seis meses después de la fecha de inicio.", "roles_change": "Los roles solo cambian cuando ambas partes están de acuerdo, por escrito.",
        "exit": "Si una parte se va: plazo de aviso y qué pasa con el trabajo y la propiedad", "exit_hint": "Acuérdenlo con un abogado.",
        "sig_n": "Nombre", "sig_d": "Fecha", "sig_s": "Firma", "foot": "Una plantilla, no un acuerdo legal. Pidan a un abogado que la revise antes de apoyarse en ella.",
        "blank": "________", "reading": "de su lectura",
    },
}


def _field(key, label, hint="", value=""):
    return {"type": "field", "key": key, "label": label, "hint": hint, "value": value}


def _blank(key, label, hint=""):
    return {"type": "blank", "key": key, "label": label, "hint": hint, "value": ""}


def _clause(cid, text, source="template", title=None):
    """A paragraph the people can edit. With a title, `text` is a newline-separated list of bullets (a role's responsibilities)."""
    c = {"type": "clause", "id": cid, "key": f"clause_text:{cid}", "text": text, "source": source}
    if title:
        c["title"] = title
    return c


def _choice(key, label, options, value="", hint=""):
    return {"type": "choice", "key": key, "label": label, "options": options, "value": value, "hint": hint}


def _text(t):
    return {"type": "text", "text": t}


def _list(items):
    return {"type": "list", "items": items}


def build(kind: str, roles: Optional[dict], language: str = "en", names: Optional[dict] = None) -> Optional[dict]:
    """The template for a pair, or None for a type that has no template yet / no roles read. `names` ({a, b}) are only HINTS for the reader."""
    try:
        if (kind or "").lower() not in KINDS or not isinstance(roles, dict) or roles.get("kind") == "hierarchy" or not roles.get("you"):
            return None
        lang = language if language in _TX else "en"
        tx, resp, nm = _TX[lang], _RESP[lang], P._NAME[lang]
        you, other = roles["you"].get("leads", []), roles["other"].get("leads", [])
        shared = roles.get("shared", [])
        openl = list(roles.get("contested", [])) + list(roles.get("gaps", []))
        gaps = list(roles.get("gaps", []))
        contested = list(roles.get("contested", []))
        join = lambda xs: (", ".join(nm[x] for x in xs[:-1]) + (" y " if lang == "es" else " and ") + nm[xs[-1]]) if len(xs) > 1 else "".join(nm[x] for x in xs)

        sections: List[dict] = []
        sections.append({"id": "parties", "title": tx["s_parties"], "items": [
            _text(tx["party_a"]), _field("party_a_name", tx["name"]), _field("party_a_id", tx["idn"]), _field("party_a_address", tx["addr"]),
            _text(tx["party_b"]), _field("party_b_name", tx["name"]), _field("party_b_id", tx["idn"]), _field("party_b_address", tx["addr"]),
            _field("effective_date", tx["eff"])]})
        sections.append({"id": "purpose", "title": tx["s_purpose"], "items": [
            _field("venture_name", tx["venture"]), _blank("venture_desc", tx["venture_d"], tx["scope_hint"])]})

        r_items: List[dict] = []
        for party, leads in ((tx["party_a"], you), (tx["party_b"], other)):
            r_items.append(_text(tx["owner_of"].format(who=party)))
            if not leads:
                r_items.append(_text(tx["assign"]))
            for lane in leads:
                r_items.append(_clause(f"role_{party[-1].lower()}_{lane}", "\n".join(resp[lane]), "reading", title=nm[lane]))
        if shared:
            r_items.append(_text(tx["shared_h"]))
            r_items.append(_clause("shared", tx["shared_t"].format(lanes=join(shared)), "reading"))
        for lane in contested:
            r_items.append(_choice(f"owner_{lane}", tx["who_owns"].format(lane=nm[lane]), tx["opts_owner"], "", tx["pick"]))
        if gaps:
            r_items.append(_clause("gaps", tx["gap_t"].format(lanes=join(gaps)), "reading"))
            for lane in gaps:
                r_items.append(_choice(f"owner_{lane}", tx["who_owns"].format(lane=nm[lane]), tx["opts_owner"], "", tx["pick"]))
        r_items.append(_clause("roles_change", tx["roles_change"]))
        sections.append({"id": "roles", "title": tx["s_roles"], "items": r_items})

        sections.append({"id": "time", "title": tx["s_time"], "items": [
            _field("hours_a", tx["party_a"] + ": " + tx["hours"]), _field("hours_b", tx["party_b"] + ": " + tx["hours"]),
            _field("full_part", tx["full"]), _blank("other_commitments", tx["others"])]})

        d_items = [_clause("dec_own", tx["dec_own"], "reading"), _clause("dec_joint", tx["dec_joint"]),
                   _field("spend_limit", tx["spend"]), _field("deadlock_days", tx["deadlock_f"]), _field("deadlock_helper", tx["deadlock_t"]),
                   _clause("disagree", tx["disagree"], "reading")]
        if (roles.get("capacity") or {}).get("solo"):
            d_items.insert(1, _clause("solo", tx["solo"], "reading"))
        sections.append({"id": "decisions", "title": tx["s_decisions"], "items": d_items})

        sections.append({"id": "communication", "title": tx["s_comm"], "items": [
            _choice("cadence", tx["cadence"], tx["cadence_o"], tx["cadence_o"][0]), _field("channels", tx["channels"], "", tx["channels_v"]),
            _clause("record", tx["record"], "reading")]})
        sections.append({"id": "ip", "title": tx["s_ip"], "items": [_blank("ip_owner", tx["ip_f"], tx["ip_hint"])]})
        sections.append({"id": "equity", "title": tx["s_equity"], "items": [
            _text(tx["eq_h"]), _blank("equity", tx["eq"]), _blank("vesting", tx["vest"]), _blank("pay", tx["pay"]), _blank("expenses", tx["exp"])]})
        sections.append({"id": "confidentiality", "title": tx["s_conf"], "items": [_blank("confidentiality", tx["conf"], tx["conf_hint"])]})
        sections.append({"id": "changes", "title": tx["s_changes"], "items": [
            _field("review_date", tx["review"], tx["review_hint"]), _blank("exit_terms", tx["exit"], tx["exit_hint"])]})
        sections.append({"id": "signatures", "title": tx["s_sign"], "items": [
            _text(tx["party_a"]), _field("sig_a_name", tx["sig_n"]), _field("sig_a_date", tx["sig_d"]), _field("sig_a_sign", tx["sig_s"]),
            _text(tx["party_b"]), _field("sig_b_name", tx["sig_n"]), _field("sig_b_date", tx["sig_d"]), _field("sig_b_sign", tx["sig_s"])]})

        doc = {"version": VERSION, "type": (kind or "").lower(), "language": lang, "title": tx["title"], "disclaimer": tx["disclaimer"], "footer": tx["foot"],
               "sections": sections, "name_hints": {"party_a": (names or {}).get("a") or "", "party_b": (names or {}).get("b") or ""}}
        doc["markdown"] = to_markdown(doc)
        return doc
    except Exception as e:
        print(f"[working-agreement] failed: {type(e).__name__}: {e}")
        return None


def apply_values(doc: dict, values: Optional[dict]) -> dict:
    """Merge the people's own edits (field values, choices, and edited clause text keyed `clause_text:<id>`) over the template. Returns a new doc."""
    if not isinstance(doc, dict) or not isinstance(values, dict) or not values:
        return doc
    out = {**doc, "sections": []}
    for s in doc.get("sections", []):
        items = []
        for it in s.get("items", []):
            it = dict(it)
            k = it.get("key")
            if k and k in values and isinstance(values[k], str):
                if it["type"] == "clause":
                    it["text"], it["edited"] = values[k], True
                else:
                    it["value"] = values[k]
            items.append(it)
        out["sections"].append({**s, "items": items})
    out["markdown"] = to_markdown(out)
    return out


def to_markdown(doc: dict) -> str:
    """The same document as plain markdown / text (blanks as ________), for download or print."""
    blank = _TX.get(doc.get("language"), _TX["en"])["blank"]
    L = [f"# {doc['title']}", "", f"_{doc['disclaimer']}_", ""]
    in_fields = False
    for n, s in enumerate(doc["sections"], 1):
        L += [f"## {n}. {s['title']}", ""]
        in_fields = False
        for it in s["items"]:
            t = it["type"]
            if t in ("field", "blank", "choice"):
                v = (it.get("value") or "").strip()
                hint = f" _({it['hint']})_" if it.get("hint") and not v else ""
                L.append(f"- {it['label']}: {v or blank}{hint}")
                in_fields = True
                continue
            if in_fields:
                L.append("")
                in_fields = False
            if t == "text":
                L += [f"**{it['text']}**", ""]
            elif t == "clause":
                if it.get("title"):
                    L += [f"**{it['title']}**"] + [f"- {x}" for x in str(it["text"]).split("\n") if x.strip()] + [""]
                else:
                    L += [it["text"], ""]
            elif t == "list":
                L += [f"- {x}" for x in it["items"]] + [""]
        if in_fields:
            L.append("")
    L += ["---", f"_{doc['footer']}_", ""]
    return "\n".join(L)




# ── the people's edits (fail-open until sql_connection_agreements.sql is run) ───────────────────────────
import re as _re

_KEY_OK = _re.compile(r"^[a-z0-9_:]{1,80}$")
_MEM: Dict[tuple, dict] = {}


def clean_values(values) -> dict:
    """Only short string values under known-shaped keys; at most 200 of them. Never raises."""
    out: Dict[str, str] = {}
    if not isinstance(values, dict):
        return out
    for k, v in list(values.items())[:200]:
        if isinstance(k, str) and _KEY_OK.match(k) and isinstance(v, str):
            out[k] = v[:4000]
    return out


def load_values(sb, session_id: str, language: str) -> dict:
    hit = _MEM.get((session_id, language))
    if hit is not None:
        return hit
    try:
        r = sb.table("connection_agreements").select("values").eq("session_id", session_id).eq("language", language).limit(1).execute().data or []
        if r and isinstance(r[0].get("values"), dict):
            _MEM[(session_id, language)] = r[0]["values"]
            return r[0]["values"]
    except Exception as e:
        print(f"[working-agreement] read skipped (table missing?): {type(e).__name__}")
    return {}


def save_values(sb, session_id: str, language: str, values: dict) -> bool:
    """True when persisted to the table; the in-process copy is always updated so the page works before the table exists."""
    _MEM[(session_id, language)] = values
    try:
        sb.table("connection_agreements").upsert({"session_id": session_id, "language": language, "values": values}, on_conflict="session_id,language").execute()
        return True
    except Exception as e:
        print(f"[working-agreement] store skipped (table missing?): {type(e).__name__}")
        return False
