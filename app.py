import streamlit as st
import pandas as pd
import os
import json
import tempfile
import base64
import plotly.express as px
from datetime import datetime, timedelta
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Page configuration
st.set_page_config(page_title="Real Estate Dashboard", page_icon="🏠", layout="wide")

# Constants
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/calendar'
]

# Predefined spreadsheet information
SPREADSHEETS = {
    "Grant": {
        "id": "1t80HNEgDIBFElZqodlvfaEuRj-bPlS4-R8T9kdLBtFk",
        "name": "Grant Information",
        "description": "Grant application and funding data",
        "icon": "📊"
    },
    "Real Estate": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y",
        "name": "Real Estate Properties",
        "description": "Property listings and details",
        "icon": "🏠"
    },
    "Agent": {
        "id": "1Om-RVVChe1GItsY4YaN_K95iM44vTpoxpSXzwTnOdAo",
        "name": "Agent Information",
        "description": "Agent profiles and performance metrics",
        "icon": "👤"
    }
}

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
if 'auth_method' not in st.session_state:
    st.session_state.auth_method = "Service Account"
if 'token_path' not in st.session_state:
    st.session_state.token_path = None

# Helper functions
def save_uploaded_file(uploaded_file):
    """Save uploaded file to a temporary location and return the path"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uploaded_file.name}') as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name

def authenticate_service_account(json_path):
    """Authenticate using a service account JSON file"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            json_path,
            scopes=SCOPES
        )
        
        with open(json_path, 'r') as f:
            sa_info = json.load(f)
            email = sa_info.get('client_email', 'Service Account')
        
        st.session_state.authenticated = True
        st.session_state.credentials = credentials
        st.session_state.user_info = {'email': email, 'name': 'Service Account'}
        st.session_state.auth_method = "Service Account"
        
        return True, "Authentication successful!"
    except Exception as e:
        return False, f"Authentication failed: {str(e)}"

def authenticate_oauth(client_secrets_path):
    """Authenticate using OAuth 2.0"""
    try:
        # Create token directory if it doesn't exist
        token_dir = Path("./tokens")
        token_dir.mkdir(exist_ok=True)
        
        # Token path for this specific client secrets file
        token_path = token_dir / f"token_{hash(client_secrets_path)}.pickle"
        st.session_state.token_path = token_path
        
        creds = None
        # Check if token file exists
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If credentials don't exist or are invalid, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_path, SCOPES)
                creds = flow.run_local_server(port=8501)
            
            # Save the credentials for the next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        # Get user info
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        
        st.session_state.authenticated = True
        st.session_state.credentials = creds
        st.session_state.user_info = {
            'email': user_info.get('email', 'Unknown'),
            'name': user_info.get('name', 'OAuth User')
        }
        st.session_state.auth_method = "OAuth"
        
        return True, "OAuth authentication successful!"
    except Exception as e:
        return False, f"OAuth authentication failed: {str(e)}"

def load_spreadsheet_data(spreadsheet_id, worksheet_name=None):
    """Load data from a Google Spreadsheet"""
    try:
        gc = gspread.authorize(st.session_state.credentials)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # If worksheet name is not provided, use the first one
        if not worksheet_name:
            worksheet = spreadsheet.sheet1
        else:
            worksheet = spreadsheet.worksheet(worksheet_name)
        
        # Get all values
        data = worksheet.get_all_values()
        
        if not data:
            return None, "No data found in the spreadsheet."
        
        # First row contains headers
        headers = data[0]
        
        # Create DataFrame
        df = pd.DataFrame(data[1:], columns=headers)
        
        # Try to convert numeric columns
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass
        
        return df, None
    except Exception as e:
        return None, f"Error loading spreadsheet data: {str(e)}"

def get_worksheet_names(spreadsheet_id):
    """Get all worksheet names from a spreadsheet"""
    try:
        gc = gspread.authorize(st.session_state.credentials)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        return [sheet.title for sheet in spreadsheet.worksheets()], None
    except Exception as e:
        return None, f"Error getting worksheet names: {str(e)}"

def sign_out():
    """Sign out and clear session state"""
    st.session_state.authenticated = False
    st.session_state.credentials = None
    st.session_state.user_info = None
    st.session_state.current_spreadsheet = None
    st.session_state.current_worksheet = None
    st.session_state.sheets_data = None
    
    # Remove token file if using OAuth
    if st.session_state.auth_method == "OAuth" and st.session_state.token_path:
        try:
            os.remove(st.session_state.token_path)
        except:
            pass
    
    return "Signed out successfully. Please refresh the page."

