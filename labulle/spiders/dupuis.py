# -*- coding: utf-8 -*-
import re
import requests
import scrapy

from bs4 import BeautifulSoup
from urllib.parse import urljoin


class DupuisSpider(scrapy.Spider):
    name = 'dupuis'
    base_url = 'https://www.dupuis.com'
    allowed_domains = ['dupuis.com']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.15,
        'AUTOTHROTTLE_ENABLED': True,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    def start_requests(self):
        collections = 'https://www.dupuis.com/catalogue/FR/recherche.html'
        yield scrapy.Request(url=urljoin(self.__class__.base_url, collections), callback=self.parse_collections)

    def parse_collections(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for a in soup.find_all('a', class_='dp-cat-voirtout-mobile'):
            url = urljoin(self.__class__.base_url, a['href'])
            yield scrapy.Request(url='/0/'.join(url.rsplit('/', 1)), callback=self.parse_collection)

    def parse_collection(self, response):
        # e.g. https://www.dupuis.com/catalogue/FR/c/vl/1426/0/dupuis-premiere-bd.html
        soup = BeautifulSoup(response.text, 'lxml')
        for item in soup.find_all('div', class_='dp-cat-series-ligne-serie'):
            try:
                yield scrapy.Request(url=urljoin(self.__class__.base_url, item.a['href']), callback=self.parse_series)
            except:
                pass  # ignore "Séries" div (first line)

    def parse_series(self, response):
        # e.g. https://www.dupuis.com/seriebd/petit-poilu/1356
        soup = BeautifulSoup(response.text, 'lxml')
        items = soup.find_all('div', class_='dp-ser-slide-cadre')

        if not hasattr(self, 'is_series'):
            self.is_series = len(items) > 1

        self.authors = {}
        for kinds, name in [(author.find('div', 'dp-auteur-metier').text.lower(), author.find('h4', 'dp-auteur-nom').text) for author in soup.find_all('div', 'dp-auteur')]:
            for kind in kinds.split(' et '):
                self.authors.setdefault(kind.strip(), []).append(name.strip())

        if self.is_series:
            self.series_url = response.url
            series_id = response.url.rsplit('/', 1)[-1]
            yield scrapy.Request(url='https://www.dupuis.com/servlet/jpcatalogue?pgm_servlet=view_serie_suite_albums&serie_id={id}&nombre_slide=5&page={page}'\
                                     .format(series_id, 1), callback=self.parse_series_page)
        else:
            yield scrapy.Request(url=urljoin(self.__class__.base_url, items[0].a['href']),
                                 callback=self.parse)

    def parse_series_page(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        items = soup.find_all('div', class_='dp-album-couv-ratio')
        for item in items:
            yield scrapy.Request(url=urljoin(self.__class__.base_url, item.a['href']), callback=self.parse)

        if len(items) >= 5:
            url, page = response.url.rsplit('=', 1)
            yield scrapy.Request(url='='.join(url, int(page) + 1), callback=self.parse_series_page)

    def parse(self, response):
        soup = BeautifulSoup(response.text, 'lxml')

        details = {}
        for line in soup.find('div', class_='dp-album-infos-technique').text.lower().strip().split('\n'):
            line = line.replace('\xa0', ' ')
            if line.startswith('parution'):
                details['date'] = '-'.join(line.rsplit(' le ', 1)[1].split('/')[::-1])
            elif line.startswith('hauteur'):
                height, width = line.split('/')
                details['height'] = int(height.rsplit(':', 1)[1].replace('mm', '').strip())
                details['width'] = int(width.rsplit(':', 1)[1].replace('mm', '').strip())
            elif line.startswith('genre'):
                details['genre'] = [genre.strip() for genre in line.rsplit(':', 1)[-1].split('/')]
            elif 'pages' in line:
                details['book'] = line.split(' - ', 1)[0].strip()
                details['pages'] = int(line.split(' - ', 1)[1].split('pages')[0].strip())
                details['black_and_white'] = 'couleurs' not in line
            else:
                try:
                    key, value = line.split(':', 1)
                except ValueError:
                    print("Error: could not split line {}".format(line))
                    pass
                else:
                    details[key.strip()] = value.strip()


        summary = soup.find('div', class_='dp-album-resume').text
        try:
            title, summary = summary.strip().split('\n', 1)
        except ValueError:
            # e.g. https://www.dupuis.com/secrets-le-serpent-sous-la-glace-l-integrale/bd/secrets-le-serpent-sous-la-glace-l-integrale-tome-1-secrets-le-serpent-sous-la-glace-l-integrale/25781
            title = summary.strip()
            summary = ''
        series = soup.find('span', class_='dp-album-infos-serie').text.strip()

        cover = soup.find('img', class_='couve_album_ratio')['src']

        try:
            volume = int(soup.find('span', 'dp-album-infos-tome').text.split('\xa0')[-1])
        except:
            volume = None

        # response
        yield {
            'objectID': details.get('isbn'),
            'publisher': 'Dupuis',
            'url': response.url,
            'title': title,
            'volume': volume,
            'series': series if self.is_series else None,
            'summary': summary,
            'cover': cover,
            'samples': [cover.replace('couv', 'page{}'.format(idx)) for idx in range(5, 10)],
            'pages': details.get('pages'),
            'date': details.get('date'),
            'price': details.get('pvp', '').replace('eur', '€'),
            'isbn': details.get('isbn'),
            'illustrators': self.authors.get('dessin', []),
            'writers': self.authors.get('scénario', []),
            'website': getattr(self, 'series_url', None),
            'black_and_white': details.get('black_and_white'),
            'age': details.get('age du lectorat'),
            'genre': details.get('genre', []),
            'book': details.get('book'),
        }
