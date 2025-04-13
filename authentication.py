import streamlit as st
import os

def main():
    # os.system(r"C:\Users\USER\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe -m pip install --upgrade pip")
    import pip
    pip.main(["install", "streamlit-authenticator", "--force-reinstall"])
    import streamlit_authenticator as stauth
    
    # Load the credentials from st.secrets
    credentials = st.secrets["credentials"]
    cookie = st.secrets["cookie"]
    preauthorized = st.secrets.get("preauthorized", {})

    # Create an instance of the Authenticate class
    authenticator = stauth.Authenticate(
        credentials,         # credentials dict
        cookie["name"],      # cookie name
        cookie["key"],       # cookie key
        cookie["expiry_days"],
        preauthorized  # optional preauthorized emails
    )

    # Create a login widget
    name, authentication_status, username = authenticator.login("Login", "main")

    if authentication_status is False:
        st.error("Username/password is incorrect")
    elif authentication_status is None:
        st.warning("Please enter your username and password")
    else:
        # If we're authenticated, show the protected content
        st.success(f"Welcome *{name}*!")
        st.write("You are now logged in. Here is your secure content...")

        # Add a logout button
        if st.button("Logout"):
            authenticator.logout("Logout", "main")
            st.experimental_rerun()

if __name__ == "__main__":
    main()
