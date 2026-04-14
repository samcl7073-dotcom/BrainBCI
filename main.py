import os

os.environ.setdefault("CI", "1")
from cmu_graphics import *
from pylsl import StreamInlet, resolve_streams

bandOrder = ("theta", "alpha", "betaL", "betaH", "gamma")
initialResolveWait = 12.0
retryResolveWait = 6.0
connectRetryInterval = 40
bandSet = frozenset(bandOrder)


def bandKey(labelText):
    stripped = (labelText or "").strip()
    if "/" not in stripped:
        return None
    tail = stripped.split("/", 1)[1].strip()
    return next(
        (name for name in bandOrder if name.lower() == tail.lower()),
        tail,
    )


def labelsFromInfo(streamInfo):
    channelsNode = streamInfo.desc().child("channels")
    if channelsNode.empty():
        return [str(idx) for idx in range(streamInfo.channel_count())]
    labels, channelNode = [], channelsNode.child("channel")
    for channelIndex in range(streamInfo.channel_count()):
        if channelNode.empty():
            labels.append(str(len(labels)))
        else:
            labelValue = channelNode.child_value("label") or str(len(labels))
            labels.append(labelValue)
        channelNode = channelNode.next_sibling()
    return labels


def openBandedInlet(streamInfo, waitSeconds):
    try:
        inlet = StreamInlet(
            streamInfo, max_buflen=360, max_chunklen=0, recover=True
        )
        infoTimeout = max(10.0, min(waitSeconds, 22.0))
        channelLabels = labelsFromInfo(inlet.info(timeout=infoTimeout))
    except Exception:
        return None
    if not any(bandKey(labelStr) in bandSet for labelStr in channelLabels):
        return None
    return inlet, channelLabels


def connect(app, ts=None):
    waitSeconds = float(initialResolveWait if ts is None else ts)
    resolved = resolve_streams(wait_time=waitSeconds)
    streamsById = {
        (streamInfo.name(), streamInfo.source_id()): streamInfo
        for streamInfo in resolved
    }
    for streamInfo in list(streamsById.values())[:24]:
        pair = openBandedInlet(streamInfo, waitSeconds)
        if pair is None:
            continue
        inlet, channelLabels = pair
        app.inlet = inlet
        app.labels = channelLabels
        app.order = list(bandOrder)
        app.avg = {}
        return


def onAppStart(app):
    app.stepsPerSecond = 60
    app.inlet = None
    app.labels = []
    app.order = list(bandOrder)
    app.avg = {}
    app.stepCount = 0


def applySample(app, sample):
    if len(sample) != len(app.labels):
        return
    sumByBand = {band: 0.0 for band in bandOrder}
    countByBand = {band: 0 for band in bandOrder}
    for channelLabel, value in zip(app.labels, sample):
        bandName = bandKey(channelLabel)
        if bandName in bandSet:
            sumByBand[bandName] += float(value)
            countByBand[bandName] += 1
    app.avg = {
        band: sumByBand[band] / countByBand[band]
        if countByBand[band]
        else 0.0
        for band in bandOrder
    }


def onStep(app):
    app.stepCount += 1
    if not app.inlet and (
        app.stepCount == 1 or app.stepCount % connectRetryInterval == 0
    ):
        connect(app, retryResolveWait if app.stepCount > 1 else None)
    if not app.inlet:
        return
    while True:
        sample = app.inlet.pull_sample(timeout=0.0)[0]
        if sample is None:
            break
        applySample(app, sample)


def redrawAll(app):
    if not app.inlet:
        return
    labelX, labelY, lineSpacing = 12, 10, 22
    for rowIndex, bandName in enumerate(app.order):
        drawLabel(
            f"{bandName}  {app.avg.get(bandName, '-')}",
            labelX,
            labelY + rowIndex * lineSpacing,
            size=16,
            fill="black",
            align="left",
        )


runApp(400, 200)
