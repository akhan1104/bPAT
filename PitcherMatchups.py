# Player Stat Scrape Class
# Created 05/17/17
import bs4 as bs
import requests

class Scraper:
    def __init__(self, player, isPitcher):
    	self.pitcher = isPitcher
    	self.stats = Stat(player)
        self.matchups = []
    
    def get_player_id(player):
    	# player list: first, last
        assert(len(player) == 2)
        # Find player ID from retrosheet
        site = requests.get('http://www.retrosheet.org/retroID.htm')
        src = site.content
        soup = bs.BeautifulSoup(src, 'lxml')
        all_players = soup.pre.get_text().splitlines()

        found = [s for s in all_players if player[-1].lower() in s.lower() and player[0].lower() in s.lower()]
        player_id = found[0].split(',')[-2].encode('ascii','replace')

        return player_id

    def get_matchups:

    	


# Statistic Superclass
# Created: 05/17/17
class Stat:
	def __init__(self, name):
		self.name = name
    
