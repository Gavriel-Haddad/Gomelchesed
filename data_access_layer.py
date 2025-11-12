import streamlit as st
import sqlalchemy as sa
import pandas as pd
from datetime import datetime


def load_days():
    engine = st.session_state["engine"]
    st.session_state["DAYS"] = pd.read_sql(sa.text("select day from days"), engine.connect())["day"].tolist()

def load_mitzvot():
    engine = st.session_state["engine"]
    st.session_state["MITZVOT"] = pd.read_sql(sa.text("select מצוה from mitsvot order by level"), engine.connect())["מצוה"].tolist()
      
def load_people():
    engine = st.session_state["engine"]
    st.session_state["PEOPLE"] = pd.read_sql("people", engine.connect())["שם"].tolist()

def load_payment_methods():
    engine = st.session_state["engine"]
    st.session_state["PAYMENT_METHODS"] = pd.read_sql("payment_methods", engine.connect())["אופן תשלום"].tolist()

def load_donations():
    engine = st.session_state["engine"]
    data = pd.read_sql("donations", engine.connect())

    new_column_order = ["תאריך", "שנה", "שם", "סכום", "אופן תשלום", "מספר פנקס", "מספר קבלה", "הערות"]
    data = data[new_column_order]

    st.session_state["DONATIONS"] = data

def load_purchases():
    engine = st.session_state["engine"]
    st.session_state["PURCHASES"] = pd.read_sql(sa.text("""
                                            select p.*, m.level 
                                            from purchases p
                                            join mitsvot m on p."מצוה" = m."מצוה"
                                    """), engine.connect())

def load_db():
    st.session_state["engine"] = sa.create_engine(st.secrets["postgres"]["db_url"], pool_pre_ping=True)

    load_days()
    load_mitzvot()
    load_people()
    load_payment_methods()
    load_donations()
    load_purchases()


def get_all_people():
    return sorted(set(st.session_state["PEOPLE"]))

def get_all_years():
    purchases_years = st.session_state["PURCHASES"]["שנה"].tolist()
    donations_years = st.session_state["DONATIONS"]["שנה"].tolist()

    return sorted(list(set(purchases_years + donations_years)))

def get_last_yesr():
	if len(get_all_years()) > 0:
		return get_all_years()[-1]
	else:
		return ""

def get_all_days(year: str = ""):
    if year:
        return list(set(st.session_state["PURCHASES"][st.session_state["PURCHASES"]["שנה"] == year]["פרשה"].tolist()))
    else:
        return st.session_state["DAYS"]

def get_all_donations(reciepted):
	if reciepted:
		return st.session_state["DONATIONS"][st.session_state["DONATIONS"]["מספר קבלה"]]
	else:
		return st.session_state["DONATIONS"][~st.session_state["DONATIONS"]["מספר קבלה"]]




def execute_query(query: str):
    # log the query (query, and datetime it was made) and execute it
    engine = st.session_state["engine"]

    log_query = f"""
        insert into logs (log, date)
        values ('{query.replace("'", "''")}', '{datetime.now()}')
    """

    with engine.begin() as con:
        con.execute(sa.text(query))
        con.execute(sa.text(log_query))

def insert_purchase(date, year, day, name, amount, mitsva, notes):
    if not date:
        raise Exception("תאריך חסר")
    if not year:
        raise Exception("שנה חסרה")
    if not day:
        raise Exception("יום חסר")
    if not name:
        raise Exception("שם חסר")
    if not mitsva:
        raise Exception("מצווה חסרה")

    
    query = f"""
        INSERT INTO purchases (הערות, תאריך, שנה, פרשה, שם, סכום, מצוה)
        VALUES
        ('{notes}', '{date}', '{year}', '{day}', '{name}', {amount}, '{mitsva}')
    """

    execute_query(query)
    load_purchases()

def insert_donation(date, year, name, amount, method, book_number, reciept_number, notes):
    if not date \
        or not year \
        or not name \
        or not method:
          raise Exception("מידע חסר")


    query = f"""
        insert into donations (תאריך, שנה, שם, סכום, "אופן תשלום", "מספר פנקס", "מספר קבלה",הערות)
		VALUES
		('{date}', '{year}', '{name}', {amount}, '{method}', '{book_number}', '{reciept_number}', '{notes}')
    """
    
    execute_query(query)
    
    load_donations()

def add_new_person(name: str):
    if not name:
          raise Exception("שם חסר")
    
    query = f"insert into people VALUES ('{name}')"
	
    execute_query(query)

    load_people()

def add_new_day(day: str):
    if not day:
        raise Exception("שם חסר")
    
    query = f"insert into days VALUES ('{day}')"
	
    execute_query(query)
    load_days()

def add_new_mitsva(mitsva: str):
    if not mitsva:
        raise Exception("מצוה חסרה")
    
    query = f"insert into mitsvot VALUES ('{mitsva}', NULL)"
	
    execute_query(query)
    load_mitzvot()


def mark_reciepts(data: pd.DataFrame):
    if data["תאריך"].hasnans \
        or data["שנה"].hasnans \
        or data["שם"].hasnans \
        or data["אופן תשלום"].hasnans:
          raise Exception("מידע חסר")
    
    data.to_sql("donations", st.session_state["engine"].connect(), if_exists='replace', index=False)
    load_donations()

def update_person_data(name: str, year, new_purchases: pd.DataFrame, new_donations: pd.DataFrame):
    if new_donations["תאריך"].hasnans \
        or new_donations["שנה"].hasnans \
        or new_donations["שם"].hasnans \
        or new_donations["אופן תשלום"].hasnans:
          raise Exception("מידע חסר")
    
    if new_purchases["תאריך"].hasnans \
        or new_purchases["שנה"].hasnans \
        or new_purchases["שם"].hasnans \
        or new_purchases["פרשה"].hasnans \
        or new_purchases["מצוה"].hasnans:
          raise Exception("מידע חסר")

    
    query = f"""
            delete from purchases
            where "שם" = '{name}'
            and "שנה" = '{year}';

            delete from donations
            where "שם" = '{name}'
            and "שנה" = '{year}';
        """
    
    execute_query(query)
    new_purchases.to_sql("purchases", st.session_state["engine"].connect(), if_exists='append', index=False)
    new_donations.to_sql("donations", st.session_state["engine"].connect(), if_exists='append', index=False)

    load_purchases()
    load_donations()

def update_day_data(year: str, day: str, new_day: pd.DataFrame):
    if new_day["תאריך"].hasnans \
        or new_day["שנה"].hasnans \
        or new_day["שם"].hasnans \
        or new_day["פרשה"].hasnans \
        or new_day["מצוה"].hasnans:
          raise Exception("מידע חסר")

    query = f"""
            delete from purchases
            where "פרשה" = '{day}'
            and "שנה" = '{year}';
        """
    
    execute_query(query)
    new_day.to_sql("purchases", st.session_state["engine"].connect(), if_exists='append', index=False)

    load_purchases()
      



