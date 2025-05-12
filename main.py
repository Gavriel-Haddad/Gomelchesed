import streamlit as st
import pandas as pd
import time
import io
import os
import data_access_layer as dal

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

# from authentication import authenticate
from datetime import datetime

st.set_page_config(page_title="גומל חסד", layout="wide")

st.markdown("""
<style>
/* Apply RTL globally */
html, body, [data-testid="stAppViewContainer"] {
    direction: rtl;
    unicode-bidi: bidi-override;
    text-align: right;
	font-size: 25px
}
			
/* Apply font size to labels */
.stTextInput label, .stTextArea label, .stNumberInput label, 
.stSelectbox label, .stMultiselect label, .stCheckbox label, 
.stRadio label {
	font-size: 25px;  /* Adjust this value as needed */
}

/* Apply font size to dataframes */
.stDataFrame, .stTable {
	font-size: 15px;  /* Adjust this value as needed */
}
			
.streamlit-expanderHeader, .stTextInput > label, .stTextArea > label, .stNumberInput > label, 
.stSelectbox > label, .stMultiselect > label, .stCheckbox > label, .stRadio > label {
	text-decoration: underline;
	margin-bottom: 6px;
	display: block;
}

</style>
""", unsafe_allow_html=True)

if "css_injected" not in st.session_state:
    st.session_state.css_injected = True
    time.sleep(1)
    st.rerun()


def display_text_in_center(text):
	st.markdown(f"""
    		<h1 style="text-align: center; font-size: 15px">{text}</h1>
		""", unsafe_allow_html=True)

def display_dataframe(data: pd.DataFrame):
	st.dataframe(data, column_config={
		"תאריך": st.column_config.DateColumn(format="DD.MM.YYYY"),
	},
	hide_index=True)


def to_excel_with_titles(dfs, titles):
	output = io.BytesIO()
	with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
		workbook = writer.book
		worksheet = workbook.add_worksheet("Sheet1")
		writer.sheets["Sheet1"] = worksheet

        # Set worksheet RTL
		worksheet.right_to_left()

        # Title style (RTL)
		title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'white',
            'bg_color': '#4F81BD'
        })

        # Column header format (RTL aligned)
		header_format = workbook.add_format({
            'align': 'right',
            'bold': True
        })

		row = 0
		for df, title in zip(dfs, titles):
			col_count = len(df.columns)

            # Merge title
			worksheet.merge_range(row, 0, row, col_count - 1, title, title_format)
			row += 2

            # Write table data
			df.to_excel(writer, sheet_name="Sheet1", startrow=row + 1, index=False, header=False)

            # Write column headers manually with right alignment
			for col_idx, col_name in enumerate(df.columns):
				worksheet.write(row, col_idx, col_name, header_format)
			row += len(df) + 4

			# Auto-fit columns
			for col_idx, col_name in enumerate(df.columns):
				if not df.empty:
					max_len = max(
						df[col_name].astype(str).map(len).max(),
						len(str(col_name))
					)
					worksheet.set_column(col_idx, col_idx, max_len + 2)
				else:
					max_len = len(str(col_name))  # fallback to just the column header

	output.seek(0)
	return output

