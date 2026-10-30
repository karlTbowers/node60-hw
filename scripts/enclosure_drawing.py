#!/usr/bin/env python3
"""Generate Node60's dimensioned enclosure drawing (DEC-020) as SVG views.

Every number comes from enclosure_geometry.py, which reads the board and
connector positions from place_connectors.py, so the drawing follows the PCB.
Third-angle views, millimetres. The docs build runs this:

    python3 scripts/enclosure_drawing.py docs/src/diagrams/build

and writes enclosure-<view>.svg plus enclosure.json (key dimensions for the
page's table). The site shows diagrams on a white panel in both themes, so the
views use fixed dark ink.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from enclosure_geometry import geometry  # noqa: E402

FONT = 12          # px
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


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class View:
    """Maps model mm to SVG px: u right, v up (flip) and a fixed scale."""

    def __init__(self, svg, scale, ox, oy):
        self.svg, self.s, self.ox, self.oy = svg, scale, ox, oy

    def p(self, u, v):
        return self.ox + self.s * u, self.oy - self.s * v

    def rect(self, u0, v0, u1, v1, cls="o", r=0.0):
        (x0, y0), (x1, y1) = self.p(u0, v1), self.p(u1, v0)
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

    def text(self, u, v, s, cls="t", anchor="middle", dx=0, dy=0, rot=0):
        x, y = self.p(u, v)
        x, y = x + dx, y + dy
        tr = f' transform="rotate({rot} {x:.2f} {y:.2f})"' if rot else ""
        self.svg.add(f'<text class="{cls}" x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}"{tr}>{s}</text>')

    def poly(self, pts, radii, cls="o"):
        """Closed polygon (model coords) with a fillet radius per vertex."""
        self.svg.add(f'<path class="{cls}" d="{rounded_path([self.p(*q) for q in pts], [r * self.s for r in radii])}"/>')

    # Dimensions -------------------------------------------------------------
    def dim_h(self, u0, u1, v_feat, v_dim, text=None):
        """Horizontal dimension between u0 and u1, dimension line at v_dim."""
        for u in (u0, u1):
            self.line(u, v_feat, u, v_dim + math.copysign(1.5 / self.s * 2, v_dim - v_feat))
        (x0, y), (x1, _) = self.p(u0, v_dim), self.p(u1, v_dim)
        self.svg.add(f'<line class="d" x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" '
                     'marker-start="url(#ar)" marker-end="url(#ar)"/>')
        self.svg.add(f'<text class="t" x="{(x0 + x1) / 2:.2f}" y="{y - 4:.2f}" text-anchor="middle">'
                     f'{text or fmt(abs(u1 - u0))}</text>')

    def dim_v(self, v0, v1, u_feat, u_dim, text=None):
        for v in (v0, v1):
            self.line(u_feat, v, u_dim + math.copysign(1.5 / self.s * 2, u_dim - u_feat), v)
        (x, y0), (_, y1) = self.p(u_dim, v0), self.p(u_dim, v1)
        self.svg.add(f'<line class="d" x1="{x:.2f}" y1="{y0:.2f}" x2="{x:.2f}" y2="{y1:.2f}" '
                     'marker-start="url(#ar)" marker-end="url(#ar)"/>')
        ym = (y0 + y1) / 2
        self.svg.add(f'<text class="t" x="{x - 4:.2f}" y="{ym:.2f}" text-anchor="middle" '
                     f'transform="rotate(-90 {x - 4:.2f} {ym:.2f})">{text or fmt(abs(v1 - v0))}</text>')

    def ordinate_u(self, datum, us, v_feat, v_line):
        """Ordinate dimensions along u from datum; vertical text at v_line, spread apart when close."""
        us = [datum] + sorted(us, key=lambda u: abs(u - datum))
        xs = [self.p(u, v_line)[0] for u in us]
        tx = spread(xs) if xs[-1] >= xs[0] else [-x for x in spread([-x for x in xs])]
        down = v_line < v_feat
        for i, (u, x, t) in enumerate(zip(us, xs, tx)):
            self.line(u, v_feat, u, v_line)
            _, y = self.p(u, v_line)
            y2 = y + (6 if down else -6)
            self.svg.add(f'<line class="d" x1="{x:.2f}" y1="{y:.2f}" x2="{t:.2f}" y2="{y2:.2f}"/>')
            yy = y2 + (3 if down else -3)
            self.svg.add(f'<text class="t" x="{t + 4:.2f}" y="{yy:.2f}" text-anchor="{"end" if down else "start"}" '
                         f'transform="rotate(-90 {t + 4:.2f} {yy:.2f})">{fmt(abs(u - datum)) if i else "0"}</text>')

    def ordinate_v(self, datum, vs, u_feat, u_line):
        """Ordinate dimensions along v from datum; text at u_line, spread apart when close."""
        vs = [datum] + sorted(vs)
        ys = [self.p(u_line, v)[1] for v in vs]
        ty = [-y for y in spread([-y for y in ys])]
        left = u_line < u_feat
        for i, (v, y, t) in enumerate(zip(vs, ys, ty)):
            self.line(u_feat, v, u_line, v)
            x, _ = self.p(u_line, v)
            x2 = x + (-6 if left else 6)
            self.svg.add(f'<line class="d" x1="{x:.2f}" y1="{y:.2f}" x2="{x2:.2f}" y2="{t:.2f}"/>')
            self.svg.add(f'<text class="t" x="{x2 + (-3 if left else 3):.2f}" y="{t + 4:.2f}" '
                         f'text-anchor="{"end" if left else "start"}">{fmt(v - datum) if i else "0"}</text>')

    def title(self, text, y=22):
        self.svg.add(f'<text class="ttl" x="{self.ox:.2f}" y="{y}" text-anchor="start">{text}</text>')


def spread(ps, gap=12.0):
    """Push sorted label positions (px) apart to at least gap, keeping their order."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out = list(ps)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out


