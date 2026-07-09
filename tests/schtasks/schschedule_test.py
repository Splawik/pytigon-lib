import datetime
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtasks.schschedule import (
    INIT_TIME,
    SChScheduler,
    _key,
    at_iterate,
    daily,
    hourly,
    in_minute_intervals,
    in_second_intervals,
    monthly,
)


class TestAtIterate:
    def test_single_int_returns_hour_with_zeros(self):
        result = at_iterate(5)
        assert result == [[5, 0, 0]]

    def test_single_zero(self):
        result = at_iterate(0)
        assert result == [[0, 0, 0]]

    def test_string_hh_mm_ss(self):
        result = at_iterate("12:30:45")
        assert result == [[12, 30, 45]]

    def test_string_hh_mm(self):
        result = at_iterate("12:30")
        assert result == [[12, 30]]

    def test_string_hh_only(self):
        result = at_iterate("12")
        assert result == [[12]]

    def test_comma_separated_strings(self):
        result = at_iterate("12:30:45,06:15:00,18:00:00")
        assert result == [[12, 30, 45], [6, 15, 0], [18, 0, 0]]

    def test_comma_with_empty_trailing(self):
        result = at_iterate("12:00,")
        assert result == [[12, 0]]

    def test_list_of_strings(self):
        result = at_iterate(["12:30:45", "06:15:00"])
        assert result == [[12, 30, 45], [6, 15, 0]]

    def test_list_of_ints(self):
        result = at_iterate([3, 6])
        assert result == [[3, 0, 0], [6, 0, 0]]

    def test_tuple_of_strings(self):
        result = at_iterate(("12:30", "18:00"))
        assert result == [[12, 30], [18, 0]]

    def test_empty_list_returns_empty(self):
        result = at_iterate([])
        assert result == []

    def test_empty_string_returns_empty_list(self):
        result = at_iterate("")
        assert result == []


