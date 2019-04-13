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


class GlenatSpider(scrapy.Spider):
    name = 'glenat'
    base_url = 'https://www.glenat.com'
    allowed_domains = ['glenat.com']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.15,
        'AUTOTHROTTLE_ENABLED': True,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    def start_requests(self):
        catalog = 'https://www.glenat.com/bd/catalogue'
        yield scrapy.Request(url=urljoin(self.__class__.base_url, catalog), callback=self.parse_catalog_page)

    def parse_catalog_page(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        # parse comics from catalog page
        for item in soup.find_all('div', class_='views-row'):
            try:
                yield scrapy.Request(url=urljoin(self.__class__.base_url, item.a['href']), callback=self.parse)
            except:
                pass

        # parse next catalog page
        try:
            next_page = soup.find('li', class_='pager-next active').a['href']
        except:
            pass
        else:
            yield scrapy.Request(url=urljoin(self.__class__.base_url, next_page), callback=self.parse_catalog_page)

    def parse(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        book = soup.find('div', about=resp.url.replace(self.__class__.base_url, ''))
        infos = soup.find('div', class_='group-infos')

        # soup.find('div', class_='field-name-hw-livre-titre-couv').text
        divtitle = soup.find('div', class_='group-title')
        try:
            div = divtitle.find('div', class_='field-name-hw-livre-serie')
            website = urljoin(self.__class__.base_url, div.a['href'])
            series = div.text
        except:
            title = divtitle.find('div', class_='field-name-hw-livre-titre-couv').text.strip()
            series = None
            volume = None
            website = None
        else:
            title = divtitle.find('div', class_='field-name-hw-livre-sous-titre').text
            try:
                volume = int(divtitle.find('div', class_='field-name-hw-livre-titre-couv').text.split('Tome')[-1].strip())
            except:
                pass

        try:
            # FIXME: this retrieves a lower res image than possible
            # (see sites/default/files/styles/couv_livre/ vs sites/default/files/styles/large/)
            cover = book.find('div', class_='field-name-hw-livre-couverture').img['src']
        except:
            cover = None

        try:
            categories = [x.text for x in infos.find('div', class_='field-name-hw-livre-collections').find_all('div', class_='field-items')]
        except:
            pass

        try:
            date = '-'.join(infos.find('div', class_='field-name-hw-livre-date-parution').find('div', class_='field-items').text.split('.')[::-1])
        except:
            pass

        try:
            pages = int(infos.find('div', class_='field-name-hw-livre-nb-pages').find('div', class_='field-items').text)
        except:
            pass

        writers = []
        illustrators = []
        for intervention in soup.find_all('div', class_='field-collection-item-hw-interventions'):
            fields = [x.text for x in intervention.find_all('div', class_='field-items')]
            if fields[0] == 'Scénariste':
                writers = fields[1:]
            else:
                illustrators.extend(fields[1:])


        # response
        yield {
            'objectID': ean,
            'publisher': 'Glénat',
            'url': response.url,
            'title': title,
            'summary': soup.find('div', class_='field-name-hw-presentation-editoriale').text,
            'cover': cover,
            'samples': [],
            'series': series,
            'volume': volume,
            'category': categories,
            'date': date,
            'pages': pages,
            'price': {},  # cannot extract price; seems that the price is generated from js
            'ean': ean,
            'illustrators': illustrators,
            'writers': writers,
            'website': website
        }

