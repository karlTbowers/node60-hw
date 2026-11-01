#!/usr/bin/env python3
"""Dimensioned enclosure drawing from a geometry spec (DropOut handbook, enclosure-drawing skill).

Board-independent: everything about a board comes from its spec, built by the board's
own adapter (scripts/enclosure_geometry.py, a function spec() returning a dict) or given
as a JSON file. The spec format is in the skill's references/spec.md.

    python3 scripts/enclosure_drawing.py scripts/enclosure_geometry.py docs/src/diagrams/build
    python3 scripts/enclosure_drawing.py scripts/enclosure_geometry.py --check

Writes enclosure-top.svg, enclosure-<face>.svg for each wall or bottom face that has
cutouts, enclosure-details.svg (one panel per cutout type) and enclosure.json (the spec
plus derived values, for the docs table). Third-angle views in millimetres; ordinate
dimensions from each view's lower-left corner as seen from outside. --check validates the
spec (cutouts and their seal areas inside their face, no two overlapping) and writes
nothing; it exits 1 on a problem.

Python 3 standard library only, so the docs CI can run it without installs.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

ENGINE_VERSION = "1.5"           # bump when the spec format changes (1.1: raised lid regions; 1.2: board notches, more boards; 1.3: panels; 1.4: bosses; 1.5: seats)
FONT = 12                        # px
SCALE = 2.6                      # px per mm for the face views; details use DETAIL_SCALE
DETAIL_SCALE = 6.0
STYLE = """<style>
.o{fill:none;stroke:#1c2127;stroke-width:1.4}
.c{fill:none;stroke:#1c2127;stroke-width:1.1}
.h{fill:none;stroke:#8a929c;stroke-width:0.8;stroke-dasharray:5 3}
.e{fill:none;stroke:#8a929c;stroke-width:0.6;stroke-dasharray:12 3 2 3}
.d{fill:none;stroke:#4b5563;stroke-width:0.6}
.t{fill:#1c2127;font:%dpx ui-monospace,SFMono-Regular,Menlo,monospace}
.l{fill:#4b5563;font:%dpx system-ui,-apple-system,sans-serif}
.ttl{fill:#1c2127;font:600 13px system-ui,-apple-system,sans-serif}
.a{fill:#4b5563}
</style>""" % (FONT, FONT)

# Each face as seen from outside: which enclosure axes run right (u) and up (v), and
# whether u runs against the axis (mirrored). Walls: v is height z; top and bottom: v is
# depth y from the front face (front at the bottom of the view).
FACES = {
    "front":  ("x", "z", False, "FRONT FACE"),
    "back":   ("x", "z", True, "BACK FACE"),
    "right":  ("y", "z", False, "RIGHT FACE (front face on the left)"),
    "left":   ("y", "z", True, "LEFT FACE (front face on the right)"),
    "top":    ("x", "y", False, "TOP (seen from above, front face at the bottom)"),
    "bottom": ("x", "y", True, "BOTTOM (seen from below, front face at the bottom)"),
}


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


# Spec handling -------------------------------------------------------------------
def load_spec(src):
    src = Path(src)
    if src.suffix == ".json":
        return json.loads(src.read_text())
    sys.path.insert(0, str(src.parent))
    mod_spec = importlib.util.spec_from_file_location(src.stem, src)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    return mod.spec()


def face_size(s, face):
    o = s["outside"]
    u, v, _, _ = FACES[face]
    return o[u], o[v]


def to_face(s, face, x=None, y=None, z=None):
    """Enclosure coordinates -> (u, v) in the face's outside view."""
    u_ax, v_ax, mirror, _ = FACES[face]
    vals = {"x": x, "y": y, "z": z}
    w, _ = face_size(s, face)
    u = vals[u_ax]
    return (w - u if mirror else u), vals[v_ax]


# Stepped tops: spec["raised"] lists plan rectangles whose top is higher than outside.z.
def _wall_axis(face):
    """Plan axis a wall face runs along, and the test for a region reaching that wall."""
    X, Y = "x", "y"
    return {"front": (X, lambda r, s: r["y0"] <= 1e-6),
            "back": (X, lambda r, s: r["y1"] >= s["outside"]["y"] - 1e-6),
            "left": (Y, lambda r, s: r["x0"] <= 1e-6),
            "right": (Y, lambda r, s: r["x1"] >= s["outside"]["x"] - 1e-6)}[face]


def top_profile(s, face, at_wall):
    """[(u0, u1, z)] of the top edge in a wall view: the wall itself (at_wall) or the silhouette."""
    ax, touches = _wall_axis(face)
    w, _ = face_size(s, face)
    mirror = FACES[face][2]
    spans = []
    for r in s.get("raised", []):
        if at_wall and not touches(r, s):
            continue
        a, b = r[f"{ax}0"], r[f"{ax}1"]
        spans.append(((w - b, w - a) if mirror else (a, b), r["z"]))
    cuts = sorted({0.0, w} | {e for (a, b), _ in spans for e in (a, b) if 0 < e < w})
    prof = []
    for a, b in zip(cuts, cuts[1:]):
        m = (a + b) / 2
        z = max([s["outside"]["z"]] + [z for (u0, u1), z in spans if u0 <= m <= u1])
        if prof and prof[-1][2] == z:
            prof[-1] = (prof[-1][0], b, z)
        else:
            prof.append((a, b, z))
    return prof


def height_at(prof, u0, u1):
    return min(z for a, b, z in prof if b > u0 and a < u1)


def placed(s, c):
    """A cutout's centre (u, v) in its face's view; c gives x/y/z as the face needs."""
    return to_face(s, c["face"], c.get("x"), c.get("y"), c.get("z"))


def outline(t):
    """Cutout outline relative to its centre (u right, v up), near edge up; plus fillet radii.

    keyed: a slot `width` wide for `full` from the near edge, then `tab` wide to `total`
    (a key when tab < width, a wider band when tab > width), placed `near` from the
    centre (the mating axis). rect: width x height, corner. round: a circle (handled apart).
    """
    if t["shape"] == "rect":
        hw, hh, r = t["width"] / 2, t["height"] / 2, t.get("corner", 0.0)
        return [(-hw, hh), (hw, hh), (hw, -hh), (-hw, -hh)], [r] * 4
    hw, ht, top = t["width"] / 2, t["tab"] / 2, t["near"]
    full, total, r, small = top - t["full"], top - t["total"], t["corner"], t.get("small_corner", 0.8)
    narrow = t["tab"] < t["width"]
    pts = [(-hw, top), (hw, top), (hw, full), (ht, full), (ht, total), (-ht, total), (-ht, full), (-hw, full)]
    radii = [r, r, r if narrow else small, small, small if narrow else r, small if narrow else r, small,
             r if narrow else small]
    return pts, radii


def envelope(t):
    """Half extents (u, v) of the area a cutout type claims on its face: seal or flange, else outline."""
    if t["shape"] == "round":
        h = max(t.get("flange", 0.0), t.get("screw_square", 0.0) + t.get("screw_d", 4.0), t["d"]) / 2
        return h, h
    if "seal" in t:
        return t["seal"][0] / 2, t["seal"][1] / 2
    pts, _ = outline(t)
    return max(abs(p[0]) for p in pts), max(abs(p[1]) for p in pts)


def flip(t, c):
    """Outline points for a placed cutout: near edge up unless the placement says down."""
    pts, radii = outline(t)
    if c.get("near_edge", "up") == "down":
        pts = [(u, -v) for u, v in pts][::-1]
        radii = radii[::-1]
    return pts, radii


def board_outline(b):
    """The board's plan outline, (x, y) corners in order, with its notches cut from the front
    (y0) or back (y1) edge."""
    back = sorted((n for n in b.get("notches", []) if n["y1"] >= b["y1"]), key=lambda n: -n["x0"])
    front = sorted((n for n in b.get("notches", []) if n["y0"] <= b["y0"]), key=lambda n: n["x0"])
    if len(back) + len(front) != len(b.get("notches", [])):
        raise ValueError("a board notch must open on the front or back edge")
    pts = [(b["x0"], b["y0"])]
    for n in front:
        pts += [(n["x0"], b["y0"]), (n["x0"], n["y1"]), (n["x1"], n["y1"]), (n["x1"], b["y0"])]
    pts += [(b["x1"], b["y0"]), (b["x1"], b["y1"])]
    for n in back:
        pts += [(n["x1"], b["y1"]), (n["x1"], n["y0"]), (n["x0"], n["y0"]), (n["x0"], b["y1"])]
    return pts + [(b["x0"], b["y1"])]


def check(s):
    problems = []
    types = s["cutout_types"]
    for c in s["cutouts"]:
        if c["type"] not in types:
            problems.append(f'{c["ref"]}: unknown cutout type {c["type"]}')
        if c["face"] not in FACES:
            problems.append(f'{c["ref"]}: unknown face {c["face"]}')
    if problems:
        return problems
    boxes = {}
    for c in s["cutouts"]:
        (u, v), (eu, ev) = placed(s, c), envelope(types[c["type"]])
        w, h = face_size(s, c["face"])
        if c["face"] in ("front", "back", "left", "right"):
            h = height_at(top_profile(s, c["face"], True), u - eu, u + eu)
        box = (u - eu, v - ev, u + eu, v + ev)
        if box[0] < 0 or box[1] < 0 or box[2] > w or box[3] > h:
            problems.append(f'{c["ref"]}: its {c["type"]} envelope leaves the {c["face"]} face')
        for other, ob in boxes.get(c["face"], []):
            if box[0] < ob[2] and ob[0] < box[2] and box[1] < ob[3] and ob[1] < box[3]:
                problems.append(f'{c["ref"]} and {other}: envelopes overlap on the {c["face"]} face')
        boxes.setdefault(c["face"], []).append((c["ref"], box))
    return problems


# SVG drawing ----------------------------------------------------------------------
def spread(ps, gap=13.0):
    """Push sorted label positions (px) apart to at least gap, keeping their order."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out = list(ps)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out


def rounded_path(pts, radii):
    """SVG path for a closed polygon with per-vertex fillets (screen coords)."""
    n, d = len(pts), []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        a, b = (p0[0] - p1[0], p0[1] - p1[1]), (p2[0] - p1[0], p2[1] - p1[1])
        la, lb, r = math.hypot(*a), math.hypot(*b), radii[i]
        if r <= 0 or la == 0 or lb == 0:
            d.append(f"{'M' if not d else 'L'}{p1[0]:.2f} {p1[1]:.2f}")
            continue
        ua, ub = (a[0] / la, a[1] / la), (b[0] / lb, b[1] / lb)
        ang = math.acos(max(-1, min(1, ua[0] * ub[0] + ua[1] * ub[1])))
        t = min(r / math.tan(ang / 2), la / 2, lb / 2)
        r = t * math.tan(ang / 2)
        st, en = (p1[0] + ua[0] * t, p1[1] + ua[1] * t), (p1[0] + ub[0] * t, p1[1] + ub[1] * t)
        sweep = 1 if (ua[0] * ub[1] - ua[1] * ub[0]) < 0 else 0
        d.append(f"{'M' if not d else 'L'}{st[0]:.2f} {st[1]:.2f}")
        d.append(f"A{r:.2f} {r:.2f} 0 0 {sweep} {en[0]:.2f} {en[1]:.2f}")
    return " ".join(d) + " Z"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.title, self.items = w, h, title, []

    def add(self, s):
        self.items.append(s)

    def write(self, path):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:.0f} {self.h:.0f}" '
                f'width="{self.w:.0f}" height="{self.h:.0f}" style="max-width:{self.w:.0f}px" role="img" '
                f'aria-label="{self.title}"><title>{self.title}</title>{STYLE}'
                '<defs><marker id="ar" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" '
                'orient="auto-start-reverse"><path class="a" d="M0 1.5 L10 5 L0 8.5 Z"/></marker></defs>')
        Path(path).write_text(head + "\n".join(self.items) + "</svg>\n")


class View:
    """Model mm (u right, v up) -> SVG px at a fixed scale."""

    def __init__(self, svg, scale, ox, oy):
        self.svg, self.s, self.ox, self.oy = svg, scale, ox, oy

    def p(self, u, v):
        return self.ox + self.s * u, self.oy - self.s * v

    def rect(self, u0, v0, u1, v1, cls="o", r=0.0):
        (x0, y0), (x1, y1) = self.p(min(u0, u1), max(v0, v1)), self.p(max(u0, u1), min(v0, v1))
        self.svg.add(f'<rect class="{cls}" x="{x0:.2f}" y="{y0:.2f}" width="{x1 - x0:.2f}" '
                     f'height="{y1 - y0:.2f}" rx="{r * self.s:.2f}"/>')

    def circle(self, u, v, d, cls="c"):
        x, y = self.p(u, v)
        self.svg.add(f'<circle class="{cls}" cx="{x:.2f}" cy="{y:.2f}" r="{d / 2 * self.s:.2f}"/>')

    def line(self, u0, v0, u1, v1, cls="d"):
        (x0, y0), (x1, y1) = self.p(u0, v0), self.p(u1, v1)
        self.svg.add(f'<line class="{cls}" x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}"/>')

    def centre(self, u, v, size):
        self.line(u - size, v, u + size, v, "e")
        self.line(u, v - size, u, v + size, "e")

    def text(self, u, v, s, cls="t", anchor="middle"):
        x, y = self.p(u, v)
        self.svg.add(f'<text class="{cls}" x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}">{s}</text>')

    def vtext(self, u, v, s, cls="t"):
        """Text reading bottom to top, centred on (u, v)."""
        x, y = self.p(u, v)
        self.svg.add(f'<text class="{cls}" x="{x:.2f}" y="{y:.2f}" text-anchor="middle" '
                     f'transform="rotate(-90 {x:.2f} {y:.2f})">{s}</text>')

    def title(self, text, y=22):
        self.svg.add(f'<text class="ttl" x="{self.ox:.2f}" y="{y}" text-anchor="start">{text}</text>')

    def poly(self, pts, radii, cls="o"):
        self.svg.add(f'<path class="{cls}" d="{rounded_path([self.p(*q) for q in pts], [r * self.s for r in radii])}"/>')

    def dim_h(self, u0, u1, v_feat, v_dim):
        for u in (u0, u1):
            self.line(u, v_feat, u, v_dim + math.copysign(3 / self.s, v_dim - v_feat))
        (x0, y), (x1, _) = self.p(u0, v_dim), self.p(u1, v_dim)
        self.svg.add(f'<line class="d" x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" '
                     'marker-start="url(#ar)" marker-end="url(#ar)"/>')
        self.svg.add(f'<text class="t" x="{(x0 + x1) / 2:.2f}" y="{y - 4:.2f}" text-anchor="middle">{fmt(abs(u1 - u0))}</text>')

    def dim_v(self, v0, v1, u_feat, u_dim):
        for v in (v0, v1):
            self.line(u_feat, v, u_dim + math.copysign(3 / self.s, u_dim - u_feat), v)
        (x, y0), (_, y1) = self.p(u_dim, v0), self.p(u_dim, v1)
        self.svg.add(f'<line class="d" x1="{x:.2f}" y1="{y0:.2f}" x2="{x:.2f}" y2="{y1:.2f}" '
                     'marker-start="url(#ar)" marker-end="url(#ar)"/>')
        ym = (y0 + y1) / 2
        self.svg.add(f'<text class="t" x="{x - 4:.2f}" y="{ym:.2f}" text-anchor="middle" '
                     f'transform="rotate(-90 {x - 4:.2f} {ym:.2f})">{fmt(abs(v1 - v0))}</text>')

    def ordinate_u(self, us, v_feat, v_line):
        """Ordinates along u from 0 (the view's left edge); vertical text below v_line."""
        us = [0.0] + sorted(set(round(u, 3) for u in us if u > 0))
        xs = [self.p(u, v_line)[0] for u in us]
        for i, (u, x, t) in enumerate(zip(us, xs, spread(xs))):
            self.line(u, v_feat, u, v_line)
            _, y = self.p(u, v_line)
            self.svg.add(f'<line class="d" x1="{x:.2f}" y1="{y:.2f}" x2="{t:.2f}" y2="{y + 6:.2f}"/>')
            self.svg.add(f'<text class="t" x="{t + 4:.2f}" y="{y + 9:.2f}" text-anchor="end" '
                         f'transform="rotate(-90 {t + 4:.2f} {y + 9:.2f})">{fmt(u) if i else "0"}</text>')

    def ordinate_v(self, vs, u_feat, u_line):
        """Ordinates along v from 0 (the view's bottom edge); text left of u_line."""
        vs = [0.0] + sorted(set(round(v, 3) for v in vs if v > 0))
        ys = [self.p(u_line, v)[1] for v in vs]
        ty = [-y for y in spread([-y for y in ys])]
        for i, (v, y, t) in enumerate(zip(vs, ys, ty)):
            self.line(u_feat, v, u_line, v)
            x, _ = self.p(u_line, v)
            self.svg.add(f'<line class="d" x1="{x:.2f}" y1="{y:.2f}" x2="{x - 6:.2f}" y2="{t:.2f}"/>')
            self.svg.add(f'<text class="t" x="{x - 9:.2f}" y="{t + 4:.2f}" text-anchor="end">{fmt(v) if i else "0"}</text>')


def draw_cutout(v, t, u0, v0, c=None, holes=True):
    if t["shape"] == "round":
        v.circle(u0, v0, t["d"])
        if t.get("screw_square"):
            h = t["screw_square"] / 2
            for su in (-1, 1):
                for sv in (-1, 1):
                    v.circle(u0 + su * h, v0 + sv * h, t.get("screw_d", 4.0))
        if t.get("flange"):
            f = t["flange"] / 2
            v.rect(u0 - f, v0 - f, u0 + f, v0 + f, "h")
        return
    pts, radii = flip(t, c or {})
    v.poly([(u0 + a, v0 + b) for a, b in pts], radii)
    if holes and t.get("holes"):
        for su in (-1, 1):
            v.circle(u0 + su * t["holes"] / 2, v0, t["hole_d"])


def face_view(s, face, out):
    w, h = face_size(s, face)
    cuts = [c for c in s["cutouts"] if c["face"] == face]
    types = s["cutout_types"]
    walls = face not in ("top", "bottom")
    if walls:
        sil, at_wall = top_profile(s, face, False), top_profile(s, face, True)
        h = max(z for _, _, z in sil)
    m, left, top = 60, 84, 95             # left: room for a six-character ordinate
    svg = Svg(w * SCALE + left + m + 30, h * SCALE + top + m + 40, f'{s["title"]}: {FACES[face][3].lower()}')
    v = View(svg, SCALE, left, top + h * SCALE)
    wall = s["wall"]
    b = s["board"]
    if walls:
        pts = [(0, 0)] + [p for a, bb, z in sil for p in ((a, z), (bb, z))] + [(w, 0)]
        v.poly(pts, [0] * len(pts))
        for a, bb, z in at_wall:              # the wall's own top edge, where a hood behind rises above it
            if any(z2 > z and bb2 > a and a2 < bb for a2, bb2, z2 in sil):
                v.line(a, z, bb, z, "c")
    else:
        v.rect(0, 0, w, h)
    if walls:
        for lv in s.get("levels", []):
            v.line(0, lv["z"], w, lv["z"], "h")
        for bd in [b] + s.get("boards", []):
            (bu0, _), (bu1, _) = to_face(s, face, bd["x0"], bd["y0"], 0), to_face(s, face, bd["x1"], bd["y1"], 0)
            v.rect(bu0, bd["z0"], bu1, bd["z1"], "h")
    else:
        v.rect(wall, wall, w - wall, h - wall, "h")
        pts = [to_face(s, face, x, y) for x, y in board_outline(b)]
        v.poly(pts, [0] * len(pts), "h")
        for bd in s.get("boards", []):
            (bu0, bv0), (bu1, bv1) = to_face(s, face, bd["x0"], bd["y0"]), to_face(s, face, bd["x1"], bd["y1"])
            v.rect(bu0, bv0, bu1, bv1, "h")
            if face == "top":
                v.text((bu0 + bu1) / 2, min(bv0, bv1) + 2, bd.get("label", "board"), "l")
        if face == "top":
            for bo in s.get("bosses", []):             # under the lid: hidden
                v.circle(bo["x"], bo["y"], bo["d"], "h")
            for se in s.get("seats", []):              # pockets in a flat lid, seen from above
                h2 = se["w"] / 2
                v.rect(se["x"] - h2, se["y"] - h2, se["x"] + h2, se["y"] + h2, "c")
            for r in s.get("raised", []):
                v.rect(r["x0"], r["y0"], r["x1"], r["y1"], "c")
                lbl = f'{r.get("label", "raised")}: top at z {fmt(r["z"])}'
                um, vm = (r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2
                if len(lbl) * FONT * 0.55 < (r["x1"] - r["x0"]) * SCALE - 8:
                    v.text(um, vm - 1.5, lbl, "l")
                else:                      # too narrow: two lines, or up the section if it's taller than wide
                    name, top_z = lbl.split(": ")
                    if r["y1"] - r["y0"] > r["x1"] - r["x0"]:
                        v.vtext(um - 1.5, vm, name, "l")
                        v.vtext(um + 3.5, vm, top_z, "l")
                    else:
                        v.text(um, vm + 1.5, name, "l")
                        v.text(um, vm - 3.5, top_z, "l")
    row_end = []                           # right edge (px) of the last label on each label row
    for c in sorted(cuts, key=lambda c: placed(s, c)[0]):
        t = types[c["type"]]
        u0, v0 = placed(s, c)
        draw_cutout(v, t, u0, v0, c)
        v.centre(u0, v0, max(envelope(t)) * 0.6)
        lbl = f'{c["ref"]} {c.get("label", "")}'.strip()
        if walls:
            half = len(lbl) * FONT * 0.3        # rough label half width (px)
            x = v.p(u0, 0)[0]
            row = next((i for i, end in enumerate(row_end) if x - half > end + 6), len(row_end))
            row_end[row:row + 1] = [x + half]
            v.text(u0, h + 3 + row * 14 / SCALE, lbl, "l")
        else:                              # above the cutout, or above its seat pocket if it has one
            seat = next((se["w"] / 2 for se in s.get("seats", []) if se.get("for") == c["ref"]), 0)
            v.text(u0, v0 + max(envelope(t)[1], seat) + 2.5, lbl, "l")
    us = [placed(s, c)[0] for c in cuts]
    vs = [placed(s, c)[1] for c in cuts] + [h]
    if walls:
        vs += [z for bd in [b] + s.get("boards", []) for z in (bd["z0"], bd["z1"])]
        vs += [lv["z"] for lv in s.get("levels", [])] + [z for _, _, z in sil + at_wall]
        us += [e for a, bb, _ in sil + at_wall for e in (a, bb) if 0 < e < w]
    elif face == "top":
        for r in s.get("raised", []) + b.get("notches", []) + s.get("boards", []) + [
                {"x0": se["x"] - se["w"] / 2, "x1": se["x"] + se["w"] / 2, "y0": se["y"] - se["w"] / 2,
                 "y1": se["y"] + se["w"] / 2} for se in s.get("seats", [])]:
            us += [r["x0"], r["x1"]]
            vs += [r["y0"], r["y1"]]
    v.ordinate_u(us, 0, -12)
    v.ordinate_v(vs, 0, -10)
    v.dim_h(0, w, h, h + 16)    # overall width, above the highest point
    if not walls:
        v.dim_v(0, h, w, w + 12)
    panel = s.get("panels", {}).get(face)
    v.title(f'{FACES[face][3]}' + (f" ({panel})" if panel else "") + (": cutouts drawn as installed" if walls else ""))
    svg.write(out / f"enclosure-{face}.svg")


def ref_ranges(refs):
    """J904, J905, J906 -> J904–J906 (runs of consecutive numbers with the same prefix)."""
    import re
    parts, out = [], []
    for r in refs:
        m = re.fullmatch(r"([A-Za-z_]*)(\d+)", r)
        parts.append((m.group(1), int(m.group(2)), r) if m else (r, None, r))
    parts.sort(key=lambda p: (p[0], p[1] if p[1] is not None else -1))
    i = 0
    while i < len(parts):
        j = i
        while (j + 1 < len(parts) and parts[i][1] is not None and parts[j + 1][0] == parts[i][0]
               and parts[j + 1][1] == parts[j][1] + 1):
            j += 1
        out.append(parts[i][2] if j - i < 2 else f"{parts[i][2]}–{parts[j][2]}")
        if 0 < j - i < 2:
            out.extend(p[2] for p in parts[i + 1:j + 1])
        i = j + 1
    return ", ".join(out)


def details_view(s, out):
    types = s["cutout_types"]
    names = [n for n in types if any(c["type"] == n for c in s["cutouts"])]
    cell = 330
    cols = min(3, max(1, len(names)))
    rows = math.ceil(len(names) / cols)
    svg = Svg(cols * cell, rows * 315, f'{s["title"]}: panel cutout details')
    for k, name in enumerate(names):
        t = types[name]
        users = [c for c in s["cutouts"] if c["type"] == name]
        refs = ref_ranges([c["ref"] for c in users])
        cx, cy = (k % cols) * cell + cell / 2, (k // cols) * 315
        svg.add(f'<text class="ttl" x="{cx:.2f}" y="{cy + 22}" text-anchor="middle">{t.get("name", name)}</text>')
        svg.add(f'<text class="l" x="{cx:.2f}" y="{cy + 38}" text-anchor="middle">{refs}</text>')
        if t["shape"] == "round":
            v = View(svg, DETAIL_SCALE, cx, cy + 175)
            draw_cutout(v, t, 0, 0)
            v.centre(0, 0, t["d"] * 0.8)
            v.text(0, -t["d"] / 2 - 2.5, f'Ø{fmt(t["d"])}', "t")
            if t.get("screw_square"):
                h = t["screw_square"] / 2
                v.dim_h(-h, h, h, h + 8)
                v.dim_v(-h, h, h, h + 8)
            note = []
            if t.get("screw_square"):
                note.append(f'4× {t.get("screw", "hole")} on {fmt(t["screw_square"])} sq')
            if t.get("flange"):
                note.append(f'flange {fmt(t["flange"])} sq (dashed)')
            v.text(0, -(t.get("flange", t["d"]) / 2) - 5, "; ".join(note), "l")
            continue
        pts, _ = outline(t)
        top_v = max(p[1] for p in pts)
        v = View(svg, DETAIL_SCALE, cx, cy + 105 + top_v * DETAIL_SCALE)
        draw_cutout(v, t, 0, 0, {"near_edge": "up"})
        eu, ev = envelope(t)
        if "seal" in t:
            v.rect(-eu, -ev, eu, ev, "h")
        v.centre(0, 0, eu * 0.6)
        if t["shape"] == "rect":
            v.dim_h(-t["width"] / 2, t["width"] / 2, t["height"] / 2, t["height"] / 2 + 5)
            v.dim_v(-t["height"] / 2, t["height"] / 2, -eu, -eu - 4)
        else:
            near = t["near"]
            v.dim_h(-t["width"] / 2, t["width"] / 2, near, near + 4)
            v.dim_h(-t["tab"] / 2, t["tab"] / 2, near - t["total"], near - t["total"] - 4)
            v.dim_v(near, near - t["full"], -eu, -eu - 4)
            v.dim_v(near, near - t["total"], eu, eu + 4)
            v.dim_v(near, 0, eu, eu + 10)
        if t.get("holes"):
            v.dim_h(-t["holes"] / 2, t["holes"] / 2, 0, -ev - 9)
        # Details are drawn in the cutout's own frame, near edge up; the face views show it as installed.
        svg.add(f'<text class="l" x="{cx:.2f}" y="{cy + 53}" text-anchor="middle">top edge faces the board</text>')
        bits = []
        if t.get("holes"):
            bits.append(f'2× Ø{fmt(t["hole_d"])} on the axis')
        if t.get("corner"):
            bits.append(f'corners R{fmt(t["corner"])}')
        v.text(0, -ev - 15, "; ".join(bits), "l")
        if "seal" in t:
            v.text(0, -ev - 17.3, f'seal area {fmt(t["seal"][0])} × {fmt(t["seal"][1])} min. (dashed)', "l")
    svg.write(out / "enclosure-details.svg")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    s = load_spec(argv[1])
    problems = check(s)
    for p in problems:
        print(f"enclosure check: {p}", file=sys.stderr)
    if "--check" in argv:
        print(f'enclosure check: {len(s["cutouts"])} cutouts, {len(problems)} problems')
        sys.exit(1 if problems else 0)
    if problems:
        sys.exit(1)
    out = Path(argv[2] if len(argv) > 2 else "docs/src/diagrams/build")
    out.mkdir(parents=True, exist_ok=True)
    face_view(s, "top", out)
    stepped = {f for f in ("front", "back", "left", "right")
               if len(top_profile(s, f, False)) > 1 or len(top_profile(s, f, True)) > 1}
    faces = [f for f in FACES if f != "top" and (any(c["face"] == f for c in s["cutouts"]) or f in stepped)]
    for f in faces:
        face_view(s, f, out)
    details_view(s, out)
    o, w = s["outside"], s["wall"]
    cutouts = [{**c, "u": placed(s, c)[0], "v": placed(s, c)[1]} for c in s["cutouts"]]
    s = {**s, "cutouts": cutouts, "engine": ENGINE_VERSION, "views": ["top"] + faces + ["details"],
         "inside": {k: o[k] - 2 * w for k in ("x", "y", "z")}}
    (out / "enclosure.json").write_text(json.dumps(s, indent=1) + "\n")
    print(f"enclosure drawing: {', '.join(s['views'])} -> {out}")


if __name__ == "__main__":
    main(sys.argv)
