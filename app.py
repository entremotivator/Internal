import streamlit as st
import pandas as pd
import os
import json
import tempfile
import base64
import plotly.express as px
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Page configuration
st.set_page_config(page_title="Google Services Dashboard", page_icon="📊", layout="wide")

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'credentials' not in st.session_state:
    st.session_state.credentials = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'current_spreadsheet' not in st.session_state:
    st.session_state.current_spreadsheet = None
if 'current_worksheet' not in st.session_state:
    st.session_state.current_worksheet = None
if 'sheets_data' not in st.session_state:
    st.session_state.sheets_data = None

# Predefined spreadsheet URLs
SPREADSHEET_URLS = {
    "Grant": "https://docs.google.com/spreadsheets/d/1t80HNEgDIBFElZqodlvfaEuRj-bPlS4-R8T9kdLBtFk/edit?gid=0#gid=0",
    "Real Estate": "https://docs.google.com/spreadsheets/d/1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y/edit?gid=666156448#gid=666156448",
    "Agent": "https://docs.google.com/spreadsheets/d/1Om-RVVChe1GItsY4YaN_K95iM44vTpoxpSXzwTnOdAo/edit?gid=1557106830#gid=1557106830"
}

# Authentication sidebar
with st.sidebar:
    st.title("Google Services Dashboard")
    st.divider()
    
    # Authentication status display
    if st.session_state.authenticated:
        st.success(f"✅ Authenticated as {st.session_state.user_info.get('email', 'Unknown')}")
    else:
        st.error("❌ Not Authenticated")
    
    # Authentication method
    auth_method = st.radio("Authentication method:", ["Service Account"], index=0)
    
    if auth_method == "Service Account":
        uploaded_file = st.file_uploader("Upload service account JSON", type="json")
        
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_creds_path = tmp.name
            
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    temp_creds_path,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/calendar',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
                
                with open(temp_creds_path, 'r') as f:
                    sa_info = json.load(f)
                    email = sa_info.get('client_email', 'Service Account')
                
                st.session_state.authenticated = True
                st.session_state.credentials = credentials
                st.session_state.user_info = {'email': email, 'name': 'Service Account'}
                
                st.success("Authentication successful! Please refresh the page.")
                os.unlink(temp_creds_path)
                
            except Exception as e:
                st.error(f"Authentication failed: {str(e)}")
                os.unlink(temp_creds_path)
    
    # Logout button
    if st.session_state.authenticated:
        if st.button("Sign Out"):
            st.session_state.authenticated = False
            st.session_state.credentials = None
            st.session_state.user_info = None
            st.session_state.current_spreadsheet = None
            st.session_state.current_worksheet = None
            st.session_state.sheets_data = None
            st.success("Signed out. Please refresh the page.")
    
    # Navigation
    if st.session_state.authenticated:
        st.divider()
        st.subheader("Navigation")
        page = st.radio(
            "Select a page:",
            ["Google Sheets", "Google Calendar", "Google Drive"]
        )
    else:
        page = "Login Required"

