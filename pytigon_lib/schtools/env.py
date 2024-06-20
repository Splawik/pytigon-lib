#! /usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY  ; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2013 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"

import environ
import os

ENV = None


def get_environ(path=None):
    global ENV
    if not ENV:
        ENV = environ.Env(
            DEBUG=(bool, False),
            PYTIGON_DEBUG=(bool, False),
            EMBEDED_DJANGO_SERVER=(bool, False),
            PYTIGON_WITHOUT_CHANNELS=(bool, False),
            PYTIGON_TASK=(bool, False),
            LOGS_TO_DOCKER=(bool, False),
            PWA=(bool, False),
            GRAPHQL=(bool, False),
            DJANGO_Q=(bool, False),
            ALLAUTH=(bool, False),
            REST=(bool, False),
            CANCAN_ENABLED=(bool, False),
            SENTRY_ENABLED=(bool, False),
            PROMETHEUS_ENABLED=(bool, False),
            COMPRESS_ENABLED=(bool, False),
            SECRET_KEY=(str, ""),
            CHANNELS_REDIS=(str, ""),
            PUBLISH_IN_SUBFOLDER=(str, ""),
            THUMBNAIL_PROTECTED=(bool, False),
            MAILER=(bool, True),
            LOG_VIEWER=(bool, False),
        )

    if path:
        env_path = os.path.join(path, ".env")
        if os.path.exists(env_path):
            environ.Env.read_env(env_path)
        env_path = os.path.join(path, "env")
        if os.path.exists(env_path):
            environ.Env.read_env(env_path)
    return ENV
