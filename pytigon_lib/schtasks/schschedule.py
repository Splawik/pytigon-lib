import asyncio
import datetime
import logging
import types
from datetime import UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from twisted.internet import reactor
from twisted.web import server, xmlrpc

LOGGER = logging.getLogger("pytigon_task")
#: Timezone-aware process start; see ``_now()`` for the local-time equivalent.
INIT_TIME = datetime.datetime.now(UTC)


def _now(tz="local"):
    """Return the current time, honouring *tz*.

    Args:
        tz: IANA timezone name, or ``"local"`` (default) for the system zone.

    Returns:
        A timezone-aware :class:`datetime.datetime`.
    """
    if tz and tz != "local":
        try:
            return datetime.datetime.now(ZoneInfo(tz))
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            LOGGER.warning("Unknown timezone %r, falling back to local time", tz)
    return datetime.datetime.now(UTC).astimezone()


def _validate_weekdays(in_weekdays, what="in_weekdays"):
    """Validate weekday numbers, raising ValueError on an out-of-range entry.

    Without this, the "search at most 7 days" loops in :func:`monthly` and
    :func:`daily` silently give up and leave the hour unset.
    """
    if not in_weekdays:
        return in_weekdays
    for pos in in_weekdays:
        if not isinstance(pos, int) or isinstance(pos, bool) or not 0 <= pos <= 6:
            raise ValueError(f"{what} must be weekday numbers 0-6 (Monday=0), got {pos!r}")
    return in_weekdays



