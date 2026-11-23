"""Builds sample_docs/lumenbay-hr-policy.pdf, a fictional 4-page HR policy used for demos and tests."""
import os
from fpdf import FPDF

SECTIONS = [
    ("1. Working Hours and Remote Work", [
        "Standard working hours at Lumen Bay Technologies are 9:30 AM to 6:30 PM, Monday to Friday, including a one-hour lunch break.",
        "Employees may work from home up to two days per week after completing probation, subject to their manager's approval.",
        "The company reimburses home internet costs of up to INR 1,000 per month for employees on the hybrid schedule. Claims must be submitted with a bill through the expense portal by the 5th of the following month.",
    ]),
    ("2. Leave Policy", [
        "Full-time employees receive 18 days of paid leave per calendar year, credited at 1.5 days per month.",
        "Up to 10 unused paid leave days can be carried forward to the next year. Any balance above 10 days lapses on 31 December.",
        "In addition, employees receive 12 days of sick leave per year. Sick leave of more than two consecutive days requires a medical certificate.",
        "Maternity leave is 26 weeks of fully paid leave. Paternity leave is 10 working days, to be taken within three months of the child's birth.",
    ]),
    ("3. Probation, Notice Period and Appraisals", [
        "All new employees serve a probation period of six months. During probation, the notice period is 15 days.",
        "After confirmation, the notice period for resignation is 60 days. Unused paid leave may not be adjusted against the notice period.",
        "Performance appraisals take place once a year in April. Salary revisions from the appraisal take effect from the July payroll.",
    ]),
    ("4. Benefits and Learning", [
        "Every employee is covered by group health insurance with a sum insured of INR 5,00,000 per year, which also covers a spouse and up to two children.",
        "Employees can claim up to INR 20,000 per year towards approved courses and certifications through the learning budget.",
        "Laptops are provided by the company and must be returned on the last working day. Lost devices must be reported to IT within 24 hours.",
    ]),
]

pdf = FPDF(format="A4")
pdf.set_margins(22, 22, 22)
for i, (title, paras) in enumerate(SECTIONS):
    pdf.add_page()
    if i == 0:
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "Lumen Bay Technologies - Employee Handbook", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, "Fictional sample document for the Document Q&A API demo. Version 2026.1", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11.5)
    for p in paras:
        pdf.multi_cell(0, 6.5, p)
        pdf.ln(3)
    pdf.set_auto_page_break(False)
    pdf.set_y(-18); pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 8, f"Page {i + 1} of {len(SECTIONS)}", align="C")
    pdf.set_auto_page_break(True, margin=22)

out = os.path.join(os.path.dirname(__file__), "..", "sample_docs", "lumenbay-hr-policy.pdf")
pdf.output(out)
print("wrote", os.path.normpath(out))
