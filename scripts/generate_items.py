#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import time
import sys
import random
import cStringIO
import logging
import json
from datetime import timedelta, datetime

import pycurl
import iso8601
import MySQLdb


log = logging.getLogger(__name__)

PORT = 8888
URL = "http://localhost:%d/items" % PORT
MIN_DATE = iso8601.parse_date("2013-01-01 00:00:00").replace(tzinfo=None)
MAX_DATE = datetime.utcnow()

_REQUEST_INFO = {
    # curl.perform() | NAMELOOKUP > CONNECT > APPCONNECT > PRETRANSFER >
    # STARTTRANSFER | TOTAL
    "namelookup": pycurl.NAMELOOKUP_TIME,  # from the start until the name
                                           # resolving was completed
    "connect": pycurl.CONNECT_TIME,  # from the phase start until the connect
                                     # to the remote host (or proxy) was
                                     # completed
    "appconnect": pycurl.APPCONNECT_TIME,  # from the phase start until the SSL
                                           # connect/handshake with the remote
                                           # host was completed
    "pretransfer": pycurl.PRETRANSFER_TIME,  # from the phase start until the
                                             # file transfer is just about to
                                             # begin
    "starttransfer": pycurl.STARTTRANSFER_TIME,  # from the phase start until
                                                 # the first byte is received
                                                 # by libcurl
    "total": pycurl.TOTAL_TIME,  # total time of the request
    "redirect": pycurl.REDIRECT_TIME,  # the time it took for all redirection
                                       # steps before final transaction was
                                       # started
    # General info on request
    "download": pycurl.SIZE_DOWNLOAD,
    "code": pycurl.HTTP_CODE,
}
INFO_TMPL = ("I: g={group_id}, n={name}, d={datetime} => "
             "total: {total:.4f} [ms], code: {code}")


ITEM_GROUPS = [
    {'items_range': [1, 10], 'count': 0.9},
    {'items_range': [11, 50], 'count': 0.07},
    {'items_range': [51, 100], 'count': 0.025},
    {'items_range': [101, 500], 'count': 0.004},
    {'items_range': [501, 1000], 'count': 0.0008},
    {'items_range': [1001, 5000], 'count': 0.00019},
    {'items_range': [5001, 100000], 'count': 0.00001},
]
TOTAL_GROUPS = 1000000


def random_date(start, end):
    """
    This function will return a random datetime between two datetime
    objects.
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)


def generate_items(group_id, count):
    for i in range(count):
        yield {
            'group_id': group_id,
            'name': 'item'[:random.randint(0, 4)],
            'datetime': random_date(MIN_DATE, MAX_DATE).isoformat(),
        }


def generate_group(group_start_id, item_range, count):
    to_generate = TOTAL_GROUPS * count
    group_id = group_start_id

    generated = 0
    while generated < to_generate:
        items_count = random.randint(*item_range)
        group = {
            'group_id': int(group_id),
            'items': generate_items(group_id, items_count),
            'items_count': items_count,
        }
        group_id += 1
        generated += 1

        yield group


def save_via_api(start_id, groups_to_generate):
    curl = pycurl.Curl()
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.WRITEFUNCTION, cStringIO.StringIO().write)
    curl.setopt(pycurl.URL, URL)

    next_id = start_id

    log.info("Creating items (be patient).....")
    for groups_data in ITEM_GROUPS:
        groups = generate_group(next_id,
                                groups_data['items_range'],
                                groups_data['count'])

        for group in groups:
            # send to server
            for item in group['items']:
                curl.setopt(pycurl.POSTFIELDS, json.dumps(dict(item=item)))
                try:
                    curl.perform()
                except:
                    raise

                info = {}
                for k, v in _REQUEST_INFO.iteritems():
                    info[k] = curl.getinfo(v)
                info.update(item)
                log.info(INFO_TMPL.format(**info))

            next_id += 1

    print "Groups generated %s" % (next_id - start_id)


def save_via_db(start_id, groups_to_generate):
    db = MySQLdb.connect('localhost', 'cirqle', 'cirqle', 'cirqle')
    cursor = db.cursor()

    sql = """
        INSERT INTO `items` (group_id, name, datetime)
        VALUES (%(group_id)s, %(name)s, %(datetime)s)
    """
    next_id = start_id
    items = []

    log.info("Creating items (be patient).....")
    for i, groups_data in enumerate(groups_to_generate):
        groups = generate_group(next_id, groups_data['items_range'],
                                groups_data['count'])

        last_bunch = True if i + 1 >= len(groups_to_generate) else False
        print "last_bunch", last_bunch
        for gi, group in enumerate(groups):
            last_group = True if gi + 1 == group['items_count'] else False
            if last_group:
                print "last_group", last_group
            items.extend(list(group['items']))

            next_id += 1

            if len(items) >= 50000 or (last_bunch and last_group):
                print "Dump %s items" % (len(items))
                cursor.executemany(sql, items)
                db.commit()
                items = []

    print "Groups generated %s" % (next_id - 1 - start_id)


def main():
    channel = logging.StreamHandler()
    log.addHandler(channel)
    log.setLevel(logging.DEBUG)

    def get_start_id(group):
        start_id = 1
        for g in ITEM_GROUPS:
            if group == g:
                break
            count = TOTAL_GROUPS * g['count']
            start_id += count

        return start_id

    # start_id = get_start_id(ITEM_GROUPS[6])
    start_id = 0
    print('start_id %s' % start_id)
    # groups_to_generate = ITEM_GROUPS[6:]
    groups_to_generate = ITEM_GROUPS

    #save_via_api(start_id, groups_to_generate)
    save_via_db(start_id, groups_to_generate)


if __name__ == '__main__':
    start_time = time.time()

    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by Ctrl-C")

    sys.exit(1)
