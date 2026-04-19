from cmu_graphics import *
from pylsl import StreamInlet, resolve_streams
#start of ai generated exempt code (from line 3 to line 130)

#def band key, def labelsFromInfo,def OpenBandInlet,def connect,def applySample, def isIdle are all exmept code
#The functions mentiond in exempt code are written by AI in order to get the EEG stream working

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
    app.bandsWithSample = frozenset(
    band for band in bandOrder if countByBand[band] > 0
)
def isIdle(app):
    bands = app.bandsWithSample 
    if not bands:
        return True
    return all(
        app.avg[band] <= idleThresholdUv2[band]
        for band in bands
    )
#end of Ai generated code


# Midpoint cutoffs (µV²): mean ≤ threshold → Idle; above → not Idle.
# I had used data from my previous attention study and got a 60% accuracy 
# rate from using these thresholds to distinguish between idle and non-idle states
idleThresholdUv2 = {
    "theta": 4.521,
    "alpha": 1.354,
    "betaL": 0.877,
    "betaH": 0.542,
    "gamma": 0.409,
}


def onAppStart(app):
    app.stepsPerSecond = 60
    app.searchForStream = False

    #exempt code: app variables in relation to EEG Stream
    app.inlet = None
    app.labels = []
    app.order = list(bandOrder)
    app.avg = {}
    app.stepCount = 0
    app.bandsWithSample = frozenset()
    #end of exempt code

    #level app variables
    app.LevelOneCleared = False

    #app variables for UI
    app.labelSpace=70

    #app variables for ball
    app.cx=app.width/2
    app.cy=app.height/2
    app.r=20

    #app variables for squares
    app.squareSpeed = 3
    app.numberOfSquares = 5
    app.squaresize=40
    
    #square spacing logic
    topPadding = 50 
    bottomPadding = 50 
    startY = topPadding + (app.squaresize / 2)
    endY = app.height - app.labelSpace - bottomPadding - (app.squaresize / 2)
    totalRange = endY - startY
    gaps = app.numberOfSquares - 1
    app.squares = []
    for i in range(app.numberOfSquares):
        direction = 1 if (i % 2 == 0) else -1
        app.squares.append({
            'index': i,
            'dir': direction,
            'cx': (app.width / (app.numberOfSquares + 1)) * (i + 1),
            'cy': startY + (totalRange / gaps) * i,
            'size': app.squaresize
        })

    #app variables for square animation
    app.squareSpeed = 2 
    app.squareDirection = 1

    #app variables used for alternative keyboard control
    app.fPressed = False


def onKeyPress(app,key):
    if key == 's':
        app.searchForStream = not app.searchForStream

def onKeyHold(app,keys):
    if 'f' in keys:
        app.fPressed = True

def onKeyRelease(app,key):
    if key == 'f':
        app.fPressed = False

def onStep(app):
    # --- EEG / Stream Logic (Exempt Code) ---
    app.stepCount += 1
    if app.searchForStream and not app.inlet and (
        app.stepCount == 1 or app.stepCount % connectRetryInterval == 0
    ):
        connect(app, retryResolveWait if app.stepCount > 1 else None)
    
    if app.inlet is not None:
        while True:
            sample = app.inlet.pull_sample(timeout=0.0)[0]
            if sample is None: break
            applySample(app, sample)
    # --- End of Exempt Code ---

    # Call the actual game mechanics
    takeStep(app)

def takeStep(app):
    #square animation logic    
    for square in app.squares:
        square['cx'] += app.squareSpeed * square['dir']
        if square['cx'] - square['size']/2 > app.width:
            square['cx'] = -square['size']/2
        elif square['cx'] + square['size']/2 < 0:
            square['cx'] = app.width + square['size']/2

    #square and circle collision logic
    for square in app.squares[:]:
        squareLeft = square['cx'] - square['size']/2
        squareRight = square['cx'] + square['size']/2
        squareTop = square['cy'] - square['size']/2
        squareBottom = square['cy'] + square['size']/2

        if (app.cx + app.r > squareLeft and app.cx - app.r < squareRight and
            app.cy + app.r > squareTop and app.cy - app.r < squareBottom):
            app.squares.remove(square)
    if len(app.squares) == 0:
        app.LevelOneCleared = True

    #the following is ai generated exempt code used to detect EEG stream
    app.stepCount += 1
    if app.searchForStream and not app.inlet and (
        app.stepCount == 1 or app.stepCount % connectRetryInterval == 0
    ):
        connect(app, retryResolveWait if app.stepCount > 1 else None)
    if app.inlet is not None:
        while True:
            sample = app.inlet.pull_sample(timeout=0.0)[0]
            if sample is None: break
            applySample(app, sample)
     #end of exempt code


    if app.inlet is not None:
        idle = isIdle(app)
    else:
        idle = not app.fPressed

    if idle: 
        if app.cy + app.r < (app.height - app.labelSpace):
            app.cy += 5
        else:
            app.cy = app.height - app.labelSpace - app.r
    else:
        if app.cy - app.r > 0:
            app.cy -= 5
        else:
            app.cy = app.r


def redrawAll(app):
    drawLabel("press s to switch to EEG stream",app.width-100,app.height-20,size=12,font='arial')
    drawLabel("press f to move ball up",app.width-100,app.height-40,size=12,font='arial')
    if app.LevelOneCleared == True:
        drawLabel("Level One Cleared!",app.width/2,app.height/2,size=30,font='arial', fill='pink')

    for square in app.squares:
        left = square['cx'] - square['size']/2
        top = square['cy'] - square['size']/2
        drawRect(left, top, square['size'], square['size'], border='black', fill=None)

    drawCircle(app.cx,app.cy,app.r,fill='cyan')
    


runApp(500, 500)
