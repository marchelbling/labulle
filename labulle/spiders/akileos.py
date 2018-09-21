# -*- coding: utf-8 -*-
import re
import requests
import scrapy

from bs4 import BeautifulSoup

DIGITS = re.compile('\d+')
# FIXMEs:
# http://www.akileos.fr/catalogue/o-sensei

def to_date_month(month):
    return {
        'Janvier': '01',
        'Février': '02',
        'F�vrier': '02',
        'Mars': '03',
        'Avril': '04',
        'Mai': '05',
        'Juin': '06',
        'Juillet': '07',
        'Août': '08',
        'Ao�t': '08',
        'Septembre': '09',
        'Octobre': '10',
        'Novembre': '11',
        'Décembre': '12',
        'D�cembre': '12',
    }[month]


def extract_int(string):
    result = DIGITS.search(string)
    if result:
        return int(result.string[result.start():result.end()])
    return None

def split(string, tokens):
    if not string:
        return []

    if not isinstance(tokens, list):
        tokens = [tokens]

    for token in tokens:
        if token in string:
            return string.split(token)

    return [string]


def peoplify(payload, from_keys):
    splitters = [' et ', ', ']
    values = []
    for from_key in from_keys:
        values.append(payload.pop(from_key, ''))
    return [token for value in values for token in split(value, splitters)]

    if values:
        payload[to_key] = values


class AkileosSpider(scrapy.Spider):
    name = 'akileos'
    allowed_domains = ['akileos.fr']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.15,
        'AUTOTHROTTLE_ENABLED': True,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    def start_requests(self):
        catalogue = 'http://akileos.fr/catalogue'
        yield scrapy.Request(url=catalogue, callback=self.parse_catalogue)

    def parse_catalogue(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for item in soup.find_all("div", {"class": "catalogue-item"}):
            yield scrapy.Request(url=item.a['href'], callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        # entry_id = soup.find(id='main').find('article').attrs['id']

        # item elements
        entry = soup.find("div", {"class": "entry-details"})
        if entry is None:
            yield {'url': response.url, 'status': 'failed'}

        values = list(filter(None,
                             map(lambda p: p.text.replace('\t', '').replace('\n', '').strip(),
                                 entry.find_all('p'))))
        keys = [l.text for l in entry.find_all('label')]

        keys += ['book', 'dimensions', 'pages', 'ean', 'price']
        values += values.pop().split(" – ")

        blob = dict(zip(keys, values))

        try:
            width, height = blob.get('dimensions', '').split('×')
        except:
            pass
        else:
            blob['width'] = int(width)
            blob['height'] = int(height)

        try:
            blob['pages'] = extract_int(blob['pages'])
        except KeyError:
            pass

        try:
            month, year = blob.get('Date de parution', '').split()
        except ValueError:
            pass
        else:
            blob['date'] = '{}-{}-01'.format(year, to_date_month(month))

        try:
            blob['book'] = blob['book'].lower()
        except:
            pass

        try:
            blob['price'] = {
                'amount': float(blob['price'].split('€')[0].strip().replace(',00', '').replace(',', '.')),
                'currency': 'eur',
            }
        except:
            blob['price'] = {}

        blob['genre'] = [genre.strip().lower() for genre in blob.get('Genre', '').split(',')]

        try:
            samples = [page.img['src'] for page in soup.find('div', id='flipbook').find_all('div', class_='page')]
        except:
            samples = []

        title = soup.find('div', {'class': 'breadcrumbs'}).find_all('span',{'property':'name'})[-1].text
        if blob.get('Série'):
            try:
                volume, title = title.rsplit(' – ', 1)
            except ValueError:
                try:
                    title, volume = title.rsplit(', ', 1)
                except ValueError:
                    volume = None

            try:
                volume = int(volume.rsplit('T.', 1)[-1])
            except:
                volume = None
        else:
            volume = None

        # response
        yield {
            'objectID': blob.get('ean'),
            'publisher': 'Akileos',
            'url': response.url,
            'title': title.strip(),
            'series': blob.get('Série'),
            'volume': volume,
            'summary': soup.find('h4', string='Résumé').find_next().text.replace('\n', ' ').replace('\t', ' ').replace('\r', '').strip(),
            'cover': soup.find('div',{'class': 'cover'}).a['href'],
            'samples': samples,
            'illustrators': peoplify(blob, from_keys=['Dessinateurs', 'Dessinatrices', 'Dessinateur', 'Dessinatrice']),
            'writers': peoplify(blob, from_keys=['Scénaristes', 'Scénariste']),
            'authors': peoplify(blob, from_keys=['Auteurs', 'Auteur']),
            'ean': blob.get('ean'),
            'genre': blob.get('genre'),
            'date': blob.get('date'),
            'book': blob.get('book'),
            'pages': blob.get('pages'),
            'width': blob.get('width'),
            'height': blob.get('height'),
            'price': blob.get('price'),
        }
