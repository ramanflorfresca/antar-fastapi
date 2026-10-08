"""An in-memory stand-in for the slice of PostgREST that Circle (and the check-back flow) uses."""
import uuid


class _Q:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.f, self._order, self._lim, self._op, self._payload, self._opts = [], None, None, "select", None, {}

    def select(self, cols="*", *_, **__): self._sel = str(cols); return self
    def eq(self, c, v): self.f.append(lambda r: r.get(c) == v); return self
    def neq(self, c, v): self.f.append(lambda r: r.get(c) != v); return self
    def gt(self, c, v): self.f.append(lambda r: str(r.get(c)) > str(v)); return self
    def gte(self, c, v): self.f.append(lambda r: str(r.get(c)) >= str(v)); return self
    def lte(self, c, v): self.f.append(lambda r: str(r.get(c)) <= str(v)); return self
    def in_(self, c, vs): self.f.append(lambda r: r.get(c) in vs); return self
    def ilike(self, *a): return self
    def is_(self, c, v): self.f.append(lambda r: r.get(c) is None); return self
    def order(self, c, desc=False): self._order = (c, desc); return self
    def limit(self, n): self._lim = n; return self
    def single(self): return self
    def insert(self, p): self._op, self._payload = "insert", p; return self
    def update(self, p): self._op, self._payload = "update", p; return self
    def delete(self): self._op = "delete"; return self

    def upsert(self, payload, on_conflict=None, ignore_duplicates=False):
        self._op, self._payload, self._opts = "upsert", payload, (on_conflict, ignore_duplicates)
        return self

    def execute(self):
        if self.db.missing and (self.db.missing is True or self.name in self.db.missing):
            raise Exception("PGRST205 Could not find the table 'public.%s' in the schema cache" % self.name)
        for tbl, col in self.db.bad_cols:        # a column that does not exist (phantom / migration not run)
            if tbl == self.name and (col in getattr(self, "_sel", "") or col in str(self._payload or "")):
                raise Exception("42703 column %s.%s does not exist" % (tbl, col))
        rows = self.db.t.setdefault(self.name, [])
        R = type("R", (), {"data": None})
        r = R()
        hit = [x for x in rows if all(f(x) for f in self.f)]
        if self._op == "select":
            if self._order:
                hit.sort(key=lambda x: str(x.get(self._order[0])), reverse=self._order[1])
            r.data = [dict(x) for x in hit[: self._lim]]
        elif self._op == "insert":
            ps = self._payload if isinstance(self._payload, list) else [self._payload]
            out = []
            for p in ps:
                row = dict(p)
                row.setdefault("id", str(uuid.uuid4()))
                row.setdefault("created_at", self.db.clock())
                for k, v in (self.db.defaults.get(self.name) or {}).items():
                    row.setdefault(k, v)
                self.db.check_unique(self.name, row, rows)
                rows.append(row)
                out.append(dict(row))
            r.data = out
        elif self._op == "update":
            for x in hit:
                x.update(self._payload)
            r.data = [dict(x) for x in hit]
        elif self._op == "delete":
            for x in hit:
                rows.remove(x)
            r.data = [dict(x) for x in hit]
        else:                                   # upsert
            key, ign = self._opts
            keys = key.split(",") if key else ["id"]
            ex = next((x for x in rows if all(x.get(k) == self._payload.get(k) for k in keys)), None)
            if ex and ign:
                r.data = []
            elif ex:
                ex.update(self._payload); r.data = [dict(ex)]
            else:
                row = dict(self._payload); row.setdefault("id", str(uuid.uuid4()))
                rows.append(row); r.data = [dict(row)]
        return r


class DB:
    def __init__(self, missing=False):
        self.t, self.missing, self._n, self.bad_cols = {}, missing, 0, set()
        self.defaults = {"circle_invites": {"accepted_chart_id": None, "resend_count": 0, "status": "pending"}}

    def clock(self):
        self._n += 1
        return "2026-10-07T00:00:%02d+00:00" % (self._n % 60)

    def table(self, name):
        return _Q(self, name)

    def rows(self, name):
        return self.t.get(name, [])

    def check_unique(self, name, row, rows):
        if name == "circle_invites" and any(x.get("token_hash") == row.get("token_hash") for x in rows):
            raise Exception("duplicate key circle_invites_token_hash_uq")
        if name == "circle_pairs":
            k = frozenset((row["chart_a"], row["chart_b"]))
            if any(frozenset((x["chart_a"], x["chart_b"])) == k for x in rows):
                raise Exception("duplicate key circle_pairs_unordered_uq")
