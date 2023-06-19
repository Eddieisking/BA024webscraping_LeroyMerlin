"""
Project: Web scraping for customer reviews
Author: Hào Cui
Date: 06/17/2023
"""

import scrapy
from scrapy import Request
import re
from webscrapy.items import WebscrapyItem


class SpiderSpider(scrapy.Spider):
    name = "spider"
    allowed_domains = ["www.leroymerlin.fr"]

    def start_requests(self):
        # keywords = ['DeWalt', 'Black+and+Decker', 'Stanley', 'Craftsman', 'Porter-Cable', 'Bostitch', 'Irwin+Tools',
        #             'Lenox']
        keywords = ['dewalt']
        # company = 'Stanley Black and Decker'

        # from search words to generate product_urls
        for keyword in keywords:
            push_key = {'keyword': keyword}

            search_url = f'https://www.leroymerlin.fr/produits/marques/{keyword}/?src=brd&query={keyword}'

            yield Request(
                url=search_url,
                callback=self.parse,
                cb_kwargs={**push_key},
            )

    def parse(self, response, **kwargs):

        # Extract the pages of product_urls
        page = response.xpath(
            '//*[@id="component-productfamilypage"]//div[@class="mc-pagination__field"]/select/option[1]/text()')[
            0].extract()
        pages = [int(num) for num in page.split() if num.isdigit()][-1]

        # Based on pages to build product_urls
        keyword = kwargs['keyword']
        # product_urls = [f'https://www.leroymerlin.fr/produits/marques/{keyword}/?p={page}' for page
        #                 in range(1, pages+1)]

        # test page = 1
        product_urls = [f'https://www.leroymerlin.fr/produits/marques/{keyword}/?p={page}' for page
                        in range(1, 2)]

        for product_url in product_urls:
            yield Request(url=product_url, callback=self.product_parse)

    def product_parse(self, response: Request, **kwargs):

        product_list = response.xpath('//*[@id="component-productfamilypage"]//ul[@class="l-resultsList '
                                      'col-container-inner js-list-products"]/li')

        for product in product_list:
            product_href = product.xpath('.//article//a/@href')[0].extract()
            product_detailed_url = f'https://www.leroymerlin.fr{product_href}'
            yield Request(url=product_detailed_url, callback=self.product_detailed_parse,)

    def product_detailed_parse(self, response, **kwargs):

        review_href = response.xpath('//*[@id="component-displaycomp"]//section[@class="col-container"]/div['
                                     '@class="col-12 m-review__link-dedicated-page"]/a/@href').extract()

        if review_href:
            review_url = f'https://www.leroymerlin.fr{review_href[0]}'
            yield Request(url=review_url, callback=self.review_multiple_parse)

        else:
            yield Request(url=response.url, callback=self.review_single_parse, dont_filter=True)

    def review_multiple_parse(self, response, **kwargs):

        page_str = response.xpath('//*[@id="component-reviewdisplay"]//section[@class="col-container"]//div['
                                  '@class="mc-pagination__field"]/select/option[@value="1"]/text()')[0].extract()
        page_number = [int(num) for num in page_str.split() if num.isdigit()][-1]

        review_single_href = response.xpath('//*[@id="component-reviewdisplay"]//section['
                                            '@class="col-container"]/div/nav/a[@title="Page '
                                            'suivante"]/@href').extract()
        review_single_url = f'https://www.leroymerlin.fr{review_single_href[0]}'

        for i in range(1, page_number + 1):
            review_single_detailed_url = re.sub(r'\?p=(\d+)', f'&page={i}#component-reviewdisplay', review_single_url)

            yield Request(url=review_single_detailed_url, callback=self.review_single_parse)

    def review_single_parse(self, response: Request, **kwargs):

        review_list = response.xpath('//section[@class="col-container"]/div[@class="review-data kl-hidden"]')

        for review in review_list:
            item = WebscrapyItem()
            item['product_name'] = response.xpath('//div[@id="component-reviewdisplay"]/section[@class="col-container '
                                                  'l-review-container m-review-resume m-review-resume--desktop '
                                                  'js-review-resume-container"]//div['
                                                  '@class="m-review-resume__designation"]/p['
                                                  '@class="m-review-resume__designation-title"]/text()').extract_first() \
                                   or response.xpath('//*[@id="product-name"]/text()').extract_first()
            item['review_id'] = review.xpath('./@data-review-id')[0].extract() or 'N/A'
            item['customer_name'] = review.xpath('./div[@class="data-review-nickname"]/text()').extract() or ['N/A']
            item['customer_rating'] = review.xpath('./div[@class="data-review-rating"]/text()')[0].extract() or 'N/A'
            item['customer_date'] = review.xpath('./div[@class="data-review-date"]/text()')[0].extract() or 'N/A'
            item['customer_review'] = review.xpath('./div[@class="data-review-text"]/text()').extract() or ['N/A']
            item['customer_support'] = review.xpath('./div[@class="data-review-useful"]/text()')[0].extract() or 'N/A'
            item['customer_disagree'] = review.xpath('./div[@class="data-review-not-useful"]/text()')[0].extract() or 'N/A'

            yield item
