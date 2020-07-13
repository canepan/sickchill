# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: https://sickchill.github.io
# Git: https://github.com/SickChill/SickChill.git
#
# This file is part of SickChill.
#
# SickChill is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickChill is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickChill. If not, see <http://www.gnu.org/licenses/>.

"""
Custom Logger for SickChill
"""

from __future__ import absolute_import, print_function, unicode_literals

# Stdlib Imports
import locale
import logging
import logging.handlers
import os
import platform
import re
import sys
import threading
import traceback
from logging import NullHandler

# Third Party Imports
import six
from github import InputFileContent
from github.GithubException import RateLimitExceededException, TwoFactorException
from requests.compat import quote
from six.moves import range

# First Party Imports
import sickbeard
from sickchill.helper.common import dateTimeFormat

# Local Folder Imports
from . import classes

# log levels
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
DB = 5

LOGGING_LEVELS = {
    'ERROR': ERROR,
    'WARNING': WARNING,
    'INFO': INFO,
    'DEBUG': DEBUG,
    'DB': DB,
}

censored_items = {}


class DispatchFormatter(logging.Formatter, object):
    """
    Censor information such as API keys, user names, and passwords from the Log
    """
    def __init__(self, fmt=None, datefmt=None, encoding='utf-8'):
        super(DispatchFormatter, self).__init__(fmt, datefmt)
        self.encoding = encoding

    def format(self, record):
        """
        Strips censored items from string and formats the log line

        :param record: to format
        """
        msg = super(DispatchFormatter, self).format(record)

        # set of censored items
        censored = {item for _, item in six.iteritems(censored_items) if item}
        # set of censored items and urlencoded counterparts
        censored = list(censored | {quote(item) for item in censored})
        # sort the list in order of descending length so that entire item is censored
        # e.g. password and password_1 both get censored instead of getting ********_1
        censored.sort(key=len, reverse=True)

        for item in censored:
            try:
                # passwords that include ++ for example will error. Cannot escape or it wont match at all.
                msg = re.sub(r'\b({item})\b'.format(item=item), '*' * 8, msg)
            except re.error:
                msg = msg.replace(item, '*' * 8)

        # Needed because Newznab apikey isn't stored as key=value in a section.
        msg = re.sub(r'([&?]r|[&?]apikey|[&?]jackett_apikey|[&?]api_key)(?:=|%3D)[^&]*([&\w]?)', r'\1=**********\2', msg, re.I)

        cur_hash = ''
        if record.levelno == ERROR and sickbeard.CUR_COMMIT_HASH and len(sickbeard.CUR_COMMIT_HASH) > 6:
            cur_hash = '[{0}] '.format(sickbeard.CUR_COMMIT_HASH[:7])

        cur_thread = threading.currentThread().getName().rstrip('_1234567890')

        if _('Missing time zone for network') in msg:
            message = '{thread} :: {message}'.format(
                thread=cur_thread, message=msg)
        else:
            message = '{thread} :: {hash}{message}'.format(
                thread=cur_thread, hash=cur_hash, message=msg)

        if record.levelno == ERROR:
            classes.ErrorViewer.add(classes.UIError(message))
        elif record.levelno == WARNING:
            classes.WarningViewer.add(classes.UIError(message))

        return msg


