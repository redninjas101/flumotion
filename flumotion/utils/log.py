# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a video streaming server
# Copyright (C) 2004 Fluendo
#
# flumotion/utils/log.py: logging for Flumotion server
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Street #330, Boston, MA 02111-1307, USA.

"""
This module provides logging to Flumotion components.

Just like in GStreamer, five levels are defined.
These are, in order of decreasing verbosity: log, debug, info, warning, error.

API Stability: unstable

Maintainer: U{Thomas Vander Stichele <thomas at apestaart dot org>}
"""

import sys
import os

from flumotion.twisted import errors

# environment variables controlling levels for each category
global FLU_DEBUG

class Loggable:
    """
    Base class for objects that want to be able to log messages with
    different level of severity.  The levels are, in order from least
    to most: log, debug, info, warning, error.

    @cvar logCategory: Implementors can provide a category to log their
       messages under.
    """

    logCategory = 'default'
    
    def error(self, *args):
        "Log an error.  By default this will also raise an exception."""
        error(self.logCategory, self.logFunction(*args))
        
    def warning(self, *args):
        "Log a warning.  Used for non-fatal problems."
        warning(self.logCategory, self.logFunction(*args))
        
    def info(self, *args):
        "Log an informational message.  Used for normal operation."
        info(self.logCategory, self.logFunction(*args))

    def debug(self, *args):
        "Log a debug message.  Used for debugging."
        debug(self.logCategory, self.logFunction(*args))

    def log(self, *args):
        "Log a log message.  Used for debugging recurring events."
        log(self.logCategory, self.logFunction(*args))

    def logFunction(self, message):
        "Overridable log function.  Default just returns passed message."
        return message

_log_handlers = []

def stderrHandler(category, type, message):
    sys.stderr.write('%-8s %-15s %s\n' % (type + ':', category + ':' , message))
    sys.stderr.flush()

def stderrHandlerLimited(category, type, message):
    'used when FLU_DEBUG is set; uses FLU_DEBUG to limit on category'
    # FIXME: we should parse FLU_DEBUG into a hash so we can look up
    # if the given category matches  
    sys.stderr.write('%-8s %-15s %s\n' % (type + ':', category + ':' , message))
    sys.stderr.flush()

def _handle(category, type, message):
    global _log_handlers

    for handler in _log_handlers:
        handler(category, type, message)
    
def error(cat, *args):
    """
    Log a fatal error message in the given category. \
    This will also raise a L{flumotion.twisted.errors.SystemError}.
    """
    msg = ' '.join(args)
    _handle(cat, 'ERROR', msg)
    raise errors.SystemError(msg)

def warning(cat, *args):
    _handle(cat, 'WARNING', ' '.join(args))

def info(cat, *args):
    _handle(cat, 'INFO', ' '.join(args))

def debug(cat, *args):
    _handle(cat, 'DEBUG', ' '.join(args))

def log(cat, *args):
    _handle(cat, 'LOG', ' '.join(args))

def enableLogging():
    global _log_handlers
    if not stderrHandler in _log_handlers:
        _log_handlers.append(stderrHandler)
    
def disableLogging():
    if stderrHandler in _log_handlers:
        _log_handlers.remove(stderrHandler)
    
def addLogHandler(func):
    _log_handlers.append(func)

def init():
    if os.environ.has_key('FLU_DEBUG'):
        # install a log handler that uses the value of FLU_DEBUG
        FLU_DEBUG = os.environ['FLU_DEBUG']
        addLogHandler(stderrHandlerLimited)
        debug('log', "FLU_DEBUG set to %s" % FLU_DEBUG)
