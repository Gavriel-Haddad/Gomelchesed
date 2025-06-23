import streamlit as st
import sqlalchemy as sa
import pandas as pd




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
    st.session_state["DONATIONS"] = pd.read_sql("donations", engine.connect())

def load_purchases():
    engine = st.session_state["engine"]
    st.session_state["PURCHASES"] = pd.read_sql(sa.text("""
                                            select p.*, m.level 
                                            from purchases p
                                            join mitsvot m on p."מצוה" = m."מצוה"
                                    """), engine.connect())

def load_db():
    # st.session_state["engine"] = sa.create_engine(st.secrets["postgres"]["db_url"], pool_pre_ping=True))
    st.session_state["engine"] = sa.create_engine(r"postgresql://Gomelchesed_owner:npg_Bz0SUtTPgkv1@ep-spring-river-a20x0ye0-pooler.eu-central-1.aws.neon.tech/Gomelchesed?sslmode=require", pool_pre_ping=True)

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
		return st.session_state["DONATIONS"][st.session_state["DONATIONS"]["קבלה"]]
	else:
		return st.session_state["DONATIONS"][~st.session_state["DONATIONS"]["קבלה"]]

def insert_purchase(date, year, day, name, amount, mitsva):
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
        INSERT INTO purchases (תאריך, שנה, פרשה, שם, סכום, מצוה)
        VALUES
        ('{date}', '{year}', '{day}', '{name}', {amount}, '{mitsva}')
    """

    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))

    load_purchases()

def insert_donation(date, year, name, amount, method, has_reciept, book_number, reciept_number):
    if not date \
        or not year \
        or not name \
        or not method \
        or amount == 0:
          raise Exception("מידע חסר")


    query = f"""
        insert into donations (תאריך, שנה, שם, סכום, "אופן תשלום", קבלה, "מספר פנקס", "מספר קבלה")
		VALUES
		('{date}', '{year}', '{name}', {amount}, '{method}', {has_reciept}, '{book_number}', '{reciept_number}')
    """
    
    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))
    
    load_donations()

def mark_reciepts(data: pd.DataFrame):
    if data["תאריך"].hasnans \
        or data["שנה"].hasnans \
        or data["שם"].hasnans \
        or data["אופן תשלום"].hasnans \
        or data["קבלה"].hasnans \
        or 0 in list(data["סכום"].values.tolist()):
          raise Exception("מידע חסר")
    
    data.to_sql("donations", st.session_state["engine"].connect(), if_exists='replace')
    load_donations()

def add_new_person(name: str):
    if not name:
          raise Exception("שם חסר")
    
    query = f"insert into people VALUES ('{name}')"
	
    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))    

    load_people()

def add_new_day(day: str):
    if not day:
        raise Exception("שם חסר")
    
    query = f"insert into days VALUES ('{day}')"
	
    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))    

    load_days()

def update_person_data(name: str, year, new_purchases: pd.DataFrame, new_donations: pd.DataFrame):
    if new_donations["תאריך"].hasnans \
        or new_donations["שנה"].hasnans \
        or new_donations["שם"].hasnans \
        or new_donations["אופן תשלום"].hasnans \
        or new_donations["קבלה"].hasnans \
        or 0 in list(new_donations["סכום"].values.tolist()):
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
    
    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))
    
    new_purchases.to_sql("purchases", st.session_state["engine"].connect(), if_exists='append', index=False)
    new_donations.to_sql("donations", st.session_state["engine"].connect(), if_exists='append', index=False)

    load_purchases()
    load_donations()

def update_day_data(year: str, day: str, new_day: pd.DataFrame):
    if new_day["תאריך"].hasnans \
        or new_day["שנה"].hasnans \
        or new_day["שם"].hasnans \
        or new_day["פרשה"].hasnans \
        or new_day["מצוה"].hasnans \
        or 0 in new_day["סכום"].values.tolist():
          raise Exception("מידע חסר")

    query = f"""
            delete from purchases
            where "פרשה" = '{day}'
            and "שנה" = '{year}';
        """
    
    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))
    
    new_day.to_sql("purchases", st.session_state["engine"].connect(), if_exists='append', index=False)
    load_purchases()
      



