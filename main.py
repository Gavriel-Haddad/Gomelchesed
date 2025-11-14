import streamlit as st
import pandas as pd
import time
import numpy as np
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
{
    font-size: 25px;  /* Adjust this value as needed */
}

/* Apply font size to dataframes */
.stDataFrame, .stTable {
    font-size: 15px;  /* Adjust this value as needed */
}

.streamlit-expanderHeader, .stTextInput > label, .stTextArea > label, .stNumberInput > label, 
.stSelectbox > label, .stMultiselect > label, .stCheckbox > label{
    text-decoration: underline;
    margin-bottom: 6px;
    display: block;
}

# /* === Keep layout LTR so sidebar renders on the left === */
# [data-testid="stAppViewContainer"] { 
#     direction: ltr !important; /* layout flow only */
# }

/* Keep visible content RTL (unchanged look & feel) */
[data-testid="stMain"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stSidebar"] {
    direction: rtl;
    unicode-bidi: bidi-override;
    text-align: right;
}

/* Sidebar fixed width = 280px */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div {
    width: 310px !important;
    min-width: 310px !important;
    max-width: 310px !important;
}

</style>
""", unsafe_allow_html=True)


if "css_injected" not in st.session_state:
    st.session_state.css_injected = True
    time.sleep(2)
    st.rerun()

def display_dataframe(data: pd.DataFrame):
	st.dataframe(data, use_container_width=True, column_config={
			"תאריך": st.column_config.DateColumn(format="DD.MM.YYYY"),
			"סכום": st.column_config.NumberColumn(format="localized"),
			"סך הכל": st.column_config.NumberColumn(format="localized"),
			"חובות שנה נוכחית": st.column_config.NumberColumn(format="localized"),
			"יתרה משנה קודמת": st.column_config.NumberColumn(format="localized"),
			"תרומות שנה נוכחית": st.column_config.NumberColumn(format="localized")
		},
		hide_index=True)


def clean_nulls(data: pd.DataFrame):
	for col in data.columns:
		if "סכום" in col or "מספר" in col:
			data[col] = data[col].astype('Int64', errors='ignore')
		else:
			data[col] = data[col].astype('str')
			data[col] = data[col].apply(lambda x: "" if x in ["None", "NaT", "nan"] else x)

	return data

def to_excel_with_titles(dfs: list[pd.DataFrame], titles):
	dfs = [df[df.columns[::-1]] for df in dfs]
	for df in dfs:
		df = clean_nulls(df)
		
		if 'תאריך' in df.columns:
			df["תאריך"] = pd.to_datetime(df["תאריך"], errors='coerce').dt.strftime("%d/%m/%Y")
	
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

	# Custom style for Hebrew titles
	styles = getSampleStyleSheet()
	hebrew_style = ParagraphStyle(
		name='Hebrew',
		parent=styles['Normal'],
		fontName='DejaVu',
		fontSize=12,
		leading=14,
		alignment=2,  # right align
		underlineColor='black'
	)

	# Prepare PDF document
	buffer = io.BytesIO()
	doc = SimpleDocTemplate(
		buffer,
		pagesize=A4,
		rightMargin=30,
		leftMargin=30,
		topMargin=30,
		bottomMargin=18
	)

	elements = []

	# Add tables and titles
	for df, title in zip(dfs, titles):
		df.fillna("", inplace=True)

		elements.append(Spacer(1, 36))
		elements.append(Paragraph(reshape_hebrew(title), hebrew_style))
		elements.append(Spacer(1, 12))

		# Convert dataframe to list of lists (header + rows)
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

	# Add בס"ד to top-right of each page
	def add_bsd(canvas, doc):
		canvas.setFont("DejaVu", 12)
		bsd_text = reshape_hebrew('בס"ד')
		canvas.drawRightString(560, 820, bsd_text)  # adjust as needed

	# Build document with בס"ד
	doc.build(elements, onFirstPage=add_bsd, onLaterPages=add_bsd)

	buffer.seek(0)
	return buffer



def handle_reciepts():
	u_data = dal.get_all_donations(reciepted=False)
	r_data = dal.get_all_donations(reciepted=True)

	u_data = u_data[u_data.columns[::-1]]
	r_data = r_data[r_data.columns[::-1]]

	if len(u_data) > 0:
		u_data["מספר פנקס"] = u_data["מספר פנקס"].astype(str)
		u_data["מספר קבלה"] = u_data["מספר קבלה"].astype(str)
		u_data = u_data[u_data["אופן תשלום"] != "הוראת קבע"]

		uneditables = u_data.columns.tolist()
		uneditables.remove("מספר פנקס")
		uneditables.remove("מספר קבלה")

		st.write(f"יש להוציא קבלות על {len(u_data)} תרומות:")
		u_data = st.data_editor(u_data, disabled=uneditables, column_config={
			"תאריך": st.column_config.DateColumn(format="DD.MM.YYYY"),
		},
		use_container_width=True,
		hide_index=True)

		if st.button("שמור"):
			with st.spinner("שומר..."):
				dal.mark_reciepts(pd.concat([u_data, r_data]))
				st.session_state["reciepts_submitted"] = True
	else:
		st.success("אין על מה להוציא קבלות!!")
	
def handle_purchase():
	date = st.date_input("תאריך", format="DD.MM.YYYY", value=None)
	year = st.text_input("שנה", value=dal.get_last_yesr())
	
	day = st.selectbox("פרשה", options=dal.get_all_days() + ["חדש"], index=None, placeholder="בחר פרשה")
	if day == "חדש":
		new_day = st.text_input("פרשה", placeholder="פרשה חדשה", key=f"new_day {st.session_state['purchase_key']}")
	else:
		new_day = ""  # to keep variable defined

	mitsva = st.selectbox("מצוה", options=st.session_state["MITZVOT"] + ["חדש"], index=None, key=f"mitsva {st.session_state['purchase_key']}", label_visibility='collapsed')
	if mitsva == "חדש":
		new_mitsva = st.text_input("מצוה", placeholder="מצוה חדשה", key=f"new_mitsva {st.session_state['purchase_key']}")
	else:
		new_mitsva = ""  # to keep variable defined

	name = st.selectbox("שם", options=dal.get_all_people() + ["חדש"], index=None, placeholder="בחר מתפלל", key=f"name {st.session_state['purchase_key']}")
	if name == "חדש":
		new_name = st.text_input("שם", placeholder="מתפלל חדש", key=f"new_name {st.session_state['purchase_key']}")
	else:
		new_name = ""  # to keep variable defined

	amount = st.number_input("סכום", step=1, key=f"amount {st.session_state['purchase_key']}")
	notes = st.text_input("הערות", placeholder="הערות", key=f"notes {st.session_state['purchase_key']}")

	if st.button("שמור"):
		with st.spinner("שומר..."):
			final_day = day if day != "חדש" else new_day
			final_mitsva = mitsva if mitsva != "חדש" else new_mitsva
			final_name = name if name != "חדש" else new_name


			if day == "חדש":
				dal.add_new_day(new_day)
			if mitsva == "חדש":
				dal.add_new_mitsva(new_mitsva)
			if name == "חדש":
				dal.add_new_person(new_name)

			dal.insert_purchase(date, year, final_day, final_name, amount, final_mitsva, notes)

			st.session_state["purchase_submitted"] = True

def handle_donation():
	name = st.selectbox("שם", options=dal.get_all_people() + ["חדש"], index=None, placeholder="בחר מתפלל", key=f"name {st.session_state['purchase_key']}")

	if name == "חדש":
		new_name = st.text_input("שם", placeholder="מתפלל חדש")
	else:
		new_name = ""  # to keep variable defined

	if name != None:
		date = st.date_input("תאריך", format="DD.MM.YYYY")
		year = st.text_input("שנה", value=dal.get_last_yesr())
		amount = st.number_input("סכום", step=1)
		method = st.selectbox("אופן תשלום", options=st.session_state["PAYMENT_METHODS"])
		notes = st.text_input("הערות", placeholder="הערות")
		has_reciept = st.checkbox("האם ניתנה קבלה?")
		
		book = " "
		reciept = " "

		if has_reciept:
			book = st.text_input("מספר פנקס")
			reciept = st.text_input("מספר קבלה")

		if st.button("שמור"):
			with st.spinner("שומר..."):
				final_name = name if name != "חדש" else new_name

				if name == "חדש":
					dal.add_new_person(new_name)

				dal.insert_donation(date, year, final_name, amount, method, book, reciept, notes)
				
				st.session_state["donation_submitted"] = True


def recombine_reciept_columns(df: pd.DataFrame):
	split = df['קבלה'].astype(str).str.split('/', n=1, expand=True)
	has_book = split[1].notna()
	df['מספר פנקס'] = split[0].where(has_book, np.nan)
	df['מספר קבלה'] = np.where(has_book, split[1], split[0])
	
	df.drop(columns=['קבלה'], inplace=True)

	columns = ["תאריך", "שנה", "שם", "סכום", "אופן תשלום", "מספר פנקס", "מספר קבלה", "הערות"]
	df = df[columns[::-1]]  # Reverse the order of columns

	return df


def get_report_by_person(name: str, year: str):
	yearly_purchases_report = st.session_state["PURCHASES"][(st.session_state["PURCHASES"]["שם"] == name) & (st.session_state["PURCHASES"]["שנה"] == year)]
	yearly_donations_report = st.session_state["DONATIONS"][(st.session_state["DONATIONS"]["שם"] == name) & (st.session_state["DONATIONS"]["שנה"] == year)]
	yearly_purchases_report["תאריך"] = yearly_purchases_report["תאריך"].astype("datetime64[ns]")
	yearly_donations_report["תאריך"] = yearly_donations_report["תאריך"].astype("datetime64[ns]")
	yearly_donations_report.sort_values(by=["תאריך"], inplace=True)
	yearly_purchases_report.sort_values(by=["תאריך"], inplace=True)

	
	previous_purchases_report = st.session_state["PURCHASES"][(st.session_state["PURCHASES"]["שם"] == name) & (st.session_state["PURCHASES"]["שנה"] < year)]
	previous_donations_report = st.session_state["DONATIONS"][(st.session_state["DONATIONS"]["שם"] == name) & (st.session_state["DONATIONS"]["שנה"] < year)]

	yearly_purchases_sum = yearly_purchases_report["סכום"].sum()
	yearly_donations_sum = yearly_donations_report["סכום"].sum()
	previous_purchases_sum = previous_purchases_report["סכום"].sum()
	previous_donations_sum = previous_donations_report["סכום"].sum()
	
	yearly_total = yearly_purchases_sum - yearly_donations_sum
	previous_total = previous_purchases_sum - previous_donations_sum

	total = yearly_total + previous_total

	# PURCHASES REPORT FORMATTING
	previous_year_row = {"סכום": previous_total, "מצוה" : "", "פרשה": f"יתרה משנה קודמת", "שנה": "", "תאריך": [None], "שם": [name]}
	previous_year_row = pd.DataFrame.from_dict(previous_year_row)
	
	separation_row = {"סכום": [""], "מצוה" : [""], "פרשה": [""], "שנה": [""], "תאריך": [""]}
	separation_row = pd.DataFrame(separation_row)

	sum_row = {"סכום": previous_total + yearly_purchases_sum, "מצוה" : "", "פרשה": f'סה"כ', "שנה": "", "תאריך": [None]}
	sum_row = pd.DataFrame(sum_row)
	yearly_purchases_report = pd.concat([previous_year_row, yearly_purchases_report, separation_row, sum_row], ignore_index=True)
	
	purchases_columns = yearly_purchases_report.columns
	reordered_purchases_columns = ["הערות"] + [col for col in purchases_columns if col != "הערות"]
	yearly_purchases_report = yearly_purchases_report[reordered_purchases_columns]


	# DONATIONS REPORT FORMATTING
	separation_row = {"הערות": "", "סכום" : [""], "מספר קבלה": [""],"מספר פנקס": [""],"אופן תשלום": [""],"שם": [""], "שנה": [""], "תאריך": [None]}
	separation_row = pd.DataFrame(separation_row)

	sum_row = {"הערות": "", "סכום" : yearly_donations_sum, "מספר קבלה": [""],"מספר פנקס": [""],"אופן תשלום": ['סה"כ'], "שם": [""], "שנה": [""], "תאריך": [None]}
	sum_row = pd.DataFrame(sum_row)
	yearly_donations_report = pd.concat([yearly_donations_report, separation_row, sum_row], ignore_index=True)
	yearly_donations_report = yearly_donations_report.loc[:, ["הערות", "סכום", "מספר קבלה", "מספר פנקס", "אופן תשלום", "שם", "שנה", "תאריך"]]
	
	# COMBINE RECIPT AND BOOK NUMBER COLUMNS
	yearly_donations_report['קבלה'] = np.where(
		yearly_donations_report['מספר פנקס'].isna() | (yearly_donations_report['מספר פנקס'].str.strip() == ''),
		yearly_donations_report['מספר קבלה'].astype(str),
		yearly_donations_report['מספר פנקס'].astype(str) + '/' + yearly_donations_report['מספר קבלה'].astype(str)
	)
	cols = list(yearly_donations_report.columns)
	cols.remove('מספר פנקס')
	cols.remove('מספר קבלה')
	cols.remove('קבלה')
	book_idx = cols.index('אופן תשלום')
	cols.insert(book_idx, 'קבלה')
	yearly_donations_report = yearly_donations_report[cols]

	# GENERAL REPORT FORMATTING
	general_report = {"סכום" : total, "שם": [""], "שנה": [""], "תאריך": [datetime.today()]}
	general_report = pd.DataFrame(general_report)


	return (yearly_donations_report, yearly_purchases_report, general_report)

def get_report_by_day(year: str, day: str):
	report = pd.DataFrame(st.session_state["PURCHASES"][(st.session_state["PURCHASES"]["שנה"] == year) & (st.session_state["PURCHASES"]["פרשה"].str.contains(day))])
	report = report.sort_values(by=["תאריך", "level"])

	display_day = sorted(report["פרשה"].tolist(), key=len)[0]

	date = datetime.strftime(report["תאריך"].tolist()[0], "%d.%m.%Y")
	message = f'פרשת "{display_day}" {year} - {date}'

	total = report["סכום"].sum()

	separation_row = ["", "", "", "", "", "", "", ""]
	separation_row = pd.DataFrame([separation_row], columns=report.columns[-1::-1])

	total_row = ["","","","", "", 'סה"כ', "", total]
	total_row = pd.DataFrame([total_row], columns=report.columns[-1::-1])

	report = pd.concat([report, separation_row, total_row])

	columns = report.columns
	reordered_columns = ["הערות"] + [col for col in columns if col != "הערות"]
	report = report[reordered_columns]
	
	return (report, message)

def get_general_report():
	people = dal.get_all_people()
	total_owed_reg = 0
	total_owed_gue = 0

	reg_names, reg_debts = [], []
	gue_names, gue_debts = [], []
	for person in people:
		_, _, report = get_report_by_person(person, dal.get_last_yesr())
		balance = float(report["סכום"].tolist()[0])

		if "אורח" in person:
			if balance > 0:
				total_owed_gue += balance
			gue_names.append(person)
			gue_debts.append(balance)
		else:
			if balance > 0:
				total_owed_reg += balance
			reg_names.append(person)
			reg_debts.append(balance)

	regulars_report = {
		"סכום": reg_debts + ["", total_owed_reg],
		"שם": reg_names + ["", "סך הכל"],
	}
	guests_report = {
		"סכום": gue_debts + ["", total_owed_gue],
		"שם": gue_names + ["", "סך הכל"],
	}

	regulars_report = pd.DataFrame(regulars_report)
	guests_report = pd.DataFrame(guests_report)


	return regulars_report, guests_report


try:
	if not "logged in" in st.session_state or \
		not st.session_state["logged in"]:
		with st.form("login form"):
			username = st.text_input("שם משתמש")
			password = st.text_input("סיסמא", type="password")
			
			if st.form_submit_button("login"):
				if username == st.secrets["credentials"]["username"] and \
					password == st.secrets["credentials"]["password"]:
					st.session_state["logged in"] = True
					st.rerun()
				else:
					st.error("כניסה נכשלה, אנא נסה שוב.")

		st.stop()

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


	actions = ["מילוי דוח שבועי", "דוח פרשה", "דוח מתפלל", "דוח כללי", "תיעוד תרומה", "הוצאת קבלות", "תיקון דוח מתפלל", "תיקון דוח פרשה"]
	action = st.sidebar.radio("מה תרצה לעשות?", options=actions, label_visibility="collapsed")

	if action != None:
		if action == "מילוי דוח שבועי":
			try:
				handle_purchase()
			except Exception as e:
				st.error(str(e))

			if st.session_state["purchase_submitted"]:
				st.success("הושלם בהצלחה!")
				time.sleep(1)

				st.session_state["purchase_key"] += 1
				st.session_state["purchase_submitted"] = False

				st.rerun()
		elif action == "תיעוד תרומה":
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
		elif action == "דוח מתפלל":
			name = st.selectbox("על מי תרצה להוציא דוח?", options=dal.get_all_people(), index=None, placeholder="בחר מתפלל")
			year = st.selectbox("שנה", options=dal.get_all_years(), index=len(dal.get_all_years())-1, placeholder="בחר שנה")
			
			if name != None:
				donations_report, purchases_report, general_report = get_report_by_person(name, year)
				purchases_report.drop(["שנה", "שם", "level"], axis=1, inplace=True)
				donations_report.drop(["שנה", "שם"], axis=1, inplace=True)
				general_report.drop(["שנה", "שם"], axis=1, inplace=True)
				

				st.write("חובות")
				display_dataframe(purchases_report)

				st.write("תרומות")
				display_dataframe(donations_report)

				st.write('סה"כ')
				display_dataframe(general_report)

				# Download buttons
				reports = [purchases_report, donations_report, general_report]
				titles = ["חובות", "תרומות", 'סה"כ']

				excel_file = to_excel_with_titles(reports, titles)
				pdf_file = to_pdf_reportlab(reports, titles)

				cols = st.columns([1.5, 1.7, 1.6, 1.7, 1.5])
				year = str(year).replace('"', '')
				cols[1].download_button("📥 Save as Excel", data=excel_file, file_name=f"{name} - {year}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
				cols[3].download_button("📄 Save as PDF", data=pdf_file, file_name=f"{name} - {year}.pdf", mime="application/pdf", use_container_width=True)
		elif action == "דוח פרשה":
			year = st.selectbox("שנה", options=dal.get_all_years(), index=len(dal.get_all_years())-1, placeholder="בחר שנה")
			if year != None:
				day = st.text_input("על איזה פרשה תרצה להוציא דוח?", placeholder="בחר פרשה")

			if st.button("הוצא דוח"):
				if year != None and day != "":
					report, message= get_report_by_day(year, day)
					report.drop(["תאריך", "שנה", "level"], axis=1, inplace=True)
					if len(set(report["פרשה"].tolist()) - set([""])) == 1:
						report.drop(["פרשה"], axis=1, inplace=True)


					st.write(message)
					display_dataframe(report)

					# Download buttons
					reports = [report]
					titles = [message]

					excel_file = to_excel_with_titles(reports, titles)
					pdf_file = to_pdf_reportlab(reports, titles)

					cols = st.columns([1.5, 1.7, 1.6, 1.7, 1.5])
					message = str(message).replace('"', '')
					cols[1].download_button("📥 Save as Excel", data=excel_file, file_name=f"{message}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
					cols[3].download_button("📄 Save as PDF", data=pdf_file, file_name=f"{message}.pdf", mime="application/pdf", use_container_width=True)
		elif action == "דוח כללי":
			regulars_report, guests_report = get_general_report()

			st.write("מתפללים רגילים")
			display_dataframe(regulars_report)

			st.write("אורחים")
			display_dataframe(guests_report)
		elif action == "הוצאת קבלות":
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
		elif action == "תיקון דוח מתפלל":
			name = st.selectbox("אצל מי צריך לתקן?", options=dal.get_all_people(), index=None, placeholder="בחר מתפלל", key=f"{st.session_state['fix_key']}")
			year = st.selectbox("שנה", options=dal.get_all_years(), index=len(dal.get_all_years())-1, placeholder="בחר שנה")
			
			if name != None and year != None:
				donations_report, purchases_report, _ = get_report_by_person(name, year)
				purchases_report.reset_index(inplace=True, drop=True)
				purchases_report.drop([0, len(purchases_report) - 2, len(purchases_report) - 1], axis=0, inplace=True)
				purchases_report.drop(["level"], axis=1, inplace=True)

				donations_report.drop([len(donations_report) - 2, len(donations_report) - 1], axis=0, inplace=True)
				donations_report = recombine_reciept_columns(donations_report)



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
						edited_purchases_report = edited_purchases_report[~edited_purchases_report["?האם למחוק"]]
						edited_donations_report = edited_donations_report[~edited_donations_report["?האם למחוק"]]

						edited_purchases_report.drop(["?האם למחוק"], axis=1, inplace=True)
						edited_donations_report.drop(["?האם למחוק"], axis=1, inplace=True)
						purchases_report.drop(["?האם למחוק"], axis=1, inplace=True)
						donations_report.drop(["?האם למחוק"], axis=1, inplace=True)


						with st.spinner("שומר..."):
							dal.update_person_data(name, year, edited_purchases_report, edited_donations_report)

						st.success("נשמר בהצלחה")
						st.session_state["fix_key"] += 1

						time.sleep(0.2)
						st.rerun()
					except Exception as e:
						st.error(str(e) + " was the error")
		elif action == "תיקון דוח פרשה":
			year = st.selectbox("שנה", options=dal.get_all_years(), index=len(dal.get_all_years())-1, placeholder="בחר שנה")
			day = st.selectbox("באחזה פרשה צריך לתקן?", options=dal.get_all_days(year), index=None, placeholder="בחר פרשה", key=f"{st.session_state['fix_key']}")
			
			if year != None and day != None:
				report, message = get_report_by_day(year, day)
				report.reset_index(inplace=True, drop=True)
				report.drop([len(report) - 2, len(report) - 1], axis=0, inplace=True)
				report.drop(["level"], axis=1, inplace=True)

				st.write(message)
				report.insert(0, "?האם למחוק", False)
				report.reset_index(drop=True, inplace=True)
				edited_report = st.data_editor(report, column_config={
					"תאריך": st.column_config.DateColumn(format="DD.MM.YYYY"),
					"מצוה": st.column_config.SelectboxColumn(options=st.session_state["MITZVOT"]),
					"שם": st.column_config.SelectboxColumn(options=st.session_state["PEOPLE"])
				}, hide_index=True, key="purchases_data_editor")


				if st.button("שמור"):
					try:
						edited_report = edited_report[~edited_report["?האם למחוק"]]
						edited_report = edited_report[~edited_report["?האם למחוק"]]

						edited_report.drop(["?האם למחוק"], axis=1, inplace=True)
						report.drop(["?האם למחוק"], axis=1, inplace=True)

						with st.spinner("שומר..."):
							dal.update_day_data(year, day, edited_report)

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










