# -*- coding: utf-8 -*-
import re
from datetime import datetime, time

from city_scrapers.constants import BOARD, COMMITTEE
from city_scrapers.spider import Spider


class ChiTeacherPensionSpider(Spider):
    name = 'chi_teacherpension'
    agency_name = 'Chicago Teachers Pension Fund'
    timezone = 'America/Chicago'
    allowed_domains = ['www.ctpf.org']
    start_urls = ['https://www.ctpf.org/post/board-meetings']

    def parse(self, response):
        """
        `parse` should always `yield` a dict that follows the Event Schema
        <https://city-bureau.github.io/city-scrapers/06_event_schema.html>.

        Change the `_parse_id`, `_parse_name`, etc methods to fit your scraping
        needs.
        """
        LOCATION = {
            'address': '203 N LaSalle St, Suite 2600 Board Room, Chicago, IL 60601',
            'name': 'CTPF office',
            'neighborhood': 'Loop'
        }
        # Iterate through headers which mark the meeting groups
        for meeting_group in response.css('#node-full .node-content h3, h4'):
            group_name = self._parse_name(meeting_group)
            if 'minutes' in group_name.lower():
                continue
            # Go through each sibling to get the next paragraph tag
            next_sib = meeting_group.xpath('following-sibling::*[1]')
            while len(next_sib) and next_sib[0].root.tag == 'ul':
                for item in next_sib.xpath('li'):
                    item_text = item.xpath('text()').extract_first()
                    date_obj, time_obj = self._parse_datetime(item_text)
                    data = {
                        '_type': 'event',
                        'name': group_name,
                        'description': '',
                        'classification': self._parse_classification(group_name),
                        'start': self._parse_start(date_obj, time_obj),
                        'end': self._parse_end(date_obj),
                        'all_day': False,
                        'location': LOCATION,
                        'sources': self._parse_sources(response),
                        'documents': self._parse_documents(item.xpath('span')),
                    }
                    data['id'] = self._generate_id(data)
                    data['status'] = self._generate_status(data)
                    next_sib = next_sib.xpath('following-sibling::*[1]')
                    yield data

    def _parse_name(self, meeting_group):
        """
        Parse or generate event name.
        """
        return meeting_group.xpath('./text()').extract_first().replace(' Schedule',
                                                                       '').replace('\xa0', ' ')

    def _parse_classification(self, group_name):
        """
        Parse or generate classification (e.g. public health, education, etc).
        """
        if 'board' in group_name.lower():
            return BOARD
        else:
            return COMMITTEE

    @staticmethod
    def _parse_datetime(datetime_str):
        date_clean_re = r'[^:\s\w\d]'
        datetime_split = datetime_str.split(',')
        date_str = ','.join(datetime_str.split(',')[:3])
        time_str = None
        if len(datetime_split) > 3:
            time_str = datetime_split[3].replace('at', '')
        if ' at ' in date_str:
            date_str, time_str = date_str.split(' at ')
        date_obj = datetime.strptime(
            re.sub(date_clean_re, '', date_str).strip(),
            '%A %B %d %Y',
        ).date()

        if time_str:
            time_str = re.sub(date_clean_re, '', time_str)
            time_obj = datetime.strptime(time_str.strip(), '%I:%M %p').time()
        else:
            time_obj = None
        return date_obj, time_obj

    def _parse_start(self, date_obj, time_obj):
        """
        Parse start date and time.
        """
        return {
            'date': date_obj,
            'time': time_obj or time(9, 30),
            'note': '',
        }

    def _parse_end(self, date_obj):
        """
        Parse end date and time.
        """
        return {
            'date': date_obj,
            'time': None,
            'note': '',
        }

    def _parse_documents(self, item):
        if not item or len(item.xpath('./a')) == 0:
            return []
        link = item.xpath('./a')[0]
        return [{
            'note': link.xpath('.//text()').extract_first(),
            'url': 'https://www.ctpf.org{}'.format(link.xpath("./@href").extract_first()),
        }]

    def _parse_sources(self, response):
        """
        Parse or generate sources.
        """
        return [{'url': response.url, 'note': ''}]
