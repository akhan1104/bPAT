import bs4 as bs
import requests

site = requests.get('http://www.retrosheet.org/boxesetc/C/Pcasts001.htm')
src = site.content

soup = bs.BeautifulSoup(src, 'lxml')

print(soup.title)