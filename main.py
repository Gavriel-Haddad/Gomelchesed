import streamlit as st
import pandas as pd
import time

from authentication import authenticate
from datetime import datetime

st.markdown("""
<style>
/* Apply RTL globally */
html, body, [data-testid="stAppViewContainer"] {
    direction: rtl;
    unicode-bidi: bidi-override;
    text-align: right;
}

/* Override RTL for dataframes */
[data-testid="stDataFrame"] {
    direction: ltr !important;
    text-align: left !important;
}
</style>
""", unsafe_allow_html=True)

BASE_PATH = r"sinagog.xlsx"
PURCHASES_PATH = (BASE_PATH, "מכירות")
DONATIONS_PATH = (BASE_PATH, "תרומות")
MITZVOT_PATH = (BASE_PATH, "מצוות")
PAYMENT_PATH = (BASE_PATH, "אופני תשלום")

PURCHASES = pd.read_excel(PURCHASES_PATH[0], sheet_name=PURCHASES_PATH[1])
DONATIONS = pd.read_excel(DONATIONS_PATH[0], sheet_name=DONATIONS_PATH[1])
MITZVOT = pd.read_excel(MITZVOT_PATH[0], sheet_name=MITZVOT_PATH[1])["מצוה"]
PAYMENT_METHODS = pd.read_excel(PAYMENT_PATH[0],sheet_name=PAYMENT_PATH[1])["אופן תשלום"]

if "purchase_key" not in st.session_state:
	st.session_state["purchase_key"] = 0
if "purchase_submitted" not in st.session_state:
	st.session_state["purchase_submitted"] = False
if "donation_submitted" not in st.session_state:
	st.session_state["donation_submitted"] = False
if "reciepts_submitted" not in st.session_state:
	st.session_state["reciepts_submitted"] = False




def get_all_people():
	return sorted(list(set(PURCHASES["שם"].tolist() + DONATIONS["שם"].tolist())))

def get_all_years():
	return sorted(list(set(PURCHASES["שנה"].tolist())))

def get_last_yesr():
	if len(get_all_years()) > 0:
		return get_all_years()[-1]
	else:
		return ""

def get_all_days(year: str):
	return list(set(PURCHASES[PURCHASES["שנה"] == year]["פרשה"].tolist()))

def get_all_donations(reciepted):
	if reciepted:
		return DONATIONS[DONATIONS["קבלה"]]
	else:
		return DONATIONS[~DONATIONS["קבלה"]]

def display_dataframe(data: pd.DataFrame, editable = False):
	st.dataframe(data, column_config={
		"תאריך": st.column_config.DateColumn(format="DD.MM.YYYY"),
	},
	hide_index=True)

def update_db():
	with pd.ExcelWriter(PURCHASES_PATH[0]) as writer:
		PURCHASES.to_excel(writer, sheet_name=PURCHASES_PATH[1], index=False)
		DONATIONS.to_excel(writer, sheet_name=DONATIONS_PATH[1], index=False)
		MITZVOT.to_excel(writer, sheet_name=MITZVOT_PATH[1], index=False)
		PAYMENT_METHODS.to_excel(writer, sheet_name=PAYMENT_PATH[1], index=False)


def handle_reciepts():
	u_data = get_all_donations(reciepted=False)
	r_data = get_all_donations(reciepted=True)

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
			global DONATIONS
			DONATIONS = pd.concat([u_data, r_data])
			update_db()

			st.session_state["reciepts_submitted"] = True
	else:
		st.success("אין על מה להוציא קבלות!!")
	
def handle_purchase():
	global PURCHASES
	global DONATIONS

	date = st.date_input("תאריך", format="DD.MM.YYYY")
	year = st.text_input("שנה", value=get_last_yesr())
	day = st.text_input("פרשה")

	name = st.selectbox("שם", options=get_all_people() + ["חדש"], index=None, placeholder="בחר מתפלל", key=f"name {st.session_state['purchase_key']}")
	if name == "חדש":
		new_name = st.text_input("שם", placeholder="מתפלל חדש", key=f"new_name {st.session_state['purchase_key']}")
	else:
		new_name = None  # to keep variable defined

	if name != None:
		mitsva = st.selectbox("מצוה", options=MITZVOT, index=None, key=f"mitsva {st.session_state['purchase_key']}")
		amount = st.number_input("סכום", step=1, key=f"amount {st.session_state['purchase_key']}")

		if st.button("שמור"):
			final_name = name if name != "חדש" else new_name
			purchase = {
				"תאריך" : [date],
				"שנה" : [year],
				"פרשה" : [day],
				"שם" : [final_name],
				"סכום" : [amount],
				"מצוה" : [mitsva],
			}

			PURCHASES = pd.concat([PURCHASES, pd.DataFrame.from_dict(purchase)])

			update_db()

			st.session_state["purchase_key"] += 1
			st.session_state["purchase_submitted"] = True

def handle_donation():
	global PURCHASES
	global DONATIONS
	global PAYMENT_METHODS

	name = st.selectbox("שם", options=get_all_people() + ["חדש"], index=None, placeholder="בחר מתפלל")

	if name == "חדש":
		new_name = st.text_input("שם", placeholder="מתפלל חדש")
	else:
		new_name = None  # to keep variable defined

	if name != None:
		date = st.date_input("תאריך", format="DD.MM.YYYY")
		year = st.text_input("שנה", value=get_last_yesr())
		amount = st.number_input("סכום", step=1)
		method = st.selectbox("אופן תשלום", options=PAYMENT_METHODS)
		has_reciept = st.checkbox("האם ניתנה קבלה?")

		book = " "
		reciept = " "

		if has_reciept:
			book = st.text_input("מספר פנקס")
			reciept = st.text_input("מספר קבלה")

		if st.button("שמור"):
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

			DONATIONS = pd.concat([DONATIONS, pd.DataFrame.from_dict(donation)])

			update_db()

			st.session_state["donation_submitted"] = True



