import math
import os
from collections import defaultdict

os.environ.setdefault("CI", "1")
from cmu_graphics import *
from pylsl import StreamInlet, resolve_streams

B = ("theta", "alpha", "betaL", "betaH", "gamma")
R0, R1, N = 12.0, 6.0, 40
SK = frozenset({"timestamp", "counter", "interpolate", "hardwaremarker", "markers"})
SC = {x.upper(): x for x in ("AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4")}


def S(r):
    t = (r or "").strip()
    return SC.get(t.upper(), t)


def G(b):
    lo = b.strip().lower()
    return next((x for x in B if x.lower() == lo), b.strip())


def BF(L):
    f = set()
    for r in L:
        t = (r or "").strip()
        if "/" in t and (k := G(t.split("/", 1)[1])):
            f.add(k)
    return sorted(f, key=lambda x: (B.index(x) if x in B else 99, x))


def openInlet(stream, to=15.0):
    inlet = StreamInlet(stream, max_buflen=360, max_chunklen=0, recover=True)
    info = inlet.info(timeout=max(10.0, float(to)))
    chs = info.desc().child("channels")
    if chs.empty():
        return inlet, [str(i) for i in range(info.channel_count())]
    out, ch = [], chs.child("channel")
    for _ in range(info.channel_count()):
        out.append(str(len(out)) if ch.empty() else (ch.child_value("label") or str(len(out))))
        ch = ch.next_sibling()
    return inlet, out


def connectLSL(ts=None):
    w = float(R0 if ts is None else ts)
    m = max(10.0, min(w, 22.0))
    try:
        C = list({(i.name(), i.source_id()): i for i in resolve_streams(wait_time=w)}.values())
        for inf in C[:24]:
            try:
                inlet, lab = openInlet(inf, m)
            except Exception:  # pylint: disable=broad-except
                continue
            if BF(lab):
                return inlet, lab, ""
            del inlet
    except Exception:  # pylint: disable=broad-except
        pass
    return None, [], ""


def parseSample(labels, sample, order):
    by = defaultdict(dict)
    for a, v in zip(labels, sample):
        k = (a or "").strip()
        if k.lower() in SK or "/" not in k:
            continue
        p, q = k.split("/", 1)
        sn, bn = S(p.strip()), q.strip()
        if not sn or not bn:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(fv):
            by[sn][G(bn)] = fv
    return {
        b: (lambda vs: sum(vs) / len(vs) if vs else 0.0)([by[s][b] for s in by if b in by[s]])
        for b in order
    }


def onAppStart(app):
    app.stepsPerSecond = 60
    app.inlet, app.labels, app.status = None, [], ""
    app.bandOrder, app.lastAvgs = list(B), {}
    app._stepI, app._lslInitialConnectPending, app.samplesReceived = 0, True, 0


def applyConnect(app, inlet, lab, st):
    app.status = st
    if not inlet:
        return
    app.inlet, app.labels = inlet, lab
    bl = BF(lab)
    fb = set(bl)
    app.bandOrder = [x for x in B if x in fb] or (bl or list(B))
    app.samplesReceived, app.lastAvgs = 0, {}


def onStep(app):
    app._stepI += 1
    if app._lslInitialConnectPending:
        app._lslInitialConnectPending = False
        applyConnect(app, *connectLSL())
    if not app.inlet:
        if app._stepI % N == 0:
            applyConnect(app, *connectLSL(R1))
        return
    try:
        while True:
            smp, _ = app.inlet.pull_sample(timeout=0.0)
            if smp is None:
                break
            if len(smp) != len(app.labels):
                continue
            app.lastAvgs = parseSample(app.labels, smp, app.bandOrder)
            app.samplesReceived += 1
    except Exception:  # pylint: disable=broad-except
        pass


def redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill="black")
    x, y, d = 12, 10, 22
    if not app.inlet:
        drawLabel(str(app.status), x, y, size=12, fill="white", align="left")
        return
    av, w0 = app.lastAvgs, app.samplesReceived == 0
    for b in app.bandOrder:
        t = "-"
        if not w0:
            try:
                z = float(av.get(b))
                t = f"{z:.10g}" if math.isfinite(z) else "-"
            except (TypeError, ValueError):
                t = "-"
        drawLabel(f"{b}  {t}", x, y, size=16, fill="white", align="left")
        y += d


runApp(400, 200)
