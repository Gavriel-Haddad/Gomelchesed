import streamlit as st
import streamlit_authenticator as stauth
import sys
import os

def authenticate():
    try:
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
        auth_res = authenticator.login(location='main', key='Login')
        if auth_res:
            name, authentication_status, username = auth_res

            if authentication_status is False:
                return False;
            elif authentication_status is None:
                return None
            else:
                return True
        else:
            return None
        
    except Exception as e:
        st.write(str(e))
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        st.write(exc_type, fname, exc_tb.tb_lineno)