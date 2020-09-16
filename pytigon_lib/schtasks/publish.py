from django.core.cache import cache


class CommunicationBasePublisher():

    def send_event(self, value):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class CommunicationByCachePublisher(CommunicationBasePublisher):
    def __init__(self, id):
        self.id = id
        cache.set('process_events_%s_count' % self.id, 0)

    def send_event(self, value):
        id2 = cache.incr('process_events_%s_count' % self.id)
        cache.set('process_events_%s_value_%d' % (self.id, id2 - 1), value)

    def close(self):
        id2 = cache.incr('process_events_%s_count' % self.id)
        cache.set('process_events_%s_value_%d' % (self.id, id2 - 1), "$$$END$$$")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class CommunicationBaseReceiver():
    def __init__(self, id, observer = None):
        self.id = id
        self.observer = observer

    def process(self):
        pass

    def handle_start(self):
        if self.observer:
            self.observer.handle_start()

    def handle_event(self, value):
        if self.observer:
            self.observer.handle_event(value)

    def handle_end(self):
        if self.observer:
            self.observer.handle_end()


class CommunicationByCacheReceiver(CommunicationBaseReceiver):
    def __init__(self, id, observer = None):
        super().__init__(id, observer)
        self.process_events_count = 0
        self.started = False

    def _remove_caches(self):
        id2 = cache.get('process_events_%s_count' % self.id, 0)
        i = 0
        while i < id2:
            cache.delete('process_events_%s_value_%d' % (self.id, i))
            i+=1
        cache.delete('process_events_%s_count' % self.id)

    def process(self):
        print("A1")
        if self.started:
            id2 = cache.get('process_events_%s_count' % self.id, 0)
            print("A2", id2)
        else:
            id2 = cache.get('process_events_%s_count' % self.id, None)
            print("A3", id2)
            if id2 != None:
                self.started = True
                self.handle_start()
            else:
                return False
        print("A4", id2)
        if id2 != self.process_events_count:
            i = self.process_events_count
            while i < id2:
                value = cache.get('process_events_%s_value_%d' % (self.id, i), "")
                if type(value) == str and value=="$$$END$$$":
                    print("F1")
                    self.handle_end()
                    print("F2")
                    self._remove_caches()
                    print("F3")
                    return True
                print("A5", "handle_event", value)
                self.handle_event(value)

                i+=1
            self.process_events_count = id2
            return True

        return False


def publish(task_publish_group="default"):
    def decorator(funct):
        def wrapper(*argi, **argv):
            id2 = argv.pop('task_publish_id',None)
            if id2:
                id3 = task_publish_group + '__' + id2
            else:
                id3 = task_publish_group
            with CommunicationByCachePublisher(id3) as cproxy:
                argv['cproxy'] = cproxy
                ret = funct(*argi, **argv)
            return ret
        return wrapper
    return decorator
