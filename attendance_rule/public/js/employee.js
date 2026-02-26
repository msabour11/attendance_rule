frappe.ui.form.on("Employee", {
	refresh: function (frm) {
		frm.add_custom_button(__("Calculate Deduction"), function () {
			frappe.call({
				method: "attendance_rule.overrides.employee.calculate_deduction",
				args: {
					employee: frm.doc.name,
					date: frm.doc.custom_date,
				},
				callback: function (r) {
					if (r.message) {
						frappe.msgprint(__("Deduction updated successfully."));
						console.log(r.message);
						frm.refresh_field("custom_monthly_deduction_hours");
					}
				},
			});
		});
	},
});
