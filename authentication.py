import streamlit as st
import streamlit_authenticator as stauth

def authenticate():
    # Load the credentials from st.secrets
    st.write("hello world")
    st.write(st.secrets)
        
    credentials = st.secrets["credentials"]
    cookie = st.secrets["cookie"]

    # Create an instance of the Authenticate class
    authenticator = stauth.Authenticate(
        credentials,         # credentials dict
        cookie["name"],      # cookie name
        cookie["key"],       # cookie key
        cookie["expiry_days"],
    )

    # Create a login widget
    name, authentication_status, username = authenticator.login("Login", "main")

    if authentication_status is False:
        return False;
    elif authentication_status is None:
        return None
    else:
        return True
        # If we're authenticated, show the protected content
        st.success(f"Welcome *{name}*!")
        st.write("You are now logged in. Here is your secure content...")

        # Add a logout button
        if st.button("Logout"):
            authenticator.logout("Logout", "main")
            st.experimental_rerun()
