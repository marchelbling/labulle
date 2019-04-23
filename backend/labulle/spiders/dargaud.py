# -*- coding: utf-8 -*-
import re
import requests
import scrapy

from bs4 import BeautifulSoup
from urllib.parse import urljoin


def on_exception(defaults):
    def wrapped(fn):
        def safe(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except:
                return defaults
        return safe
    return wrapped


def clean_article(string):
    for article in ['Le', 'La', 'L\'', 'Les', 'Des', 'De', 'Un', 'Une', 'D\'']:
        suffix = '({})'.format(article)
        if string.endswith(suffix):
            return (article + ' ' + string.rsplit(suffix, 1)[0]).strip()
    return string.strip()


class DargaudSpider(scrapy.Spider):
    name = 'dargaud'
    base_url = 'http://www.dargaud.com'
    allowed_domains = ['dargaud.com']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.25,
        'AUTOTHROTTLE_ENABLED': True,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    def start_requests(self):
        collections = 'bd/catalogue'
        yield scrapy.Request(url=urljoin(self.__class__.base_url, collections), callback=self.parse_catalogue)

    def parse_catalogue(self, response):
        # http://www.dargaud.com/bd/catalogue
        soup = BeautifulSoup(response.text, 'lxml')
        for a in soup.find('div', class_='abecedaire clearfix').find_all('a'):
            url = urljoin(self.__class__.base_url, a['href'])
            yield scrapy.Request(url=url, callback=self.parse_letter)

    def parse_letter(self, response):
        # http://www.dargaud.com/bd/catalogue/(letter)/A
        soup = BeautifulSoup(response.text, 'lxml')
        for li in soup.find_all('li', class_='bd clearfix'):
            if li.find('a', class_='all-albums'):
                # find if this is a series
                yield scrapy.Request(url=urljoin(self.__class__.base_url, li.a['href']), callback=self.parse_series)

    def parse_series(self, response):
        # http://www.dargaud.com/bd/Abelard
        soup = BeautifulSoup(response.text, 'lxml')
        if soup.find('li', class_='bd clearfix'):
            # e.g. http://www.dargaud.com/bd/Abelard
            for li in soup.find_all('li', class_='bd clearfix'):
                if li.find('a', class_='all-albums'):
                    yield scrapy.Request(url=urljoin(self.__class__.base_url, li.a['href']), callback=self.parse_sub_series)
        else:
            # e.g. http://www.dargaud.com/bd/Petit-livre-de-Le
            for li in soup.find_all('li', class_='bd'):
                yield scrapy.Request(url=urljoin(self.__class__.base_url, li.a['href']), callback=self.parse_album)

    def parse_sub_series(self, response):
        # http://www.dargaud.com/bd/Abelard/Alvin
        soup = BeautifulSoup(response.text, 'lxml')
        for li in soup.find_all('li', class_='bd'):
            yield scrapy.Request(url=urljoin(self.__class__.base_url, li.a['href']), callback=self.parse_album)

    def parse_album(self, response):
        @on_exception([None, None, None])
        def parse_title_series_volume(soup):
            if soup.find('span', class_='page-title-album'):
                title = soup.find('span', class_='page-title-album').text
                title = title if not title.startswith(' ') else title[3:]
                series, volume = soup.find('div', class_='page-title-container').find('span').text.split(' Tome ')
            else:
                title = soup.find('h2', class_='h2-like hide-phone').text.replace('Résumé ', '')
                series = None
                volume = None
            return clean_article(title), clean_article(series) if series else None, int(volume) if volume else None

        @on_exception(None)
        def parse_series_url(soup):
            if soup.find('span', class_='page-title-album'):
                a = soup.find('nav', class_='breadcrumb hide-phone').find_all('li')[-2].a
                return urljoin(self.__class__.base_url, a['href'])
            else:
                return None

        @on_exception(None)
        def parse_date(soup):
            return '-'.join(soup.find('time', class_='date').text.rsplit(' ', 1)[-1].split('/')[::-1])

        @on_exception(None)
        def parse_pages(soup):
            return int(soup.find('div', class_='pages').find('strong').text.split(' ', 1)[0])

        @on_exception([None, None])
        def parse_width_height(soup):
            return list(map(int, soup.find('div', class_='format').find('strong').text.split('x')))

        @on_exception(None)
        def parse_ean(soup):
            return soup.find('div', class_='ean').find('strong').text

        @on_exception(None)
        def parse_price(soup):
            return {
                'amount': float(soup.find('div', class_='infosPrix').find('strong').text.replace(',', '.').replace('€', '')),
                'currency': 'eur'
            }

        @on_exception(None)
        def parse_summary(soup):
            return soup.find('div', class_='read-more-content-description-album').text.strip()

        @on_exception(None)
        def parse_cover(soup):
            return soup.find('div', class_='clearfix presentationAlbum').find('div', class_='couverture-wrapper').find('img')['src'].replace('M320x500', 'M1200x900')

        @on_exception([])
        def parse_samples(soup):
            cover = parse_cover(soup)
            return [cover.replace('couv', 'page{}'.format(i)) for i in range(1, 10)]

        @on_exception(None)
        def parse_age(soup):
            age = soup.find('div', class_='public').find('li').text.lower()
            if 'partir de ' in age:
                return int(age.split('partir de ', 1)[-1].split(' ')[0])
            if 'tous publics - enfants' in age:
                return 6
            if 'tous publics - famille' in age:
                return 9

        @on_exception({})
        def parse_authors(soup):
            # note: this produces garbage key/values but results should be get with explicit keys
            authors = {}
            for li in soup.find('ul', class_='introAlbum').find_all('li'):
                for a in li.find_all('a'):
                    authors.setdefault(li.text.split(':', 1)[0].strip().lower(), []).append(a.text)
            return authors

        @on_exception(None)
        def parse_genres(soup):
            genres = []
            for li in soup.find('div', class_='genre').find_all('li'):
                genres.extend([g.lower().strip() for g in li.text.split('/')])
            return genres

        soup = BeautifulSoup(response.text, 'lxml')
        title, series, volume = parse_title_series_volume(soup)
        authors = parse_authors(soup)
        illustrators = [value for key, value in authors.items() if key.startswith('dessin')]
        writers = [value for key, value in authors.items() if key.startswith('scénar')]
        ean = parse_ean(soup)
        width, height = parse_width_height(soup)

        # response
        yield {
            'objectID': ean,
            'ean': ean,
            'publisher': 'Dargaud',
            'url': response.url,
            'title': title,
            'series': series,
            'volume': volume,
            'summary': parse_summary(soup),
            'date': parse_date(soup),
            'illustrators': illustrators[0] if illustrators else [],
            'writers': writers[0] if writers else [],
            'cover': parse_cover(soup),
            'samples': parse_samples(soup),

            'misc': {
                'pages': parse_pages(soup),
                'price': parse_price(soup),
                'website': parse_series_url(soup),
                'tags': parse_genres(soup),
                'age': parse_age(soup),
                'width': width,
                'height': height,
            }
        }
