# -*- coding: utf-8 -*-
import httplib
import logging
from itertools import chain
import time

import tornado
from tornado import gen
from schema import SchemaError

from route import route
from schemas import create_item_schema, pagination_schema
from settings import ITEMS_PER_PAGE
from utils import ObjectDict


class BaseAPIHandler(tornado.web.RequestHandler):
    """Base class for all API handlers"""

    def write_error(self, status_code, **kwargs):
        response = {
            'error': self._reason or 'Unknown error'
        }

        if ('exc_info' in kwargs and
                isinstance(kwargs['exc_info'][1], SchemaError)):
            e = kwargs['exc_info'][1]
            response['error'] = ', '.join(filter(None,
                                                 chain(e.errors, e.autos)))
            self.set_status(400)

        self.finish(response)

    def get_form_data(self):
        """Prepare data for forms and validators

        urlparse.parse_qs function converts all values to list, but it's wrong.
        We need to convert values to string by default and convert it  to list
        when we get a few values for the same key only
        """
        arguments_dict = dict(self.request.arguments.items() +
                              self.request.files.items())

        return dict([(k, v if len(v) > 1 else v[0])
                    for k, v in arguments_dict.iteritems()])

    @property
    def db(self):
        return self.application.db


class BaseItemsHandler(BaseAPIHandler):
    """Base handler for all item handlers"""

    @gen.coroutine
    def get_item_position(self, item):
        """Calculates item position in group

        It uses MySQL query with subquery based on datetime ordering
        """

        position_sql = """
            SELECT
                COUNT(*) + 1 as position
            FROM
                items
            FORCE INDEX (i_group_datetime)
            WHERE
                `datetime` >= (
                    SELECT
                        `datetime`
                    FROM
                        items
                    WHERE id=%s)
            AND group_id = %s
            AND id != %s
            ORDER BY datetime DESC
        """
        t1 = time.time()
        position, error = yield self.db.tquery(
            position_sql, [item.id, item.group_id, item.id]
        )
        logging.debug('Position query time %s', time.time() - t1)

        raise gen.Return(int(position[0].position))