# Sidebar for authentication and navigation
with st.sidebar:
    st.title("Real Estate Dashboard")
    st.divider()
    
    # Authentication status display
    if st.session_state.authenticated:
        st.success(f"✅ Authenticated as {st.session_state.user_info.get('email', 'Unknown')}")
        st.caption(f"Method: {st.session_state.auth_method}")
    else:
        st.error("❌ Not Authenticated")
    
    # Authentication section
    if not st.session_state.authenticated:
        st.subheader("Authentication")
        auth_method = st.radio("Select authentication method:", ["Service Account", "OAuth 2.0"])
        
        if auth_method == "Service Account":
            st.info("Upload a service account JSON key file to authenticate.")
            uploaded_file = st.file_uploader("Upload service account JSON", type="json")
            
            if uploaded_file and st.button("Authenticate", key="auth_sa"):
                temp_path = save_uploaded_file(uploaded_file)
                success, message = authenticate_service_account(temp_path)
                
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
                
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
        
        elif auth_method == "OAuth 2.0":
            st.info("Upload a client secrets JSON file to authenticate with OAuth.")
            uploaded_file = st.file_uploader("Upload client secrets JSON", type="json")
            
            if uploaded_file and st.button("Authenticate", key="auth_oauth"):
                temp_path = save_uploaded_file(uploaded_file)
                success, message = authenticate_oauth(temp_path)
                
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
                
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    # Navigation (only show if authenticated)
    if st.session_state.authenticated:
        st.divider()
        st.subheader("Navigation")
        
        # Main page selection
        page = st.radio(
            "Select a page:",
            ["Dashboard", "Google Sheets", "Google Calendar", "Google Drive"]
        )
        
        # Sign out button
        if st.button("Sign Out", key="signout"):
            message = sign_out()
            st.success(message)
            st.rerun()

