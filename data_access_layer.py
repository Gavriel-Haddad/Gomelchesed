import streamlit as st
import sqlalchemy as sa
import pandas as pd


def load_db():
    # st.session_state["engine"] = sa.create_engine(st.secrets["postgres"]["db_url"])
    st.session_state["engine"] = sa.create_engine(r"postgresql://Gomelchesed_owner:npg_Bz0SUtTPgkv1@ep-spring-river-a20x0ye0-pooler.eu-central-1.aws.neon.tech/Gomelchesed?sslmode=require")
    engine = st.session_state["engine"]

    st.session_state["MITZVOT"] = pd.read_sql(sa.text("select מצוה from mitsvot order by level"), engine.connect())["מצוה"].tolist()
    st.session_state["PEOPLE"] = pd.read_sql("people", engine.connect())["שם"].tolist()
    st.session_state["PAYMENT_METHODS"] = pd.read_sql("payment_methods", engine.connect())["אופן תשלום"].tolist()

    st.session_state["DONATIONS"] = pd.read_sql("donations", engine.connect())
    st.session_state["PURCHASES"] = pd.read_sql(sa.text("""
                                            select p.*, m.level 
                                            from purchases p
                                            join mitsvot m on p."מצוה" = m."מצוה"
                                    """), engine.connect())

def get_all_people():
	return sorted(st.session_state["PEOPLE"])

def get_all_years():
	return sorted(list(set(st.session_state["PURCHASES"]["שנה"].tolist())))

def get_last_yesr():
	if len(get_all_years()) > 0:
		return get_all_years()[-1]
	else:
		return ""

def get_all_days(year: str):
	return list(set(st.session_state["PURCHASES"][st.session_state["PURCHASES"]["שנה"] == year]["פרשה"].tolist()))

def get_all_donations(reciepted):
	if reciepted:
		return st.session_state["DONATIONS"][st.session_state["DONATIONS"]["קבלה"]]
	else:
		return st.session_state["DONATIONS"][~st.session_state["DONATIONS"]["קבלה"]]

def insert_purchase(date, year, day, name, amount, mitsva):
    query = f"""
        INSERT INTO purchases (תאריך, שנה, פרשה, שם, סכום, מצוה)
        VALUES
        ('{date}', '{year}', '{day}', '{name}', {amount}, '{mitsva}')
    """

    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))

def insert_donation(date, year, name, amount, method, has_reciept, book_number, reciept_number):
    query = f"""
        insert into donations (תאריך, שנה, שם, סכום, "אופן תשלום", קבלה, "מספר פנקס", "מספר קבלה")
		VALUES
		('{date}', '{year}', '{name}', {amount}, '{method}', {has_reciept}, '{book_number}', '{reciept_number}')
    """
    
    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))
		
def mark_donations(data: pd.DataFrame):
    truncate_query = "TRUBCATE TABLE donations"
	
    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(truncate_query))
		
    data.to_sql("donations", if_exists='append')

def add_new_person(name: str):
    query = f"insert into people VALUES ('{name}')"
	
    with st.session_state["engine"].begin() as con:
        con.execute(sa.text(query))    

def update_person_data(name: str, year, new_purchases: pd.DataFrame, new_donations: pd.DataFrame):
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