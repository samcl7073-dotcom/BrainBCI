from cmu_graphics import *
from pylsl import StreamInlet, resolve_streams
#resolve_streams: scans local network (WiFi or Bluetooth) for active data streams. 
#Returns a list of every device found

#StreamInlet:creates the connection that allows script to read data

bandOrder = ("theta", "alpha", "betaL", "betaH", "gamma")
#brainwave categories

#configuration constants
initialResolveWait = 12.0
#number of seconds the script will wait at appstart to find a brainwave stream. 
#EEG devices often have a bit of lag when connecting
retryResolveWait = 6.0
# If the initial connection fails, the script becomes slightly more aggressive.
# When it tries again later, it only waits 6 seconds for a response to keep the app 
# from freezing for too long.
connectRetryInterval = 40
# measured in frames (steps). 
# Since the app runs at 60 frames per second, 
# this tells the script to try reconnecting roughly every 0.66 seconds if the connection is lost.

bandSet = frozenset(bandOrder)
#converts list of brainwaves (theta, alpha, etc.) into a unchangable set


def bandKey(labelText):
    # finds bandKey from labelText from stream
    # e.g. "EEG/Alpha": extracts just the word "alpha"

    stripped = (labelText or "").strip()
    if "/" not in stripped:
        return None
    #a stream might send labels formatted like this:EEG/Alpha
    tail = stripped.split("/", 1)[1].strip()
    # tail=the part after the first slash. 
    # If it finds EEG/Alpha, it splits the string to grab Alpha. 
    # If there is no slash, the split("/", 1)[1] command on the next line would crash 
    # the program because there would be no "second part" to grab.
    for name in bandOrder:
        if name.lower() == tail.lower():
            return name  # Found a match, exit the function early   
    return tail


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
    #The Handshake
    #checks if the stream found on the network is actually a brainwave stream
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
    #
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
    #must define app.inlet as None onAppStart
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
    #calculates average for each band
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
        #grabs the latest bit of electricity data from the buffer.
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
