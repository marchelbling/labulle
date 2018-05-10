# -*- coding: utf-8 -*-
import re
import requests
import scrapy

from bs4 import BeautifulSoup
from urllib.parse import urljoin

DIGITS = re.compile('\d+')
DATE_PARSER = re.compile('(\d{1,2})?\s*(janvier|janv|février|fév|mars|avril|avr|mai|juin|juillet|juil|août|septembre|sept|octobre|oct|novembre|nov|décembre|déc).?\s*(\d{4})')

def to_date_month(month):
    return {
        'janvier': '01',
        'janv': '01',
        'février': '02',
        'fév': '02',
        'mars': '03',
        'avril': '04',
        'avr': '04',
        'mai': '05',
        'juin': '06',
        'juillet': '07',
        'juil': '07',
        'août': '08',
        'septembre': '09',
        'sept': '09',
        'octobre': '10',
        'oct': '10',
        'novembre': '11',
        'nov': '11',
        'décembre': '12',
        'déc': '12',
    }[month]


def extract_int(string):
    result = DIGITS.search(string)
    if result:
        return int(result.string[result.start():result.end()])
    return None


class LaBoiteABulleSpider(scrapy.Spider):
    name = 'laboiteabulles'
    base_url = 'http://www.la-boite-a-bulles.com'
    allowed_domains = ['la-boite-a-bulles.com']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.15,
        'AUTOTHROTTLE_ENABLED': True,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    def start_requests(self):
        catalogue = 'catalogue/styleList'
        yield scrapy.Request(url=urljoin(self.__class__.base_url, catalogue), callback=self.parse_catalogue)

    def parse_catalogue(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for item in soup.find('div', id='styleListCatalogueAllWork').find_all('li'):
            yield scrapy.Request(url=urljoin(self.__class__.base_url, item['data-url']), callback=self.parse)

    def parse(self, response):
        def parse_images(soup):
            try:
                samples = [a['href'] for a in soup.find('ul', id='div_extraits').find_all('a')]
            except AttributeError:
                return None, []

            cover = soup.find('div', id='div_couverture2')
            if cover:
                # sample: http://www.la-boite-a-bulles.com/work/84
                cover = cover.find('a')['href']
            else:
                # sample: http://www.la-boite-a-bulles.com/work/13
                cover, samples = samples[0], samples[1:]
            return cover, samples

        def parse_peoples(soup):
            authors = soup.find('p', class_='workAuthors')
            if authors:
                return dict(zip([s.text for s in authors.find_all('span')],
                                [s.text for s in authors.find_all('a')]))
            else:
                authors = soup.find('a', class_='authors').text.replace('(Scénario et dessin)', '')
                return {
                    'Dessin': authors,
                    'Scénario': authors,
                }

        def parse_date(blob):
            try:
                date = [DATE_PARSER.match(line.lower()) for line in blob][0].groups()
                return '{}-{}-{}'.format(date[2], to_date_month(date[1]), date[0] or '01')
            except:
                return None

        def parse_book(blob):
            lines = [line for line in blob if line.strip().lower() in ('cartonné', 'broché',)]
            return ''.join(lines)

        def parse_ean(blob):
            lines = [line for line in blob if 'EAN' in line]
            return ''.join(lines).split('EAN')[1].strip()[:13]

        def parse_price(blob):
            lines = [line for line in blob if '€' in line]
            return ''.join(lines).split('€')[0].strip().replace(',00', '').replace(',', '.') + '€'

        def parse_pages(blob):
            lines = [line for line in blob if 'pages' in line]
            return ''.join(lines).split('pages')[0].strip()

        def parse_series(soup):
            lines = [line for line in blob if 'pages' in line]
            return ''.join(lines).split('pages')[0].strip()

        soup = BeautifulSoup(response.text, 'lxml')

        # sub-items
        try:
            # inspired by https://stackoverflow.com/a/13911764
            for link in soup.find('div', class_='workViewListAlbum').find_all('a'):
                request = scrapy.Request(url=urljoin(self.__class__.base_url, link['href']), callback=self.parse)
                request.meta['series'] = soup.title.text.strip()
                yield request
        except AttributeError:
            pass

        # item elements
        mention = soup.find('p', class_='mention')
        if mention:
            cover, samples = parse_images(soup)
            peoples = parse_peoples(soup)
            blob = [s.text.strip() for s in mention.find_all('span')] + [s.next_sibling.strip() for s in mention.find_all('br')]

            summary = soup.find('p', class_='workShortBody').text
            try:
                summary +=  ' ' + soup.find('div', id='div_description2').find_all('p')[-1].text
            except:
                summary +=  ' ' + soup.find('div', class_='box_main').text.strip()

            # response
            yield {
                'objectID': parse_ean(blob),
                'publisher': 'La Boite à Bulle',
                'url': response.url,
                'title': soup.find('div', id='page_album').h1.text,
                'summary': summary.replace('\n', '').replace('\r', '').replace('\t', ''),
                'cover': cover,
                'samples': samples,
                'series': response.meta.get('series', None),
                'date': parse_date(blob),
                'book': parse_book(blob),
                'pages': parse_pages(blob),
                'ean': parse_ean(blob),
                'price': parse_price(blob),
                'illustrators': [people.strip() for people in peoples.get('Dessin', '').split(', ')],
                'writers': [people.strip() for people in peoples.get('Scénario', '').split(', ')],
            }
