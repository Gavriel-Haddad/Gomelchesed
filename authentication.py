import streamlit as st
import streamlit_authenticator as stauth

def authenticate():
    # Load the credentials from st.secrets
    credentials = dict(st.secrets["credentials"])
    cookie = dict(st.secrets["cookie"])

    # Create an instance of the Authenticate class
    authenticator = stauth.Authenticate(
        credentials,         # credentials dict
        cookie["name"],      # cookie name
        cookie["key"],       # cookie key
        cookie["expiry_days"],
    )


    # Create a login widget
    name, authentication_status, username = authenticator.login("Login")

    if authentication_status is None:
        pass
    elif authentication_status is False:
        st.session_state["logged_in"] = False
    else:
        st.session_state["logged_in"] = True