def rounded_path(pts, radii):
    """SVG path for a closed polygon with per-vertex fillets (screen coords)."""
    n, segs = len(pts), []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        r = radii[i]
        a = (p0[0] - p1[0], p0[1] - p1[1])
        b = (p2[0] - p1[0], p2[1] - p1[1])
        la, lb = math.hypot(*a), math.hypot(*b)
        if r <= 0 or la == 0 or lb == 0:
            segs.append(("L", p1, None))
            continue
        ua, ub = (a[0] / la, a[1] / la), (b[0] / lb, b[1] / lb)
        ang = math.acos(max(-1, min(1, ua[0] * ub[0] + ua[1] * ub[1])))
        t = min(r / math.tan(ang / 2), la / 2, lb / 2)
        r = t * math.tan(ang / 2)
        s = (p1[0] + ua[0] * t, p1[1] + ua[1] * t)
        e = (p1[0] + ub[0] * t, p1[1] + ub[1] * t)
        sweep = 1 if (ua[0] * ub[1] - ua[1] * ub[0]) < 0 else 0
        segs.append(("A", s, (e, r, sweep)))
    d = []
    for kind, p, arc in segs:
        d.append(f"{'M' if not d else 'L'}{p[0]:.2f} {p[1]:.2f}")
        if kind == "A":
            e, r, sweep = arc
            d.append(f"A{r:.2f} {r:.2f} 0 0 {sweep} {e[0]:.2f} {e[1]:.2f}")
    return " ".join(d) + " Z"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.title, self.items = w, h, title, []

    def add(self, s):
        self.items.append(s)

    def write(self, path):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:.0f} {self.h:.0f}" '
                f'width="{self.w:.0f}" height="{self.h:.0f}" style="max-width:{self.w:.0f}px" role="img" '
                f'aria-label="{self.title}">'
                f'<title>{self.title}</title>{STYLE}'
                '<defs><marker id="ar" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" '
                'orient="auto-start-reverse"><path class="a" d="M0 1.5 L10 5 L0 8.5 Z"/></marker></defs>')
        Path(path).write_text(head + "\n".join(self.items) + "</svg>\n")


# Cutout outlines in their own frame: u across, w from the edge nearest the board
# (installed upside down, so w grows downward in the enclosure).
def cutout_pts(c):
    hw, ht = c["width"] / 2, c["tab"] / 2
    pts = [(-hw, 0), (hw, 0), (hw, c["full"]), (ht, c["full"]), (ht, c["total"]), (-ht, c["total"]),
           (-ht, c["full"]), (-hw, c["full"])]
    narrow_tab = c["tab"] < c["width"]
    r = c["corner"]
    radii = [r, r, r if narrow_tab else 0.8, 0.8, 0.8 if narrow_tab else r, 0.8 if narrow_tab else r,
             0.8, r if narrow_tab else 0.8]
    return pts, radii