def to_pdf_reportlab(dfs, titles):
	def reshape_hebrew(text):
		reshaped = arabic_reshaper.reshape(text)
		return get_display(reshaped)

	# Register a Hebrew-supporting font
	font_path = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
	pdfmetrics.registerFont(TTFont("DejaVu", font_path))

	# Custom style for Hebrew
	styles = getSampleStyleSheet()
	hebrew_style = ParagraphStyle(
		name='Hebrew',
		parent=styles['Normal'],
		fontName='DejaVu',
		fontSize=12,
		leading=14,
		rightIndent=0,
		alignment=2,  # right-align
	)

	buffer = io.BytesIO()
	doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)

	elements = []
	styles = getSampleStyleSheet()

	for df, title in zip(dfs, titles):
        # Section title
		elements.append(Paragraph(title, styles['Heading2']))
		elements.append(Spacer(1, 12))

        # Convert DataFrame to list of lists
		data = [df.columns.tolist()] + df.values.tolist()

        # Create table
		table = Table(data)
		table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
		elements.append(table)
		elements.append(Spacer(1, 24))  # space between tables

	buffer = io.BytesIO()
	doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
	elements = []

	for df, title in zip(dfs, titles):
		elements.append(Paragraph(reshape_hebrew(title), hebrew_style))
		elements.append(Spacer(1, 12))

        # Prepare reshaped data
		data = [[reshape_hebrew(str(col)) for col in df.columns]]
		for _, row in df.iterrows():
			reshaped_row = [reshape_hebrew(str(cell)) for cell in row]
			data.append(reshaped_row)

		table = Table(data)
		table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVu'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
		elements.append(table)
		elements.append(Spacer(1, 24))

	doc.build(elements)
	buffer.seek(0)
	return buffer


def handle_reciepts():
	u_data = dal.get_all_donations(reciepted=False)
	r_data = dal.get_all_donations(reciepted=True)

	if len(u_data) > 0:
		u_data["מספר פנקס"] = u_data["מספר פנקס"].astype(str)
		u_data["מספר קבלה"] = u_data["מספר קבלה"].astype(str)

		uneditables = u_data.columns.tolist()
		uneditables.remove("קבלה")
		uneditables.remove("מספר פנקס")
		uneditables.remove("מספר קבלה")

		u_data = st.data_editor(u_data, disabled=uneditables, column_config={
			"תאריך": st.column_config.DateColumn(format="DD.MM.YYYY"),
		},
		hide_index=True)

		if st.button("שמור"):
			# st.session_state["DONATIONS"] = pd.concat([u_data, r_data])
			# dal.mark_reciepts(st.session_state["DONATIONS"])
			
			with st.spinner("שומר..."):
				dal.mark_reciepts(pd.concat([u_data, r_data]))
				dal.load_donations()
				st.session_state["reciepts_submitted"] = True
	else:
		st.success("אין על מה להוציא קבלות!!")
	
def handle_purchase():
	date = st.date_input("תאריך", format="DD.MM.YYYY")
	year = st.text_input("שנה", value=dal.get_last_yesr())
	day = st.text_input("פרשה")
	mitsva = st.selectbox("מצוה", options=st.session_state["MITZVOT"], index=None, key=f"mitsva {st.session_state['purchase_key']}", label_visibility='collapsed')
	name = st.selectbox("שם", options=dal.get_all_people() + ["חדש"], index=None, placeholder="בחר מתפלל", key=f"name {st.session_state['purchase_key']}")

	if name == "חדש":
		new_name = st.text_input("שם", placeholder="מתפלל חדש", key=f"new_name {st.session_state['purchase_key']}")
	else:
		new_name = None  # to keep variable defined

	if name != None:
		amount = st.number_input("סכום", step=1, key=f"amount {st.session_state['purchase_key']}")

		if st.button("שמור"):
			with st.spinner("שומר..."):
				final_name = name if name != "חדש" else new_name
				purchase = {
					"תאריך" : [date],
					"שנה" : [year],
					"פרשה" : [day],
					"שם" : [final_name],
					"סכום" : [amount],
					"מצוה" : [mitsva],
				}

				dal.insert_purchase(date, year, day, final_name, amount, mitsva)
				dal.load_purchases()
				# st.session_state["PURCHASES"] = pd.concat([st.session_state["PURCHASES"], pd.DataFrame.from_dict(purchase)])

				if name == "חדש":
					dal.add_new_person(new_name)
					dal.load_people()
					# st.session_state["PEOPLE"].append(new_name)

				st.session_state["purchase_key"] += 1
				st.session_state["purchase_submitted"] = True

