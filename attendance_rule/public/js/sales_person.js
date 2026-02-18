frappe.ui.form.on("Sales Person", {
	refresh: function (frm) {},
});

frappe.ui.form.on("Sales Man Commission", {
	create_commission: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.call({
			method: "attendance_rule.overrides.sales_person.calculate_employee_commission",
			args: {
				sales_person: frm.doc.name,
				rule: frm.doc.custom_employee_commission_rule,
				date: row.date,
			},
			callback: function (r) {
				if (r.message) {
					console.log(r.message);
					frappe.model.set_value(
						cdt,
						cdn,
						"commission_amount",
						r.message.commission_amount,
					);
					frm.refresh_field("commission_amount");
					frm.save();
				}
			},
		});
	},

	create_cash_commission: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.call({
			method: "attendance_rule.overrides.sales_person.calculate_cash_commission",
			args: {
				sales_person: frm.doc.name,
				rule: frm.doc.custom_employee_commission_rule,
				date: row.date,
			},
			callback: function (r) {
				if (r.message) {
					console.log(r.message);
					frappe.model.set_value(
						cdt,
						cdn,
						"cash_commission_amount",
						r.message.commission_amount,
					);
					frm.refresh_field("cash_commission_amount");
					frm.save();
				}
			},
		});
	},
	create_additional_salary: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.call({
			method: "attendance_rule.overrides.sales_person.create_additional_salary",
			args: {
				sales_person: frm.doc.name,
				rule: frm.doc.custom_employee_commission_rule,
				date: row.date,
				amount: row.commission_amount,
			},
			callback: function (r) {
				if (r.message) {
					frappe.msgprint("Additional Salary Created");
				}
			},
		});
	},
	create_cash_additional_salary: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.call({
			method: "attendance_rule.overrides.sales_person.create_cash_additional_salary",
			args: {
				sales_person: frm.doc.name,
				rule: frm.doc.custom_employee_commission_rule,
				date: row.date,
				amount: row.cash_commission_amount,
			},
			callback: function (r) {
				if (r.message) {
					frappe.msgprint("Cash Commission Additional Salary Created");
				}
			},
		});
	},
});