def draw_cutout(v, c, u0, z_near, holes=True):
    """Header cutout on a wall view: centre u0, near edge at z_near, far edge below it."""
    pts, radii = cutout_pts(c)
    v.poly([(u0 + u, z_near - w) for u, w in pts], radii)
    if holes:
        for sx in (-1, 1):
            v.circle(u0 + sx * c["holes"] / 2, z_near - (c["axis"] - c["near"]), c["hole_d"])


# Views -----------------------------------------------------------------------
def view_top(g, out):
    s, m = 2.6, 70
    L, Dp = g["outside"]["x"], g["outside"]["y"]
    svg = Svg(L * s + 2 * m + 40, Dp * s + 2 * m + 50, "Node60 enclosure, top view (lid)")
    v = View(svg, s, m + 30, m + 40 + Dp * s)
    sur = g["parts"]["SURLOK"]
    v.rect(0, 0, L, Dp)
    w = g["assumptions"]["wall"]
    v.rect(w, w, L - w, Dp - w, "h")
    b = g["board"]
    v.rect(b["x0"], b["y0"], b["x1"], b["y1"], "h")
    for t in g["lid"]:
        v.circle(t["x"], t["y"], sur["cutout_d"])
        h = sur["screw_square"] / 2
        for sx in (-1, 1):
            for sy in (-1, 1):
                v.circle(t["x"] + sx * h, t["y"] + sy * h, 4.0)
        v.rect(t["x"] - sur["flange"] / 2, t["y"] - sur["flange"] / 2, t["x"] + sur["flange"] / 2,
               t["y"] + sur["flange"] / 2, "h")
        v.centre(t["x"], t["y"], 17)
        v.text(t["x"], t["y"] + sur["flange"] / 2 + 3, f'{t["ref"]} {t["net"]}', "l")
    xs = sorted({t["x"] for t in g["lid"]})
    ys = sorted({t["y"] for t in g["lid"]})
    v.ordinate_u(0, xs, 0, -14)
    v.ordinate_v(0, ys, 0, -10)
    v.dim_h(0, L, Dp, Dp + 12)
    v.dim_v(0, Dp, L, L + 12)
    v.title("TOP VIEW: LID, seen from above (front face at the bottom)")
    svg.write(out / "enclosure-top.svg")


def view_front(g, out):
    s, m = 2.6, 60
    L, H = g["outside"]["x"], g["outside"]["z"]
    at = g["parts"]["AT13"]
    svg = Svg(L * s + 2 * m + 60, H * s + 2 * m + 70, "Node60 enclosure, front view")
    v = View(svg, s, m + 40, m + 30 + H * s)
    v.rect(0, 0, L, H)
    z = g["z"]
    v.line(0, z["floor_inner"], L, z["floor_inner"], "h")
    v.line(0, z["lid_inner"], L, z["lid_inner"], "h")
    b = g["board"]
    v.rect(b["x0"], b["z_component_side"], b["x1"], b["z_back_face"], "h")
    for o in g["outputs"]:
        draw_cutout(v, at, o["x"], b["z_component_side"] - at["near"])
        v.centre(o["x"], o["z"], 14)
        v.text(o["x"], H + 3, f'{o["ref"]} {o["label"]}', "l")
    v.ordinate_u(0, [o["x"] for o in g["outputs"]], 0, -12)
    v.ordinate_v(0, [g["outputs"][0]["z"], b["z_component_side"], b["z_back_face"], z["lid_inner"], H], 0, -10)
    v.dim_h(0, L, H, H + 16)
    v.title("FRONT VIEW: OUTPUTS (cutouts upside down: key toward the floor)")
    svg.write(out / "enclosure-front.svg")


