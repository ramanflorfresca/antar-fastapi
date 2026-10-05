"""[wa-policy 2026-10-05] In-chat data-policy acceptance before anything is processed."""
from antar_engine import messaging as msg


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.op, self.payload, self.f = db, table, "select", None, {}

    def select(self, *a, **k):
        return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def update(self, row):
        self.op, self.payload = "update", row
        return self

    def eq(self, k, v):
        self.f[k] = v
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self.db.get("missing") and self.table == "wa_policy_acceptances":
            raise RuntimeError("Could not find the table 'public.wa_policy_acceptances' in the schema cache")
        rows = self.db.setdefault(self.table, [])
        if self.op == "insert":
            rows.append(dict(self.payload))
            return type("R", (), {"data": [self.payload]})()
        if self.op == "update":
            for r in rows:
                if all(str(r.get(k)) == str(v) for k, v in self.f.items()):
                    r.update(self.payload)
            return type("R", (), {"data": []})()
        hit = [r for r in reversed(rows) if all(str(r.get(k)) == str(v) for k, v in self.f.items())]
        return type("R", (), {"data": hit})()


class FakeSB:
    def __init__(self, missing=False):
        self.db = {"missing": missing}

    def table(self, t):
        return _Q(self.db, t)


N = "+573001112233"


def test_unknown_number_must_accept_the_current_wording():
    sb = FakeSB()
    assert msg.policy_state(sb, N, None) == "needed"
    assert msg.record_policy(sb, N, "yes", "es")
    assert msg.policy_state(sb, N, None) == "ok"
    row = sb.db["wa_policy_acceptances"][0]
    assert row["decision"] == "accepted" and row["policy_version"] == msg.WA_CONSENT_VERSION
    assert row["policy_url"].endswith("lang=es")


def test_decline_is_recorded_and_stays_needed():
    sb = FakeSB()
    msg.record_policy(sb, N, "no", "en")
    assert msg.policy_state(sb, N, None) == "needed"
    assert sb.db["wa_policy_acceptances"][0]["decision"] == "declined"


def test_app_consent_counts_and_old_wording_does_not():
    sb = FakeSB()
    assert msg.policy_state(sb, N, {"consent_version": msg.WA_CONSENT_VERSION}) == "ok"
    assert msg.policy_state(sb, N, {"consent_version": "wa-2020-01-01"}) == "needed"


def test_accepting_refreshes_a_linked_numbers_consent():
    sb = FakeSB()
    sb.db["messaging_links"] = [{"id": 7, "consent_version": "old"}]
    msg.record_policy(sb, N, "yes", "pt", link={"id": 7})
    assert sb.db["messaging_links"][0]["consent_version"] == msg.WA_CONSENT_VERSION
    assert sb.db["messaging_links"][0]["consent_source"] == "whatsapp"


def test_missing_table_fails_open():
    assert msg.policy_state(FakeSB(missing=True), N, None) == "unknown"


def test_reply_parsing_four_languages_and_buttons():
    for t in ("ACEPTO", "acepto.", "Accept", "aceito", "manzoor", "1"):
        assert msg.parse_policy_reply(t) == "yes"
    for t in ("No acepto", "NO", "não aceito", "nahi", "2"):
        assert msg.parse_policy_reply(t) == "no"
    assert msg.parse_policy_reply("x", "pol:yes") == "yes" and msg.parse_policy_reply("x", "pol:no") == "no"
    assert msg.parse_policy_reply("How is my day?") is None