def get_report_by_person(name: str, year: str = None):
	if year:
		yearly_purchases_report = PURCHASES[(PURCHASES["שם"] == name) & (PURCHASES["שנה"] == year)].drop("שם", axis=1)
		yearly_donations_report = DONATIONS[(DONATIONS["שם"] == name) & (DONATIONS["שנה"] == year)].drop("שם", axis=1)

		previous_purchases_report = PURCHASES[(PURCHASES["שם"] == name) & (PURCHASES["שנה"] < year)].drop("שם", axis=1)
		previous_donations_report = DONATIONS[(DONATIONS["שם"] == name) & (DONATIONS["שנה"] < year)].drop("שם", axis=1)


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
			'סך הכל שנה נוכחית': [previous_total],
			'סך הכל': [total_sum],
		}

		general_report = pd.DataFrame.from_dict(general_report)
		return (general_report, yearly_donations_report, yearly_purchases_report)
	else:
		purchases_report = PURCHASES[PURCHASES["שם"] == name].drop("שם", axis=1)
		donations_report = DONATIONS[DONATIONS["שם"] == name].drop("שם", axis=1)

		purchases_sum = purchases_report["סכום"].sum()
		donations_sum = donations_report["סכום"].sum()
		
		total = donations_sum - purchases_sum

		general_report = {
			'תרומות': [donations_sum],
			'חובות': [purchases_sum],
			'סך הכל': [total],
		}

		general_report = pd.DataFrame.from_dict(general_report)
		return (general_report, donations_report, purchases_report)

def get_report_by_day(year: str, day: str):
	report = PURCHASES[(PURCHASES["שנה"] == year) & (PURCHASES["פרשה"] == day)]
	date = datetime.strftime(report["תאריך"].tolist()[0], "%d.%m.%Y")
	message = f"שבת פרשת {day}, שנת {year}, {date}"

	return (report.drop(["תאריך", "שנה", "פרשה"], axis=1), message, report["סכום"].sum())

def get_general_report():
	people = get_all_people()
	money_owed = 0

	names, debts = [], []
	for person in people:
		report, _, _ = get_report_by_person(person)
		
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




if "logged_in" not in st.session_state:
	st.write("hello there")
	authenticate()
elif not st.session_state["logged_in"]:
	st.error("Username/password is incorrect")
else:
	actions = ["למלא דוח שבועי", "לתעד תרומה", "להוציא קבלות", "להוציא דוח"]
	action = st.selectbox("מה תרצה לעשות?", options=actions, index=None, placeholder="בחר אפשרות")#, key=st.session_state["purchase_key"])

	if action != None:
		if action == "למלא דוח שבועי":
			handle_purchase()

			if st.session_state["purchase_submitted"]:
				st.success("הושלם בהצלחה!")
				time.sleep(0.2)

				st.session_state["purchase_submitted"] = False

				st.rerun()
		elif action == "לתעד תרומה":
			handle_donation()

			if st.session_state["donation_submitted"]:
				st.success("הושלם בהצלחה!")
				time.sleep(0.2)

				st.session_state["purchase_key"] += 1
				st.session_state["donation_submitted"] = False

				st.rerun()
		elif action == "להוציא דוח":
			options = ["לפי אדם", "לפי פרשה", "כללי"]
			choice = st.selectbox("איזה דוח תרצה להוציא?", options=options, index=None, placeholder="בחר דוח")


			if choice == "לפי אדם":
				name = st.selectbox("על מי תרצה להוציא דוח?", options=get_all_people(), index=None, placeholder="בחר אדם")
				year = st.selectbox("שנה", options=get_all_years(), index=len(get_all_years())-1, placeholder="בחר שנה")
				
				if name != None:
					general_report, donations_report, purchases_report = get_report_by_person(name, year)

					st.write("כללי")
					display_dataframe(general_report)

					st.write("חובות")
					display_dataframe(purchases_report)

					st.write("תרומות")
					display_dataframe(donations_report)
			elif choice == "לפי פרשה":
				year = st.selectbox("שנה", options=get_all_years(), index=None, placeholder="בחר שנה")
				if year != None:
					day = st.selectbox("על איזה פרשה תרצה להוציא דוח?", options=get_all_days(year), index=None, placeholder="בחר פרשה")

				if year != None and day != None:
					report, message, total = get_report_by_day(year, day)
					
					st.write(message)
					st.write(f"סכום כולל: {total:,}")
					display_dataframe(report)

			elif choice == "כללי":
				total, general_report = get_general_report()

				st.write(f"כסף בחוץ: {total:,}")
				display_dataframe(general_report)
		elif action == "להוציא קבלות":
			handle_reciepts()
			
			if st.session_state["reciepts_submitted"]:
				st.success("הושלם בהצלחה!")
				time.sleep(0.2)

				st.session_state["purchase_key"] += 1
				st.session_state["reciepts_submitted"] = False

				st.rerun()