def handle_donation():
	name = st.selectbox("שם", options=dal.get_all_people() + ["חדש"], index=None, placeholder="בחר מתפלל", key=f"name {st.session_state['purchase_key']}")

	if name == "חדש":
		new_name = st.text_input("שם", placeholder="מתפלל חדש")
	else:
		new_name = None  # to keep variable defined

	if name != None:
		date = st.date_input("תאריך", format="DD.MM.YYYY")
		year = st.text_input("שנה", value=dal.get_last_yesr())
		amount = st.number_input("סכום", step=1)
		method = st.selectbox("אופן תשלום", options=st.session_state["PAYMENT_METHODS"])
		has_reciept = st.checkbox("האם ניתנה קבלה?")
		
		book = " "
		reciept = " "

		if has_reciept:
			book = st.text_input("מספר פנקס")
			reciept = st.text_input("מספר קבלה")

		if st.button("שמור"):
			with st.spinner("שומר..."):
				final_name = name if name != "חדש" else new_name
				donation = {
					"תאריך" : [date],
					"שנה" : [year],
					"שם" : [final_name],
					"סכום" : [amount],
					"אופן תשלום": [method],
					"קבלה" : [has_reciept],
					"מספר פנקס" : [book],
					"מספר קבלה" : [reciept],
				}

				donation = pd.DataFrame.from_dict(donation)
				donation["תאריך"] = donation["תאריך"].astype("datetime64[ns]")
				
				dal.insert_donation(date, year, final_name, amount, method, has_reciept, book, reciept)
				dal.load_donations()
				# st.session_state["DONATIONS"] = pd.concat([st.session_state["DONATIONS"], pd.DataFrame.from_dict(donation)])

				if name == "חדש":
					dal.add_new_person(new_name)
					dal.load_people()
					# st.session_state["PEOPLE"].append(new_name)

				st.session_state["donation_submitted"] = True



def get_report_by_person(name: str, year: str = None):
	if year:
		yearly_purchases_report = st.session_state["PURCHASES"][(st.session_state["PURCHASES"]["שם"] == name) & (st.session_state["PURCHASES"]["שנה"] == year)].drop("שם", axis=1)
		yearly_donations_report = st.session_state["DONATIONS"][(st.session_state["DONATIONS"]["שם"] == name) & (st.session_state["DONATIONS"]["שנה"] == year)].drop("שם", axis=1)

		previous_purchases_report = st.session_state["PURCHASES"][(st.session_state["PURCHASES"]["שם"] == name) & (st.session_state["PURCHASES"]["שנה"] < year)].drop("שם", axis=1)
		previous_donations_report = st.session_state["DONATIONS"][(st.session_state["DONATIONS"]["שם"] == name) & (st.session_state["DONATIONS"]["שנה"] < year)].drop("שם", axis=1)

		yearly_purchases_sum = yearly_purchases_report["סכום"].sum()
		yearly_donations_sum = yearly_donations_report["סכום"].sum()
		previous_purchases_sum = previous_purchases_report["סכום"].sum()
		previous_donations_sum = previous_donations_report["סכום"].sum()
		
		yearly_total = yearly_donations_sum - yearly_purchases_sum
		previous_total = previous_donations_sum - previous_purchases_sum

		total_sum = yearly_total + previous_total

		general_report = {
			'יתרה משנה קודמת': [previous_total],
			'תרומות שנה נוכחית': [yearly_donations_sum],
			'חובות שנה נוכחית': [yearly_purchases_sum],
			'סך הכל': [total_sum],
		}

		previous_year_row = {"סכום": previous_total, "מצוה" : "", "פרשה": f"יתרה משנה קודמת", "שנה": "", "תאריך": [None]}
		previous_year_row = pd.DataFrame.from_dict(previous_year_row)
		
		separation_row = {"סכום": [""], "מצוה" : [""], "פרשה": [""], "שנה": [""], "תאריך": [""]}
		separation_row = pd.DataFrame(separation_row)

		sum_row = {"סכום": previous_total + yearly_purchases_sum, "מצוה" : "", "פרשה": f'סה"כ', "שנה": "", "תאריך": [None]}
		sum_row = pd.DataFrame(sum_row)
		yearly_purchases_report = pd.concat([previous_year_row, yearly_purchases_report, separation_row, sum_row], ignore_index=True)

		general_report = pd.DataFrame.from_dict(general_report)
		return (general_report, yearly_donations_report, yearly_purchases_report.drop(["level"], axis=1))
	# else:
	# 	purchases_report = st.session_state["PURCHASES"][st.session_state["PURCHASES"]["שם"] == name].drop("שם", axis=1)
	# 	donations_report = st.session_state["DONATIONS"][st.session_state["DONATIONS"]["שם"] == name].drop("שם", axis=1)

	# 	purchases_sum = purchases_report["סכום"].sum()
	# 	donations_sum = donations_report["סכום"].sum()
		
	# 	total = donations_sum - purchases_sum

	# 	general_report = {
	# 		'תרומות': [donations_sum],
	# 		'חובות': [purchases_sum],
	# 		'סך הכל': [total],
	# 	}

	# 	general_report = pd.DataFrame.from_dict(general_report)
	# 	return (general_report, donations_report, purchases_report)