# Helper functions
def load_spreadsheet_data():
    if not st.session_state.current_spreadsheet or not st.session_state.current_worksheet:
        return None
    
    try:
        gc = gspread.authorize(st.session_state.credentials)
        spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
        worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
        data = worksheet.get_all_values()
        
        if data:
            headers = data[0]
            df = pd.DataFrame(data[1:], columns=headers)
            
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except:
                    pass
            
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def spreadsheet_selector():
    # Preset spreadsheet selection
    st.subheader("Select a Preset Spreadsheet")
    preset_option = st.selectbox(
        "Choose a preset spreadsheet:",
        ["Select..."] + list(SPREADSHEET_URLS.keys())
    )
    
    spreadsheet_url = ""
    if preset_option != "Select...":
        spreadsheet_url = SPREADSHEET_URLS[preset_option]
        st.info(f"Selected: {preset_option} - {spreadsheet_url}")
    
    # Or enter custom URL
    st.subheader("Or Enter Custom URL")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        custom_url = st.text_input("Enter Google Sheets URL:", value=spreadsheet_url)
    
    with col2:
        load_button = st.button("Load", use_container_width=True)
    
    if custom_url and load_button:
        try:
            if "/d/" in custom_url and "/edit" in custom_url:
                spreadsheet_id = custom_url.split("/d/")[1].split("/edit")[0]
            else:
                spreadsheet_id = custom_url
            
            gc = gspread.authorize(st.session_state.credentials)
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet_list = [sheet.title for sheet in spreadsheet.worksheets()]
            
            st.session_state.current_spreadsheet = spreadsheet_id
            st.success(f"Spreadsheet loaded: {spreadsheet.title}")
            
            selected_sheet = st.selectbox("Select worksheet:", worksheet_list, index=0)
            
            if selected_sheet:
                st.session_state.current_worksheet = selected_sheet
                df = load_spreadsheet_data()
                if df is not None:
                    st.session_state.sheets_data = df
                    return True
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    return False