class Logger(object):
    """
    Logger to create log entries
    """
    def __init__(self):
        self.logger = logging.getLogger('sickchill')

        self.loggers = [
            logging.getLogger('sickchill'),
            logging.getLogger('tornado.general'),
            logging.getLogger('tornado.application'),
            # logging.getLogger('subliminal'),
            # logging.getLogger('tornado.access'),
            # logging.getLogger('tvdb_api'),
            # logging.getLogger("requests.packages.urllib3")
        ]

        self.console_logging = False
        self.file_logging = False
        self.debug_logging = False
        self.database_logging = False
        self.log_file = None

        self.submitter_running = False

    def init_logging(self, console_logging=False, file_logging=False, debug_logging=False, database_logging=False):
        """
        Initialize logging

        :param console_logging: True if logging to console
        :param file_logging: True if logging to file
        :param debug_logging: True if debug logging is enabled
        :param database_logging: True if logging database access
        """
        self.log_file = self.log_file or os.path.join(sickbeard.LOG_DIR, 'sickchill.log')

        global log_file
        log_file = self.log_file

        self.debug_logging = debug_logging
        self.console_logging = console_logging
        self.file_logging = file_logging
        self.database_logging = database_logging

        logging.addLevelName(DB, 'DB')  # add a new logging level DB
        logging.getLogger().addHandler(NullHandler())  # nullify root logger

        # set custom root logger
        for logger in self.loggers:
            if logger is not self.logger:
                logger.root = self.logger
                logger.parent = self.logger

        log_level = DB if self.database_logging else DEBUG if self.debug_logging else INFO

        # set minimum logging level allowed for loggers
        for logger in self.loggers:
            logger.setLevel(log_level)

        logging.getLogger("tornado.general").setLevel('ERROR')

        # console log handler
        if self.console_logging:
            console = logging.StreamHandler()
            console.setFormatter(DispatchFormatter('%(asctime)s %(levelname)s::%(message)s', '%H:%M:%S'))
            console.setLevel(log_level)

            for logger in self.loggers:
                logger.addHandler(console)

        # rotating log file handler
        if self.file_logging:
            rfh = logging.handlers.RotatingFileHandler(
                self.log_file, maxBytes=int(sickbeard.LOG_SIZE * 1048576), backupCount=sickbeard.LOG_NR, encoding='utf-8'
            )
            rfh.setFormatter(DispatchFormatter('%(asctime)s %(levelname)-8s %(message)s', dateTimeFormat))
            rfh.setLevel(log_level)

            for logger in self.loggers:
                logger.addHandler(rfh)

    def set_level(self):
        self.debug_logging = sickbeard.DEBUG
        self.database_logging = sickbeard.DBDEBUG

        level = DB if self.database_logging else DEBUG if self.debug_logging else INFO
        for logger in self.loggers:
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)

    @staticmethod
    def shutdown():
        """
        Shut down the logger
        """
        logging.shutdown()

    def log_error_and_exit(self, error_msg, *args, **kwargs):
        self.log(error_msg, ERROR, *args, **kwargs)

        if not self.console_logging:
            sys.exit(error_msg)
        else:
            sys.exit(1)

    def submit_errors(self):

        submitter_result = ''
        issue_id = None

        if not all((sickbeard.GIT_TOKEN, sickbeard.DEBUG, sickbeard.gh, classes.ErrorViewer.errors)):
            submitter_result = 'Please set your GitHub token in the config and enable debug. Unable to submit issue ticket to GitHub!'
            return submitter_result, issue_id

        try:
            from .versionChecker import CheckVersion
            checkversion = CheckVersion()
            checkversion.check_for_new_version()
            commits_behind = checkversion.updater.get_num_commits_behind()
        except Exception:
            submitter_result = 'Could not check if your SickChill is updated, unable to submit issue ticket to GitHub!'
            return submitter_result, issue_id

        if commits_behind is None or commits_behind > 0:
            submitter_result = 'Please update SickChill, unable to submit issue ticket to GitHub with an outdated version!'
            return submitter_result, issue_id

        if self.submitter_running:
            submitter_result = 'Issue submitter is running, please wait for it to complete'
            return submitter_result, issue_id

        self.submitter_running = True

        try:
            # read log file
            __log_data = None

            if os.path.isfile(self.log_file):
                with open(self.log_file) as log_f:
                    __log_data = log_f.readlines()

            for i in range(1, int(sickbeard.LOG_NR)):
                f_name = '{0}.{1:d}'.format(self.log_file, i)
                if os.path.isfile(f_name) and (len(__log_data) <= 500):
                    with open(f_name) as log_f:
                        __log_data += log_f.readlines()

            __log_data = list(reversed(__log_data))

            # parse and submit errors to issue tracker
            for cur_error in sorted(classes.ErrorViewer.errors, key=lambda error: error.time, reverse=True)[:500]:
                try:
                    title_error = str(cur_error.title)
                    if not title_error or title_error == 'None':
                        title_error = re.match(r'^[A-Za-z0-9\-\[\] :]+::\s(?:\[[\w]{7}\])\s*(.*)$', cur_error.message).group(1)

                    if len(title_error) > 1000:
                        title_error = title_error[0:1000]

                except Exception as err_msg:
                    self.log('Unable to get error title : {0}'.format(str(err_msg)), ERROR)
                    title_error = 'UNKNOWN'

                gist = None
                regex = r'^(?P<time>{time})\s+(?P<level>[A-Z]+)\s+[A-Za-z0-9\-\[\] :]+::.*$'.format(time=re.escape(cur_error.time))
                for i, data in enumerate(__log_data):
                    match = re.match(regex, data)
                    if match:
                        level = match.group('level')
                        if LOGGING_LEVELS[level] == ERROR:
                            paste_data = ''.join(__log_data[i:i + 50])
                            if paste_data:
                                gist = sickbeard.gh.get_user().create_gist(False, {'sickchill.log': InputFileContent(paste_data)})
                            break
                    else:
                        gist = 'No ERROR found'

                try:
                    locale_name = locale.getdefaultlocale()[1]
                except Exception:
                    locale_name = 'unknown'

                if gist and gist != 'No ERROR found':
                    log_link = 'Link to Log: {0}'.format(gist.html_url)
                else:
                    log_link = 'No Log available with ERRORS:'

                msg = [
                    '### INFO',
                    'Python Version: **{0}**'.format(sys.version[:120].replace('\n', '')),
                    'Operating System: **{0}**'.format(platform.platform()),
                    'Locale: {0}'.format(locale_name),
                    'Branch: **{0}**'.format(sickbeard.BRANCH),
                    'Commit: SickChill/SickChill@{0}'.format(sickbeard.CUR_COMMIT_HASH),
                    log_link,
                    '### ERROR',
                    '```',
                    cur_error.message,
                    '```',
                    '---',
                    '_STAFF NOTIFIED_: @SickChill/owners @SickChill/moderators',
                ]

                message = '\n'.join(msg)
                title_error = '[APP SUBMITTED]: {0}'.format(title_error)

                repo = sickbeard.gh.get_organization(sickbeard.GIT_ORG).get_repo(sickbeard.GIT_REPO)
                reports = repo.get_issues(state='all')

                def is_ascii_error(title):
                    # [APP SUBMITTED]: 'ascii' codec can't encode characters in position 00-00: ordinal not in range(128)
                    # [APP SUBMITTED]: 'charmap' codec can't decode byte 0x00 in position 00: character maps to <undefined>
                    return re.search(r'.* codec can\'t .*code .* in position .*:', title) is not None

                def is_malformed_error(title):
                    # [APP SUBMITTED]: not well-formed (invalid token): line 0, column 0
                    return re.search(r'.* not well-formed \(invalid token\): line .* column .*', title) is not None

                ascii_error = is_ascii_error(title_error)
                malformed_error = is_malformed_error(title_error)

                issue_found = False
                for report in reports:
                    if title_error.rsplit(' :: ')[-1] in report.title or \
                        (malformed_error and is_malformed_error(report.title)) or \
                            (ascii_error and is_ascii_error(report.title)):

                        issue_id = report.number
                        if not report.raw_data['locked']:
                            if report.create_comment(message):
                                submitter_result = 'Commented on existing issue #{0} successfully!'.format(issue_id)
                            else:
                                submitter_result = 'Failed to comment on found issue #{0}!'.format(issue_id)
                        else:
                            submitter_result = 'Issue #{0} is locked, check GitHub to find info about the error.'.format(issue_id)

                        issue_found = True
                        break

                if not issue_found:
                    issue = repo.create_issue(title_error, message)
                    if issue:
                        issue_id = issue.number
                        submitter_result = 'Your issue ticket #{0} was submitted successfully!'.format(issue_id)
                    else:
                        submitter_result = 'Failed to create a new issue!'

                if issue_id and cur_error in classes.ErrorViewer.errors:
                    # clear error from error list
                    classes.ErrorViewer.errors.remove(cur_error)
        except RateLimitExceededException:
            submitter_result = 'Your Github user has exceeded its API rate limit, please try again later'
            issue_id = None
        except TwoFactorException:
            submitter_result = ('Your Github account requires Two-Factor Authentication, '
                                'please change your auth method in the config')
            issue_id = None
        except Exception:
            self.log(traceback.format_exc(), ERROR)
            submitter_result = 'Exception generated in issue submitter, please check the log'
            issue_id = None
        finally:
            self.submitter_running = False

        return submitter_result, issue_id


