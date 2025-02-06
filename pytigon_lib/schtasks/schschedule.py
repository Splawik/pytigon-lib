import datetime
import asyncio
import types
import logging
from twisted.internet import reactor
from twisted.web import xmlrpc, server

LOGGER = logging.getLogger("pytigon_task")
INIT_TIME = datetime.datetime.now()


def at_iterate(param):
    """Convert a string or list of time strings into a list of [hour, minute, second] lists."""
    ret = []

    def tab_from_str(s):
        """Convert a time string 'HH:MM:SS' into a list of integers."""
        return [int(x) for x in s.split(":")[:3]]

    if isinstance(param, (list, tuple)):
        for pos in param:
            if isinstance(pos, str):
                ret.append(tab_from_str(pos))
            else:
                ret.append([pos, 0, 0])
    elif isinstance(param, str):
        for pos in param.split(","):
            if pos:
                ret.append(tab_from_str(pos))
    else:
        ret.append([param, 0, 0])
    return ret


def monthly(day=1, at=0, in_months=None, in_weekdays=None, tz="local"):
    """Generate monthly schedule functions."""
    ret = []
    _day = day

    def make_monthly_fun(_hour, _minute, _second):
        def _monthly(dt=None):
            nonlocal day, _day, _hour, _minute, _second, in_months, in_weekdays, tz
            dt = dt or INIT_TIME
            x = dt.replace(day=day, hour=_hour, minute=_minute, second=_second)

            if x < dt:
                x = x.replace(month=x.month + 1)

            if in_months and x.month not in in_months:
                x = x.replace(month=in_months[0])

            if in_weekdays and x.weekday() not in in_weekdays:
                for _ in range(7):
                    x = x.replace(day=x.day + 1)
                    if x.weekday() in in_weekdays:
                        break
            return x

        return _monthly

    for _hour, _minute, _second in at_iterate(at):
        ret.append(make_monthly_fun(_hour, _minute, _second))
    return ret


def daily(at=0, in_weekdays=None, tz="local"):
    """Generate daily schedule functions."""
    ret = []

    def make_daily_fun(_hour, _minute, _second):
        def _daily(dt=None):
            nonlocal _hour, _minute, _second, in_weekdays, tz
            dt = dt or INIT_TIME
            x = dt.replace(hour=_hour, minute=_minute, second=_second)

            if x < dt:
                x = x.replace(day=x.day + 1)

            if in_weekdays and x.weekday() not in in_weekdays:
                for _ in range(7):
                    x = x.replace(day=x.day + 1)
                    if x.weekday() in in_weekdays:
                        break
            return x

        return _daily

    for _hour, _minute, _second in at_iterate(at):
        ret.append(make_daily_fun(_hour, _minute, _second))
    return ret


def hourly(period=1, at=0, in_weekdays=None, in_hours=None):
    """Generate hourly schedule functions."""
    ret = []

    def make_hourly_fun(_minute, _second):
        def _hourly(dt=None):
            nonlocal period, _minute, _second, in_weekdays, in_hours
            dt = dt or INIT_TIME
            x = dt.replace(minute=_minute, second=_second)

            if x < dt:
                x = x.replace(hour=x.hour + period)

            if in_hours and x.hour not in in_hours:
                x = x.replace(hour=in_hours[0], day=x.day + 1)

            if in_weekdays and x.weekday() not in in_weekdays:
                for _ in range(7):
                    x = x.replace(day=x.day + 1)
                    if x.weekday() in in_weekdays:
                        if in_hours:
                            x = x.replace(hour=in_hours[0])
                        else:
                            x = x.replace(hour=0)
                        break
            return x

        return _hourly

    for _minute, _second, _ in at_iterate(at):
        ret.append(make_hourly_fun(_minute, _second))
    return ret


