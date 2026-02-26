import frappe
import frappe
from frappe.utils import getdate, get_datetime, time_diff_in_hours
from datetime import datetime, timedelta
from collections import defaultdict


@frappe.whitelist()
def calculate_deduction(employee, date):
    if not employee or not date:
        frappe.throw("Employee and Date are required")

    # first and last day of month
    given_date = getdate(date)
    first_day = given_date.replace(day=1)

    if given_date.month == 12:
        last_day = given_date.replace(
            year=given_date.year + 1, month=1, day=1
        ) - timedelta(days=1)
    else:
        last_day = given_date.replace(month=given_date.month + 1, day=1) - timedelta(
            days=1
        )

    # Fetch checkins for month
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee, "time": ["between", [first_day, last_day]]},
        fields=["time", "log_type"],
        order_by="time asc",
    )

    if not checkins:
        return "No checkins found"

    # group by day
    attendance_by_day = defaultdict(list)

    for log in checkins:
        log_date = get_datetime(log.time).date()
        attendance_by_day[log_date].append(log)

    total_deduction_hours = 0

    for day, logs in attendance_by_day.items():
        in_time = None
        out_time = None

        for log in logs:
            if log.log_type == "IN" and not in_time:
                in_time = get_datetime(log.time)
            elif log.log_type == "OUT":
                out_time = get_datetime(log.time)

        if in_time and out_time:
            worked_hours = time_diff_in_hours(out_time, in_time)

            if worked_hours < 8:
                total_deduction_hours += 8 - worked_hours

    frappe.db.set_value(
        "Employee", employee, "custom_monthly_deduction_hours", total_deduction_hours
    )

    return round(total_deduction_hours, 2)
