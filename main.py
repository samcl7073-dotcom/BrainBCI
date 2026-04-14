import math
import os
from collections import defaultdict

os.environ.setdefault("CI", "1")
from cmu_graphics import *
from pylsl import StreamInlet, resolve_streams

bandOrder = ("theta", "alpha", "betaL", "betaH", "gamma")
lslResolveSeconds, lslRetrySeconds, lslRetryEverySteps = 12.0, 6.0, 40
skipLabels = frozenset({"timestamp", "counter", "interpolate", "hardwaremarker", "markers"})
epocXSensors = (
    "AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4",
)
sensorCanon = {s.upper(): s for s in epocXSensors}


def canonicalSensor(raw):
    text = (raw or "").strip()
    return sensorCanon.get(text.upper(), text)


def canonicalBand(band):
    low = band.strip().lower()
    return next((x for x in bandOrder if x.lower() == low), band.strip())


def bandsFrom(labels):
    foundBands = set()
    for labelRow in labels:
        text = (labelRow or "").strip()
        if "/" not in text:
            continue
        bandKey = canonicalBand(text.split("/", 1)[1])
        if bandKey:
            foundBands.add(bandKey)
    return sorted(foundBands, key=lambda x: (bandOrder.index(x) if x in bandOrder else 99, x))


def openInlet(stream, timeoutSec=15.0):
    inlet = StreamInlet(stream, max_buflen=360, max_chunklen=0, recover=True)
    info = inlet.info(timeout=max(10.0, float(timeoutSec)))
    channelsRoot = info.desc().child("channels")
    if channelsRoot.empty():
        return inlet, [str(i) for i in range(info.channel_count())]
    labelList, channelNode = [], channelsRoot.child("channel")
    for _ in range(info.channel_count()):
        labelList.append(
            str(len(labelList))
            if channelNode.empty()
            else (channelNode.child_value("label") or str(len(labelList)))
        )
        channelNode = channelNode.next_sibling()
    return inlet, labelList


def connectLSL(timeoutSeconds=None):
    waitSeconds = float(lslResolveSeconds if timeoutSeconds is None else timeoutSeconds)
    shortSuffix = " Start LSL (Band Power) in Emotiv." if waitSeconds < lslResolveSeconds else ""
    metaTimeout = max(10.0, min(waitSeconds, 22.0))
    try:
        candidates = list(
            {(i.name(), i.source_id()): i for i in resolve_streams(wait_time=waitSeconds)}.values()
        )
        if not candidates:
            return None, [], f"No LSL streams found.{shortSuffix} Start the outlet on this machine."
        lastMessage = "No stream had SENSOR/band labels."
        for streamInfo in candidates[:24]:
            try:
                inlet, labels = openInlet(streamInfo, metaTimeout)
            except Exception as err:  # pylint: disable=broad-except
                lastMessage = f"Open failed {streamInfo.name()!r}: {err}{shortSuffix}"
                continue
            bandNames = bandsFrom(labels)
            if not bandNames:
                del inlet
                lastMessage = f"{streamInfo.name()!r}: no SENSOR/band labels.{shortSuffix}"
                continue
            return (
                inlet,
                labels,
                f"{streamInfo.name()} — {len(labels)} ch @ {streamInfo.nominal_srate()} Hz",
            )
        return None, [], f"{lastMessage} (tried up to 24 streams)"
    except Exception as err:  # pylint: disable=broad-except
        return None, [], f"LSL error ({err}).{shortSuffix}"


def parseSample(labels, sample, bandOrderArg):
    bySensor = defaultdict(dict)
    for labelRow, rawValue in zip(labels, sample):
        key = (labelRow or "").strip()
        if key.lower() in skipLabels or "/" not in key:
            continue
        sensorPart, bandPart = key.split("/", 1)
        sensorName, bandName = canonicalSensor(sensorPart.strip()), bandPart.strip()
        if not sensorName or not bandName:
            continue
        try:
            floatValue = float(rawValue)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(floatValue):
            continue
        bySensor[sensorName][canonicalBand(bandName)] = floatValue

    def averageForBand(band):
        values = [bySensor[s][band] for s in bySensor if band in bySensor[s]]
        return sum(values) / len(values) if values else 0.0

    return {band: averageForBand(band) for band in bandOrderArg}


def onAppStart(app):
    app.stepsPerSecond = 60
    app.inlet, app.labels = None, []
    app.status = "Starting…"
    app.bandOrder = list(bandOrder)
    app.lastAvgs = {}
    app._stepI, app._lslInitialConnectPending = 0, True
    app.samplesReceived = 0


def applyConnect(app, inlet, labels, status):
    app.status = status
    if inlet is None:
        return
    app.inlet, app.labels = inlet, labels
    bandList = bandsFrom(labels)
    bandOrderSet = set(bandList)
    app.bandOrder = [x for x in bandOrder if x in bandOrderSet] or (bandList or list(bandOrder))
    app.samplesReceived, app.lastAvgs = 0, {}


def onStep(app):
    app._stepI += 1
    if app._lslInitialConnectPending:
        app._lslInitialConnectPending = False
        app.status = "Searching for LSL…"
        applyConnect(app, *connectLSL())
    if app.inlet is None:
        if app._stepI % lslRetryEverySteps == 0:
            app.status = "Still searching…"
            applyConnect(app, *connectLSL(lslRetrySeconds))
        return
    try:
        while True:
            sample, _ = app.inlet.pull_sample(timeout=0.0)
            if sample is None:
                break
            if len(sample) != len(app.labels):
                continue
            app.lastAvgs = parseSample(app.labels, sample, app.bandOrder)
            app.samplesReceived += 1
    except Exception:  # pylint: disable=broad-except
        pass


def formatBandNumber(rawValue):
    try:
        x = float(rawValue)
        return f"{x:.10g}" if math.isfinite(x) else "-"
    except (TypeError, ValueError):
        return "-"


def redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill="black")
    marginX, lineY, lineHeight = 12, 10, 22
    if app.inlet is None:
        drawLabel(str(app.status), marginX, lineY, size=12, fill="white", align="left")
        return
    bandsToDraw = list(app.bandOrder)
    if not bandsToDraw:
        return
    waitingForFirstSample = app.samplesReceived == 0
    averages = app.lastAvgs
    for bandName in bandsToDraw:
        displayNumber = "-" if waitingForFirstSample else formatBandNumber(averages.get(bandName))
        drawLabel(f"{bandName}  {displayNumber}", marginX, lineY, size=16, fill="white", align="left")
        lineY += lineHeight


runApp(400, 200)