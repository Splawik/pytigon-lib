#! /usr/bin/python3
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

"""Diango channels based server"""

from multiprocessing import Process
import socket
import datetime
import sys
import threading

import django

# from channels import DEFAULT_CHANNEL_LAYER, channel_layers
# from channels.asgi import get_channel_layer
# from channels.handler import ViewConsumer
# from channels.worker import Worker

import pytigon.schserw.schsys.initdjango


# class WorkerThread(threading.Thread):
#    def __init__(self, channel_layer):
#        super(WorkerThread, self).__init__()
#        self.channel_layer = channel_layer

#    def run(self):
#        worker = Worker(channel_layer=self.channel_layer, signal_handlers=False)
#        worker.run()


def log_action(protocol, action, details):
    msg = "[%s] " % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    if protocol == "http" and action == "complete":
        msg += (
            "HTTP %(method)s %(path)s %(status)s [%(time_taken).2f, %(client)s]\n"
            % details
        )
    elif protocol == "websocket" and action == "connected":
        msg += "WebSocket CONNECT %(path)s [%(client)s]\n" % details
    elif protocol == "websocket" and action == "disconnected":
        msg += "WebSocket DISCONNECT %(path)s [%(client)s]\n" % details
    sys.stderr.write(msg)


def _run(addr, port, prod, params=None):
    if params and "wsgi" in params:
        from waitress.runner import run

        django.setup()
        run(["embeded", "--listen=%s:%s" % (addr, str(port)), "wsgi:application"])
    else:
        try:
            from daphne.server import Server
            from daphne.endpoints import build_endpoint_description_strings
            from channels.routing import get_default_application

            django.setup()

            # application = django.core.handlers.wsgi.WSGIHandler()

            endpoints = build_endpoint_description_strings(host=addr, port=int(port))

            server = Server(
                # channel_layer=channel_layer,
                get_default_application(),
                endpoints=endpoints,
                # host=addr,
                # port=int(port),
                signal_handlers=False,
                action_logger=log_action,
                http_timeout=60,
            )
            server.run()
        except KeyboardInterrupt:
            return


class ServProc:
    def __init__(self, proc):
        self.proc = proc

    def stop(self):
        self.proc.terminate()


def run_server(address, port, prod=True, params=None):
    """Run django chanels server

    Args:
        address - adres to bind http server
        port - tcp ip port, on which server start running
        prod - if True - start server in production mode, in production mode workers shoud be running in external
        processes (with redis for example). If prod == False - server is runing in development mode, 4 workers are
        started in the some process.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Starting server: ", address, port)

    proc = Process(target=_run, args=(address, port, prod, params))
    proc.start()

    while True:
        try:
            s.connect((address, port))
            s.close()
            break
        except:
            pass

    print("Server started")

    return ServProc(proc)
