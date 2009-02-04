#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This module contains functions to manipulate very restricted UTC
timestamps and time deltas.
'''

import time as _time
import datetime as _datetime

from BTL.canonical.unicode import to_utf8 as _to_utf8


def to_datetime(dt):
    '''
    Convert dt to a datetime.datetime instance if it is not one
    already. Other acceptable input types:

    tuple or time.struct_time: UTC time tuple, as returned by time.gmtime()

    int or float: timestamp (seconds since the Epoch) as returned by
    time.time()

    str or unicode: UTC timestamp in the following ISO-8601-compatible
    format: "YYYY-mm-ddTHH:MM:SS+00:00" with the following fields:

        "YYYY": year

        "mm": month

        "dd": day

        "T": the letter "T"

        "HH": hours (24-hr)

        "MM": minutes

        "SS": seconds

        "+00:00": time zone indicator for UTC
    '''
    if isinstance(dt, (tuple, _time.struct_time)):
        dt = _time.strftime('%Y-%m-%dT%H:%M:%S+00:00', dt)
    if isinstance(dt, (str, unicode)):
        dt = _time.mktime(_time.strptime(_to_utf8(dt),
                                         '%Y-%m-%dT%H:%M:%S+00:00'))
        if isinstance(dt, (int, float)):
            dt = _datetime.datetime.fromtimestamp(dt)
    if isinstance(dt, (int, float)):
        dt = _datetime.datetime.utcfromtimestamp(dt)
    if not isinstance(dt, _datetime.datetime):
        raise TypeError('TypeError: to_datetime() argument must be a datetime.datetime instance, tuple, time.struct_time, int, float, str, or unicode')
    return dt

def to_8601(dt):
    '''
    Convert a datetime.datetime dt to a UTC timestamp in the following
    ISO-8601-compatible format: "YYYY-mm-ddTHH:MM:SS+00:00" with the
    following fields:

        "YYYY": year

        "mm": month

        "dd": day

        "T": the letter "T"

        "HH": hours (24-hr)

        "MM": minutes

        "SS": seconds

        "+00:00": time zone indicator for UTC

    NOTE: input is first converted using to_datetime(dt)
    '''
    dt = to_datetime(dt)
    return '%04.4d-%02.2d-%02.2dT%02.2d:%02.2d:%02.2d+00:00' % dt.utctimetuple()[:6]

def to_timedelta(td):
    '''
    Convert td to a datetime.timedelta instance if it is not one
    already. Other acceptable input types:

    int, float: number of seconds

    str, unicode: stringified floating-point number of seconds
    '''
    if isinstance(td, (str, unicode)):
        td = float(_to_utf8(td))
    if isinstance(td, (int, float)):
        td = _datetime.timedelta(0, td)
    if not isinstance(td, _datetime.timedelta):
        raise TypeError('TypeError: to_timedelta() argument must be a datetime.timedelta instance, int, float, str, or unicode')
    return td

def to_seconds(td):
    '''
    Convert a datetime.timedelta td to a floating-point number of seconds.

    NOTE: input is first converted using to_timedelta(td)
    '''
    td = to_timedelta(td)
    return td.days * 86400 + td.seconds + td.microseconds * 1e-6

def test():
    '''
    Trivial smoke tests to make sure this module has not broken.
    '''
    for i, o in (
        (_datetime.datetime(2006, 9, 23),
         '2006-09-23T00:00:00+00:00',
         ),
        (_datetime.datetime(2006, 9, 23, 0, 0, 0),
         '2006-09-23T00:00:00+00:00',
         ),
        ('2006-09-23T00:00:00+00:00',
         '2006-09-23T00:00:00+00:00',
         ),
        (_datetime.datetime(1970, 1, 1),
         '1970-01-01T00:00:00+00:00',
         ),
        (0,
         '1970-01-01T00:00:00+00:00',
         ),
        (0.0,
         '1970-01-01T00:00:00+00:00',
         ),
        ('1970-01-01T00:00:00+00:00',
         '1970-01-01T00:00:00+00:00',
         ),
        ('2006-02-02T01:30:00+00:00',
         '2006-02-02T01:30:00+00:00',
         ),
        ('2006-02-02T02:30:00+00:00',
         '2006-02-02T02:30:00+00:00',
         ),
        ('2006-02-02T03:30:00+00:00',
         '2006-02-02T03:30:00+00:00',
         ),
        ('2006-10-29T01:30:00+00:00',
         '2006-10-29T01:30:00+00:00',
         ),
        ('2006-10-29T02:30:00+00:00',
         '2006-10-29T02:30:00+00:00',
         ),
        ('2006-10-29T03:30:00+00:00',
         '2006-10-29T03:30:00+00:00',
         ),
        (1161912600,
         '2006-10-27T01:30:00+00:00',
         ),
        (1161851400,
         '2006-10-26T08:30:00+00:00',
         ),
        (1161916200,
         '2006-10-27T02:30:00+00:00',
         ),
        (1161855000,
         '2006-10-26T09:30:00+00:00',
         ),
        (1161919800,
         '2006-10-27T03:30:00+00:00',
         ),
        (1161858600,
         '2006-10-26T10:30:00+00:00',
         ),
        ):
        assert to_8601(i) == o
        assert to_datetime(o) == to_datetime(i)
        assert to_datetime(o) + to_timedelta(8*60*60) == to_datetime(i) + to_timedelta(8*60*60)
        assert to_datetime(o) + to_timedelta(7*60*60) == to_datetime(i) + to_timedelta(7*60*60)
        assert to_datetime(o) - to_timedelta(8*60*60) == to_datetime(i) - to_timedelta(8*60*60)
        assert to_datetime(o) - to_timedelta(7*60*60) == to_datetime(i) - to_timedelta(7*60*60)
    for i, o in (
        (_datetime.timedelta(0, 3.141528),
         3.141528,
        ),
        (3.141528,
         3.141528,
        ),
        ('3.141528',
         3.141528,
        ),
        (_datetime.timedelta(0),
         0.0,
        ),
        (0,
         0.0,
        ),
        (0.0,
         0.0,
        ),
        ('0',
         0.0,
        ),
        ('0.0',
         0.0,
        ),
        ):
        assert to_seconds(i) == o
        assert to_timedelta(o) == to_timedelta(i)
    

test()