def view_sides(g, out):
    s, m = 2.6, 60
    Dp, H = g["outside"]["y"], g["outside"]["z"]
    atm = g["parts"]["ATM13"]
    row = H * s + 2 * m + 40                                           # one view per row
    svg = Svg(Dp * s + 2 * m + 100, 2 * row, "Node60 enclosure, left and right views")
    b, z = g["board"], g["z"]
    for k, t in enumerate(sorted(g["t1s"], key=lambda t: t["face"])):   # left, then right
        v = View(svg, s, m + 40, k * row + m + 30 + H * s)
        left = t["face"] == "left"
        u = (lambda y: Dp - y) if left else (lambda y: y)                  # front on the right / left
        v.rect(0, 0, Dp, H)
        v.line(0, z["floor_inner"], Dp, z["floor_inner"], "h")
        v.line(0, z["lid_inner"], Dp, z["lid_inner"], "h")
        v.rect(min(u(b["y0"]), u(b["y1"])), b["z_component_side"], max(u(b["y0"]), u(b["y1"])), b["z_back_face"], "h")
        draw_cutout(v, atm, u(t["y"]), b["z_component_side"] - atm["near"])
        v.centre(u(t["y"]), t["z"], 14)
        v.text(u(t["y"]), H + 3, f'{t["ref"]} {t["label"]}', "l")
        v.dim_h(u(t["y"]), u(0), 0, -12)
        heights = [t["z"], b["z_component_side"], b["z_back_face"], z["lid_inner"], H]
        v.ordinate_v(0, heights, 0, -10) if left else v.ordinate_v(0, heights, Dp, Dp + 10)
        v.title("LEFT VIEW (front face on the right)" if left else "RIGHT VIEW (front face on the left)",
                y=k * row + 22)
    svg.write(out / "enclosure-sides.svg")


def view_details(g, out):
    s, cell = 6.0, 330
    svg = Svg(3 * cell, 300, "Node60 enclosure, panel cutout details")
    for k, (name, c) in enumerate((("AT13-2P-BM04 (J904–J909)", g["parts"]["AT13"]),
                                   ("ATM13-2P-BM04 (J903, J912)", g["parts"]["ATM13"]))):
        v = View(svg, s, k * cell + cell / 2, 90)
        near = 0.0
        pts, radii = cutout_pts(c)
        v.poly([(u, near - w) for u, w in pts], radii)
        za = near - (c["axis"] - c["near"])
        for sx in (-1, 1):
            v.circle(sx * c["holes"] / 2, za, c["hole_d"])
        sw, sh = c["seal"]
        v.rect(-sw / 2, za - sh / 2, sw / 2, za + sh / 2, "h")
        v.centre(0, za, 20)
        v.dim_h(-c["width"] / 2, c["width"] / 2, near, near + 4)
        v.dim_h(-c["holes"] / 2, c["holes"] / 2, za, za - sh / 2 - 9)
        v.dim_h(-c["tab"] / 2, c["tab"] / 2, near - c["total"], near - c["total"] - 4)
        v.dim_v(near, near - c["full"], -sw / 2, -sw / 2 - 4)
        v.dim_v(near, near - c["total"], sw / 2, sw / 2 + 4)
        v.dim_v(near, za, sw / 2, sw / 2 + 10)
        svg.add(f'<text class="ttl" x="{v.ox:.2f}" y="22" text-anchor="middle">{name}</text>')
        svg.add(f'<text class="l" x="{v.ox:.2f}" y="38" text-anchor="middle">top edge faces the board</text>')
        v.text(0, za - sh / 2 - 15, f'2× Ø{fmt(c["hole_d"])} on the axis; corners R{fmt(c["corner"])}', "l")
        v.text(0, za - sh / 2 - 17.3, f'seal area {fmt(sw)} × {fmt(sh)} min. (dashed)', "l")
    sur = g["parts"]["SURLOK"]
    v = View(svg, s, 2 * cell + cell / 2, 200)
    v.circle(0, 0, sur["cutout_d"])
    h = sur["screw_square"] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            v.circle(sx * h, sy * h, 4.0)
    v.rect(-sur["flange"] / 2, -sur["flange"] / 2, sur["flange"] / 2, sur["flange"] / 2, "h")
    v.centre(0, 0, 17)
    v.dim_h(-h, h, h, h + 8)
    v.dim_v(-h, h, h, h + 8)
    v.text(0, -sur["cutout_d"] / 2 - 2.5, f'Ø{fmt(sur["cutout_d"])}', "t")
    svg.add(f'<text class="ttl" x="{v.ox:.2f}" y="22" text-anchor="middle">SurLok Plus 5.7 mm (lid)</text>')
    v.text(0, -sur["flange"] / 2 - 4, f'4× M4 on {fmt(sur["screw_square"])} sq; flange {fmt(sur["flange"])} sq (dashed)', "l")
    svg.write(out / "enclosure-details.svg")


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    g = geometry()
    view_top(g, out)
    view_front(g, out)
    view_sides(g, out)
    view_details(g, out)
    (out / "enclosure.json").write_text(json.dumps(g, indent=1) + "\n")
    print(f"enclosure drawing: {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/src/diagrams/build")
