class PitcherSeason(object):
    """Class to define a pitcher season"""
    pitcherName = None
    pitchTypes = None
    starts = None
    feature_array = None


    def getPitches(self):
        return self.pitchesThrown


    def getFeatures(self):
        return self.feature_array


    def getPitcherName(self):
        return self.pitcherName


    def __init__(self, df, fields=None):
        """Constructor takes in the pitch dataframe and extracts the relevant features"""
        import re
        assert len(set(df.pitcher_name)) == 1, "This class only accepts single pitchers"
        assert 'gameday_link' in df.columns, 'gameday_link must be passed to the class'
        #assert len(df) == len(df[df.gameday_link.str.contains(year)]), 'Dataframe must only contain data from a single season'
        assert 'pitcher_name' in df.columns, 'pitcher_name must be passed to the class'
        #year = re.findall('[0-9]{4}', list(res.gameday_link)[0])[0]
        if fields is None:
            fields = ['start_speed', 'pfx_x', 'pfx_z', 'px', 'pz', 'vx0', 'vz0']

        df = df[fields].dropna(how='any')

        self.starts = len(set(df['gameday_link']))
        self.pitchesThrown = len(list(df.pitcher_name))
        self.pitcher_name = list(df.pitcher_name)[0]
        self.pitchTypes = list(set(df.pitch_type))
        self.feature_array = df[fields].values


class PitchFx(object):
    """ Class to simplify sqlite interaction """

    def __init__(self, path):
        """
            Constructor takes in path(s) to the files
            @Input: Single file path to a sqlite db OR a list of paths to sqlite dbs
            @Output: N/A

        """
        assert isinstance(path, str) or isinstance(path, list), "Constructor must be passed a string or list of strings"
        self._files = []
        self._pitchDF = []
        self._abDF = []
        if isinstance(path, list):
            self._files = path
        else:
            self._files.append(path)


    def queryData(self, pitch_query='ALL', atbat_query='ALL', pitch=True, atbat=True):
        """
            Query the sqlite databases
            @Input: pitch_query: sqlite query string that will be used to query pitch db
                    atbat_query: sqlite query string that will be used to query pitch db
                    pitch: flag to load pitch table
                    atbat: flag to load atbat table
            @Output: N/A
        """
        import sqlite3
        import pandas as pd
        import os

        assert isinstance(pitch_query, str) and isinstance(atbat_query, str), "Query parameter must be a string"
        assert isinstance(pitch, bool) and isinstance(atbat, bool), "pitch, atbat parameters must be bool"

        if not (pitch or atbat):
            return

        self._abDF = []
        self._pitchDF = []
        for f in self._files:
            if not os.path.isfile(f): #check if files exist
                print "DB FILE NOT FOUND: " + f + " , SKIPPING TO NEXT FILE"
                continue
            conn = sqlite3.connect(f)

            if pitch:
                if pitch_query == 'ALL':
                    self._pitchDF.append(pd.read_sql_query('SELECT * FROM pitch;', conn))
                else:
                    try:
                        self._pitchDF.append(pd.read_sql_query(pitch_query, conn))
                    except Exception as err:
                        # not sure how to handle errant query
                        raise err
            if atbat:
                if atbat_query == 'ALL':
                    self._abDF.append(pd.read_sql_query('SELECT * FROM atbat;', conn))
                else:
                    try:
                        self._abDF.append(pd.read_sql_query(atbat_query, conn))
                    except Exception as err:
                        raise err


    def getPitchDF(self):
        """ Get results of pitch query if available
            @Input: self
            @Output: None if no results, dataframe, or list of dataframes
        """

        if len(self._pitchDF) == 0: # no results
            return None

        elif len(self._pitchDF) == 1: # single result
            return self._pitchDF[0]

        else:
            return self._pitchDF


    def getAtbatDF(self):
        """ Get results of pitch query if available
            @Input: self
            @Output: None if no results, dataframe, or list of dataframes
        """
        if len(self._abDF) == 0:  # no results
            return None

        elif len(self._abDF) == 1:  # single result
            return self._abdF[0]

        else:
            return self._abDF










    









