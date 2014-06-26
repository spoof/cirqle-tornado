#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import json
import datetime
import unittest
import httplib

from tornado.testing import AsyncTestCase, gen_test
from tornado.httpclient import AsyncHTTPClient, HTTPError

HOSTNAME = 'localhost:8888'
ITEM_CREATE_URL = 'http://%s/items' % HOSTNAME

ITEM_DATE = datetime.datetime.utcnow().replace(microsecond=0).isoformat()


class ItemsTestCase(AsyncTestCase):

    @gen_test
    def test_item_creation(self):
        item = {
            'item': {
                'group_id': 1,
                'name': 'name',
                'datetime': ITEM_DATE,
            },
        }
        client = AsyncHTTPClient(self.io_loop)
        response = yield client.fetch(ITEM_CREATE_URL, method='POST',
                                      body=json.dumps(item))
        master_response = item
        master_response['item'].update({
            'id': 1,
            'position': 1,
        })
        response_data = json.loads(response.body)
        self.assertDictEqual(master_response, response_data)

    @gen_test
    def test_item_creation_invalid(self):
        item = {
            'item': {
                'group_id': 1,
                'name': 'name',
                'datetime': '',
            },
        }
        client = AsyncHTTPClient(self.io_loop)
        try:
            yield client.fetch(ITEM_CREATE_URL, method='POST',
                               body=json.dumps(item))
        except HTTPError as e:
            self.assertEqual(e.code, httplib.BAD_REQUEST)

            response_data = json.loads(e.response.body)
            self.assertIn('error', response_data)
            self.assertIn("'datetime' should be ISO8601 in range",
                          response_data['error'])
        else:
            self.fail('Response must fails with code %s' % httplib.BAD_REQUEST)

    @gen_test
    def test_item_getting(self):
        item_id = 1
        item = {
            'item': {
                'id': item_id,
                'group_id': 1,
                'name': 'name',
                'datetime': ITEM_DATE,
                'position': 1,
            },
        }
        client = AsyncHTTPClient(self.io_loop)
        response = yield client.fetch(ITEM_CREATE_URL + "/%s" % item_id)
        self.assertDictEqual(item, json.loads(response.body))


if __name__ == '__main__':
    unittest.main()