class TestMonthly:
    def test_basic_monthly_returns_list(self):
        result = monthly(day=15, at="12:30:00")
        assert len(result) == 1
        assert callable(result[0])

    def test_future_monthly_same_month(self):
        results = monthly(day=25, at="12:00:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 10, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.month == 1
        assert next_time.day == 25
        assert next_time.hour == 12

    def test_past_day_moves_to_next_month(self):
        results = monthly(day=5, at="10:00:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 15, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.month == 2
        assert next_time.day == 5

    def test_multiple_at_times(self):
        results = monthly(day=1, at="08:00:00,20:00:00")
        assert len(results) == 2

    def test_in_months_filter(self):
        results = monthly(day=1, at="12:00:00", in_months=[3])
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.month == 3

    def test_in_weekdays_filter(self):
        results = monthly(day=1, at="12:00:00", in_weekdays=[0])
        fn = results[0]
        dt = datetime.datetime(2024, 3, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.weekday() == 0


class TestDaily:
    def test_basic_daily_at_specific_time(self):
        results = daily(at="15:30:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 10, 0, 0)
        next_time = fn(dt)
        assert next_time.day == 1
        assert next_time.hour == 15
        assert next_time.minute == 30

    def test_daily_past_time_moves_to_next_day(self):
        results = daily(at="10:00:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 14, 0, 0)
        next_time = fn(dt)
        assert next_time.day == 2
        assert next_time.hour == 10

    def test_daily_int_param(self):
        results = daily(at=8)
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.hour == 8
        assert next_time.minute == 0

    def test_daily_in_weekdays_skips_weekends(self):
        results = daily(at="12:00:00", in_weekdays=[2])
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.weekday() == 2

    def test_daily_multiple_at_times(self):
        results = daily(at="06:00:00,18:00:00")
        assert len(results) == 2


class TestHourly:
    def test_basic_hourly_past_time_moves_to_next_period(self):
        results = hourly(at="00:15:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 10, 0)
        next_time = fn(dt)
        assert next_time.hour == 1
        assert next_time.minute == 0
        assert next_time.second == 15

    def test_hourly_past_minute_moves_to_next_period(self):
        results = hourly(period=2, at="00:30:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 40, 0)
        next_time = fn(dt)
        assert next_time.hour == 2

    def test_hourly_in_hours_filter(self):
        results = hourly(at="00:00:00", in_hours=[12, 18])
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 10, 0, 0)
        next_time = fn(dt)
        assert next_time.hour == 12

    def test_hourly_in_weekdays_filter(self):
        results = hourly(at="00:00:00", in_weekdays=[3])
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.weekday() == 3

    def test_hourly_period_default_one(self):
        results = hourly(at="00:30:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.hour == 0


class TestInMinuteIntervals:
    def test_basic_minute_interval_sets_second_correctly(self):
        results = in_minute_intervals(at="00:30:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.second == 30
        assert next_time.minute == 0

    def test_minute_past_second_in_same_minute(self):
        results = in_minute_intervals(period=5, at="00:15:00")
        fn = results[0]
        dt = datetime.datetime(2024, 1, 1, 0, 0, 10)
        next_time = fn(dt)
        assert next_time.second == 15
        assert next_time.minute == 0

    def test_minute_in_hours_and_weekdays(self):
        results = in_minute_intervals(at="00:00:00", in_hours=[8], in_weekdays=[0])
        fn = results[0]
        dt = datetime.datetime(2024, 1, 5, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.hour == 8
        assert next_time.weekday() == 0


class TestInSecondIntervals:
    def test_creates_callable(self):
        fn = in_second_intervals()
        assert callable(fn)

    def test_advances_by_period(self):
        fn = in_second_intervals(period=10)
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.second == 10

    def test_respects_in_hours(self):
        fn = in_second_intervals(period=10, in_hours=[5])
        dt = datetime.datetime(2024, 1, 1, 10, 0, 0)
        next_time = fn(dt)
        assert next_time.hour == 5
        assert next_time.day == 2

    def test_respects_in_weekdays_with_in_hours(self):
        fn = in_second_intervals(period=10, in_weekdays=[2], in_hours=[8])
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        next_time = fn(dt)
        assert next_time.weekday() == 2
        assert next_time.hour == 8


class TestKeyFunction:
    def test_key_returns_fifth_element(self):
        assert _key([0, 0, 0, 0, 42, 0]) == 42

    def test_key_with_datetime(self):
        dt = datetime.datetime(2024, 1, 1)
        assert _key([0, 0, 0, 0, dt]) == dt


class TestSChSchedulerInit:
    def test_initializes_without_rpc_port(self):
        scheduler = SChScheduler()
        assert scheduler.tasks == []
        assert scheduler.rpcserver is None

    def test_fmap_contains_all_schedule_types(self):
        scheduler = SChScheduler()
        assert "M" in scheduler.fmap
        assert "d" in scheduler.fmap
        assert "h" in scheduler.fmap
        assert "m" in scheduler.fmap
        assert "s" in scheduler.fmap

    def test_getattr_returns_fmap_value(self):
        scheduler = SChScheduler()
        assert scheduler.M is scheduler.fmap["M"]
        assert scheduler.d is scheduler.fmap["d"]
        assert scheduler.h is scheduler.fmap["h"]

    def test_clear_removes_all_tasks(self):
        scheduler = SChScheduler()
        scheduler.tasks.append(["dummy"])
        scheduler.clear()
        assert scheduler.tasks == []

    def test_show_tasks_returns_serialized_task_info(self):
        scheduler = SChScheduler()
        mock_fn = MagicMock()
        mock_fn.return_value = datetime.datetime(2024, 1, 1, 12, 0, 0)
        mock_task = MagicMock()
        mock_task.__name__ = "test_task"
        scheduler.tasks.append([mock_task, ("arg1",), {"kw": "val"}, mock_fn, mock_fn(), mock_task.__name__])
        result = scheduler.show_tasks()
        assert len(result) == 1
        assert result[0][0] == "test_task"

    def test_remove_tasks_removes_by_name(self):
        scheduler = SChScheduler()
        scheduler.tasks = [
            [None, None, None, None, None, "keep"],
            [None, None, None, None, None, "remove"],
        ]
        scheduler.remove_tasks("remove")
        assert len(scheduler.tasks) == 1
        assert scheduler.tasks[0][5] == "keep"

    def test_get_tasks_returns_matching_by_name(self):
        scheduler = SChScheduler()
        scheduler.tasks = [
            [None, None, None, None, None, "task_a"],
            [None, None, None, None, None, "task_b"],
            [None, None, None, None, None, "task_a"],
        ]
        result = scheduler.get_tasks("task_a")
        assert len(result) == 2

    def test_add_task_with_string_schedule(self):
        scheduler = SChScheduler()
        async def dummy_task():
            pass

        scheduler.add_task("daily(at='12:00:00')", dummy_task)
        assert len(scheduler.tasks) > 0

    def test_add_task_with_function_list(self):
        scheduler = SChScheduler()
        async def dummy_task():
            pass

        results = daily(at="12:00:00")
        scheduler.add_task(results, dummy_task)
        assert len(scheduler.tasks) == len(results)
