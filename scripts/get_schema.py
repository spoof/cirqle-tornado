#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

SCHEMAS = []


def create_table(query, debug=False):
    group = (debug, query)
    SCHEMAS.append(group)


def show_create_tables(debug=False):
    def _debug_mode_filter(group):
        debug_mode = group[0]
        if debug:
            return True
        else:
            return not debug_mode

    return '\n'.join([i[1] for i in filter(_debug_mode_filter, SCHEMAS)])


create_table('''
    CREATE TABLE IF NOT EXISTS `items` (
        `id` bigint auto_increment primary key,
        `group_id` bigint not null,
        `name` varchar(5) not null,
        `datetime` DATETIME,

        KEY `i_group` (`group_id`) USING BTREE,
        KEY `i_group_datetime_id` (`group_id`,`datetime`,`id`),
        KEY `i_group_datetime` (`group_id`,`datetime`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
''')


create_table('''
    CREATE TABLE IF NOT EXISTS `group_totals` (
        `group_id` bigint primary key,
        `count` varchar(5) not null

    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
''')


print show_create_tables(debug=False)
