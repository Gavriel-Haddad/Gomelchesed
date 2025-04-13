import streamlit as st
import streamlit_authenticator as stauth
import sys
import os

def authenticate():
    # Load the credentials from st.secrets
    credentials = dict(st.secrets["credentials"])
    cookie = dict(st.secrets["cookie"])

    # Create an instance of the Authenticate class
    authenticator = stauth.Authenticate(credentials,         # credentials dict
        cookie["name"],      # cookie name
        cookie["key"],       # cookie key
        cookie["expiry_days"],
    )


    # Create a login widget
    auth_res = authenticator.login(location='unrendered', key='Login')

    if auth_res:
        st.write("we are in")
        name, authentication_status, username = auth_res

        if authentication_status is None:
            pass
        elif authentication_status is False:
            st.session_state["logged_in"] = False
        else:
            st.session_state["logged_in"] = True
    else:
        st.write("we are not in")
        return None