# Main content area
if not st.session_state.authenticated:
    st.title("Welcome to Google Services Dashboard")
    st.info("Please authenticate using the sidebar to access the application.")
    
    st.header("Features")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        - Connect to and analyze Google Sheets data
        - View and manage Google Calendar events
        - Upload and manage files on Google Drive
        - Access preset spreadsheets for Grant, Real Estate, and Agent data
        """)
    with col2:
        st.image("https://storage.googleapis.com/gweb-cloudblog-publish/images/1_GDragon_hero_image_1.max-2000x2000.jpg", 
                 caption="Connect to Google Services", width=300)

elif page == "Google Sheets":
    st.title("Google Sheets Data Viewer")
    
    # Spreadsheet selector
    data_loaded = spreadsheet_selector()
    
    if data_loaded and st.session_state.sheets_data is not None:
        df = st.session_state.sheets_data
        
        # Data overview
        st.header("Data Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", f"{len(df)}")
        with col2:
            st.metric("Columns", f"{len(df.columns)}")
        with col3:
            numeric_cols = df.select_dtypes(include=['number']).columns
            st.metric("Numeric Columns", f"{len(numeric_cols)}")
        
        # Data preview
        st.header("Data Preview")
        st.dataframe(df.head(10), use_container_width=True)
        
        # Simple visualization
        if len(numeric_cols) > 0:
            st.header("Quick Visualization")
            
            viz_type = st.selectbox("Chart type:", ["Bar Chart", "Line Chart", "Scatter Plot"])
            
            if viz_type == "Bar Chart":
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                if categorical_cols:
                    x_col = st.selectbox("Category (X-axis):", categorical_cols)
                    y_col = st.selectbox("Value (Y-axis):", numeric_cols)
                    
                    fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No categorical columns found for bar chart.")
            
            elif viz_type == "Line Chart":
                x_col = st.selectbox("X-axis:", df.columns.tolist())
                y_col = st.selectbox("Y-axis:", numeric_cols)
                
                fig = px.line(df.sort_values(x_col), x=x_col, y=y_col, title=f"{y_col} over {x_col}")
                st.plotly_chart(fig, use_container_width=True)
            
            elif viz_type == "Scatter Plot":
                x_col = st.selectbox("X-axis:", numeric_cols)
                y_cols = [col for col in numeric_cols if col != x_col]
                if y_cols:
                    y_col = st.selectbox("Y-axis:", y_cols)
                    
                    fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Need at least two numeric columns for scatter plot.")
        
        # Download option
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="data.csv">Download CSV</a>'
        st.markdown(href, unsafe_allow_html=True)

elif page == "Google Calendar":
    st.title("Google Calendar Events")
    
    try:
        service = build('calendar', 'v3', credentials=st.session_state.credentials)
        
        calendar_id = st.text_input("Calendar ID (or 'primary'):", "primary")
        
        if calendar_id:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start date", datetime.now().date())
            with col2:
                end_date = st.date_input("End date", (datetime.now() + timedelta(days=30)).date())
            
            if start_date <= end_date:
                start_datetime = datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z'
                end_datetime = datetime.combine(end_date, datetime.max.time()).isoformat() + 'Z'
                
                with st.spinner("Fetching events..."):
                    events_result = service.events().list(
                        calendarId=calendar_id,
                        timeMin=start_datetime,
                        timeMax=end_datetime,
                        maxResults=50,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                
                if events:
                    st.header(f"Events ({len(events)})")
                    
                    for event in events:
                        start = event['start'].get('dateTime', event['start'].get('date'))
                        end = event['end'].get('dateTime', event['end'].get('date'))
                        
                        if 'T' in start:
                            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            start_formatted = start_dt.strftime('%Y-%m-%d %H:%M')
                        else:
                            start_formatted = start
                        
                        with st.expander(f"{start_formatted} - {event.get('summary', 'No title')}"):
                            st.write(f"**End:** {end}")
                            if event.get('location'):
                                st.write(f"**Location:** {event.get('location')}")
                            if event.get('description'):
                                st.write("**Description:**")
                                st.write(event.get('description'))
                else:
                    st.info(f"No events found between {start_date} and {end_date}.")
            else:
                st.error("End date must be after start date.")
    except Exception as e:
        st.error(f"Error accessing Google Calendar: {str(e)}")

elif page == "Google Drive":
    st.title("Google Drive File Manager")
    
    try:
        drive_service = build('drive', 'v3', credentials=st.session_state.credentials)
        
        drive_tab = st.radio("Select function:", ["Upload Files", "Browse Files"], horizontal=True)
        
        if drive_tab == "Upload Files":
            st.header("Upload Files to Google Drive")
            
            uploaded_file = st.file_uploader("Choose a file to upload")
            
            folders_result = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = folders_result.get('files', [])
            folder_options = ["root"] + [folder['name'] for folder in folders]
            selected_folder = st.selectbox("Destination folder:", folder_options)
            
            if selected_folder == "root":
                folder_id = "root"
            else:
                folder_id = next(folder['id'] for folder in folders if folder['name'] == selected_folder)
            
            if uploaded_file and st.button("Upload"):
                with st.spinner("Uploading..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uploaded_file.name}') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        temp_file_path = tmp.name
                    
                    try:
                        file_metadata = {
                            'name': uploaded_file.name,
                            'parents': [folder_id]
                        }
                        
                        media = MediaFileUpload(temp_file_path, resumable=True)
                        
                        file = drive_service.files().create(
                            body=file_metadata,
                            media_body=media,
                            fields='id,name,webViewLink'
                        ).execute()
                        
                        os.unlink(temp_file_path)
                        
                        st.success(f"File uploaded: {file.get('name')}")
                        st.markdown(f"[View in Drive]({file.get('webViewLink')})")
                    
                    except Exception as e:
                        os.unlink(temp_file_path)
                        st.error(f"Error uploading: {str(e)}")
        
        elif drive_tab == "Browse Files":
            st.header("Browse Google Drive Files")
            
            folders_result = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = [{'id': 'root', 'name': 'Root'}] + folders_result.get('files', [])
            
            selected_folder = st.selectbox("Select folder:", [folder['name'] for folder in folders])
            folder_id = next(folder['id'] for folder in folders if folder['name'] == selected_folder)
            
            with st.spinner("Loading files..."):
                files_result = drive_service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces='drive',
                    fields="files(id, name, mimeType, webViewLink)"
                ).execute()
                
                files = files_result.get('files', [])
            
            if files:
                st.write(f"Found {len(files)} files in {selected_folder}")
                
                for file in files:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"{file.get('name')} ({file.get('mimeType')})")
                    with col2:
                        st.markdown(f"[Open]({file.get('webViewLink')})")
            else:
                st.info(f"No files found in {selected_folder}")
    
    except Exception as e:
        st.error(f"Error accessing Google Drive: {str(e)}")

st.divider()
st.caption("Google Services Dashboard | Developed with Streamlit")