def in_minute_intervals(period=1, at=0, in_weekdays=None, in_hours=None):
    """Generate minute interval schedule functions."""
    ret = []

    def make_in_minute_intervals_fun(_second):
        def _in_minute_intervals(dt=None):
            nonlocal period, _second, in_weekdays, in_hours
            dt = dt or INIT_TIME
            x = dt.replace(second=_second)

            if x < dt:
                x = x.replace(minute=x.minute + period)

            if in_hours and x.hour not in in_hours:
                x = x.replace(hour=in_hours[0], day=x.day + 1)

            if in_weekdays and x.weekday() not in in_weekdays:
                for _ in range(7):
                    x = x.replace(day=x.day + 1)
                    if x.weekday() in in_weekdays:
                        if in_hours:
                            x = x.replace(hour=in_hours[0])
                        else:
                            x = x.replace(hour=0)
                        break
            return x

        return _in_minute_intervals

    for _minute, _second, _ in at_iterate(at):
        ret.append(make_in_minute_intervals_fun(_second))
    return ret


def in_second_intervals(period=1, in_weekdays=None, in_hours=None):
    """Generate second interval schedule functions."""

    def _in_second_intervals(dt=None):
        nonlocal period, in_weekdays, in_hours
        dt = dt or INIT_TIME
        x = dt.replace(second=dt.second + period)

        if in_hours and x.hour not in in_hours:
            x = x.replace(hour=in_hours[0], day=x.day + 1)

        if in_weekdays and x.weekday() not in in_weekdays:
            for _ in range(7):
                x = x.replace(day=x.day + 1)
                if x.weekday() in in_weekdays:
                    if in_hours:
                        x = x.replace(hour=in_hours[0])
                    else:
                        x = x.replace(hour=0)
                    break
        return x

    return _in_second_intervals


def _key(elem):
    """Key function for sorting tasks by their next execution time."""
    return elem[4]