# Main content area
if not st.session_state.authenticated:
    # Welcome page for unauthenticated users
    st.title("Welcome to Real Estate Dashboard")
    st.info("Please authenticate using the sidebar to access the application.")
    
    st.header("Features")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        - Access and analyze real estate data from Google Sheets
        - View grant information and funding details
        - Track agent performance and metrics
        - Visualize data with interactive charts
        - Export data for further analysis
        """)
    with col2:
        st.image("https://storage.googleapis.com/gweb-cloudblog-publish/images/1_GDragon_hero_image_1.max-2000x2000.jpg", 
                 caption="Connect to Google Services", width=300)

elif page == "Dashboard":
    st.title("Real Estate Dashboard")
    st.subheader("Quick Access to Data")
    
    # Display cards for each predefined spreadsheet
    cols = st.columns(len(SPREADSHEETS))
    
    for i, (key, sheet_info) in enumerate(SPREADSHEETS.items()):
        with cols[i]:
            st.markdown(f"### {sheet_info['icon']} {key}")
            st.markdown(f"*{sheet_info['description']}*")
            
            if st.button(f"Load {key} Data", key=f"load_{key}"):
                # Set current spreadsheet and try to load first worksheet
                st.session_state.current_spreadsheet = sheet_info['id']
                
                # Get worksheet names
                worksheet_names, error = get_worksheet_names(sheet_info['id'])
                
                if error:
                    st.error(error)
                elif worksheet_names:
                    st.session_state.current_worksheet = worksheet_names[0]
                    
                    # Load data
                    df, error = load_spreadsheet_data(
                        sheet_info['id'], 
                        st.session_state.current_worksheet
                    )
                    
                    if error:
                        st.error(error)
                    else:
                        st.session_state.sheets_data = df
                        # Switch to Google Sheets page
                        st.rerun()
    
    # Recent activity or summary section
    st.divider()
    st.subheader("System Status")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Authentication Status", "Active" if st.session_state.authenticated else "Inactive")
    with col2:
        st.metric("User", st.session_state.user_info.get('email', 'Unknown') if st.session_state.authenticated else "None")
    with col3:
        st.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M"))

elif page == "Google Sheets":
    st.title("Google Sheets Data Viewer")
    
    # Spreadsheet selection section
    st.subheader("Select Data Source")
    
    tab1, tab2 = st.tabs(["Preset Spreadsheets", "Custom Spreadsheet"])
    
    with tab1:
        # Display preset spreadsheets as selectable cards
        for key, sheet_info in SPREADSHEETS.items():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"**{sheet_info['icon']} {key}**: {sheet_info['description']}")
            
            with col2:
                if st.button("Select", key=f"select_{key}"):
                    st.session_state.current_spreadsheet = sheet_info['id']
                    
                    # Get worksheet names
                    worksheet_names, error = get_worksheet_names(sheet_info['id'])
                    
                    if error:
                        st.error(error)
                    elif worksheet_names:
                        # Show worksheet selection
                        st.session_state.current_worksheet = worksheet_names[0]
                        st.rerun()
    
    with tab2:
        # Custom spreadsheet URL input
        spreadsheet_url = st.text_input("Enter Google Sheets URL:")
        
        if spreadsheet_url and st.button("Load Custom Spreadsheet"):
            try:
                # Extract spreadsheet ID from URL
                if "/d/" in spreadsheet_url and "/edit" in spreadsheet_url:
                    spreadsheet_id = spreadsheet_url.split("/d/")[1].split("/edit")[0]
                else:
                    spreadsheet_id = spreadsheet_url
                
                st.session_state.current_spreadsheet = spreadsheet_id
                
                # Get worksheet names
                worksheet_names, error = get_worksheet_names(spreadsheet_id)
                
                if error:
                    st.error(error)
                elif worksheet_names:
                    st.session_state.current_worksheet = worksheet_names[0]
                    st.rerun()
            
            except Exception as e:
                st.error(f"Error parsing spreadsheet URL: {str(e)}")
    
    # Display data if a spreadsheet is selected
    if st.session_state.current_spreadsheet:
        st.divider()
        
        # Get spreadsheet name for display
        spreadsheet_name = "Custom Spreadsheet"
        for key, info in SPREADSHEETS.items():
            if info['id'] == st.session_state.current_spreadsheet:
                spreadsheet_name = info['name']
        
        st.subheader(f"Working with: {spreadsheet_name}")
        
        # Get worksheet names
        worksheet_names, error = get_worksheet_names(st.session_state.current_spreadsheet)
        
        if error:
            st.error(error)
        elif worksheet_names:
            # Worksheet selection
            selected_worksheet = st.selectbox(
                "Select worksheet:", 
                worksheet_names,
                index=worksheet_names.index(st.session_state.current_worksheet) if st.session_state.current_worksheet in worksheet_names else 0
            )
            
            if selected_worksheet != st.session_state.current_worksheet:
                st.session_state.current_worksheet = selected_worksheet
                # Load data for the selected worksheet
                df, error = load_spreadsheet_data(
                    st.session_state.current_spreadsheet, 
                    st.session_state.current_worksheet
                )
                
                if error:
                    st.error(error)
                else:
                    st.session_state.sheets_data = df
            
            # Load data if not already loaded
            if st.session_state.sheets_data is None:
                df, error = load_spreadsheet_data(
                    st.session_state.current_spreadsheet, 
                    st.session_state.current_worksheet
                )
                
                if error:
                    st.error(error)
                else:
                    st.session_state.sheets_data = df
            
            # Display data if available
            if st.session_state.sheets_data is not None:
                df = st.session_state.sheets_data
                
                # Data overview
                st.subheader("Data Overview")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rows", f"{len(df)}")
                with col2:
                    st.metric("Columns", f"{len(df.columns)}")
                with col3:
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    st.metric("Numeric Columns", f"{len(numeric_cols)}")
                
                # Data tabs
                data_tab1, data_tab2, data_tab3 = st.tabs(["Data Preview", "Visualization", "Export"])
                
                with data_tab1:
                    # Data filtering options
                    with st.expander("Filter Options"):
                        filter_col = st.selectbox("Filter by column:", ["None"] + df.columns.tolist())
                        
                        filtered_df = df
                        if filter_col != "None":
                            if df[filter_col].dtype == 'object':
                                filter_values = st.multiselect(
                                    "Select values:", 
                                    options=sorted(df[filter_col].unique()),
                                    default=[]
                                )
                                if filter_values:
                                    filtered_df = df[df[filter_col].isin(filter_values)]
                            else:
                                min_val, max_val = st.slider(
                                    "Value range:",
                                    min_value=float(df[filter_col].min()),
                                    max_value=float(df[filter_col].max()),
                                    value=(float(df[filter_col].min()), float(df[filter_col].max()))
                                )
                                filtered_df = df[(df[filter_col] >= min_val) & (df[filter_col] <= max_val)]
                    
                    # Data preview
                    st.subheader("Data Preview")
                    st.dataframe(filtered_df, use_container_width=True)
                
                with data_tab2:
                    # Visualization options
                    if len(numeric_cols) > 0:
                        st.subheader("Data Visualization")
                        
                        viz_type = st.selectbox(
                            "Chart type:", 
                            ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Histogram"]
                        )
                        
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
                                color_col = st.selectbox("Color by (optional):", ["None"] + df.columns.tolist())
                                
                                if color_col != "None":
                                    fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=f"{y_col} vs {x_col}")
                                else:
                                    fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
                                
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning("Need at least two numeric columns for scatter plot.")
                        
                        elif viz_type == "Pie Chart":
                            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                            if categorical_cols:
                                names_col = st.selectbox("Categories:", categorical_cols)
                                values_col = st.selectbox("Values:", numeric_cols)
                                
                                fig = px.pie(df, names=names_col, values=values_col, title=f"{values_col} by {names_col}")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning("No categorical columns found for pie chart.")
                        
                        elif viz_type == "Histogram":
                            hist_col = st.selectbox("Column:", numeric_cols)
                            bins = st.slider("Number of bins:", min_value=5, max_value=100, value=20)
                            
                            fig = px.histogram(df, x=hist_col, nbins=bins, title=f"Distribution of {hist_col}")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No numeric columns found for visualization.")
                
                with data_tab3:
                    st.subheader("Export Data")
                    
                    export_format = st.radio("Export format:", ["CSV", "Excel", "JSON"])
                    
                    if export_format == "CSV":
                        csv = df.to_csv(index=False)
                        b64 = base64.b64encode(csv.encode()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="data.csv" class="btn">Download CSV</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    
                    elif export_format == "Excel":
                        output = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                        df.to_excel(output.name, index=False)
                        with open(output.name, "rb") as f:
                            excel_data = f.read()
                        b64 = base64.b64encode(excel_data).decode()
                        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="data.xlsx" class="btn">Download Excel</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        os.unlink(output.name)
                    
                    elif export_format == "JSON":
                        json_str = df.to_json(orient='records')
                        b64 = base64.b64encode(json_str.encode()).decode()
                        href = f'<a href="data:file/json;base64,{b64}" download="data.json" class="btn">Download JSON</a>'
                        st.markdown(href, unsafe_allow_html=True)

elif page == "Google Calendar":
    st.title("Google Calendar Events")
    
    try:
        service = build('calendar', 'v3', credentials=st.session_state.credentials)
        
        # Calendar selection
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        if calendars:
            calendar_options = [{"id": cal['id'], "name": cal.get('summary', cal['id'])} for cal in calendars]
            selected_calendar = st.selectbox(
                "Select calendar:",
                options=[cal['id'] for cal in calendar_options],
                format_func=lambda x: next((cal['name'] for cal in calendar_options if cal['id'] == x), x)
            )
        else:
            selected_calendar = st.text_input("Calendar ID (or 'primary'):", "primary")
        
        if selected_calendar:
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
                        calendarId=selected_calendar,
                        timeMin=start_datetime,
                        timeMax=end_datetime,
                        maxResults=50,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                
                if events:
                    st.header(f"Events ({len(events)})")
                    
                    # Group events by date
                    events_by_date = {}
                    for event in events:
                        start = event['start'].get('dateTime', event['start'].get('date'))
                        
                        # Extract date part
                        if 'T' in start:
                            date_str = start.split('T')[0]
                        else:
                            date_str = start
                        
                        if date_str not in events_by_date:
                            events_by_date[date_str] = []
                        
                        events_by_date[date_str].append(event)
                    
                    # Display events grouped by date
                    for date_str in sorted(events_by_date.keys()):
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%A, %B %d, %Y")
                        
                        with st.expander(formatted_date):
                            for event in events_by_date[date_str]:
                                start = event['start'].get('dateTime', event['start'].get('date'))
                                end = event['end'].get('dateTime', event['end'].get('date'))
                                
                                # Format time for display
                                if 'T' in start:
                                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                                    start_formatted = start_dt.strftime('%H:%M')
                                else:
                                    start_formatted = "All day"
                                
                                st.markdown(f"**{start_formatted}** - {event.get('summary', 'No title')}")
                                
                                # Event details
                                details_col1, details_col2 = st.columns(2)
                                
                                with details_col1:
                                    if event.get('location'):
                                        st.markdown(f"📍 {event.get('location')}")
                                
                                with details_col2:
                                    if event.get('attendees'):
                                        attendees = [a.get('email', 'Unknown') for a in event.get('attendees')]
                                        st.markdown(f"👥 {', '.join(attendees[:3])}{' and more...' if len(attendees) > 3 else ''}")
                                
                                if event.get('description'):
                                    st.markdown("---")
                                    st.markdown(event.get('description'))
                                
                                st.markdown("---")
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
        
        drive_tab1, drive_tab2, drive_tab3 = st.tabs(["Browse Files", "Upload Files", "Search Files"])
        
        with drive_tab1:
            st.header("Browse Google Drive Files")
            
            # Get folders
            with st.spinner("Loading folders..."):
                folders_result = drive_service.files().list(
                    q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                    spaces='drive',
                    fields='files(id, name, parents)'
                ).execute()
                
                folders = folders_result.get('files', [])
            
            # Add root folder
            all_folders = [{'id': 'root', 'name': 'My Drive', 'parents': []}] + folders
            
            # Create folder hierarchy
            folder_dict = {folder['id']: folder for folder in all_folders}
            
            # Function to get folder path
            def get_folder_path(folder_id):
                path = []
                current_id = folder_id
                
                while current_id and current_id != 'root':
                    if current_id in folder_dict:
                        folder = folder_dict[current_id]
                        path.insert(0, folder['name'])
                        
                        if 'parents' in folder and folder['parents']:
                            current_id = folder['parents'][0]
                        else:
                            current_id = None
                    else:
                        current_id = None
                
                if folder_id != 'root':
                    path.insert(0, 'My Drive')
                
                return ' / '.join(path)
            
            # Display folder selection
            folder_options = [{'id': f['id'], 'name': f['name'], 'path': get_folder_path(f['id'])} for f in all_folders]
            
            selected_folder = st.selectbox(
                "Select folder:",
                options=[f['id'] for f in folder_options],
                format_func=lambda x: next((f['path'] for f in folder_options if f['id'] == x), x)
            )
            
            if selected_folder:
                with st.spinner("Loading files..."):
                    files_result = drive_service.files().list(
                        q=f"'{selected_folder}' in parents and trashed=false",
                        spaces='drive',
                        fields="files(id, name, mimeType, webViewLink, iconLink, createdTime, modifiedTime, size)"
                    ).execute()
                    
                    files = files_result.get('files', [])
                
                if files:
                    st.write(f"Found {len(files)} files in selected folder")
                    
                    # Display files in a table
                    file_data = []
                    for file in files:
                        file_type = file.get('mimeType', '').split('.')[-1]
                        created = datetime.fromisoformat(file.get('createdTime', '').replace('Z', '+00:00')).strftime('%Y-%m-%d')
                        modified = datetime.fromisoformat(file.get('modifiedTime', '').replace('Z', '+00:00')).strftime('%Y-%m-%d')
                        
                        size = file.get('size')
                        if size:
                            size_mb = float(size) / (1024 * 1024)
                            size_display = f"{size_mb:.2f} MB"
                        else:
                            size_display = "N/A"
                        
                        file_data.append({
                            "Name": file.get('name'),
                            "Type": file_type,
                            "Created": created,
                            "Modified": modified,
                            "Size": size_display,
                            "Link": file.get('webViewLink')
                        })
                    
                    # Convert to DataFrame for display
                    file_df = pd.DataFrame(file_data)
                    
                    # Add link column
                    file_df['Actions'] = file_df['Link'].apply(lambda x: f'<a href="{x}" target="_blank">Open</a>')
                    
                    # Display table
                    st.dataframe(
                        file_df[['Name', 'Type', 'Created', 'Modified', 'Size', 'Actions']],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Actions": st.column_config.Column(
                                "Actions",
                                width="small",
                            )
                        }
                    )
                else:
                    st.info(f"No files found in selected folder")
        
        with drive_tab2:
            st.header("Upload Files to Google Drive")
            
            uploaded_file = st.file_uploader("Choose a file to upload")
            
            # Folder selection for upload
            with st.spinner("Loading folders..."):
                folders_result = drive_service.files().list(
                    q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                    spaces='drive',
                    fields='files(id, name, parents)'
                ).execute()
                
                folders = folders_result.get('files', [])
            
            # Add root folder
            all_folders = [{'id': 'root', 'name': 'My Drive', 'parents': []}] + folders
            
            # Create folder hierarchy
            folder_dict = {folder['id']: folder for folder in all_folders}
            
            # Function to get folder path (reused from above)
            def get_folder_path(folder_id):
                path = []
                current_id = folder_id
                
                while current_id and current_id != 'root':
                    if current_id in folder_dict:
                        folder = folder_dict[current_id]
                        path.insert(0, folder['name'])
                        
                        if 'parents' in folder and folder['parents']:
                            current_id = folder['parents'][0]
                        else:
                            current_id = None
                    else:
                        current_id = None
                
                if folder_id != 'root':
                    path.insert(0, 'My Drive')
                
                return ' / '.join(path)
            
            # Display folder selection
            folder_options = [{'id': f['id'], 'name': f['name'], 'path': get_folder_path(f['id'])} for f in all_folders]
            
            selected_upload_folder = st.selectbox(
                "Destination folder:",
                options=[f['id'] for f in folder_options],
                format_func=lambda x: next((f['path'] for f in folder_options if f['id'] == x), x),
                key="upload_folder"
            )
            
            if uploaded_file and st.button("Upload"):
                with st.spinner("Uploading..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uploaded_file.name}') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        temp_file_path = tmp.name
                    
                    try:
                        file_metadata = {
                            'name': uploaded_file.name,
                            'parents': [selected_upload_folder]
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
        
        with drive_tab3:
            st.header("Search Files")
            
            search_query = st.text_input("Search for files:")
            file_type = st.selectbox(
                "Filter by type:",
                [
                    "All Files",
                    "Documents",
                    "Spreadsheets",
                    "Presentations",
                    "PDFs",
                    "Images",
                    "Videos",
                    "Audio"
                ]
            )
            
            # Map file type to MIME type query
            mime_type_query = ""
            if file_type == "Documents":
                mime_type_query = "mimeType='application/vnd.google-apps.document' or mimeType contains 'text/' or mimeType contains 'application/msword' or mimeType contains 'application/vnd.openxmlformats-officedocument.wordprocessingml'"
            elif file_type == "Spreadsheets":
                mime_type_query = "mimeType='application/vnd.google-apps.spreadsheet' or mimeType contains 'application/vnd.ms-excel' or mimeType contains 'application/vnd.openxmlformats-officedocument.spreadsheetml'"
            elif file_type == "Presentations":
                mime_type_query = "mimeType='application/vnd.google-apps.presentation' or mimeType contains 'application/vnd.ms-powerpoint' or mimeType contains 'application/vnd.openxmlformats-officedocument.presentationml'"
            elif file_type == "PDFs":
                mime_type_query = "mimeType='application/pdf'"
            elif file_type == "Images":
                mime_type_query = "mimeType contains 'image/'"
            elif file_type == "Videos":
                mime_type_query = "mimeType contains 'video/'"
            elif file_type == "Audio":
                mime_type_query = "mimeType contains 'audio/'"
            
            if search_query and st.button("Search"):
                with st.spinner("Searching..."):
                    # Build query
                    query = f"name contains '{search_query}' and trashed=false"
                    if mime_type_query:
                        query += f" and ({mime_type_query})"
                    
                    # Execute search
                    search_result = drive_service.files().list(
                        q=query,
                        spaces='drive',
                        fields="files(id, name, mimeType, webViewLink, iconLink, createdTime, modifiedTime, size, parents)"
                    ).execute()
                    
                    search_files = search_result.get('files', [])
                
                if search_query and 'search_files' in locals():
                    if search_files:
                        st.write(f"Found {len(search_files)} results for '{search_query}'")
                        
                        # Display files in a table
                        search_data = []
                        for file in search_files:
                            file_type = file.get('mimeType', '').split('.')[-1]
                            created = datetime.fromisoformat(file.get('createdTime', '').replace('Z', '+00:00')).strftime('%Y-%m-%d')
                            
                            # Get folder path
                            folder_path = "Unknown"
                            if 'parents' in file and file['parents']:
                                parent_id = file['parents'][0]
                                folder_path = get_folder_path(parent_id)
                            
                            search_data.append({
                                "Name": file.get('name'),
                                "Type": file_type,
                                "Location": folder_path,
                                "Created": created,
                                "Link": file.get('webViewLink')
                            })
                        
                        # Convert to DataFrame for display
                        search_df = pd.DataFrame(search_data)
                        
                        # Add link column
                        search_df['Actions'] = search_df['Link'].apply(lambda x: f'<a href="{x}" target="_blank">Open</a>')
                        
                        # Display table
                        st.dataframe(
                            search_df[['Name', 'Type', 'Location', 'Created', 'Actions']],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info(f"No files found matching '{search_query}'")
    
    except Exception as e:
        st.error(f"Error accessing Google Drive: {str(e)}")

st.divider()
st.caption("Real Estate Dashboard | Developed with Streamlit")