class Wrapper(object):
    instance = Logger()

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, name):
        try:
            return getattr(self.wrapped, name)
        except AttributeError:
            return getattr(self.instance, name)


_globals = sys.modules[__name__] = Wrapper(sys.modules[__name__])

LOG_FILTERS = {
    '<NONE>': _('&lt;No Filter&gt;'),
    'DAILYSEARCHER': _('Daily Searcher'),
    'BACKLOG': _('Backlog'),
    'SHOWUPDATER': _('Show Updater'),
    'CHECKVERSION': _('Check Version'),
    'SHOWQUEUE': _('Show Queue'),
    'SEARCHQUEUE': _('Search Queue (All)'),
    'SEARCHQUEUE-DAILY-SEARCH': _('Search Queue (Daily Searcher)'),
    'SEARCHQUEUE-BACKLOG': _('Search Queue (Backlog)'),
    'SEARCHQUEUE-MANUAL': _('Search Queue (Manual)'),
    'SEARCHQUEUE-RETRY': _('Search Queue (Retry/Failed)'),
    'SEARCHQUEUE-RSS': _('Search Queue (RSS)'),
    'FINDPROPERS': _('Find Propers'),
    'POSTPROCESSOR': _('Postprocessor'),
    'FINDSUBTITLES': _('Find Subtitles'),
    'TRAKTCHECKER': _('Trakt Checker'),
    'EVENT': _('Event'),
    'ERROR': _('Error'),
    'TORNADO': _('Tornado'),
    'Thread': _('Thread'),
    'MAIN': _('Main'),
}


