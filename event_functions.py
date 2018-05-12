def applyBirthYear(ev):
    year = ev['dob'][-4:]
    return year


def applyHit(ev):
    
    hit = set(('Single', 'Double', 'Triple', 'Home Run', 'Fan Interference'))
    try:
      if ev['event'] in hit:
          h = True
      else:
          h = False
      return h
    except NameError:
        print "PARSE ERROR"


def applyNameChange(x):

    return x['pitcher_name'] + x['date'][:4]


def applyReach(ev):

    reachBase = set(('Walk', 'Intent Walk', 'Batter Interference', 'Hit By Pitch'))

    try:
      if ev['event'] in reachBase:
          h = True
      else:
          h = False
      return h
    except NameError:
        print "PARSE ERROR"


def applySac(ev):

    sac = set(('Sac Fly DP', 'Sac Fly', 'Sac Bunt'))

    try:
      if ev['event'] in sac:
          h = True
      else:
          h = False
      return h
    except NameError:
        print "PARSE ERROR"



def applyBatterHands(ev):
    return lookupHand(ev.batter, True)


def applyPitcherHands(ev):
    return lookupHand(ev.pitcher, False)


def lookupHand(id, batter):
    # assumes bio dataframe loaded in environment, change when converted to clean OOP
    if batter:
        return bio[bio.id == id].reset_index(drop=True).loc[0].bats
    else:
        return bio[bio.id == id].reset_index(drop=True).loc[0].throws

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
        data for events BELOW idx...Only for SLG, SLGagainst, FIPagainst"""
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


def getLastHR(events, bio):
    """For each event, get a players HR from last year"""

    db = MySQLdb.connect('localhost', 'root', 'pw4free', 'lahman2016')

    for i, ev in events.iterrows():

        first, last, year = searchBio(bio, ev.batter)
        lastyear = int(ev.game_id[4:8]) - 1
        #print last, first, year, lastyear
        try:
            query = queryLahman(last, first, year, lastyear, 'HR', db)
        except ValueError:
            query = -1.0
        events.loc[i, 'HRLast'] = query
        if i % 100 == 0:
            print i
    db.close()
    return events



def searchBio(bio, id):
    """ Search bio dataframe for id, return First name Last name and year born"""
    found = bio[bio.id == id].reset_index(drop=True)

    if len(found) == 0:
        raise ValueError("Player was not found")

    return found.loc[0].first_name, found.loc[0].last_name, int(found.loc[0].dob[-4:])

def queryLahman(lastname, firstname, year_born, season, stat, db):

    import MySQLdb

    if type(lastname) is not str or type(firstname) is not str or type(season) is not int or type(stat) is not str:
        raise TypeError("argument types are not correct")

    

    try:
        playerID = _masterQuery(lastname, firstname, year_born, db)
    except ValueError:
        #print "PLAYER NOT FOUND, REFINE QUERY"
        raise

    ret = _hitterStatQuery(playerID, season, stat, db)
    #db.close()

    return ret
    
        

def _masterQuery(lastname, firstname, year_born, db):
    """ Return a playerID from the master table query """

    import pandas as pd
    import MySQLdb

    query = "SELECT * FROM Master WHERE nameLast = " + "\"" + lastname \
            + "\"" +' AND nameFirst = ' + "\"" +firstname+"\"" \
            +' AND birthYear = ' +str(year_born)+';'

    df = pd.read_sql(query, db)
    #print query
    if len(df) != 1:
        raise ValueError("A single query result was not returned for the parameters")

    return df.loc[0].playerID


def _hitterStatQuery(playerID, season, stat, db):
    """ Given a playerID, query a specific stat """

    query = "SELECT " + stat + " FROM Batting WHERE playerID = " + "'" + playerID \
            + "'" +' AND yearID = '  +str(season)+';'

    df = pd.read_sql(query, db)

    if len(df) != 1:
        raise ValueError("A single query result was not returned, refine parameters")


    if stat == '*':
        return df
    else:
        return df.loc[0, stat]


# def pitchTypeFeatures(events):
#     """ For an event dataframe return a binary encoded np array for the pitch type"""
#     from sklearn.preprocessing import OneHotEncoder
    
def writeSQL_events(events):
    """Void function, writes events table to SQL db"""
    import MySQLdb
    db = MySQLdb.connect(host='localhost', user='root', passwd='pw4free', db='lahman2016')

    cursor = db.cursor()

    query = """INSERT INTO events (ab_num, b, b1, b2, b3, batter, event, event_num, game_id, o, pitch_speed, pitch_type, pitcher, s) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """

    for i, r in events.iterrows():
        values = (r.ab_num, r.b, r.b1 if isinstance(r.b1, int) else -1,\
                 r.b2 if isinstance(r.b2, int) else -1, r.b3 if isinstance(r.b3, int) else -1, \
                 r.batter, r.event, r.event_num, r.game_id, r.o, \
                 -1 if np.isnan(r.pitch_speed) else r.pitch_speed, r.pitch_type, r.pitcher, r.s)
                 #,\
                 # 1 if r.Hit else 0, 1 if r.Out else 0, 1 if r.ReachBase else 0, 1 if r.Sac else 0,\
                 # r.PitcherHand, r.BatterHand)
        
        print values
        print query
        cursor.execute(query, values)

    cursor.close()
    db.commit()
    db.close()


def writeSQL_bio(bio):
    """Void function, writes bio table to SQL db"""
    import MySQLdb
    db = MySQLdb.connect(host='localhost', user='root', passwd='pw4free', db='lahman2016')

    cursor = db.cursor()

    query = """INSERT INTO bio (bats, current_position, dob, first_name, height, id, jersey_number, last_name, pos, team, throws, type, weight, dob_reformat, birth_year) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """

    for i, r in bio.iterrows():
        values = (r.bats, r.current_position, r.dob, r.first_name,\
                  r.height, r.id, r.jersey_number, r.last_name, r.pos,\
                  r.team, r.throws, r.type, r.weight, r.dob_reformat, r.BirthYear)

        cursor.execute(query, values)

    cursor.close()
    db.commit()
    db.close()


def hashJoin(x):
    """Combine keys to join easily with pandas (game id and ab num)"""
    hashstr = x['gameday_link'] + '+' + str(x['num'])

    return hashstr


def plotPitches(df, col='pitch_type'):
    import matplotlib.pyplot as plt
    import seaborn as sns

    pitches = list(set(df[col]))
    fg = sns.FacetGrid(data=df, hue=col, hue_order=pitches)
    fg.map(plt.scatter, 'px', 'pz').add_legend()
    plt.show()


# """ Generate pitch based features """
# f = ['start_speed', 'end_speed', 'pfx_x', 'pfx_z', 'px', 'pz',\
#      'x0', 'y0', 'z0', 'vx0', 'vy0', 'vz0', 'ax', 'ay', 'az',\
#      'break_y', 'break_length', 'type_confidence',\
#      'zone', 'spin_dir', 'spin_rate'] #batter hand
#      # combine binary and numeric features linearly
#      # d = d1 + ad2 +bd3...

# #code to join pitch, atbat tables
# import sqlite3
# import pandas as pd

# conn = sqlite3.connect('/Users/AleemKhan/Documents/Projects/bPAT/pitchfxData/pitchfx.sqlite2016')
# conn2 = sqlite3.connect('/Users/AleemKhan/Documents/Projects/bPAT/pitchfxData/pitchfx.sqlite2017')
# query_pitch = 'SELECT * FROM pitch;'
# query_ab = 'SELECT * FROM atbat;'
# pitch1 = pd.read_sql_query(query_pitch, conn)
# atbat1 = pd.read_sql_query(query_ab, conn)

# pitch2 = pd.read_sql_query(query_pitch, conn2)
# atbat2 = pd.read_sql_query(query_ab, conn2)

# pitch = pd.concat([pitch1, pitch2])
# atbat = pd.concat([atbat1, atbat2])

# pitch['hashJoin'] = pitch.apply(hashJoin, axis=1)
# atbat['hashJoin'] = atbat.apply(hashJoin, axis=1)

# abJoin = atbat.set_index('hashJoin')
# pitchJoin = pitch.set_index('hashJoin')

# inplay = pitch
# res = pd.merge(pitchJoin, abJoin[['p_throws', 'event', 'pitcher_name']], left_index=True, right_index=True, how='inner')




# import pandas as pd
# execfile('PitcherSeason.py')
# pfx1 = PitchFx('/Users/AleemKhan/Documents/Projects/bPAT/pitchfxData/pitchfx.sqlite2017')
# pfx2 = PitchFx('/Users/AleemKhan/Documents/Projects/bPAT/pitchfxData/pitchfx.sqlite2016')
# pfx1.queryData()
# pfx2.queryData()
# ab1 = pfx1.getAtbatDF()
# pi1= pfx1.getPitchDF()
# ab2 = pfx2.getAtbatDF()
# pi2 = pfx2.getPitchDF()
# atbat = pd.concat([ab1, ab2])
# pitch = pd.concat([pi1, pi2])
# pc = PitcherClustering()
# pc.addModel('/Users/AleemKhan/Documents/Projects/bPAT/SerializedModels/kmeans250.pickle', is_pickled=True)
# pc.fit(pitch, atbat)
# pc.cluster()