def get_report_by_day(year: str, day: str):
	report = pd.DataFrame(st.session_state["PURCHASES"][(st.session_state["PURCHASES"]["שנה"] == year) & (st.session_state["PURCHASES"]["פרשה"].str.contains(day))])
	report = report.sort_values(by=["תאריך", "level"])

	display_day = sorted(report["פרשה"].tolist(), key=len)[0]

	date = datetime.strftime(report["תאריך"].tolist()[0], "%d.%m.%Y")
	message = f'פרשת "{display_day}" {year} - {date}'

	total = report["סכום"].sum()

	separation_row = ["", "", "", "", "", "", ""]
	separation_row = pd.DataFrame([separation_row], columns=report.columns[-1::-1])

	total_row = ["","","", "", 'סה"כ', "", total]
	total_row = pd.DataFrame([total_row], columns=report.columns[-1::-1])

	report = pd.concat([report, separation_row, total_row])
	
	report = report.drop(["תאריך", "שנה", "level"], axis=1)
	if len(set(report["פרשה"].tolist()) - set([""])) == 1:
		return (report.drop(["פרשה"], axis=1), message)
	else:
		return (report, message)

def get_general_report():
	people = dal.get_all_people()
	money_owed = 0

	names, debts = [], []
	for person in people:
		report, _, _ = get_report_by_person(person, dal.get_last_yesr())
		
		balance = float(report["סך הכל"].tolist()[0])

		if balance < 0:
			money_owed += balance * -1
			names.append(person)
			debts.append(balance * -1)

	general_report = {
		"סכום": debts,
		"שם": names,
	}

	general_report = pd.DataFrame.from_dict(general_report)
	return (money_owed, general_report)



	# if "logged_in" not in st.session_state:
	# 	if authenticate():
	# 		st.rerun()
	# else:



