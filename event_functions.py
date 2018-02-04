def applyOut(ev):
    """test"""
    outs = set(('Strikeout', 'Groundout', 'Bunt Groundout', 'Bunt Lineout', 'Lineout',
               'Grounded Into DP', 'Field Error', 'Forceout', 'Fielders Choice Out',
               'Double Play', 'Triple Play', 'Strikeout - DP', 'Pop Out', 'Flyout',
               'Bunt Pop Out', 'Fielders Choice', 'Grounded Into DP'))

    try:
      if ev['event'] in outs:
          h = True
      else:
          h = False
      return h
    except NameError:
        print "PARSE ERROR"


def getSlugging(events):

    """Will compute the slugging percentage at the end of all these events"""
    numBases = {'Single' : 1, 'Double' : 2, 'Triple' : 3, 'Home Run' : 4}

    bases = 0
    for i in list(events[events.Hit == True].event):
        try:
            val = numBases[i]
        except KeyError:
            val = 0
        bases += val

    if (np.sum(events.Hit) + np.sum(events.Out)) == 0:
        return 0.0
    else:
        return float(bases)/float(np.sum(events.Hit) + np.sum(events.Out))


def getIP(events):

    dps = set(('Grounded Into DP', 'Strikeout - DP', 'Double Play'))

    outs = events[events.Out == True]

    twoOuts = np.sum(outs.event.isin(dps))

    return (float(len(outs))/3. + twoOuts/3.)


def getFIP(events):

    ip = getIP(events)
    hr = len(events[events.event == 'Home Run'])
    BB = len( events[ (events.event == 'Walk') | (events.event == 'Intent Walk') ] )
    HBP = len( events[ events.event == 'Hit By Pitch' ])
    k = len( events[ (events.event == 'Strikeout') | (events.event == 'Strikeout - DP') ])

    cFIP = 3.136888328037377

    if float(ip) == 0.0:
        return cFIP

    fip = ((13. * hr + 3 * (BB + HBP) - 2*k) / float(ip)) + cFIP

    return fip


def applyStats(events):

    events.reset_index(drop=True, inplace=True)

    for i, t in events.iterrows():
        events.loc[i, 'FIP'] = getFIP(events.truncate(after=i))
        events.loc[i, 'SluggingPCT'] = getSlugging(events.truncate(after=i))

    return events


def getHRData(events, idx):
    """ Extract features and target data for home run data, will only generate 
        data for events BELOW idx"""
    import numpy as np

    sub_events = events.truncate(before=idx)
    x = np.zeros((len(events) - idx, 3))
    y = np.zeros((len(events) - idx, ))

    cnt = 0
    for i, t in sub_events.iterrows():

        curr_batter = t.batter
        curr_pitcher = t.pitcher
        curr_gameid = t.game_id
        curr_pitcher_hand = t.PitcherHand
        curr_batter_hand = t.BatterHand
   
        # we want the splits

        events_batter = events[ (events.batter == curr_batter) & (events.PitcherHand == curr_pitcher_hand) ].truncate(after=i)
        

        if curr_pitcher_hand == 'R':
            events_pitcher = events[ (events.pitcher == curr_pitcher) & ( (events.BatterHand == 'L') | (events.BatterHand == 'S'))].truncate(after=i)
        else:
            events_pitcher = events[ (events.pitcher == curr_pitcher) & ( (events.BatterHand == 'R') | (events.BatterHand == 'S'))].truncate(after=i)

        #print events_batter

        events_pitcher = events[events.pitcher == curr_pitcher].truncate(after=i)
        x[cnt, 0] = getSlugging(events_batter)
        x[cnt, 1] = getSlugging(events_pitcher)
        x[cnt, 2] = getFIP(events_pitcher)
        if t.event == 'Home Run':
            y[cnt] = 1
        else:
            y[cnt] = 0

        cnt += 1

    return x, y