class SChScheduler:
    """Scheduler class for managing and executing tasks."""

    def __init__(self, mail_conf=None, rpc_port=None):
        self.tasks = []
        self.fmap = {
            "M": monthly,
            "d": daily,
            "h": hourly,
            "m": in_minute_intervals,
            "s": in_second_intervals,
        }

        if rpc_port:

            class RpcServer(xmlrpc.XMLRPC):
                def __init__(self, scheduler):
                    self.scheduler = scheduler
                    super().__init__()

                def xmlrpc_echo(self, x):
                    return x

                def xmlrpc_show_tasks(self):
                    return self.scheduler.show_tasks()

                def xmlrpc_show_current_tasks(self):
                    return self.scheduler.show_current_tasks()

            self.rpcserver = RpcServer(self)
            reactor.listenTCP(rpc_port, server.Site(self.rpcserver))
        else:
            self.rpcserver = None

        self.rpcserver_activated = False

    def __getattr__(self, item):
        return self.fmap[item]

    def add_task(self, time_functions, task, *argi, **argv):
        """Add a task to the scheduler."""
        functions = []
        if isinstance(time_functions, str):
            for pos in time_functions.split(";"):
                if pos:
                    if (len(pos) > 2 and pos[1] == "(") or len(pos) == 1:
                        if pos[0] in self.fmap:
                            x = pos.split("(")
                            pos = f"{self.fmap[pos[0]].__name__}({x[1] if len(x) > 1 else ''})"
                    y = eval(pos, globals())
                    if isinstance(y, (list, tuple)):
                        functions.extend(y)
                    else:
                        functions.append(y)
        elif isinstance(time_functions, (list, tuple)):
            functions = time_functions
        else:
            functions = [time_functions]

        for fun in functions:
            self.tasks.append([task, argi, argv, fun, fun(), task.__name__])

    def add_rpc_fun(self, name, fun):
        """Add an RPC function to the server."""
        if self.rpcserver:
            setattr(
                self.rpcserver, f"xmlrpc_{name}", types.MethodType(fun, self.rpcserver)
            )
            self.rpcserver_activated = True

    def get_tasks(self, name):
        """Get tasks by name."""
        return [task for task in self.tasks if task[5] == name]

    def remove_tasks(self, name):
        """Remove tasks by name."""
        self.tasks = [task for task in self.tasks if task[5] != name]

    def clear(self):
        """Clear all tasks."""
        self.tasks.clear()

    async def process(self, dt):
        """Process tasks that are due."""
        if self.tasks:
            processes = []
            for task in self.tasks:
                if task[4] <= dt:
                    try:
                        task[4] = task[3](task[4])
                        processes.append(task[0](*task[1], **task[2]))
                        LOGGER.info(f"Running task: {task[5]}")
                    except Exception as e:
                        LOGGER.exception(f"An error occurred in executing task: {e}")

            if processes:
                self.tasks.sort(key=_key)
                try:
                    done, pending = await asyncio.wait(processes)
                    results = [future.result() for future in done]
                except Exception as e:
                    LOGGER.exception(f"An error occurred in task: {e}")

    def show_tasks(self):
        """Show all tasks."""
        return [
            (str(task[5]), str(task[4]), str(task[1]), str(task[2]))
            for task in self.tasks
        ]

    def show_current_tasks(self):
        """Show currently running tasks."""
        return [
            task._coro.__name__
            for task in asyncio.all_tasks()
            if task._coro.__name__ not in ("_run", "process")
        ]

    async def _run(self):
        """Main scheduler loop."""
        while self.tasks or self.rpcserver_activated:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self.process(datetime.datetime.now()))
            except Exception as e:
                LOGGER.exception(f"Problem with scheduler: {e}")
            await asyncio.sleep(1)

    def run(self):
        """Run the scheduler."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run())


if __name__ == "__main__":
    INIT_TIME = datetime.datetime(2016, 5, 1)
    scheduler = SChScheduler(rpc_port=7080)

    async def hello():
        print("Hello world")

    async def hello1(name="", scheduler=None):
        if scheduler:
            tasks = scheduler.get_tasks("hello1")
            if tasks:
                print(tasks[0][4])
                return
        print("Hello world 1")

    async def hello2(scheduler):
        print("Hello world 2")
        x = 1 / 0  # Simulate an error

    async def exit(scheduler):
        scheduler.clear()

    scheduler.add_task(in_minute_intervals(1), hello)
    scheduler.add_task("in_second_intervals(3)", hello)
    scheduler.add_task(in_second_intervals(4), hello)
    scheduler.add_task(hourly(at="2,3"), hello)
    scheduler.add_task(daily(at="22:07"), hello)
    scheduler.add_task(monthly(day=1, at="22:07"), hello)

    scheduler.add_task(
        monthly(day=1, at="22:07"), hello1, name="monthly", scheduler=scheduler
    )
    scheduler.add_task(
        daily(at="22:07", in_weekdays=(1, 2, 3, 4, 5)),
        hello1,
        name="monthly",
        scheduler=scheduler,
    )
    scheduler.add_task(
        "hourly(at=7,in_weekdays=range(1,6), in_hours=range(3,5))",
        hello1,
        name="monthly",
        scheduler=scheduler,
    )
    scheduler.add_task(
        "in_second_intervals(in_weekdays=range(1,2), in_hours=range(3,5))",
        hello1,
        name="in_second_intervals",
        scheduler=scheduler,
    )
    scheduler.add_task(
        "in_second_intervals(in_weekdays=range(1,2), in_hours=range(3,5))",
        hello2,
        scheduler,
    )
    scheduler.add_task(in_minute_intervals(1), exit, scheduler=scheduler)
    scheduler.add_task(
        "M(day=31, at='22:07')", hello1, name="monthly", scheduler=scheduler
    )
    scheduler.add_task("M", hello1, name="monthly", scheduler=scheduler)
    scheduler.add_task(scheduler.s(), hello1, name="monthly", scheduler=scheduler)

    scheduler.run()