try:
	if "purchase_key" not in st.session_state:
		st.session_state["purchase_key"] = 0
	if "fix_key" not in st.session_state:
		st.session_state["fix_key"] = 0
	if "purchase_submitted" not in st.session_state:
		st.session_state["purchase_submitted"] = False
	if "donation_submitted" not in st.session_state:
		st.session_state["donation_submitted"] = False
	if "reciepts_submitted" not in st.session_state:
		st.session_state["reciepts_submitted"] = False
	if "db_loaded" not in st.session_state:
		with st.spinner("אנחנו מכינים הכל... אנא התאזרו בסבלנות"):
			dal.load_db()
		st.session_state["db_loaded"] = True


	actions = ["למלא דוח שבועי", "לתעד תרומה", "להוציא קבלות", "להוציא דוח", "לעשות תיקון"]
	action = st.selectbox("מה תרצה לעשות?", options=actions, index=None, placeholder="בחר אפשרות")#, key=st.session_state["purchase_key"])

	if action != None:
		if action == "למלא דוח שבועי":
			try:
				handle_purchase()
			except Exception as e:
				st.error(str(e))

			if st.session_state["purchase_submitted"]:
				st.success("הושלם בהצלחה!")
				time.sleep(0.2)

				st.session_state["purchase_submitted"] = False

				st.rerun()
		elif action == "לתעד תרומה":
			try:
				handle_donation()
			except Exception as e:
				st.error(str(e))

			if st.session_state["donation_submitted"]:
				st.success("הושלם בהצלחה!")
				time.sleep(0.2)

				st.session_state["purchase_key"] += 1
				st.session_state["donation_submitted"] = False

				st.rerun()
		elif action == "להוציא דוח":
			options = ["לפי מתפלל", "לפי פרשה", "כללי"]
			choice = st.selectbox("איזה דוח תרצה להוציא?", options=options, index=None, placeholder="בחר דוח")


			if choice == "לפי מתפלל":
				name = st.selectbox("על מי תרצה להוציא דוח?", options=dal.get_all_people(), index=None, placeholder="בחר מתפלל")
				year = st.selectbox("שנה", options=dal.get_all_years(), index=len(dal.get_all_years())-1, placeholder="בחר שנה")
				
				if name != None:
					general_report, donations_report, purchases_report = get_report_by_person(name, year)
					purchases_report.drop(["שנה"], axis=1, inplace=True)
					donations_report.drop(["שנה"], axis=1, inplace=True)
					
					st.write("סיכום")
					display_dataframe(general_report)

					st.write("חובות")
					display_dataframe(purchases_report)

					st.write("תרומות")
					display_dataframe(donations_report)


					# Download buttons
					reports = [general_report, purchases_report, donations_report]
					titles = ["סיכום", "חובות", "תרומות"]

					excel_file = to_excel_with_titles(reports, titles)
					pdf_file = to_pdf_reportlab(reports, titles)

					cols = st.columns([0.5,1,0.5,1,0.5])
					year = str(year).replace('"', '')
					cols[1].download_button("📥 Save as Excel", data=excel_file, file_name=f"{name} - {year}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
					cols[3].download_button("📄 Save as PDF", data=pdf_file, file_name=f"{name} - {year}.pdf", mime="application/pdf")
			elif choice == "לפי פרשה":
				year = st.selectbox("שנה", options=dal.get_all_years(), index=len(dal.get_all_years())-1, placeholder="בחר שנה")
				if year != None:
					day = st.text_input("על איזה פרשה תרצה להוציא דוח?", placeholder="בחר פרשה")

				if st.button("הוצא דוח"):
					if year != None and day != "":
						report, message= get_report_by_day(year, day)
						
						st.write(message)
						display_dataframe(report)

						# Download buttons
						reports = [report]
						titles = [message]

						excel_file = to_excel_with_titles(reports, titles)
						pdf_file = to_pdf_reportlab(reports, titles)

						cols = st.columns([0.5,1,0.5,1,0.1])
						message = str(message).replace('"', '')
						cols[1].download_button("📥 Save as Excel", data=excel_file, file_name=f"{message}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
						cols[3].download_button("📄 Save as PDF", data=pdf_file, file_name=f"{message}.pdf", mime="application/pdf")
			elif choice == "כללי":
				total, general_report = get_general_report()

				st.write(f"כסף בחוץ: {total:,}")
				display_dataframe(general_report)
		elif action == "להוציא קבלות":
			try:
				handle_reciepts()
			except Exception as e:
				st.error(str(e))
			
			if st.session_state["reciepts_submitted"]:
				st.success("הושלם בהצלחה!")
				time.sleep(0.2)

				st.session_state["purchase_key"] += 1
				st.session_state["reciepts_submitted"] = False

				st.rerun()
		elif action == "לעשות תיקון":
			name = st.selectbox("אצל מי צריך לתקן?", options=dal.get_all_people(), index=None, placeholder="בחר מתפלל", key=f"{st.session_state['fix_key']}")
			year = st.selectbox("שנה", options=dal.get_all_years(), index=len(dal.get_all_years())-1, placeholder="בחר שנה")
			
			if name != None and year != None:
				_, donations_report, purchases_report = get_report_by_person(name, year)
				purchases_report.reset_index(inplace=True, drop=True)
				purchases_report.drop([0, len(purchases_report) - 2, len(purchases_report) - 1], axis=0, inplace=True)

				st.write("חובות")
				purchases_report.insert(0, "?האם למחוק", False)
				purchases_report.reset_index(drop=True, inplace=True)
				edited_purchases_report = st.data_editor(purchases_report, column_config={
					"תאריך": st.column_config.DateColumn(format="DD.MM.YYYY"),
					"מצוה": st.column_config.SelectboxColumn(options=st.session_state["MITZVOT"])
				}, hide_index=True, key="purchases_data_editor")

				st.write("תרומות")
				donations_report.insert(0, "?האם למחוק", False)
				donations_report.reset_index(drop=True, inplace=True)
				edited_donations_report = st.data_editor(donations_report, column_config={
					"תאריך": st.column_config.DateColumn(format="DD.MM.YYYY"),
				}, hide_index=True, key="donations_data_editor")

				if st.button("שמור"):
					try:
						edited_purchases_report.insert(1, "שם", name)
						edited_donations_report.insert(5, "שם", name)

						edited_purchases_report = edited_purchases_report[~edited_purchases_report["?האם למחוק"]]
						edited_donations_report = edited_donations_report[~edited_donations_report["?האם למחוק"]]

						edited_purchases_report.drop(["?האם למחוק"], axis=1, inplace=True)
						edited_donations_report.drop(["?האם למחוק"], axis=1, inplace=True)
						purchases_report.drop(["?האם למחוק"], axis=1, inplace=True)
						donations_report.drop(["?האם למחוק"], axis=1, inplace=True)

						with st.spinner("שומר..."):
							dal.update_person_data(name, year, edited_purchases_report, edited_donations_report)
							dal.load_donations()
							dal.load_purchases()
							
							# all_data = pd.DataFrame(st.session_state["PURCHASES"]).reset_index(drop=True)
							# person_data_before_edit = purchases_report
							# person_data_before_edit.insert(1, "שם", name)
							# combined = pd.concat([all_data, person_data_before_edit, person_data_before_edit])
							# duplicate_column_set = list(combined.columns)
							# duplicate_column_set.remove("level")
							# all_data_without_person = combined.drop_duplicates(keep=False, ignore_index=True, subset=duplicate_column_set)
							# st.session_state["PURCHASES"] = pd.concat([all_data_without_person, edited_purchases_report])

							# all_data = pd.DataFrame(st.session_state["DONATIONS"]).reset_index(drop=True)
							# person_data_before_edit = donations_report
							# person_data_before_edit.insert(1, "שם", name)
							# combined = pd.concat([all_data, person_data_before_edit, person_data_before_edit])
							# all_data_without_person = combined.drop_duplicates(keep=False, ignore_index=True)
							# st.session_state["DONATIONS"] = pd.concat([all_data_without_person, edited_donations_report])

						st.success("נשמר בהצלחה")
						st.session_state["fix_key"] += 1

						time.sleep(0.2)
						st.rerun()
					except Exception as e:
						st.error(str(e) + " was the error")

except Exception as e:
	st.error("""
			מצטערים... קרתה תקלה...\n\n
		  אנא פנו לצוות התמיכה הטכנית בטלפון 0508248214
		""")
	
	st.error(str(e))










