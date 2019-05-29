# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import next
import re
import time as timenow
import math
from datetime import datetime, tzinfo, timedelta, date, time
import pytz
import difflib
import yaml

timeFormat = "%Y-%m-%dT%H:%M:%S"
# https://github.com/matiasb/python-unidiff/blob/master/unidiff/constants.py#L37
# @@ (source offset, length) (target offset, length) @@ (section header)
RE_HUNK_HEADER = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))?\ @@[ ]?(.*)$", flags=re.MULTILINE
)


def formatTime(t):
    """ Properly Format Time for permlinks
    """
    if isinstance(t, float):
        return datetime.utcfromtimestamp(t).strftime("%Y%m%dt%H%M%S%Z")
    if isinstance(t, (datetime, date, time)):
        return t.strftime("%Y%m%dt%H%M%S%Z")


def addTzInfo(t, timezone="UTC"):
    """Returns a datetime object with tzinfo added"""
    if t and isinstance(t, (datetime, date, time)) and t.tzinfo is None:
        utc = pytz.timezone(timezone)
        t = utc.localize(t)
    return t


def formatTimeString(t):
    """ Properly Format Time for permlinks
    """
    if isinstance(t, (datetime, date, time)):
        return t.strftime(timeFormat)
    return addTzInfo(datetime.strptime(t, timeFormat))


def formatToTimeStamp(t):
    """ Returns a timestamp integer

        :param datetime t: datetime object
        :return: Timestamp as integer
    """
    if isinstance(t, (datetime, date, time)):
        t = addTzInfo(t)
    else:
        t = formatTimeString(t)
    epoch = addTzInfo(datetime(1970, 1, 1))
    return int((t - epoch).total_seconds())


def formatTimeFromNow(secs=0):
    """ Properly Format Time that is `x` seconds in the future

        :param int secs: Seconds to go in the future (`x>0`) or the
                         past (`x<0`)
        :return: Properly formated time for Graphene (`%Y-%m-%dT%H:%M:%S`)
        :rtype: str

    """
    return datetime.utcfromtimestamp(timenow.time() + int(secs)).strftime(timeFormat)


def formatTimedelta(td):
    """Format timedelta to String
    """
    if not isinstance(td, timedelta):
        return ""
    days, seconds = td.days, td.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return "%d:%s:%s" % (hours, str(minutes).zfill(2), str(seconds).zfill(2))


def parse_time(block_time):
    """Take a string representation of time from the blockchain, and parse it
       into datetime object.
    """
    utc = pytz.timezone("UTC")
    return utc.localize(datetime.strptime(block_time, timeFormat))


def assets_from_string(text):
    """Correctly split a string containing an asset pair.

    Splits the string into two assets with the separator being on of the
    following: ``:``, ``/``, or ``-``.
    """
    return re.split(r"[\-:/]", text)


def sanitize_permlink(permlink):
    permlink = permlink.strip()
    permlink = re.sub("_|\s|\.", "-", permlink)
    permlink = re.sub("[^\w-]", "", permlink)
    permlink = re.sub("[^a-zA-Z0-9-]", "", permlink)
    permlink = permlink.lower()
    return permlink


def remove_from_dict(obj, keys=list(), keep_keys=True):
    """ Prune a class or dictionary of all but keys (keep_keys=True).
        Prune a class or dictionary of specified keys.(keep_keys=False).
    """
    if type(obj) == dict:
        items = list(obj.items())
    elif isinstance(obj, dict):
        items = list(obj.items())
    else:
        items = list(obj.__dict__.items())
    if keep_keys:
        return {k: v for k, v in items if k in keys}
    else:
        return {k: v for k, v in items if k not in keys}


def make_patch(a, b, n=3):
    # _no_eol = '\n' + "\ No newline at end of file" + '\n'
    _no_eol = "\n"
    diffs = difflib.unified_diff(a.splitlines(True), b.splitlines(True), n=n)
    try:
        _, _ = next(diffs), next(diffs)
        del _
    except StopIteration:
        pass
    return "".join([d if d[-1] == "\n" else d + _no_eol for d in diffs])


def findall_patch_hunks(body=None):
    return RE_HUNK_HEADER.findall(body)


def seperate_yaml_dict_from_body(content):
    parameter = {}
    body = ""
    if len(content.split("---")) > 1:
        body = content[content.find("---", 1) + 3 :]
        yaml_content = content[content.find("---") + 3 : content.find("---", 1)]
        parameter = yaml.load(yaml_content)
        if not isinstance(parameter, dict):
            parameter = yaml.load(yaml_content.replace(":", ": ").replace("  ", " "))
    else:
        body = content
    return body, parameter
