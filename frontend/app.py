import streamlit as st
import requests

# App Title 🎉
st.set_page_config(page_title="CreditCheck Chat Application", page_icon="💳")
st.title("💳 CreditCheck Chat Application")
st.markdown("Your personal assistant for seamless credit assessments and financial guidance! 💼")

# Add developer and organization links
st.sidebar.markdown("### Developer Profile")
st.sidebar.markdown("[![GitHub](https://img.shields.io/badge/GitHub-Sayrikey1-blue?style=flat-square&logo=github)](https://github.com/Sayrikey1)")

BASE_URL = "http://127.0.0.1:8000/"
# BASE_URL = "https://your-api-endpoint.com/"

def signup():
    st.subheader("👤 Create an Account")
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    email = st.text_input("📧 Email")
    password = st.text_input("🔑 Password", type="password")
    role = st.selectbox("🎭 Select Role", ["staff", "admin"])
    
    if st.button("🚀 Sign Up"):
        response = requests.post(f"{BASE_URL}/auth/signup", json={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
            "role": role
        })
        if response.status_code == 201:
            st.success("🎉 User registered successfully! You can now log in.")
        else:
            st.error(response.json().get("detail", "Registration failed ❌"))

def login():
    st.subheader("🔑 Login to Your Account")
    email = st.text_input("📧 Email")
    password = st.text_input("🔒 Password", type="password")
    
    if st.button("✅ Login"):
        response = requests.post(f"{BASE_URL}/auth/login", data={
            "username": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json()["access_token"]
            st.session_state["token"] = token
            st.session_state["logged_in"] = True
            st.success("🎉 Login successful! Welcome back!")
            st.rerun()  # Rerun the app to redirect to the chatbot page
        else:
            st.error(response.json().get("detail", "Login failed ❌"))

def get_user():
    st.subheader("📋 User Profile")
    token = st.session_state.get("token")
    if not token:
        st.warning("⚠️ Please log in first.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/user/me", headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        
        # Display user profile in a clean format
        st.markdown("### 🧑‍💻 User Information")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**First Name:** {user_data.get('first_name', 'N/A')}")
            st.markdown(f"**Last Name:** {user_data.get('last_name', 'N/A')}")
            st.markdown(f"**Email:** {user_data.get('email', 'N/A')}")
        
        with col2:
            st.markdown(f"**Account Status:** {'Active ✅' if user_data.get('is_active') else 'Inactive ❌'}")
            st.markdown(f"**Superuser:** {'Yes 👑' if user_data.get('is_superuser') else 'No'}")
            st.markdown(f"**Verified:** {'Yes ✔️' if user_data.get('is_verified') else 'No ❌'}")
        
        st.success("✅ Profile loaded successfully!")
    else:
        st.error(response.json().get("detail", "Failed to fetch user details ❌"))

def chatbot_page():
    st.subheader("🤖 Chatbot")
    token = st.session_state.get("token")
    if not token:
        st.warning("⚠️ Please log in first.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Fetch chat history
    response = requests.get(f"{BASE_URL}/chatbot/history/", headers=headers)
    if response.status_code == 200:
        chat_history = response.json()
        
        # Add a dropdown to select the number of messages to display
        max_messages = st.selectbox(
            "Show last messages:",
            options=[10, 15, 20, 25],
            index=0  # Default to 10 messages
        )
        
        # Display only the last `max_messages` messages
        for chat in chat_history[-max_messages:]:
            st.write(f"**You:** {chat['user_input']}")
            st.write(f"**Bot:** {chat['response']}")
            st.write(f"*{chat['timestamp']}*")
            st.write("---")
    else:
        st.error("Waiting for responses... ⏳")
    
    # Chat input
    user_input = st.text_input("Type your message here...")
    if st.button("Send"):
        if user_input.strip():
            with st.spinner("🤖 Bot is thinking..."):
                response = requests.post(f"{BASE_URL}/chatbot/", json={"user_input": user_input}, headers=headers)
                if response.status_code == 200:
                    st.write(f"**Bot:** {response.json()['response']}")
                    st.rerun()  # Rerun the app to refresh the chat history
                else:
                    st.error("Waiting for responses... ⏳")

        else:
            st.warning("Please enter a message.")

def main():
    st.sidebar.title("🔍 Navigation")
    if st.session_state.get("logged_in"):
        option = st.sidebar.radio("Go to", ["🤖 Chatbot", "👤 Profile"])
    else:
        option = st.sidebar.radio("Go to", ["🏠 Sign Up", "🔐 Login"])
    
    if option == "🏠 Sign Up":
        signup()
    elif option == "🔐 Login":
        login()
    elif option == "👤 Profile":
        get_user()
    elif option == "🤖 Chatbot":
        chatbot_page()

if __name__ == "__main__":
    main()
