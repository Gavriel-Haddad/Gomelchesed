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

    st.write(name, authentication_status, username)
    if st.session_state["authentication_status"] is None:
        pass
    elif st.session_state["authentication_status"] is False:
        st.error("Username/password is incorrect")
    else:
        st.session_state["logged_in"] = True
        return True