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
    # total_sales = frappe.db.sql(
    #     """
    #     SELECT IFNULL(SUM(si.net_total), 0)
    #     FROM `tabSales Invoice` si
    #     JOIN `tabSales Team` st ON st.parent = si.name
    #     WHERE st.sales_person = %s
    #       AND si.docstatus = 1
    #       AND si.posting_date BETWEEN %s AND %s
    #     """,
    #     (sales_person, start_date, end_date),
    # )[0][0]
    total_sales = frappe.db.sql(
        """
		SELECT IFNULL(SUM(net_total), 0)
		FROM `tabSales Invoice`
		WHERE sales_person = %s
		  AND docstatus = 1
		  AND posting_date BETWEEN %s AND %s
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
            "payroll_date": date,
            "description": f"Commission for {date}",
        }
    )
    additional_salary.insert()
    additional_salary.submit()
    return additional_salary.name


# This function calculates cash commission based on payments received for sales invoices linked to the salesperson.
# @frappe.whitelist()
# def calculate_cash_commission(sales_person, rule, date=None):
#     if not sales_person or not rule:
#         frappe.throw("Sales Person and Commission Rule are required.")

#     # ----------------------------------------------------
#     # 1. Resolve date range (current month default)
#     # ----------------------------------------------------
#     if not date:
#         date = today()

#     start_date = get_first_day(date)
#     end_date = get_last_day(date)

#     # ----------------------------------------------------
#     # 2. Get total CASH collected for this salesperson
#     #    (from Payment Entry allocated to Sales Invoices)
#     # ----------------------------------------------------
#     total_cash = frappe.db.sql(
#         """
#         SELECT IFNULL(SUM(per.allocated_amount), 0)
#         FROM `tabPayment Entry` pe
#         JOIN `tabPayment Entry Reference` per
#             ON per.parent = pe.name
#         JOIN `tabSales Invoice` si
#             ON si.name = per.reference_name
#         JOIN `tabSales Team` st
#             ON st.parent = si.name
#         WHERE pe.docstatus = 1
#           AND pe.posting_date BETWEEN %s AND %s
#           AND st.sales_person = %s
#         """,
#         (start_date, end_date, sales_person),
#     )[0][0]

#     if total_cash <= 0:
#         return {"sales_person": sales_person, "total_cash": 0, "commission_amount": 0}

#     # ----------------------------------------------------
#     # 3. Get Cash Commission Slabs
#     # ----------------------------------------------------
#     rule_doc = frappe.get_doc("Employee Commission Rule", rule)

#     if not rule_doc.cash_commission:
#         return

#     slabs = sorted(
#         [s for s in rule_doc.cash_commission if s.enable], key=lambda x: x.target_from
#     )

#     # ----------------------------------------------------
#     # 4. Progressive Slab Calculation
#     # ----------------------------------------------------
#     commission_total = 0
#     remaining_cash = total_cash

#     for slab in slabs:
#         slab_from = slab.target_from or 0
#         slab_to = slab.target_to or float("inf")
#         rate = slab.commission_rate or 0  # percentage

#         if remaining_cash <= 0:
#             break

#         slab_range = slab_to - slab_from

#         # Amount eligible inside this slab
#         applicable_amount = min(max(total_cash - slab_from, 0), slab_range)

#         if applicable_amount > 0:
#             commission_total += applicable_amount * (rate / 100)

#     return {
#         "sales_person": sales_person,
#         "from_date": start_date,
#         "to_date": end_date,
#         "total_cash": total_cash,
#         "commission_amount": commission_total,
#     }


################cash commission
@frappe.whitelist()
def calculate_cash_commission(sales_person, rule, date=None):
    if not sales_person:
        frappe.throw("Sales Person is required.")

    if not date:
        date = today()

    start_date = get_first_day(date)
    end_date = get_last_day(date)

    # ----------------------------------------------------
    # 1. Get total received cash
    # ----------------------------------------------------
    total_cash = frappe.db.sql(
        """
        SELECT IFNULL(SUM(pe.paid_amount), 0)
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
          AND pe.payment_type = 'Receive'
          AND pe.posting_date BETWEEN %s AND %s
          AND pe.sales_person = %s
        """,
        (start_date, end_date, sales_person),
    )[0][0]

    commission = 0

    # ----------------------------------------------------
    # Threshold must reach 100k first
    # ----------------------------------------------------
    if total_cash >= 100000:

        # First 100k → 1%
        commission += 100000 * 0.01

        # ------------------------------------------------
        # Second 100k → 1.5%
        # ------------------------------------------------
        if total_cash > 100000:
            second_tier_amount = min(total_cash - 100000, 100000)
            commission += second_tier_amount * 0.015

        # ------------------------------------------------
        # Above 200k → 2%
        # ------------------------------------------------
        if total_cash > 200000:
            third_tier_amount = total_cash - 200000
            commission += third_tier_amount * 0.02

    return {
        "sales_person": sales_person,
        "from_date": start_date,
        "to_date": end_date,
        "total_cash": total_cash,
        "commission_amount": round(commission, 2),
    }


@frappe.whitelist()
def create_cash_additional_salary(sales_person, rule, date, amount):
    if not sales_person or not rule or not date or not amount:
        frappe.throw("All parameters are required.")

    employee = frappe.db.get_value("Sales Person", sales_person, "employee")
    if not employee:
        frappe.throw("No employee linked to this sales person.")
    rule_doc = frappe.get_doc("Employee Commission Rule", rule)
    salary_component = rule_doc.cash_salary_component
    if not salary_component:
        frappe.throw("Commission Rule must have a linked Cash Salary Component.")
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
            "payroll_date": date,
            "description": f"Cash Commission for {date}",
        }
    )
    additional_salary.insert()
    additional_salary.submit()
    # additional_salary.save()
    return additional_salary.name
