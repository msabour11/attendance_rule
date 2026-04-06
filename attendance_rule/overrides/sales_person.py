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
    # total_sales = frappe.db.sql(
    #     """
    # 	SELECT IFNULL(SUM(net_total), 0)
    # 	FROM `tabSales Invoice`
    # 	WHERE sales_person = %s
    # 	  AND docstatus = 1
    # 	  AND posting_date BETWEEN %s AND %s
    # 	""",
    #     (sales_person, start_date, end_date),
    # )[0][0]

    rule_doc = frappe.get_doc("Employee Commission Rule", rule)
    if not rule_doc.sales_commission:
        return {
            "sales_person": sales_person,
            "from_date": start_date,
            "to_date": end_date,
            "total_sales": total_sales,
            "commission_amount": 0,
        }

    slabs = sorted(
        [s for s in rule_doc.sales_commission if s.enable], key=lambda x: x.target_from
    )

    commission_total = 0

    if total_sales > 0:
        matching_slab = next(
            (
                slab
                for slab in slabs
                if total_sales >= flt(slab.target_from)
                and (not slab.target_to or total_sales <= flt(slab.target_to))
            ),
            None,
        )

        if matching_slab:
            commission_total = flt(matching_slab.commission_amount)

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


# cash commission
@frappe.whitelist()
def calculate_cash_commission(sales_person, rule, date=None):
    if not sales_person or not rule:
        frappe.throw("Sales Person and Commission Rule are required.")

    if not date:
        date = today()

    start_date = get_first_day(date)
    end_date = get_last_day(date)
    # invoices = frappe.db.sql(
    #     """
    #     SELECT
    #         si.name,
    #         si.net_total,
    #         si.outstanding_amount
    #     FROM `tabSales Invoice` si
    #     WHERE si.sales_person = %s
    #       AND si.docstatus = 1
    #       AND si.posting_date BETWEEN %s AND %s
    #     """,
    #     (sales_person, start_date, end_date),
    #     as_dict=True,
    # )

    invoices = frappe.db.sql(
        """
    SELECT  si.name, si.net_total, si.outstanding_amount
    FROM `tabSales Invoice` si
    JOIN `tabSales Team` st ON st.parent = si.name
    WHERE st.sales_person = %s
        AND si.docstatus = 1
        AND si.posting_date BETWEEN %s AND %s
    """,
        (sales_person, start_date, end_date),
        as_dict=True,
    )

    total_net_total = flt(sum(flt(invoice.net_total) for invoice in invoices), 2)
    total_outstanding = flt(
        sum(flt(invoice.outstanding_amount) for invoice in invoices), 2
    )

    rule_doc = frappe.get_doc("Employee Commission Rule", rule)
    slabs = sorted(
        [slab for slab in rule_doc.cash_commission if slab.enable],
        key=lambda slab: slab.target_from or 0,
    )

    commission = 0

    if total_net_total > 0 and total_outstanding <= 10:
        matching_slab = next(
            (
                slab
                for slab in slabs
                if total_net_total >= flt(slab.target_from)
                and (not slab.target_to or total_net_total <= flt(slab.target_to))
            ),
            None,
        )

        if matching_slab:
            commission = flt(
                total_net_total * (flt(matching_slab.commission_rate) / 100), 2
            )

    return {
        "sales_person": sales_person,
        "from_date": start_date,
        "to_date": end_date,
        "total_cash": total_net_total,
        "total_net_total": total_net_total,
        "total_outstanding": total_outstanding,
        "commission_amount": commission,
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


@frappe.whitelist()
def create_cash_journal_entry(sales_person, rule, amount, employee):
    if not sales_person or not rule or not amount or not employee:
        frappe.throw("All parameters are required.")

    rule_doc = frappe.get_doc("Employee Commission Rule", rule)

    salary_component_name = rule_doc.cash_salary_component
    if not salary_component_name:
        frappe.throw("Commission Rule must have a linked Cash Salary Component.")

    salary_component = frappe.get_doc("Salary Component", salary_component_name)

    # Guard against empty accounts table
    if not salary_component.accounts:
        frappe.throw("Salary Component has no linked accounts.")

    debit_account = salary_component.accounts[0].account  # expense account
    if not debit_account:
        frappe.throw("Salary Component account is not set.")

    credit_account = rule_doc.cash_account  # cash/bank account
    if not credit_account:
        frappe.throw("Commission Rule must have a linked Cash Account.")

    if flt(amount) <= 0:
        frappe.throw("Commission amount must be greater than zero.")

    company = frappe.get_value("Employee", employee, "company")

    je = frappe.get_doc(
        {
            "doctype": "Journal Entry",
            "posting_date": today(),
            "user_remark": f"Cash Commission for {sales_person} on {today()}",  # fixed field name
            "company": company,
        }
    )

    # Debit the expense (salary component) account
    je.append(
        "accounts",
        {
            "account": debit_account,
            "debit_in_account_currency": flt(amount),
            "party_type": "Employee",
            "party": employee,
            "user_remark": f"Commission for Sales Person: {sales_person}",
        },
    )

    # Credit the cash account
    je.append(
        "accounts",
        {
            "account": credit_account,
            "credit_in_account_currency": flt(amount),
            "party_type": "Employee",
            "party": employee,
        },
    )

    je.insert()
    # je.submit()
    return je.name
