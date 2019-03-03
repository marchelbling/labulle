# -*- coding: utf-8 -*-
import re
import requests
import scrapy

from bs4 import BeautifulSoup
from urllib.parse import urljoin

DIGITS = re.compile('\d+')


def extract_int(string):
    result = DIGITS.search(string)
    if result:
        return int(result.string[result.start():result.end()])
    return None


class DelcourtSpider(scrapy.Spider):
    name = 'delcourt'
    base_url = 'https://www.editions-delcourt.fr'
    allowed_domains = ['editions-delcourt.fr']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.15,
        'AUTOTHROTTLE_ENABLED': True,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    # 'conquistador': 10, # collection/id
    # 'erotix': 15,
    # 'histoire & histoires': 18,
    # 'humour de rire': 20,
    # 'insomnie': 22,
    # 'long métrage': 26,
    # 'encrages': 14,
    # 'ex-libris': 16,
    # 'hors collection': 19,
    # 'impact': 21,
    # catalogue = 'https://www.editions-delcourt.fr/index.php?option=com_dlc_catalogue&controller=collection&task=getTitresOfCollection&format=raw'
    # yield scrapy.FormRequest.from_response(catalogue,
    #                                        formdata={'id': 19, 'order': 'a.date_publication DESC', 'page': 1},
    #                                        callback=self.parse_item)

    def start_requests(self):
        collections = 'https://www.editions-delcourt.fr/bd/liste-des-collections-bd.html'
        yield scrapy.Request(url=urljoin(self.__class__.base_url, collections), callback=self.parse_collections)

    def parse_collections(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for h2 in soup.find('div', class_='list-items collections').find_all('h2', class_='title'):
            yield scrapy.Request(url=urljoin(self.__class__.base_url, h2.a['href'].replace('.html', '-voir-tout.html')), callback=self.parse_collection)

    def parse_collection(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for item in soup.find('div', id='list-articles-collection').find_all('div', class_='item'):
            yield scrapy.Request(url=urljoin(self.__class__.base_url, item.find('div', class_='thumb').a['href']), callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        details = soup.find('div', class_='details')
        meta = [li.text.strip() for li in soup.find('ul', class_='metadatas').find_all('li')]
        meta = dict(zip([key.split(':')[0].strip() for key in meta], [val.split(':')[1].strip() for val in meta]))

        try:
            samples = [a['href'] for a in soup.find('div', class_='visual').find('div', class_='previews').find_all('a')]
        except:
            samples = []

        try:
            soup.find('div', class_='block related-items').find('ul', class_='list-items catalog')
            series = meta.get('Série')
        except:
            series = None

        try:
            website = urljoin(self.__class__, soup.find('div', class_='list-items news').a['href'])
        except:
            website = None

        try:
            price = {
                'amount': float(soup.find('div', class_='prices').span.text.replace(' ', '').replace('€', '')),
                'currency': 'eur'
            }
        except:
            price = {}

        def peoplify(names):
            for i, name in enumerate(names):
                tokens = name.strip().split(' ', 1)
                if len(tokens) == 2 and tokens[0].isupper():
                    names[i] = tokens[1] + ' ' + tokens[0].capitalize()
                else:
                    names[i] = tokens[0].capitalize()
            return names

        def titlify(title):
            tokens = title.rsplit(' ', 1)
            if tokens[-1][0] == '(' and tokens[-1][-1] == ')':
                if tokens[-1].lower() == '(réédition)':
                    return tokens[0]
                elif len(tokens) == 2:
                    if tokens[1] in ("(Le)", "(Les)", "(La)", "(L')"):
                        return tokens[1][1:-1] + ' ' + tokens[0]
            return title

        isbn = details.find('span', class_='isbn').text.replace('-', '')

        # response
        yield {
            'objectID': isbn,
            'publisher': 'Delcourt',
            'url': response.url,
            'title': titlify(details.h1.text.strip()),
            'summary': soup.find('div', class_='resume').text.replace('\n', ' ').replace('\t', ' ').replace('\r', '').strip(),
            'cover': soup.find('div', class_='visual').a['href'],
            'samples': samples,
            'series': series,
            'date': '-'.join(details.find('span', class_='published_at').text.strip().split(': ')[-1].split('/')[::-1]),
            'price': price,
            'isbn': isbn,
            'illustrators': peoplify(meta.get('Illustrateur', meta.get('Dessinateur', '')).split(',')),
            'writers': peoplify(meta.get('Scénariste', '').split(',')),
            'black_and_white': meta.get('Coloriste') is None,
            'website': website
        }
