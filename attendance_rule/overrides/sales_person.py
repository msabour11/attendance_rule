import frappe
from frappe.utils import get_first_day, get_last_day, today, flt


@frappe.whitelist()
def calculate_employee_commission(sales_person, rule, date=None):
    if not sales_person or not rule:
        frappe.throw("Sales Person and Commission Rule are required.")
    # ----------------------------------------------------
    # 1. Resolve date range (current month by default)
    # ----------------------------------------------------
    if not date:
        date = today()

    start_date = get_first_day(date)
    end_date = get_last_day(date)

    # ----------------------------------------------------
    # 2. Get total sales for the salesperson (this month)
    # ----------------------------------------------------
    total_sales = frappe.db.sql(
        """
        SELECT IFNULL(SUM(si.net_total), 0)
        FROM `tabSales Invoice` si
        JOIN `tabSales Team` st ON st.parent = si.name
        WHERE st.sales_person = %s
          AND si.docstatus = 1
          AND si.posting_date BETWEEN %s AND %s
        """,
        (sales_person, start_date, end_date),
    )[0][0]

    if total_sales <= 0:
        return 0

    # ----------------------------------------------------
    # 3. Get commission rule slabs
    # ----------------------------------------------------
    rule_doc = frappe.get_doc("Employee Commission Rule", rule)
    if not rule_doc.sales_commission:
        return

    slabs = sorted(
        [s for s in rule_doc.sales_commission if s.enable], key=lambda x: x.target_from
    )

    # ----------------------------------------------------
    # 4. Calculate tier-based commission
    # ----------------------------------------------------
    commission_total = 0
    remaining_sales = total_sales

    for slab in slabs:
        if remaining_sales <= 0:
            break

        slab_from = slab.target_from or 0
        slab_to = slab.target_to or float("inf")
        slab_amount = slab.commission_amount or 0

        slab_range = slab_to - slab_from
        applicable_amount = min(remaining_sales, slab_range)

        if applicable_amount > 0:
            commission_total += slab_amount
            remaining_sales -= applicable_amount

    return {
        "sales_person": sales_person,
        "from_date": start_date,
        "to_date": end_date,
        "total_sales": total_sales,
        "commission_amount": commission_total,
    }


@frappe.whitelist()
def create_additional_salary(sales_person, rule, date, amount):
    if not sales_person or not rule or not date or not amount:
        frappe.throw("All parameters are required.")

    employee = frappe.db.get_value("Sales Person", sales_person, "employee")
    if not employee:
        frappe.throw("No employee linked to this sales person.")
    rule_doc = frappe.get_doc("Employee Commission Rule", rule)
    salary_component = rule_doc.sales_salary_component
    if not salary_component:
        frappe.throw("Commission Rule must have a linked Salary Component.")
    if flt(amount) <= 0:
        frappe.throw("Commission amount must be greater than zero.")

    additional_salary = frappe.get_doc(
        {
            "doctype": "Additional Salary",
            "employee": employee,
            "salary_component": salary_component,
            "amount": flt(amount),
            "from_date": date,
            "to_date": date,
            "description": f"Commission for {date}",
        }
    )
    additional_salary.insert()
    additional_salary.submit()
    return additional_salary.name
