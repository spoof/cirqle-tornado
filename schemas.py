# -*- coding: utf-8 -*-
import json
from datetime import datetime

import iso8601
from pytz import timezone, utc
from schema import Schema, Use, And, Optional

from settings import TIMEZONE


tz = timezone(TIMEZONE)
BEGIN_DATE = iso8601.parse_date("2013-01-01 00:00:00").replace(tzinfo=None)

create_item_schema = Schema(And(Use(json.loads), {
    'item': {
        'group_id': And(Use(int), lambda x: x > 0,
                        error="'group_id' should be positive integer"),
        'name': And(Use(str), lambda s: len(s) <= 5,
                    error="'name' should be string with length <= 5"),
        'datetime':  And(Use(iso8601.parse_date),
                         Use(lambda x: x.astimezone(utc).replace(tzinfo=None)),
                         lambda d: BEGIN_DATE < d <= datetime.utcnow(),
                         error=("'datetime' should be ISO8601 in range "
                                "(2013-01-01 00:00:00, NOW)")),
    }
}))

pagination_schema = Schema({
    'group_id': And(Use(int), lambda x: x > 0,
                    error="'group_id' should be positive integer"),
    Optional('offset'): And(Use(int), lambda x: x >= 0,
                            error="'offset' should be positive integer or 0"),
})
