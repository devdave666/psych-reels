"""Forward-kinematics stick-figure rig (pycairo). Poses are dicts: lean + two legs + two arms, each limb (angle, bend)."""
import math

import cairo

L_TORSO, L_ARM1, L_ARM2, L_LEG1, L_LEG2, HEAD_R = 90.0, 52.0, 52.0, 64.0, 64.0, 30.0


def clamp(x, lo=0.0, hi=1.0):
    return min(hi, max(lo, x))


def smooth(x):
    x = clamp(x)
    return x * x * x * (x * (6 * x - 15) + 10)


def lerp(a, b, t):
    return a + (b - a) * t


def P(lean, legA, legB, armA, armB):
    return dict(lean=lean, legA=legA, legB=legB, armA=armA, armB=armB)


STANCE = P(0.15, (0.55, 0.7), (-0.5, 0.6), (0.9, 1.6), (0.5, 1.9))
SIT = P(0.38, (1.0, 1.7), (0.85, 1.6), (0.55, 0.5), (0.35, 0.5))            # slumped, forearms on knees
HANDS_ON_KNEES = P(0.55, (0.4, 0.55), (-0.1, 0.5), (0.45, 0.15), (0.3, 0.15))
AIR = P(0.1, (0.9, 1.3), (-0.3, 1.1), (2.6, 0.3), (2.2, 0.3))
CHEER = P(-0.05, (0.1, 0.1), (-0.1, 0.1), (2.3, 0.2), (-2.3, -0.2))             # arms in a V, clear of the head
HOP = P(0.05, (0.9, 1.3), (-0.3, 1.1), (2.3, 0.2), (-2.3, -0.2))


def lerp_pose(a, b, u):
    out = {"lean": lerp(a["lean"], b["lean"], u)}
    for k in ("legA", "legB", "armA", "armB"):
        out[k] = (lerp(a[k][0], b[k][0], u), lerp(a[k][1], b[k][1], u))
    return out


def walk_pose(ph, amp, knee, arm, lean):
    def leg(p):
        return amp * math.sin(2 * math.pi * p), 0.1 + knee * max(0.0, math.cos(2 * math.pi * p))

    def arms(p):
        return -arm * math.sin(2 * math.pi * p), 0.5 + 0.4 * (arm > 0.7)

    return P(lean, leg(ph), leg(ph + 0.5), arms(ph), arms(ph + 0.5))


def idle_pose(t):
    b = 0.03 * math.sin(t * 2.2)
    return P(0.0, (0.08, 0.05), (-0.08, 0.05), (0.12 + b, 0.25), (-0.12 - b, 0.25))


def blend(pairs):
    s = sum(w for w, _ in pairs)
    pairs = [(w / s, p) for w, p in pairs if w > 0]
    out = {"lean": sum(w * p["lean"] for w, p in pairs)}
    for k in ("legA", "legB", "armA", "armB"):
        out[k] = (sum(w * p[k][0] for w, p in pairs), sum(w * p[k][1] for w, p in pairs))
    return out


def limb(a, k, l1, l2):
    a2 = a - k
    return (l1 * math.sin(a) + l2 * math.sin(a2), l1 * math.cos(a) + l2 * math.cos(a2)), (l1 * math.sin(a), l1 * math.cos(a))


def joints_from(p, hx, air, mirror=False):
    legs = [limb(*p[k], L_LEG1, L_LEG2) for k in ("legA", "legB")]
    hip_h = max(l[0][1] for l in legs)              # ground-lock the lowest foot
    hy = -hip_h - air
    lean = p["lean"]
    tv = (math.sin(lean), -math.cos(lean))
    neck = (hx + L_TORSO * tv[0], hy + L_TORSO * tv[1])
    head = (neck[0] + (HEAD_R + 6) * tv[0], neck[1] + (HEAD_R + 6) * tv[1])
    sh = (hx + 0.92 * L_TORSO * tv[0], hy + 0.92 * L_TORSO * tv[1])
    limbs = [[(hx, hy), (hx + kn[0], hy + kn[1]), (hx + ft[0], hy + ft[1])] for ft, kn in legs]
    for key in ("armA", "armB"):
        a, e = p[key]
        a2 = a + e
        el = (sh[0] + L_ARM1 * math.sin(a), sh[1] + L_ARM1 * math.cos(a))
        hand = (el[0] + L_ARM2 * math.sin(a2), el[1] + L_ARM2 * math.cos(a2))
        limbs.append([sh, el, hand])
    j = dict(hip=(hx, hy), neck=neck, head=head, limbs=limbs)
    if mirror:
        mx = lambda pt: (2 * hx - pt[0], pt[1])
        j = dict(hip=j["hip"], neck=mx(neck), head=mx(head), limbs=[[mx(q) for q in l] for l in limbs])
    return j


def draw_figure(c, j, color, width=13):
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_source_rgb(*color)
    c.set_line_width(width)
    c.move_to(*j["hip"]); c.line_to(*j["neck"]); c.stroke()
    for pts in j["limbs"]:
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.stroke()
    c.arc(j["head"][0], j["head"][1], HEAD_R, 0, 2 * math.pi)
    c.fill()


def draw_shadow(c, x, air):
    c.save()
    c.translate(x, 4); c.scale(1, 0.12)
    c.arc(0, 0, 70 + air * 0.1, 0, 2 * math.pi)
    c.restore()
    c.set_source_rgba(0, 0, 0, max(0.0, 0.35 - air / 900))
    c.fill()


def catmull(keys, t):
    """Catmull-Rom through (t, v1, v2, ...) keys; returns the tuple of values at t."""
    ts = [k[0] for k in keys]
    if t <= ts[0]:
        return keys[0][1:]
    if t >= ts[-1]:
        return keys[-1][1:]
    i = max(j for j in range(len(ts)) if ts[j] <= t)
    p0, p1 = keys[max(i - 1, 0)], keys[i]
    p2, p3 = keys[i + 1], keys[min(i + 2, len(keys) - 1)]
    u = (t - p1[0]) / (p2[0] - p1[0])
    out = []
    for d in range(1, len(p1)):
        a, b, c, e = p0[d], p1[d], p2[d], p3[d]
        out.append(0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - e) * u * u + (-a + 3 * b - 3 * c + e) * u ** 3))
    return tuple(out)