def _add_months(dt, months=1):
    """Add months to a datetime, handling year rollover and day clamping."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    import calendar

    last_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day)


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
    in_weekdays = _validate_weekdays(in_weekdays)

    def make_monthly_fun(_hour, _minute, _second):
        def _monthly(dt=None):
            nonlocal day, _day, _hour, _minute, _second, in_months, in_weekdays, tz
            dt = dt or _now(tz)
            x = dt.replace(day=day, hour=_hour, minute=_minute, second=_second)

            if x < dt:
                x = _add_months(x, 1)

            if in_months and x.month not in in_months:
                target = in_months[0]
                delta = target - x.month if target >= x.month else 12 - x.month + target
                x = _add_months(x, delta)

            if in_weekdays and x.weekday() not in in_weekdays:
                # in_weekdays is validated at registration, so a match is
                # guaranteed within one week.
                for _ in range(7):
                    x = x + datetime.timedelta(days=1)
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
    in_weekdays = _validate_weekdays(in_weekdays)

    def make_daily_fun(_hour, _minute, _second):
        def _daily(dt=None):
            nonlocal _hour, _minute, _second, in_weekdays, tz
            dt = dt or _now(tz)
            x = dt.replace(hour=_hour, minute=_minute, second=_second)

            if x < dt:
                x = x + datetime.timedelta(days=1)

            if in_weekdays and x.weekday() not in in_weekdays:
                for _ in range(7):
                    x = x + datetime.timedelta(days=1)
                    if x.weekday() in in_weekdays:
                        break
            return x

        return _daily

    for _hour, _minute, _second in at_iterate(at):
        ret.append(make_daily_fun(_hour, _minute, _second))
    return ret


def hourly(period=1, at=0, in_weekdays=None, in_hours=None, tz="local"):
    """Generate hourly schedule functions."""
    ret = []
    in_weekdays = _validate_weekdays(in_weekdays)

    def make_hourly_fun(_minute, _second):
        def _hourly(dt=None):
            nonlocal period, _minute, _second, in_weekdays, in_hours
            dt = dt or _now(tz)
            x = dt.replace(minute=_minute, second=_second)

            if x < dt:
                x = x + datetime.timedelta(hours=period)

            if in_hours and x.hour not in in_hours:
                x = (x + datetime.timedelta(days=1)).replace(hour=in_hours[0])

            if in_weekdays and x.weekday() not in in_weekdays:
                for _ in range(7):
                    x = x + datetime.timedelta(days=1)
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


def in_minute_intervals(period=1, at=0, in_weekdays=None, in_hours=None, tz="local"):
    """Generate minute interval schedule functions."""
    ret = []
    in_weekdays = _validate_weekdays(in_weekdays)

    def make_in_minute_intervals_fun(_second):
        def _in_minute_intervals(dt=None):
            nonlocal period, _second, in_weekdays, in_hours
            dt = dt or _now(tz)
            x = dt.replace(second=_second)

            if x < dt:
                x = x + datetime.timedelta(minutes=period)

            if in_hours and x.hour not in in_hours:
                x = (x + datetime.timedelta(days=1)).replace(hour=in_hours[0])

            if in_weekdays and x.weekday() not in in_weekdays:
                for _ in range(7):
                    x = x + datetime.timedelta(days=1)
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


def in_second_intervals(period=1, in_weekdays=None, in_hours=None, tz="local"):
    """Generate second interval schedule functions."""
    in_weekdays = _validate_weekdays(in_weekdays)

    def _in_second_intervals(dt=None):
        nonlocal period, in_weekdays, in_hours
        dt = dt or _now(tz)
        x = dt + datetime.timedelta(seconds=period)

        if in_hours and x.hour not in in_hours:
            x = (x + datetime.timedelta(days=1)).replace(hour=in_hours[0])

        if in_weekdays and x.weekday() not in in_weekdays:
            for _ in range(7):
                x = x + datetime.timedelta(days=1)
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
        # Must raise AttributeError (not KeyError) for unknown names, otherwise
        # copy/pickle probing for dunders recurses instead of failing cleanly.
        try:
            return self.fmap[item]
        except KeyError:
            raise AttributeError(item) from None

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
                    y = eval(pos, {"__builtins__": {}}, {fn.__name__: fn for fn in self.fmap.values()})
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

    async def process(self, dt, timeout=None):
        """Process tasks that are due.

        Args:
            dt: The current time; tasks scheduled at or before it are run.
            timeout: Maximum seconds to wait for the started tasks. Pending
                tasks are cancelled when it expires.
        """
        if self.tasks:
            processes = []
            for task in self.tasks:
                if task[4] <= dt:
                    try:
                        task[4] = task[3](task[4])
                        # asyncio.wait() requires Tasks, not bare coroutines.
                        result = task[0](*task[1], **task[2])
                        if asyncio.iscoroutine(result):
                            result = asyncio.ensure_future(result)
                        processes.append(result)
                        LOGGER.info(f"Running task: {task[5]}")
                    except Exception as e:
                        LOGGER.exception(f"An error occurred in executing task: {e}")

            if processes:
                self.tasks.sort(key=_key)
                try:
                    if timeout is not None:
                        async with asyncio.timeout(timeout):
                            done, pending = await asyncio.wait(processes)
                    else:
                        done, pending = await asyncio.wait(processes)
                    for future in pending:
                        future.cancel()
                    _ = [future.result() for future in done]
                except Exception as e:
                    LOGGER.exception(f"An error occurred in task: {e}")
                    for process in processes:
                        if not asyncio.isfuture(process) or not process.done():
                            continue
                        process.cancel()

    def show_tasks(self):
        """Show all tasks."""
        return [
            (str(task[5]), str(task[4]), str(task[1]), str(task[2]))
            for task in self.tasks
        ]

    def show_current_tasks(self):
        """Show currently running tasks."""
        result = []
        for task in asyncio.all_tasks():
            coro = getattr(task, "get_coro", lambda: None)()
            if coro is not None and hasattr(coro, "__name__"):
                name = coro.__name__
            else:
                name = task.get_name()
            if name not in ("_run", "process"):
                result.append(name)
        return result

    async def _run(self, timeout=None):
        """Main scheduler loop."""
        # The task set keeps a strong reference: CPython only holds a weak one
        # to a running task, so discarding the result can let it be collected
        # mid-flight and the scheduler silently stop running jobs.
        running = set()
        while self.tasks or self.rpcserver_activated:
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(self.process(_now(), timeout=timeout))
                running.add(task)
                task.add_done_callback(running.discard)
            except Exception as e:
                LOGGER.exception("Problem with scheduler: %s", e)
            await asyncio.sleep(1)

        if running:
            await asyncio.gather(*running, return_exceptions=True)

    def run(self, timeout=None):
        """Run the scheduler.

        Args:
            timeout: Optional per-cycle task timeout in seconds.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run(timeout))


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
        _ = 1 / 0  # Simulate an error

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