@route('/items')
class ItemsHandler(BaseItemsHandler):
    """Handler for working with a bunch of items"""

    @gen.coroutine
    def get(self):
        """
        2 - GET /items?group_id=<integer>&offset=<integer>
        получение списка объектов item в определенной группе, отсортированного
        по полю datetime по убыванию
        где:
            group_id - группа, из которой запрашиваются элементы
            offset - отступ от начала списка (начало списка содержит элемент с
                                              наибольшим значением position и
                                              datetime)

        Тело ответа:
        {
            items: [
                {
                    "id": <integer>,
                    "name": <string>,
                    "datetime": <datetime>,
                    "position": <integer>
                },
                {
                    "id": <integer>,
                    "name": <string>,
                    "datetime": <datetime>,
                    "position": <integer>
                },
            ],
            items_count: <integer> # количество объектов item в группе с
                                   # идентификатором group_id
        }
        """

        t1 = time.time()
        validated_data = pagination_schema.validate(self.get_form_data())
        offset = validated_data.get('offset', 0)
        group_id = validated_data['group_id']

        sql = """
            SELECT SQL_NO_CACHE
                i.*
            FROM  (
                SELECT
                    id
                FROM
                    `items`
                WHERE
                    group_id = %s
                ORDER BY
                    datetime DESC
                LIMIT %s, %s
                ) o
            JOIN items i
            ON i.id = o.id
            ORDER BY datetime DESC, id ASC;
        """
        c_sql = """
            SELECT
                count
            FROM
                `group_totals`
            WHERE
                group_id = %s
        """
        items, error = yield self.db.tquery(
            sql, [group_id, offset, ITEMS_PER_PAGE]
        )
        items = items or []

        result_c, error = yield self.db.tquery(
            c_sql, [group_id, ]
        )
        logging.debug('result_c %s', result_c)
        try:
            count = result_c[0]['count']
        except IndexError:
            count = 0

        items_ = []
        for position, item in enumerate(items):
            item_data = {
                'id': item.id,
                'group_id': item.group_id,
                'name': item.name,
                'datetime': item.datetime.isoformat(),
                'position': offset + position + 1,
            }
            items_.append(item_data)

        logging.debug('time %s', time.time() - t1)
        self.write(dict(items=items_, items_count=count))

    @gen.coroutine
    def post(self):
        """Create item

        Input:
        {
            item: {
                "group_id": <integer>,  # идентификатор группы, к которой
                                        # относится элемент, диапазон значений
                                        # 1 - 1 000 000
                "name": <string>,       # random текст от 0 до 5 слов
                "datetime": <datetime>, # random дата и время в формате
                                        # ISO-8601, диапазон значений
                                        # 2013-01-01 00:00:00 - NOW()
            }
        }

        Response:
        {
            item: {
                "id": <integer>,        # уникальный идентификатор элемента
                "group_id": <integer>,
                "name": <string>,
                "datetime": <datetime>,
                "position": <integer>   # позиция элемента в списке с одинаковым
                                        # значением поля group_id,
                                        # отсортированном по полю datetime по
                                        # убыванию (position со значением 1 у
                                        # элемента с наименьшим значением в поле
                                        # datetime)
            }
        }
        """
        print self.request.body
        validated_data = create_item_schema.validate(self.request.body)
        item_data = validated_data['item']

        item = ObjectDict({
            'id': None,
            'group_id': item_data['group_id'],
            'name': item_data['name'],
            'datetime': item_data['datetime'],
            'position': None,
        })

        sql = """
            INSERT INTO `items` (group_id, name, datetime)
            VALUES (%s, %s, %s)
        """
        item.id, error = yield self.db.tinsert(
            sql, [item.group_id, item.name, item.datetime]
        )

        if error:
            logging.error('error %s', error)
            raise Exception('Error on saving to db')

        sql = """
            INSERT INTO `group_totals` (group_id, count)
            VALUES (%s, 0) ON DUPLICATE KEY UPDATE count=count+1
        """
        _, error = yield self.db.tinsert(
            sql, [item.group_id, ]
        )

        item.position = yield self.get_item_position(item)
        item_data = {
            'id': item.id,
            'group_id': item.group_id,
            'name': item.name,
            'datetime': item.datetime.isoformat(),
            'position': item.position,
        }
        self.set_status(httplib.CREATED)
        self.write(dict(item=item_data))


@route(r'/items/(\d+)')
class ItemHandler(BaseItemsHandler):
    """Handler for working with the single item"""

    @gen.coroutine
    def get_item_with_multiple_queries(self, item_id):
        """Gets item from database and calculates its position"""
        item_sql = """
            SELECT
                *
            FROM
                `items`
            WHERE id = %s
        """
        t1 = time.time()
        item, error = yield self.db.tquery(item_sql, [item_id, ])
        logging.debug('Query time %s', time.time() - t1)

        if not item:
            raise gen.Return((None, None))

        item = item[0]
        position = yield self.get_item_position(item)

        raise gen.Return((item, position))

    @gen.coroutine
    def get(self, item_id):
        """
        3 - GET /items/:id - получение объекта item

        Тело ответа:
        {
            item: {
                "id": <integer>,
                "group_id": <integer>,
                "name": <string>,
                "datetime": <datetime>,
                "position": <integer>
            }
        }
        """
        item, position = yield self.get_item_with_multiple_queries(item_id)

        if not item:
            self.write(dict(error='No such item'))
            self.set_status(httplib.NOT_FOUND)
            raise gen.Return()
        item_data = {
            'id': item.id,
            'group_id': item.group_id,
            'name': item.name,
            'datetime': item.datetime.isoformat(),
            'position': int(position)
        }
        self.write(dict(item=item_data))