def log_data(min_level, log_filter, log_search, max_lines):
    regex = r"^(\d\d\d\d)\-(\d\d)\-(\d\d)\s*(\d\d)\:(\d\d):(\d\d)\s*([A-Z]+)\s*(.+?)\s*\:\:\s*(.*)$"
    if log_filter not in LOG_FILTERS:
        log_filter = '<NONE>'

    final_data = []

    log_files = []
    if os.path.isfile(Wrapper.instance.log_file):
        log_files.append(Wrapper.instance.log_file)

        for i in range(1, int(sickbeard.LOG_NR)):
            name = Wrapper.instance.log_file + "." + str(i)
            if not os.path.isfile(name):
                break
            log_files.append(name)
    else:
        return final_data

    data = []
    for _log_file in log_files:
        if len(data) < max_lines:
            with open(_log_file, 'r') as f:
                data += [line.strip() + '\n' for line in reversed(f.readlines()) if line.strip()]
        else:
            break

    found_lines = 0
    for x in data:
        match = re.match(regex, x)

        if match:
            level = match.group(7)
            log_name = match.group(8)

            if not sickbeard.DEBUG and level == 'DEBUG':
                continue

            if not sickbeard.DBDEBUG and level == 'DB':
                continue

            if level not in LOGGING_LEVELS:
                final_data.append('AA ' + x)
                found_lines += 1
            elif log_search and log_search.lower() in x.lower():
                final_data.append(x)
                found_lines += 1
            elif not log_search and LOGGING_LEVELS[level] >= int(min_level) and (log_filter == '<NONE>' or log_name.startswith(log_filter)):
                final_data.append(x)
                found_lines += 1
        else:
            final_data.append('AA ' + x)
            found_lines += 1

        if found_lines >= max_lines:
            break

    return final_data


log_error_and_exit = Wrapper.instance.log_error_and_exit
log_file = Wrapper.instance.log_file

log = Wrapper.instance.logger.log
debug = Wrapper.instance.logger.debug
info = Wrapper.instance.logger.info
warning = Wrapper.instance.logger.warning
error = Wrapper.instance.logger.error
exception = logging.exception
critical = Wrapper.instance.logger.critical

submit_errors = Wrapper.instance.submit_errors
init_logging = Wrapper.instance.init_logging
set_level = Wrapper.instance.set_level
shutdown = Wrapper.instance.shutdown
