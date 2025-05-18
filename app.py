import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import tempfile
import time
import base64
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Page configuration
st.set_page_config(
    page_title="Google Services Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .page-header {
        font-size: 1.8rem;
        color: #0D47A1;
        margin-bottom: 0.8rem;
        border-bottom: 2px solid #1E88E5;
        padding-bottom: 0.3rem;
    }
    .section-header {
        font-size: 1.3rem;
        color: #1565C0;
        margin: 1rem 0 0.5rem 0;
    }
    .success-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #4CAF50;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #2196F3;
    }
    .warning-box {
        background-color: #FFF8E1;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #FFC107;
    }
    .error-box {
        background-color: #FFEBEE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #F44336;
    }
    .sidebar .sidebar-content {
        background-color: #F5F7FA;
    }
    .auth-status {
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin-bottom: 1rem;
    }
    .auth-status.logged-in {
        background-color: #E8F5E9;
        border: 1px solid #4CAF50;
    }
    .auth-status.logged-out {
        background-color: #FFEBEE;
        border: 1px solid #F44336;
    }
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

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

# Authentication sidebar
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>Google Services Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Authentication status display
    if st.session_state.authenticated:
        st.markdown(f"""
        <div class="auth-status logged-in">
            <strong>✅ Authenticated</strong><br>
            User: {st.session_state.user_info.get('email', 'Unknown')}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="auth-status logged-out">
            <strong>❌ Not Authenticated</strong><br>
            Please log in to continue
        </div>
        """, unsafe_allow_html=True)
    
    # Authentication methods
    st.markdown("<h3>Authentication</h3>", unsafe_allow_html=True)
    auth_method = st.radio(
        "Select authentication method:",
        ["Service Account", "OAuth2 (User Account)"],
        index=0
    )
    
    if auth_method == "Service Account":
        uploaded_file = st.file_uploader("Upload service account JSON", type="json")
        
        if uploaded_file:
            # Save the uploaded credentials to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_creds_path = tmp.name
            
            try:
                # Create credentials from the uploaded file
                credentials = service_account.Credentials.from_service_account_file(
                    temp_creds_path,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/calendar',
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/userinfo.email',
                        'https://www.googleapis.com/auth/userinfo.profile'
                    ]
                )
                
                # Get service account email
                with open(temp_creds_path, 'r') as f:
                    sa_info = json.load(f)
                    email = sa_info.get('client_email', 'Service Account')
                
                st.session_state.authenticated = True
                st.session_state.credentials = credentials
                st.session_state.user_info = {'email': email, 'name': 'Service Account'}
                
                st.success("Authentication successful! Please refresh the page to continue.")
                os.unlink(temp_creds_path)  # Clean up the temporary file
                
            except Exception as e:
                st.error(f"Authentication failed: {str(e)}")
                os.unlink(temp_creds_path)  # Clean up the temporary file
    
    elif auth_method == "OAuth2 (User Account)":
        st.info("This is a simulation of OAuth2 authentication for demonstration purposes.")
        
        # In a real app, you would implement OAuth2 flow here
        # For this demo, we'll simulate the OAuth2 process
        
        email = st.text_input("Email address")
        password = st.text_input("Password", type="password")
        
        if st.button("Sign In with Google"):
            if email and password:  # In a real app, you would validate with Google
                # Simulate OAuth2 authentication
                with st.spinner("Authenticating..."):
                    time.sleep(2)  # Simulate network delay
                    
                    # Create a simulated credentials object
                    # In a real app, this would be a real OAuth2 token
                    st.session_state.authenticated = True
                    st.session_state.user_info = {'email': email, 'name': email.split('@')[0]}
                    
                    st.success("Authentication successful! Please refresh the page to continue.")
            else:
                st.error("Please enter both email and password")
    
    # Logout button
    if st.session_state.authenticated:
        if st.button("Sign Out"):
            st.session_state.authenticated = False
            st.session_state.credentials = None
            st.session_state.user_info = None
            st.session_state.current_spreadsheet = None
            st.session_state.current_worksheet = None
            st.session_state.sheets_data = None
            
            st.success("You have been signed out. Please refresh the page.")
    
    st.markdown("---")
    
    # Navigation - only show if authenticated
    if st.session_state.authenticated:
        st.markdown("<h3>Navigation</h3>", unsafe_allow_html=True)
        page = st.radio(
            "Select a page:",
            [
                "Google Sheets - Data Viewer",
                "Google Sheets - Data Analysis",
                "Google Sheets - Data Comparison",
                "Google Sheets - Dashboard",
                "Google Sheets - Data Editor",
                "Google Calendar",
                "Google Drive"
            ]
        )
    else:
        page = "Login Required"
        st.info("Please authenticate to access the application")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <small>Google Services Dashboard<br>v2.0</small>
    </div>
    """, unsafe_allow_html=True)

# Helper functions
def load_spreadsheet_data():
    """Load and cache spreadsheet data"""
    if not st.session_state.current_spreadsheet or not st.session_state.current_worksheet:
        return None
    
    try:
        # Connect to Google Sheets
        gc = gspread.authorize(st.session_state.credentials)
        spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
        worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
        
        # Get all values from the worksheet
        data = worksheet.get_all_values()
        
        if data:
            # Convert to DataFrame
            headers = data[0]
            df = pd.DataFrame(data[1:], columns=headers)
            
            # Try to convert numeric columns
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except:
                    pass
            
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading spreadsheet data: {str(e)}")
        return None

def spreadsheet_selector():
    """Common spreadsheet selector UI component"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        spreadsheet_url = st.text_input("Enter Google Sheets URL:")
    
    with col2:
        st.write("&nbsp;")  # Spacer
        load_button = st.button("Load Spreadsheet", use_container_width=True)
    
    if spreadsheet_url and load_button:
        try:
            # Extract spreadsheet ID from URL
            if "/d/" in spreadsheet_url and "/edit" in spreadsheet_url:
                spreadsheet_id = spreadsheet_url.split("/d/")[1].split("/edit")[0]
            else:
                spreadsheet_id = spreadsheet_url
            
            # Connect to Google Sheets
            gc = gspread.authorize(st.session_state.credentials)
            spreadsheet = gc.open_by_key(spreadsheet_id)
            
            # Get list of worksheets
            worksheet_list = [sheet.title for sheet in spreadsheet.worksheets()]
            
            # Store spreadsheet ID
            st.session_state.current_spreadsheet = spreadsheet_id
            
            # Display worksheet selector
            st.success(f"Spreadsheet loaded: {spreadsheet.title}")
            
            selected_sheet = st.selectbox(
                "Select a worksheet:",
                worksheet_list,
                index=0
            )
            
            if selected_sheet:
                st.session_state.current_worksheet = selected_sheet
                
                # Load the data
                df = load_spreadsheet_data()
                if df is not None:
                    st.session_state.sheets_data = df
                    return True
        
        except Exception as e:
            st.error(f"Error accessing Google Sheets: {str(e)}")
    
    return False

def render_chart(chart_config, df):
    """Render a chart based on configuration"""
    st.markdown(f"<h3 class='section-header'>{chart_config['title']}</h3>", unsafe_allow_html=True)
    
    if chart_config["type"] == "Bar Chart":
        # Group by the x column and aggregate the y column
        grouped = df.groupby(chart_config["x_col"])[chart_config["y_col"]].sum().reset_index()
        grouped = grouped.sort_values(chart_config["y_col"], ascending=False)
        
        # Limit to top 15 categories if there are too many
        if len(grouped) > 15:
            grouped = grouped.head(15)
        
        fig = px.bar(
            grouped,
            x=chart_config["x_col"],
            y=chart_config["y_col"],
            title=chart_config["title"],
            text_auto='.2s'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_config["type"] == "Line Chart":
        # Sort by the x column
        plot_df = df.sort_values(by=chart_config["x_col"])
        
        fig = go.Figure()
        
        for y_col in chart_config["y_cols"]:
            fig.add_trace(
                go.Scatter(
                    x=plot_df[chart_config["x_col"]],
                    y=plot_df[y_col],
                    mode='lines+markers',
                    name=y_col
                )
            )
        
        fig.update_layout(
            title=chart_config["title"],
            xaxis_title=chart_config["x_col"],
            yaxis_title="Value",
            legend_title="Variables"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_config["type"] == "Pie Chart":
        # Group by the labels column and aggregate the values column
        grouped = df.groupby(chart_config["labels_col"])[chart_config["values_col"]].sum().reset_index()
        
        # Limit to top 10 categories if there are too many
        if len(grouped) > 10:
            # Keep top 9 and group the rest as "Other"
            top_9 = grouped.nlargest(9, chart_config["values_col"])
            other_sum = grouped.nsmallest(len(grouped) - 9, chart_config["values_col"])[chart_config["values_col"]].sum()
            
            other_row = pd.DataFrame({
                chart_config["labels_col"]: ["Other"],
                chart_config["values_col"]: [other_sum]
            })
            
            grouped = pd.concat([top_9, other_row])
        
        fig = px.pie(
            grouped,
            names=chart_config["labels_col"],
            values=chart_config["values_col"],
            title=chart_config["title"]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_config["type"] == "Scatter Plot":
        fig = px.scatter(
            df,
            x=chart_config["x_col"],
            y=chart_config["y_col"],
            color=chart_config["color_col"],
            title=chart_config["title"],
            trendline="ols" if not chart_config["color_col"] else None
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_config["type"] == "Heatmap":
        # Create a pivot table
        pivot = df.pivot_table(
            index=chart_config["y_col"],
            columns=chart_config["x_col"],
            values=chart_config["z_col"],
            aggfunc="mean"
        )
        
        fig = px.imshow(
            pivot,
            title=chart_config["title"],
            labels=dict(
                x=chart_config["x_col"],
                y=chart_config["y_col"],
                color=chart_config["z_col"]
            ),
            color_continuous_scale="Viridis"
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Main content area
if not st.session_state.authenticated:
    st.markdown("<h1 class='main-header'>Welcome to Google Services Dashboard</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("""
        <div class="info-box">
            <h3>Features:</h3>
            <ul>
                <li>Connect to and analyze Google Sheets data</li>
                <li>View and manage Google Calendar events</li>
                <li>Upload and manage files on Google Drive</li>
                <li>Create interactive dashboards from your data</li>
                <li>Compare data across different sheets</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="warning-box">
            <h3>Getting Started:</h3>
            <p>To use this application, you need to authenticate with Google. Please use the sidebar to:</p>
            <ol>
                <li>Choose your authentication method</li>
                <li>Provide the necessary credentials</li>
                <li>Sign in to access all features</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.image("https://storage.googleapis.com/gweb-cloudblog-publish/images/1_GDragon_hero_image_1.max-2000x2000.jpg", 
                 caption="Connect to Google Services")

elif page == "Google Sheets - Data Viewer":
    st.markdown("<h1 class='main-header'>Google Sheets Data Viewer</h1>", unsafe_allow_html=True)
    
    # Spreadsheet selector
    data_loaded = spreadsheet_selector()
    
    if data_loaded and st.session_state.sheets_data is not None:
        df = st.session_state.sheets_data
        
        # Data overview
        st.markdown("<h2 class='page-header'>Data Overview</h2>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", f"{len(df)}")
        with col2:
            st.metric("Columns", f"{len(df.columns)}")
        with col3:
            numeric_cols = df.select_dtypes(include=['number']).columns
            st.metric("Numeric Columns", f"{len(numeric_cols)}")
        
        # Data preview with filters
        st.markdown("<h2 class='page-header'>Data Preview & Filtering</h2>", unsafe_allow_html=True)
        
        # Column selector
        selected_columns = st.multiselect(
            "Select columns to display:",
            df.columns.tolist(),
            default=df.columns.tolist()[:5] if len(df.columns) > 5 else df.columns.tolist()
        )
        
        # Filters
        st.markdown("<h3 class='section-header'>Filters</h3>", unsafe_allow_html=True)
        
        filters = {}
        cols = st.columns(3)
        
        for i, col_name in enumerate(selected_columns[:3]):  # Limit to 3 filters for simplicity
            with cols[i % 3]:
                if df[col_name].dtype == 'object':
                    unique_values = df[col_name].unique().tolist()
                    if len(unique_values) <= 10:  # Only show selector if reasonable number of options
                        selected_values = st.multiselect(
                            f"Filter by {col_name}:",
                            unique_values,
                            default=[]
                        )
                        if selected_values:
                            filters[col_name] = selected_values
                elif df[col_name].dtype in ['int64', 'float64']:
                    min_val = float(df[col_name].min())
                    max_val = float(df[col_name].max())
                    
                    filter_range = st.slider(
                        f"Filter by {col_name}:",
                        min_val, max_val,
                        (min_val, max_val)
                    )
                    
                    if filter_range != (min_val, max_val):
                        filters[col_name] = filter_range
        
        # Apply filters
        filtered_df = df.copy()
        for col, filter_val in filters.items():
            if isinstance(filter_val, list):
                filtered_df = filtered_df[filtered_df[col].isin(filter_val)]
            elif isinstance(filter_val, tuple) and len(filter_val) == 2:
                filtered_df = filtered_df[(filtered_df[col] >= filter_val[0]) & 
                                         (filtered_df[col] <= filter_val[1])]
        
        # Display filtered data
        if selected_columns:
            st.dataframe(filtered_df[selected_columns], use_container_width=True)
            
            # Download button
            csv = filtered_df[selected_columns].to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="filtered_data.csv" class="btn">Download Filtered Data as CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.warning("Please select at least one column to display")

elif page == "Google Sheets - Data Analysis":
    st.markdown("<h1 class='main-header'>Google Sheets Data Analysis</h1>", unsafe_allow_html=True)
    
    # Spreadsheet selector
    data_loaded = spreadsheet_selector()
    
    if data_loaded and st.session_state.sheets_data is not None:
        df = st.session_state.sheets_data
        
        # Identify numeric columns for analysis
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if not numeric_cols:
            st.warning("No numeric columns found in the data. Please select a different sheet with numeric data.")
        else:
            # Statistical Analysis
            st.markdown("<h2 class='page-header'>Statistical Analysis</h2>", unsafe_allow_html=True)
            
            # Summary statistics
            st.markdown("<h3 class='section-header'>Summary Statistics</h3>", unsafe_allow_html=True)
            st.dataframe(df[numeric_cols].describe(), use_container_width=True)
            
            # Correlation analysis
            if len(numeric_cols) > 1:
                st.markdown("<h3 class='section-header'>Correlation Matrix</h3>", unsafe_allow_html=True)
                corr = df[numeric_cols].corr()
                
                # Heatmap of correlation
                fig = px.imshow(
                    corr,
                    text_auto=True,
                    aspect="auto",
                    color_continuous_scale='RdBu_r',
                    title="Correlation Between Numeric Variables"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Highlight strong correlations
                strong_corr = corr.unstack().reset_index()
                strong_corr.columns = ['Variable 1', 'Variable 2', 'Correlation']
                strong_corr = strong_corr[
                    (strong_corr['Variable 1'] != strong_corr['Variable 2']) & 
                    (abs(strong_corr['Correlation']) > 0.5)
                ].sort_values(by='Correlation', ascending=False)
                
                if not strong_corr.empty:
                    st.markdown("<h3 class='section-header'>Strong Correlations</h3>", unsafe_allow_html=True)
                    st.dataframe(strong_corr, use_container_width=True)
            
            # Data Visualization
            st.markdown("<h2 class='page-header'>Data Visualization</h2>", unsafe_allow_html=True)
            
            viz_type = st.selectbox(
                "Select visualization type:",
                ["Histogram", "Box Plot", "Scatter Plot", "Bar Chart", "Line Chart"]
            )
            
            if viz_type == "Histogram":
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    hist_col = st.selectbox("Select column for histogram:", numeric_cols)
                
                with col2:
                    bins = st.slider("Number of bins:", 5, 100, 20)
                
                fig = px.histogram(
                    df, 
                    x=hist_col,
                    nbins=bins,
                    title=f"Histogram of {hist_col}",
                    marginal="box"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Basic statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Mean", f"{df[hist_col].mean():.2f}")
                with col2:
                    st.metric("Median", f"{df[hist_col].median():.2f}")
                with col3:
                    st.metric("Std Dev", f"{df[hist_col].std():.2f}")
                with col4:
                    st.metric("IQR", f"{df[hist_col].quantile(0.75) - df[hist_col].quantile(0.25):.2f}")
            
            elif viz_type == "Box Plot":
                box_col = st.selectbox("Select column for box plot:", numeric_cols)
                
                # Optional grouping
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                group_by = None
                
                if categorical_cols:
                    use_grouping = st.checkbox("Group by category")
                    if use_grouping:
                        group_by = st.selectbox("Select grouping column:", categorical_cols)
                
                if group_by:
                    fig = px.box(
                        df,
                        x=group_by,
                        y=box_col,
                        title=f"Box Plot of {box_col} by {group_by}",
                        points="all"
                    )
                else:
                    fig = px.box(
                        df,
                        y=box_col,
                        title=f"Box Plot of {box_col}",
                        points="all"
                    )
                
                st.plotly_chart(fig, use_container_width=True)
            
            elif viz_type == "Scatter Plot":
                col1, col2 = st.columns(2)
                
                with col1:
                    x_col = st.selectbox("Select X-axis:", numeric_cols)
                
                with col2:
                    y_col = st.selectbox(
                        "Select Y-axis:", 
                        [col for col in numeric_cols if col != x_col],
                        index=min(1, len(numeric_cols)-1) if len(numeric_cols) > 1 else 0
                    )
                
                # Optional color grouping
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                color_by = None
                
                if categorical_cols:
                    use_color = st.checkbox("Color by category")
                    if use_color:
                        color_by = st.selectbox("Select color column:", categorical_cols)
                
                fig = px.scatter(
                    df,
                    x=x_col,
                    y=y_col,
                    color=color_by,
                    title=f"Scatter Plot: {y_col} vs {x_col}",
                    trendline="ols" if not color_by else None
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show correlation
                corr_val = df[[x_col, y_col]].corr().iloc[0, 1]
                st.metric("Correlation", f"{corr_val:.4f}")
            
            elif viz_type == "Bar Chart":
                # For bar charts, we need a categorical and a numeric column
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                
                if not categorical_cols:
                    st.warning("No categorical columns found for bar chart. Converting a numeric column to categories.")
                    # Convert a numeric column to categories
                    cat_options = [f"{col} (binned)" for col in numeric_cols]
                    selected_cat = st.selectbox("Select categorical column (will be binned):", numeric_cols)
                    
                    # Create bins
                    num_bins = st.slider("Number of bins:", 3, 10, 5)
                    df[f"{selected_cat} (binned)"] = pd.cut(df[selected_cat], bins=num_bins)
                    cat_col = f"{selected_cat} (binned)"
                else:
                    cat_col = st.selectbox("Select categorical column:", categorical_cols)
                
                # Select numeric column for values
                value_col = st.selectbox(
                    "Select value column:", 
                    [col for col in numeric_cols],
                    index=0
                )
                
                # Aggregation method
                agg_method = st.selectbox(
                    "Aggregation method:",
                    ["Sum", "Mean", "Count", "Median", "Min", "Max"]
                )
                
                # Group by the categorical column and aggregate
                agg_func = {
                    "Sum": "sum",
                    "Mean": "mean",
                    "Count": "count",
                    "Median": "median",
                    "Min": "min",
                    "Max": "max"
                }[agg_method]
                
                grouped = df.groupby(cat_col)[value_col].agg(agg_func).reset_index()
                grouped = grouped.sort_values(value_col, ascending=False)
                
                # Limit to top N categories if there are too many
                if len(grouped) > 15:
                    show_top_n = st.slider("Show top N categories:", 5, 30, 10)
                    grouped = grouped.head(show_top_n)
                
                fig = px.bar(
                    grouped,
                    x=cat_col,
                    y=value_col,
                    title=f"{agg_method} of {value_col} by {cat_col}",
                    text_auto='.2s'
                )
                
                fig.update_layout(xaxis_title=cat_col, yaxis_title=f"{agg_method} of {value_col}")
                st.plotly_chart(fig, use_container_width=True)
            
            elif viz_type == "Line Chart":
                # For line charts, we typically need a time series or sequential data
                date_cols = []
                
                # Try to identify date columns
                for col in df.columns:
                    if df[col].dtype == 'object':
                        try:
                            pd.to_datetime(df[col])
                            date_cols.append(col)
                        except:
                            pass
                
                if date_cols:
                    x_col = st.selectbox("Select date/time column:", date_cols)
                    
                    # Convert to datetime
                    df[x_col] = pd.to_datetime(df[x_col], errors='coerce')
                else:
                    # If no date columns, use a numeric column as sequence
                    x_col = st.selectbox("Select sequence column:", numeric_cols)
                
                # Select columns to plot
                y_cols = st.multiselect(
                    "Select columns to plot:",
                    [col for col in numeric_cols if col != x_col],
                    default=[numeric_cols[0]] if numeric_cols and numeric_cols[0] != x_col else []
                )
                
                if y_cols:
                    # Sort by the x column
                    plot_df = df.sort_values(by=x_col)
                    
                    fig = go.Figure()
                    
                    for y_col in y_cols:
                        fig.add_trace(
                            go.Scatter(
                                x=plot_df[x_col],
                                y=plot_df[y_col],
                                mode='lines+markers',
                                name=y_col
                            )
                        )
                    
                    fig.update_layout(
                        title=f"Line Chart over {x_col}",
                        xaxis_title=x_col,
                        yaxis_title="Value",
                        legend_title="Variables"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Please select at least one column to plot")
            
            # Outlier Detection
            st.markdown("<h2 class='page-header'>Outlier Detection</h2>", unsafe_allow_html=True)
            
            outlier_col = st.selectbox("Select column for outlier detection:", numeric_cols)
            
            # Calculate IQR
            Q1 = df[outlier_col].quantile(0.25)
            Q3 = df[outlier_col].quantile(0.75)
            IQR = Q3 - Q1
            
            # Define outliers
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = df[(df[outlier_col] < lower_bound) | (df[outlier_col] > upper_bound)]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Outliers", f"{len(outliers)}")
            with col2:
                st.metric("Lower Bound", f"{lower_bound:.2f}")
            with col3:
                st.metric("Upper Bound", f"{upper_bound:.2f}")
            
            if not outliers.empty:
                st.dataframe(outliers, use_container_width=True)
                
                # Visualize outliers
                fig = px.box(
                    df,
                    y=outlier_col,
                    title=f"Outliers in {outlier_col}",
                    points="all"
                )
                
                # Highlight outliers
                fig.add_trace(
                    go.Scatter(
                        x=[0] * len(outliers),
                        y=outliers[outlier_col],
                        mode='markers',
                        marker=dict(color='red', size=10, symbol='x'),
                        name='Outliers'
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No outliers detected in {outlier_col} using the IQR method")

elif page == "Google Sheets - Data Comparison":
    st.markdown("<h1 class='main-header'>Google Sheets Data Comparison</h1>", unsafe_allow_html=True)
    
    st.info("This page allows you to compare data across different worksheets or spreadsheets.")
    
    # First dataset
    st.markdown("<h2 class='page-header'>First Dataset</h2>", unsafe_allow_html=True)
    
    # Spreadsheet selector for first dataset
    spreadsheet_url_1 = st.text_input("Enter first Google Sheets URL:")
    
    if spreadsheet_url_1:
        try:
            # Extract spreadsheet ID from URL
            if "/d/" in spreadsheet_url_1 and "/edit" in spreadsheet_url_1:
                spreadsheet_id_1 = spreadsheet_url_1.split("/d/")[1].split("/edit")[0]
            else:
                spreadsheet_id_1 = spreadsheet_url_1
            
            # Connect to Google Sheets
            gc = gspread.authorize(st.session_state.credentials)
            spreadsheet_1 = gc.open_by_key(spreadsheet_id_1)
            
            # Get list of worksheets
            worksheet_list_1 = [sheet.title for sheet in spreadsheet_1.worksheets()]
            
            # Display worksheet selector
            st.success(f"First spreadsheet loaded: {spreadsheet_1.title}")
            
            selected_sheet_1 = st.selectbox(
                "Select first worksheet:",
                worksheet_list_1,
                index=0,
                key="sheet1"
            )
            
            if selected_sheet_1:
                # Get the selected worksheet
                worksheet_1 = spreadsheet_1.worksheet(selected_sheet_1)
                
                # Get all values from the worksheet
                data_1 = worksheet_1.get_all_values()
                
                if data_1:
                    # Convert to DataFrame
                    headers_1 = data_1[0]
                    df_1 = pd.DataFrame(data_1[1:], columns=headers_1)
                    
                    # Try to convert numeric columns
                    for col in df_1.columns:
                        try:
                            df_1[col] = pd.to_numeric(df_1[col])
                        except:
                            pass
                    
                    st.write(f"First dataset: {len(df_1)} rows, {len(df_1.columns)} columns")
                    
                    # Second dataset
                    st.markdown("<h2 class='page-header'>Second Dataset</h2>", unsafe_allow_html=True)
                    
                    # Option to use same spreadsheet or different one
                    use_same_spreadsheet = st.checkbox("Use same spreadsheet for second dataset", value=True)
                    
                    if use_same_spreadsheet:
                        spreadsheet_2 = spreadsheet_1
                        worksheet_list_2 = worksheet_list_1
                        
                        # Make sure to select a different worksheet
                        other_worksheets = [sheet for sheet in worksheet_list_2 if sheet != selected_sheet_1]
                        
                        if other_worksheets:
                            selected_sheet_2 = st.selectbox(
                                "Select second worksheet:",
                                other_worksheets,
                                index=0,
                                key="sheet2"
                            )
                        else:
                            st.warning("This spreadsheet only has one worksheet. Please select a different spreadsheet for comparison.")
                            selected_sheet_2 = None
                    else:
                        # Spreadsheet selector for second dataset
                        spreadsheet_url_2 = st.text_input("Enter second Google Sheets URL:")
                        
                        if spreadsheet_url_2:
                            try:
                                # Extract spreadsheet ID from URL
                                if "/d/" in spreadsheet_url_2 and "/edit" in spreadsheet_url_2:
                                    spreadsheet_id_2 = spreadsheet_url_2.split("/d/")[1].split("/edit")[0]
                                else:
                                    spreadsheet_id_2 = spreadsheet_url_2
                                
                                # Connect to Google Sheets
                                spreadsheet_2 = gc.open_by_key(spreadsheet_id_2)
                                
                                # Get list of worksheets
                                worksheet_list_2 = [sheet.title for sheet in spreadsheet_2.worksheets()]
                                
                                # Display worksheet selector
                                st.success(f"Second spreadsheet loaded: {spreadsheet_2.title}")
                                
                                selected_sheet_2 = st.selectbox(
                                    "Select second worksheet:",
                                    worksheet_list_2,
                                    index=0,
                                    key="sheet2"
                                )
                            except Exception as e:
                                st.error(f"Error accessing second Google Sheets: {str(e)}")
                                selected_sheet_2 = None
                        else:
                            selected_sheet_2 = None
                    
                    if selected_sheet_2:
                        # Get the selected worksheet
                        worksheet_2 = spreadsheet_2.worksheet(selected_sheet_2)
                        
                        # Get all values from the worksheet
                        data_2 = worksheet_2.get_all_values()
                        
                        if data_2:
                            # Convert to DataFrame
                            headers_2 = data_2[0]
                            df_2 = pd.DataFrame(data_2[1:], columns=headers_2)
                            
                            # Try to convert numeric columns
                            for col in df_2.columns:
                                try:
                                    df_2[col] = pd.to_numeric(df_2[col])
                                except:
                                    pass
                            
                            st.write(f"Second dataset: {len(df_2)} rows, {len(df_2.columns)} columns")
                            
                            # Comparison options
                            st.markdown("<h2 class='page-header'>Comparison Options</h2>", unsafe_allow_html=True)
                            
                            comparison_type = st.radio(
                                "Select comparison type:",
                                ["Column Statistics", "Data Distribution", "Common Columns", "Merged Data"]
                            )
                            
                            if comparison_type == "Column Statistics":
                                # Compare basic statistics of common numeric columns
                                common_numeric_cols = []
                                
                                for col in df_1.columns:
                                    if col in df_2.columns:
                                        try:
                                            pd.to_numeric(df_1[col])
                                            pd.to_numeric(df_2[col])
                                            common_numeric_cols.append(col)
                                        except:
                                            pass
                                
                                if common_numeric_cols:
                                    selected_col = st.selectbox(
                                        "Select column to compare:",
                                        common_numeric_cols
                                    )
                                    
                                    # Calculate statistics
                                    stats_1 = df_1[selected_col].describe()
                                    stats_2 = df_2[selected_col].describe()
                                    
                                    # Create comparison dataframe
                                    stats_df = pd.DataFrame({
                                        f"{selected_sheet_1}": stats_1,
                                        f"{selected_sheet_2}": stats_2,
                                        "Difference": stats_2 - stats_1,
                                        "Percent Diff": ((stats_2 - stats_1) / stats_1 * 100).round(2)
                                    })
                                    
                                    st.dataframe(stats_df, use_container_width=True)
                                    
                                    # Visualize comparison
                                    fig = go.Figure()
                                    
                                    fig.add_trace(
                                        go.Box(
                                            y=pd.to_numeric(df_1[selected_col], errors='coerce'),
                                            name=f"{selected_sheet_1}",
                                            boxmean=True
                                        )
                                    )
                                    
                                    fig.add_trace(
                                        go.Box(
                                            y=pd.to_numeric(df_2[selected_col], errors='coerce'),
                                            name=f"{selected_sheet_2}",
                                            boxmean=True
                                        )
                                    )
                                    
                                    fig.update_layout(
                                        title=f"Comparison of {selected_col}",
                                        yaxis_title=selected_col
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    # Histogram comparison
                                    fig = go.Figure()
                                    
                                    fig.add_trace(
                                        go.Histogram(
                                            x=pd.to_numeric(df_1[selected_col], errors='coerce'),
                                            name=f"{selected_sheet_1}",
                                            opacity=0.7,
                                            nbinsx=20
                                        )
                                    )
                                    
                                    fig.add_trace(
                                        go.Histogram(
                                            x=pd.to_numeric(df_2[selected_col], errors='coerce'),
                                            name=f"{selected_sheet_2}",
                                            opacity=0.7,
                                            nbinsx=20
                                        )
                                    )
                                    
                                    fig.update_layout(
                                        title=f"Distribution Comparison of {selected_col}",
                                        xaxis_title=selected_col,
                                        yaxis_title="Count",
                                        barmode='overlay'
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.warning("No common numeric columns found between the two datasets.")
                            
                            elif comparison_type == "Data Distribution":
                                # Compare distributions of all numeric columns
                                numeric_cols_1 = df_1.select_dtypes(include=['number']).columns.tolist()
                                numeric_cols_2 = df_2.select_dtypes(include=['number']).columns.tolist()
                                
                                if numeric_cols_1 and numeric_cols_2:
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        selected_col_1 = st.selectbox(
                                            f"Select column from {selected_sheet_1}:",
                                            numeric_cols_1
                                        )
                                    
                                    with col2:
                                        selected_col_2 = st.selectbox(
                                            f"Select column from {selected_sheet_2}:",
                                            numeric_cols_2
                                        )
                                    
                                    # Create histograms
                                    fig = go.Figure()
                                    
                                    fig.add_trace(
                                        go.Histogram(
                                            x=df_1[selected_col_1],
                                            name=f"{selected_sheet_1}: {selected_col_1}",
                                            opacity=0.7,
                                            nbinsx=20,
                                            histnorm='probability'
                                        )
                                    )
                                    
                                    fig.add_trace(
                                        go.Histogram(
                                            x=df_2[selected_col_2],
                                            name=f"{selected_sheet_2}: {selected_col_2}",
                                            opacity=0.7,
                                            nbinsx=20,
                                            histnorm='probability'
                                        )
                                    )
                                    
                                    fig.update_layout(
                                        title=f"Distribution Comparison",
                                        xaxis_title="Value",
                                        yaxis_title="Probability",
                                        barmode='overlay'
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    # Show statistics side by side
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.markdown(f"**Statistics for {selected_col_1}**")
                                        st.dataframe(df_1[selected_col_1].describe())
                                    
                                    with col2:
                                        st.markdown(f"**Statistics for {selected_col_2}**")
                                        st.dataframe(df_2[selected_col_2].describe())
                                else:
                                    st.warning("One or both datasets don't have numeric columns.")
                            
                            elif comparison_type == "Common Columns":
                                # Find common columns
                                common_cols = [col for col in df_1.columns if col in df_2.columns]
                                
                                if common_cols:
                                    st.success(f"Found {len(common_cols)} common columns: {', '.join(common_cols)}")
                                    
                                    # Select columns to compare
                                    selected_common_cols = st.multiselect(
                                        "Select columns to compare:",
                                        common_cols,
                                        default=common_cols[:min(5, len(common_cols))]
                                    )
                                    
                                    if selected_common_cols:
                                        # Show data side by side
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            st.markdown(f"**Data from {selected_sheet_1}**")
                                            st.dataframe(df_1[selected_common_cols].head(10))
                                        
                                        with col2:
                                            st.markdown(f"**Data from {selected_sheet_2}**")
                                            st.dataframe(df_2[selected_common_cols].head(10))
                                        
                                        # Compare value counts for categorical columns
                                        for col in selected_common_cols:
                                            if df_1[col].dtype == 'object' or df_2[col].dtype == 'object':
                                                st.markdown(f"**Value comparison for {col}**")
                                                
                                                # Get value counts
                                                vc1 = df_1[col].value_counts().reset_index()
                                                vc1.columns = ['Value', f'Count in {selected_sheet_1}']
                                                
                                                vc2 = df_2[col].value_counts().reset_index()
                                                vc2.columns = ['Value', f'Count in {selected_sheet_2}']
                                                
                                                # Merge the value counts
                                                merged_vc = pd.merge(vc1, vc2, on='Value', how='outer').fillna(0)
                                                
                                                # Calculate difference
                                                merged_vc['Difference'] = merged_vc[f'Count in {selected_sheet_2}'] - merged_vc[f'Count in {selected_sheet_1}']
                                                
                                                st.dataframe(merged_vc, use_container_width=True)
                                                
                                                # Visualize comparison
                                                fig = go.Figure()
                                                
                                                fig.add_trace(
                                                    go.Bar(
                                                        x=merged_vc['Value'],
                                                        y=merged_vc[f'Count in {selected_sheet_1}'],
                                                        name=f"{selected_sheet_1}"
                                                    )
                                                )
                                                
                                                fig.add_trace(
                                                    go.Bar(
                                                        x=merged_vc['Value'],
                                                        y=merged_vc[f'Count in {selected_sheet_2}'],
                                                        name=f"{selected_sheet_2}"
                                                    )
                                                )
                                                
                                                fig.update_layout(
                                                    title=f"Comparison of {col} values",
                                                    xaxis_title=col,
                                                    yaxis_title="Count",
                                                    barmode='group'
                                                )
                                                
                                                st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.warning("No common columns found between the two datasets.")
                            
                            elif comparison_type == "Merged Data":
                                # Merge the two datasets
                                st.markdown("<h3 class='section-header'>Merge Options</h3>", unsafe_allow_html=True)
                                
                                # Find common columns for potential join keys
                                common_cols = [col for col in df_1.columns if col in df_2.columns]
                                
                                if common_cols:
                                    # Select join key
                                    join_key = st.selectbox(
                                        "Select column to join on:",
                                        common_cols
                                    )
                                    
                                    # Select join type
                                    join_type = st.selectbox(
                                        "Select join type:",
                                        ["inner", "left", "right", "outer"],
                                        format_func=lambda x: {
                                            "inner": "Inner Join (only matching rows)",
                                            "left": f"Left Join (all rows from {selected_sheet_1})",
                                            "right": f"Right Join (all rows from {selected_sheet_2})",
                                            "outer": "Outer Join (all rows from both)"
                                        }[x]
                                    )
                                    
                                    # Perform the merge
                                    df_1_suffix = f"_{selected_sheet_1}"
                                    df_2_suffix = f"_{selected_sheet_2}"
                                    
                                    merged_df = pd.merge(
                                        df_1, 
                                        df_2,
                                        on=join_key,
                                        how=join_type,
                                        suffixes=(df_1_suffix, df_2_suffix)
                                    )
                                    
                                    # Show merge results
                                    st.success(f"Merged dataset has {len(merged_df)} rows and {len(merged_df.columns)} columns")
                                    st.dataframe(merged_df.head(10), use_container_width=True)
                                    
                                    # Analyze the merge
                                    if join_type == "inner":
                                        st.info(f"Found {len(merged_df)} matching rows based on {join_key}")
                                    elif join_type == "left":
                                        matched = merged_df[merged_df.iloc[:, len(df_1.columns)].notna()].shape[0]
                                        st.info(f"{matched} out of {len(df_1)} rows from {selected_sheet_1} have matches in {selected_sheet_2}")
                                    elif join_type == "right":
                                        matched = merged_df[merged_df.iloc[:, 0].notna()].shape[0]
                                        st.info(f"{matched} out of {len(df_2)} rows from {selected_sheet_2} have matches in {selected_sheet_1}")
                                    elif join_type == "outer":
                                        only_left = merged_df[merged_df.iloc[:, len(df_1.columns)].isna()].shape[0]
                                        only_right = merged_df[merged_df.iloc[:, 0].isna()].shape[0]
                                        both = len(merged_df) - only_left - only_right
                                        
                                        st.info(f"Merged dataset contains {both} rows present in both sheets, {only_left} rows only in {selected_sheet_1}, and {only_right} rows only in {selected_sheet_2}")
                                    
                                    # Option to download merged data
                                    csv = merged_df.to_csv(index=False)
                                    b64 = base64.b64encode(csv.encode()).decode()
                                    href = f'<a href="data:file/csv;base64,{b64}" download="merged_data.csv" class="btn">Download Merged Data as CSV</a>'
                                    st.markdown(href, unsafe_allow_html=True)
                                else:
                                    st.warning("No common columns found for joining the datasets.")
                        else:
                            st.warning("Second worksheet is empty.")
                else:
                    st.warning("First worksheet is empty.")
        except Exception as e:
            st.error(f"Error accessing Google Sheets: {str(e)}")

elif page == "Google Sheets - Dashboard":
    st.markdown("<h1 class='main-header'>Google Sheets Dashboard</h1>", unsafe_allow_html=True)
    
    # Spreadsheet selector
    data_loaded = spreadsheet_selector()
    
    if data_loaded and st.session_state.sheets_data is not None:
        df = st.session_state.sheets_data
        
        # Dashboard configuration
        st.markdown("<h2 class='page-header'>Dashboard Configuration</h2>", unsafe_allow_html=True)
        
        # Identify numeric and categorical columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        if not numeric_cols:
            st.warning("No numeric columns found in the data. Dashboard requires numeric data for visualization.")
        else:
            # Dashboard layout
            dashboard_layout = st.radio(
                "Select dashboard layout:",
                ["2x2 Grid", "3x1 Grid", "1x3 Grid", "Custom"],
                horizontal=True
            )
            
            # Dashboard title
            dashboard_title = st.text_input("Dashboard title:", "Google Sheets Data Dashboard")
            
            # KPI metrics
            st.markdown("<h3 class='section-header'>KPI Metrics</h3>", unsafe_allow_html=True)
            
            kpi_cols = st.multiselect(
                "Select columns for KPI metrics (max 4):",
                numeric_cols,
                default=numeric_cols[:min(4, len(numeric_cols))]
            )
            
            # Limit to 4 KPIs
            kpi_cols = kpi_cols[:4]
            
            # Chart configuration
            st.markdown("<h3 class='section-header'>Chart Configuration</h3>", unsafe_allow_html=True)
            
            # Number of charts based on layout
            if dashboard_layout == "2x2 Grid":
                num_charts = 4
            elif dashboard_layout == "3x1 Grid" or dashboard_layout == "1x3 Grid":
                num_charts = 3
            elif dashboard_layout == "Custom":
                num_charts = st.slider("Number of charts:", 1, 6, 3)
            
            # Configure each chart
            charts = []
            
            for i in range(num_charts):
                st.markdown(f"**Chart {i+1}**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    chart_type = st.selectbox(
                        f"Chart {i+1} type:",
                        ["Bar Chart", "Line Chart", "Pie Chart", "Scatter Plot", "Heatmap"],
                        key=f"chart_type_{i}"
                    )
                
                with col2:
                    chart_title = st.text_input(f"Chart {i+1} title:", f"Chart {i+1}", key=f"chart_title_{i}")
                
                # Different options based on chart type
                if chart_type == "Bar Chart":
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if categorical_cols:
                            x_col = st.selectbox(
                                f"X-axis (categories) for chart {i+1}:",
                                categorical_cols,
                                key=f"x_col_{i}"
                            )
                        else:
                            x_col = st.selectbox(
                                f"X-axis for chart {i+1}:",
                                df.columns.tolist(),
                                key=f"x_col_{i}"
                            )
                    
                    with col2:
                        y_col = st.selectbox(
                            f"Y-axis (values) for chart {i+1}:",
                            numeric_cols,
                            key=f"y_col_{i}"
                        )
                    
                    charts.append({
                        "type": chart_type,
                        "title": chart_title,
                        "x_col": x_col,
                        "y_col": y_col
                    })
                
                elif chart_type == "Line Chart":
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        x_col = st.selectbox(
                            f"X-axis for chart {i+1}:",
                            df.columns.tolist(),
                            key=f"x_col_{i}"
                        )
                    
                    with col2:
                        y_cols = st.multiselect(
                            f"Y-axis (values) for chart {i+1}:",
                            numeric_cols,
                            default=[numeric_cols[0]] if numeric_cols else [],
                            key=f"y_cols_{i}"
                        )
                    
                    charts.append({
                        "type": chart_type,
                        "title": chart_title,
                        "x_col": x_col,
                        "y_cols": y_cols
                    })
                
                elif chart_type == "Pie Chart":
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if categorical_cols:
                            labels_col = st.selectbox(
                                f"Labels for chart {i+1}:",
                                categorical_cols,
                                key=f"labels_col_{i}"
                            )
                        else:
                            labels_col = st.selectbox(
                                f"Labels for chart {i+1}:",
                                df.columns.tolist(),
                                key=f"labels_col_{i}"
                            )
                    
                    with col2:
                        values_col = st.selectbox(
                            f"Values for chart {i+1}:",
                            numeric_cols,
                            key=f"values_col_{i}"
                        )
                    
                    charts.append({
                        "type": chart_type,
                        "title": chart_title,
                        "labels_col": labels_col,
                        "values_col": values_col
                    })
                
                elif chart_type == "Scatter Plot":
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        x_col = st.selectbox(
                            f"X-axis for chart {i+1}:",
                            numeric_cols,
                            key=f"x_col_{i}"
                        )
                    
                    with col2:
                        y_col = st.selectbox(
                            f"Y-axis for chart {i+1}:",
                            [col for col in numeric_cols if col != x_col],
                            index=min(1, len(numeric_cols)-1) if len(numeric_cols) > 1 else 0,
                            key=f"y_col_{i}"
                        )
                    
                    with col3:
                        if categorical_cols:
                            color_col = st.selectbox(
                                f"Color by (optional) for chart {i+1}:",
                                ["None"] + categorical_cols,
                                key=f"color_col_{i}"
                            )
                        else:
                            color_col = "None"
                    
                    charts.append({ 
                            color_col = "None"
                    
                    charts.append({
                        "type": chart_type,
                        "title": chart_title,
                        "x_col": x_col,
                        "y_col": y_col,
                        "color_col": None if color_col == "None" else color_col
                    })
                
                elif chart_type == "Heatmap":
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if categorical_cols:
                            x_col = st.selectbox(
                                f"X-axis for chart {i+1}:",
                                categorical_cols,
                                key=f"x_col_{i}"
                            )
                        else:
                            x_col = st.selectbox(
                                f"X-axis for chart {i+1}:",
                                df.columns.tolist(),
                                key=f"x_col_{i}"
                            )
                    
                    with col2:
                        if categorical_cols:
                            y_col = st.selectbox(
                                f"Y-axis for chart {i+1}:",
                                [col for col in categorical_cols if col != x_col],
                                index=min(1, len(categorical_cols)-1) if len(categorical_cols) > 1 else 0,
                                key=f"y_col_{i}"
                            )
                        else:
                            y_col = st.selectbox(
                                f"Y-axis for chart {i+1}:",
                                [col for col in df.columns if col != x_col],
                                key=f"y_col_{i}"
                            )
                    
                    with col3:
                        z_col = st.selectbox(
                            f"Values for chart {i+1}:",
                            numeric_cols,
                            key=f"z_col_{i}"
                        )
                    
                    charts.append({
                        "type": chart_type,
                        "title": chart_title,
                        "x_col": x_col,
                        "y_col": y_col,
                        "z_col": z_col
                    })
            
            # Generate dashboard
            if st.button("Generate Dashboard"):
                st.markdown(f"<h1 style='text-align: center;'>{dashboard_title}</h1>", unsafe_allow_html=True)
                
                # KPI metrics
                if kpi_cols:
                    kpi_cols = kpi_cols[:4]  # Limit to 4
                    cols = st.columns(len(kpi_cols))
                    
                    for i, col_name in enumerate(kpi_cols):
                        with cols[i]:
                            value = df[col_name].mean()
                            st.metric(
                                label=col_name,
                                value=f"{value:.2f}",
                                delta=f"{value - df[col_name].median():.2f}"
                            )
                
                # Charts based on layout
                if dashboard_layout == "2x2 Grid":
                    # 2x2 grid
                    for i in range(0, min(4, len(charts)), 2):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            render_chart(charts[i], df)
                        
                        if i + 1 < len(charts):
                            with col2:
                                render_chart(charts[i + 1], df)
                
                elif dashboard_layout == "3x1 Grid":
                    # 3 charts in a column
                    for i in range(min(3, len(charts))):
                        render_chart(charts[i], df)
                
                elif dashboard_layout == "1x3 Grid":
                    # 3 charts in a row
                    cols = st.columns(3)
                    
                    for i in range(min(3, len(charts))):
                        with cols[i]:
                            render_chart(charts[i], df)
                
                elif dashboard_layout == "Custom":
                    # Custom layout
                    for i in range(min(num_charts, len(charts))):
                        render_chart(charts[i], df)
                
                # Add timestamp
                st.markdown(f"<p style='text-align: right; color: #888; font-size: 0.8em;'>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

elif page == "Google Sheets - Data Editor":
    st.markdown("<h1 class='main-header'>Google Sheets Data Editor</h1>", unsafe_allow_html=True)
    
    # Spreadsheet selector
    data_loaded = spreadsheet_selector()
    
    if data_loaded and st.session_state.sheets_data is not None:
        df = st.session_state.sheets_data.copy()
        
        # Data editor options
        st.markdown("<h2 class='page-header'>Edit Data</h2>", unsafe_allow_html=True)
        
        edit_mode = st.radio(
            "Select edit mode:",
            ["Edit Cells", "Add Row", "Delete Rows", "Add Column", "Delete Columns"],
            horizontal=True
        )
        
        if edit_mode == "Edit Cells":
            st.info("Edit cells directly in the table below. Click 'Save Changes' when done.")
            
            # Use Streamlit's data editor
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True
            )
            
            if st.button("Save Changes to Google Sheets"):
                try:
                    # Connect to Google Sheets
                    gc = gspread.authorize(st.session_state.credentials)
                    spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
                    worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
                    
                    # Clear the worksheet and update with new data
                    worksheet.clear()
                    
                    # Convert all data to strings for gspread
                    edited_df = edited_df.astype(str)
                    
                    # Update the worksheet
                    set_with_dataframe(worksheet, edited_df, include_index=False, include_column_header=True)
                    
                    # Update the session state
                    st.session_state.sheets_data = edited_df
                    
                    st.success("Changes saved successfully!")
                except Exception as e:
                    st.error(f"Error saving changes: {str(e)}")
        
        elif edit_mode == "Add Row":
            st.markdown("<h3 class='section-header'>Add New Row</h3>", unsafe_allow_html=True)
            
            # Create input fields for each column
            new_row = {}
            
            # Use columns to make the form more compact
            col_groups = [df.columns[i:i+3] for i in range(0, len(df.columns), 3)]
            
            for col_group in col_groups:
                cols = st.columns(len(col_group))
                
                for i, col in enumerate(col_group):
                    with cols[i]:
                        # Determine the input type based on column data type
                        if df[col].dtype in ['int64', 'float64']:
                            new_row[col] = st.number_input(f"{col}:", key=f"new_row_{col}")
                        else:
                            new_row[col] = st.text_input(f"{col}:", key=f"new_row_{col}")
            
            if st.button("Add Row"):
                try:
                    # Add the new row to the dataframe
                    new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # Connect to Google Sheets
                    gc = gspread.authorize(st.session_state.credentials)
                    spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
                    worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
                    
                    # Convert all values to strings for gspread
                    row_values = [str(new_row[col]) for col in df.columns]
                    
                    # Append the new row
                    worksheet.append_row(row_values)
                    
                    # Update the session state
                    st.session_state.sheets_data = new_df
                    
                    st.success("Row added successfully! Please refresh the page to see the updated data.")
                except Exception as e:
                    st.error(f"Error adding row: {str(e)}")
        
        elif edit_mode == "Delete Rows":
            st.markdown("<h3 class='section-header'>Delete Rows</h3>", unsafe_allow_html=True)
            
            # Show the dataframe with row numbers
            df_with_index = df.copy()
            df_with_index.index = range(1, len(df) + 1)  # 1-based indexing for user
            
            st.dataframe(df_with_index, use_container_width=True)
            
            # Input for row numbers to delete
            rows_to_delete = st.text_input(
                "Enter row numbers to delete (comma-separated, e.g., 1,3,5):"
            )
            
            if st.button("Delete Rows") and rows_to_delete:
                try:
                    # Parse the row numbers
                    row_indices = [int(x.strip()) for x in rows_to_delete.split(",")]
                    
                    # Validate row indices
                    valid_indices = [idx for idx in row_indices if 1 <= idx <= len(df)]
                    
                    if valid_indices:
                        # Convert to 0-based indexing for pandas
                        zero_based_indices = [idx - 1 for idx in valid_indices]
                        
                        # Delete the rows
                        new_df = df.drop(zero_based_indices).reset_index(drop=True)
                        
                        # Connect to Google Sheets
                        gc = gspread.authorize(st.session_state.credentials)
                        spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
                        worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
                        
                        # Clear the worksheet
                        worksheet.clear()
                        
                        # Update with new data
                        set_with_dataframe(worksheet, new_df, include_index=False, include_column_header=True)
                        
                        # Update the session state
                        st.session_state.sheets_data = new_df
                        
                        st.success(f"Deleted {len(valid_indices)} rows successfully! Please refresh the page to see the updated data.")
                    else:
                        st.warning("No valid row numbers provided.")
                except Exception as e:
                    st.error(f"Error deleting rows: {str(e)}")
        
        elif edit_mode == "Add Column":
            st.markdown("<h3 class='section-header'>Add New Column</h3>", unsafe_allow_html=True)
            
            # Column name and type
            col1, col2 = st.columns(2)
            
            with col1:
                new_col_name = st.text_input("New column name:")
            
            with col2:
                col_type = st.selectbox(
                    "Column type:",
                    ["Text", "Number", "Formula", "Calculated"]
                )
            
            if col_type == "Text":
                default_value = st.text_input("Default value (leave empty for blank):")
                
                if st.button("Add Column") and new_col_name:
                    try:
                        # Add the new column to the dataframe
                        df[new_col_name] = default_value
                        
                        # Connect to Google Sheets
                        gc = gspread.authorize(st.session_state.credentials)
                        spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
                        worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
                        
                        # Get the next column letter
                        next_col = chr(65 + len(df.columns) - 1)  # A=65, B=66, etc.
                        
                        # Add the column header
                        worksheet.update_cell(1, len(df.columns), new_col_name)
                        
                        # Add the default value to all rows if provided
                        if default_value:
                            cell_range = f"{next_col}2:{next_col}{len(df)+1}"
                            cell_list = worksheet.range(cell_range)
                            
                            for cell in cell_list:
                                cell.value = default_value
                            
                            worksheet.update_cells(cell_list)
                        
                        # Update the session state
                        st.session_state.sheets_data = df
                        
                        st.success(f"Column '{new_col_name}' added successfully! Please refresh the page to see the updated data.")
                    except Exception as e:
                        st.error(f"Error adding column: {str(e)}")
            
            elif col_type == "Number":
                default_value = st.number_input("Default value:", value=0.0)
                
                if st.button("Add Column") and new_col_name:
                    try:
                        # Add the new column to the dataframe
                        df[new_col_name] = default_value
                        
                        # Connect to Google Sheets
                        gc = gspread.authorize(st.session_state.credentials)
                        spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
                        worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
                        
                        # Get the next column letter
                        next_col = chr(65 + len(df.columns) - 1)  # A=65, B=66, etc.
                        
                        # Add the column header
                        worksheet.update_cell(1, len(df.columns), new_col_name)
                        
                        # Add the default value to all rows
                        cell_range = f"{next_col}2:{next_col}{len(df)+1}"
                        cell_list = worksheet.range(cell_range)
                        
                        for cell in cell_list:
                            cell.value = str(default_value)
                        
                        worksheet.update_cells(cell_list)
                        
                        # Update the session state
                        st.session_state.sheets_data = df
                        
                        st.success(f"Column '{new_col_name}' added successfully! Please refresh the page to see the updated data.")
                    except Exception as e:
                        st.error(f"Error adding column: {str(e)}")
            
            elif col_type == "Formula":
                formula = st.text_input("Google Sheets formula (e.g., =A2+B2):")
                
                if st.button("Add Column") and new_col_name and formula:
                    try:
                        # Connect to Google Sheets
                        gc = gspread.authorize(st.session_state.credentials)
                        spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
                        worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
                        
                        # Get the next column letter
                        next_col = chr(65 + len(df.columns))  # A=65, B=66, etc.
                        
                        # Add the column header
                        worksheet.update_cell(1, len(df.columns) + 1, new_col_name)
                        
                        # Add the formula to all rows
                        for i in range(2, len(df) + 2):  # Start from row 2 (after header)
                            # Replace generic row number with specific row
                            row_formula = formula.replace("2", str(i))
                            worksheet.update_cell(i, len(df.columns) + 1, row_formula)
                        
                        # Refresh the data
                        updated_data = worksheet.get_all_values()
                        headers = updated_data[0]
                        updated_df = pd.DataFrame(updated_data[1:], columns=headers)
                        
                        # Update the session state
                        st.session_state.sheets_data = updated_df
                        
                        st.success(f"Column '{new_col_name}' with formula added successfully! Please refresh the page to see the updated data.")
                    except Exception as e:
                        st.error(f"Error adding formula column: {str(e)}")
            
            elif col_type == "Calculated":
                st.info("This will calculate values in Python and add them to the sheet.")
                
                # Select columns to use in calculation
                cols_to_use = st.multiselect(
                    "Select columns to use in calculation:",
                    df.columns.tolist()
                )
                
                # Python expression
                python_expr = st.text_input("Python expression (use 'x' for the row, e.g., x['A'] + x['B']):")
                
                if st.button("Add Column") and new_col_name and python_expr and cols_to_use:
                    try:
                        # Calculate the new column
                        df[new_col_name] = df.apply(
                            lambda x: eval(python_expr),
                            axis=1
                        )
                        
                        # Connect to Google Sheets
                        gc = gspread.authorize(st.session_state.credentials)
                        spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
                        worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
                        
                        # Clear the worksheet
                        worksheet.clear()
                        
                        # Update with new data
                        set_with_dataframe(worksheet, df, include_index=False, include_column_header=True)
                        
                        # Update the session state
                        st.session_state.sheets_data = df
                        
                        st.success(f"Column '{new_col_name}' calculated and added successfully! Please refresh the page to see the updated data.")
                    except Exception as e:
                        st.error(f"Error adding calculated column: {str(e)}")
        
        elif edit_mode == "Delete Columns":
            st.markdown("<h3 class='section-header'>Delete Columns</h3>", unsafe_allow_html=True)
            
            # Select columns to delete
            cols_to_delete = st.multiselect(
                "Select columns to delete:",
                df.columns.tolist()
            )
            
            if st.button("Delete Columns") and cols_to_delete:
                try:
                    # Delete the columns
                    new_df = df.drop(columns=cols_to_delete)
                    
                    # Connect to Google Sheets
                    gc = gspread.authorize(st.session_state.credentials)
                    spreadsheet = gc.open_by_key(st.session_state.current_spreadsheet)
                    worksheet = spreadsheet.worksheet(st.session_state.current_worksheet)
                    
                    # Clear the worksheet
                    worksheet.clear()
                    
                    # Update with new data
                    set_with_dataframe(worksheet, new_df, include_index=False, include_column_header=True)
                    
                    # Update the session state
                    st.session_state.sheets_data = new_df
                    
                    st.success(f"Deleted {len(cols_to_delete)} columns successfully! Please refresh the page to see the updated data.")
                except Exception as e:
                    st.error(f"Error deleting columns: {str(e)}")
        
        # Data preview
        st.markdown("<h2 class='page-header'>Data Preview</h2>", unsafe_allow_html=True)
        st.dataframe(df.head(10), use_container_width=True)

elif page == "Google Calendar":
    st.markdown("<h1 class='main-header'>Google Calendar Events</h1>", unsafe_allow_html=True)
    
    if st.session_state.authenticated:
        try:
            # Build the Calendar service
            service = build('calendar', 'v3', credentials=st.session_state.credentials)
            
            # Get calendar ID
            calendar_id = st.text_input("Enter Calendar ID (or 'primary' for your primary calendar):", "primary")
            
            if calendar_id:
                # Date range selection
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start date", datetime.now().date())
                with col2:
                    end_date = st.date_input("End date", (datetime.now() + timedelta(days=30)).date())
                
                if start_date <= end_date:
                    # Convert to datetime and format for API
                    start_datetime = datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z'
                    end_datetime = datetime.combine(end_date, datetime.max.time()).isoformat() + 'Z'
                    
                    # Call the Calendar API
                    with st.spinner("Fetching calendar events..."):
                        events_result = service.events().list(
                            calendarId=calendar_id,
                            timeMin=start_datetime,
                            timeMax=end_datetime,
                            maxResults=100,
                            singleEvents=True,
                            orderBy='startTime'
                        ).execute()
                        
                        events = events_result.get('items', [])
                    
                    if events:
                        # Create a DataFrame for the events
                        event_list = []
                        for event in events:
                            start = event['start'].get('dateTime', event['start'].get('date'))
                            end = event['end'].get('dateTime', event['end'].get('date'))
                            
                            # Format the dates
                            if 'T' in start:  # It's a datetime
                                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                                start_formatted = start_dt.strftime('%Y-%m-%d %H:%M')
                            else:  # It's a date
                                start_formatted = start
                                
                            if 'T' in end:  # It's a datetime
                                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                                end_formatted = end_dt.strftime('%Y-%m-%d %H:%M')
                            else:  # It's a date
                                end_formatted = end
                            
                            event_list.append({
                                'Summary': event.get('summary', 'No title'),
                                'Start': start_formatted,
                                'End': end_formatted,
                                'Location': event.get('location', ''),
                                'Description': event.get('description', ''),
                                'ID': event.get('id', '')
                            })
                        
                        events_df = pd.DataFrame(event_list)
                        
                        # Display events in different views
                        view_type = st.radio(
                            "Select view:",
                            ["List View", "Calendar View", "Timeline View"],
                            horizontal=True
                        )
                        
                        if view_type == "List View":
                            # Display events as a table
                            st.markdown("<h2 class='page-header'>Upcoming Events</h2>", unsafe_allow_html=True)
                            st.dataframe(events_df[['Summary', 'Start', 'End', 'Location']], use_container_width=True)
                            
                            # Event details
                            selected_event = st.selectbox(
                                "Select an event to view details:",
                                events_df['Summary'].tolist()
                            )
                            
                            if selected_event:
                                event_details = events_df[events_df['Summary'] == selected_event].iloc[0]
                                
                                st.markdown("<h3 class='section-header'>Event Details</h3>", unsafe_allow_html=True)
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown(f"**Event:** {event_details['Summary']}")
                                    st.markdown(f"**Start:** {event_details['Start']}")
                                    st.markdown(f"**End:** {event_details['End']}")
                                
                                with col2:
                                    if event_details['Location']:
                                        st.markdown(f"**Location:** {event_details['Location']}")
                                    
                                    # Add a map if location is available
                                    if event_details['Location']:
                                        st.markdown(f"[View on Google Maps](https://www.google.com/maps/search/?api=1&query={event_details['Location']})")
                                
                                if event_details['Description']:
                                    st.markdown("**Description:**")
                                    st.markdown(event_details['Description'])
                        
                        elif view_type == "Calendar View":
                            st.markdown("<h2 class='page-header'>Calendar View</h2>", unsafe_allow_html=True)
                            
                            # Group events by date
                            events_by_date = {}
                            
                            for _, event in events_df.iterrows():
                                date_str = event['Start'].split(' ')[0]  # Get just the date part
                                
                                if date_str not in events_by_date:
                                    events_by_date[date_str] = []
                                
                                events_by_date[date_str].append(event)
                            
                            # Display events by date
                            for date_str in sorted(events_by_date.keys()):
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                                day_name = date_obj.strftime('%A')
                                
                                st.markdown(f"### {day_name}, {date_str}")
                                
                                for event in events_by_date[date_str]:
                                    with st.expander(f"{event['Start'].split(' ')[1] if ' ' in event['Start'] else 'All day'} - {event['Summary']}"):
                                        st.markdown(f"**End:** {event['End']}")
                                        
                                        if event['Location']:
                                            st.markdown(f"**Location:** {event['Location']}")
                                        
                                        if event['Description']:
                                            st.markdown("**Description:**")
                                            st.markdown(event['Description'])
                        
                        elif view_type == "Timeline View":
                            st.markdown("<h2 class='page-header'>Timeline View</h2>", unsafe_allow_html=True)
                            
                            # Create a timeline chart
                            fig = go.Figure()
                            
                            # Add events to the timeline
                            for i, event in events_df.iterrows():
                                # Parse start and end times
                                if ' ' in event['Start']:  # It has a time component
                                    start_dt = datetime.strptime(event['Start'], '%Y-%m-%d %H:%M')
                                else:
                                    start_dt = datetime.strptime(event['Start'], '%Y-%m-%d')
                                
                                if ' ' in event['End']:  # It has a time component
                                    end_dt = datetime.strptime(event['End'], '%Y-%m-%d %H:%M')
                                else:
                                    end_dt = datetime.strptime(event['End'], '%Y-%m-%d')
                                
                                # Add a bar for each event
                                fig.add_trace(
                                    go.Bar(
                                        x=[end_dt - start_dt],
                                        y=[event['Summary']],
                                        orientation='h',
                                        base=[start_dt],
                                        name=event['Summary'],
                                        hoverinfo='text',
                                        text=f"{event['Summary']}<br>{event['Start']} to {event['End']}<br>{event['Location']}",
                                        marker=dict(
                                            color=f'rgba({hash(event["Summary"]) % 256}, {(hash(event["Summary"]) // 256) % 256}, {(hash(event["Summary"]) // 65536) % 256}, 0.8)'
                                        )
                                    )
                                )
                            
                            fig.update_layout(
                                title="Event Timeline",
                                xaxis=dict(
                                    type='date',
                                    title="Date/Time"
                                ),
                                yaxis=dict(
                                    title="Event",
                                    autorange="reversed"
                                ),
                                height=600,
                                barmode='overlay'
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No events found between {start_date} and {end_date}.")
                else:
                    st.error("End date must be after start date.")
        except Exception as e:
            st.error(f"Error accessing Google Calendar: {str(e)}")
    else:
        st.info("Please authenticate to view Google Calendar events.")

elif page == "Google Drive":
    st.markdown("<h1 class='main-header'>Google Drive File Manager</h1>", unsafe_allow_html=True)
    
    if st.session_state.authenticated:
        try:
            # Build the Drive service
            drive_service = build('drive', 'v3', credentials=st.session_state.credentials)
            
            # Tabs for different functions
            drive_tab = st.radio(
                "Select function:",
                ["Upload Files", "Browse Files", "Search Files", "Manage Folders"],
                horizontal=True
            )
            
            if drive_tab == "Upload Files":
                st.markdown("<h2 class='page-header'>Upload Files to Google Drive</h2>", unsafe_allow_html=True)
                
                # File uploader
                uploaded_file = st.file_uploader("Choose a file to upload", type=None, accept_multiple_files=False)
                
                # Folder selection
                st.subheader("Select Destination Folder")
                
                # Option to create a new folder
                create_new_folder = st.checkbox("Create a new folder")
                
                if create_new_folder:
                    folder_name = st.text_input("Enter new folder name:")
                else:
                    # Get folders from Drive
                    folders_result = drive_service.files().list(
                        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                        spaces='drive',
                        fields='files(id, name)'
                    ).execute()
                    
                    folders = folders_result.get('files', [])
                    
                    if folders:
                        folder_options = ["root"] + [folder['name'] for folder in folders]
                        selected_folder = st.selectbox("Select destination folder:", folder_options)
                        
                        if selected_folder == "root":
                            folder_id = "root"
                            folder_name = None
                        else:
                            folder_id = next(folder['id'] for folder in folders if folder['name'] == selected_folder)
                            folder_name = selected_folder
                    else:
                        st.info("No folders found in your Drive. Files will be uploaded to the root folder.")
                        folder_id = "root"
                        folder_name = None
                
                if uploaded_file:
                    # Button to upload
                    if st.button("Upload to Google Drive"):
                        with st.spinner("Uploading file..."):
                            # Save the uploaded file temporarily
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uploaded_file.name}') as tmp:
                                tmp.write(uploaded_file.getvalue())
                                temp_file_path = tmp.name
                            
                            try:
                                # Handle folder creation if needed
                                if create_new_folder and folder_name:
                                    # Create the folder
                                    folder_metadata = {
                                        'name': folder_name,
                                        'mimeType': 'application/vnd.google-apps.folder'
                                    }
                                    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                                    folder_id = folder.get('id')
                                    st.success(f"Created new folder: {folder_name}")
                                
                                # Upload the file
                                file_metadata = {
                                    'name': uploaded_file.name,
                                    'parents': [folder_id]
                                }
                                
                                media = MediaFileUpload(
                                    temp_file_path,
                                    resumable=True
                                )
                                
                                file = drive_service.files().create(
                                    body=file_metadata,
                                    media_body=media,
                                    fields='id,name,webViewLink,iconLink,thumbnailLink'
                                ).execute()
                                
                                # Clean up the temporary file
                                os.unlink(temp_file_path)
                                
                                st.success(f"File uploaded successfully: {file.get('name')}")
                                
                                # Display file info
                                col1, col2 = st.columns([1, 3])
                                
                                with col1:
                                    if 'thumbnailLink' in file:
                                        st.image(file.get('thumbnailLink'), width=100)
                                    elif 'iconLink' in file:
                                        st.image(file.get('iconLink'), width=50)
                                
                                with col2:
                                    st.markdown(f"**File:** {file.get('name')}")
                                    st.markdown(f"**Location:** {folder_name if folder_name else 'Root'}")
                                    st.markdown(f"[View file in Google Drive]({file.get('webViewLink')})")
                            
                            except Exception as e:
                                # Clean up the temporary file in case of error
                                os.unlink(temp_file_path)
                                st.error(f"Error uploading file: {str(e)}")
            
            elif drive_tab == "Browse Files":
                st.markdown("<h2 class='page-header'>Browse Google Drive Files</h2>", unsafe_allow_html=True)
                
                # Get folders from Drive
                folders_result = drive_service.files().list(
                    q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                    spaces='drive',
                    fields='files(id, name)'
                ).execute()
                
                folders = folders_result.get('files', [])
                
                # Add root folder
                folders = [{'id': 'root', 'name': 'Root'}] + folders
                
                # Select folder to browse
                selected_folder = st.selectbox(
                    "Select folder to browse:",
                    [folder['name'] for folder in folders]
                )
                
                folder_id = next(folder['id'] for folder in folders if folder['name'] == selected_folder)
                
                # Get files in the selected folder
                query = f"'{folder_id}' in parents and trashed=false"
                
                # File type filter
                file_type = st.selectbox(
                    "Filter by file type:",
                    ["All Files", "Documents", "Spreadsheets", "Presentations", "Images", "Videos", "Audio", "PDFs"]
                )
                
                if file_type == "Documents":
                    query += " and (mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType='application/msword')"
                elif file_type == "Spreadsheets":
                    query += " and (mimeType='application/vnd.google-apps.spreadsheet' or mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='application/vnd.ms-excel')"
                elif file_type == "Presentations":
                    query += " and (mimeType='application/vnd.google-apps.presentation' or mimeType='application/vnd.openxmlformats-officedocument.presentationml.presentation' or mimeType='application/vnd.ms-powerpoint')"
                elif file_type == "Images":
                    query += " and (mimeType contains 'image/')"
                elif file_type == "Videos":
                    query += " and (mimeType contains 'video/')"
                elif file_type == "Audio":
                    query += " and (mimeType contains 'audio/')"
                elif file_type == "PDFs":
                    query += " and mimeType='application/pdf'"
                
                # Sort options
                sort_by = st.selectbox(
                    "Sort by:",
                    ["Modified Time (newest first)", "Modified Time (oldest first)", "Name (A-Z)", "Name (Z-A)"]
                )
                
                if sort_by == "Modified Time (newest first)":
                    order_by = "modifiedTime desc"
                elif sort_by == "Modified Time (oldest first)":
                    order_by = "modifiedTime"
                elif sort_by == "Name (A-Z)":
                    order_by = "name"
                elif sort_by == "Name (Z-A)":
                    order_by = "name desc"
                
                # Get files
                with st.spinner("Loading files..."):
                    files_result = drive_service.files().list(
                        q=query,
                        spaces='drive',
                        fields="files(id, name, mimeType, modifiedTime, size, webViewLink, iconLink, thumbnailLink)",
                        orderBy=order_by
                    ).execute()
                    
                    files = files_result.get('files', [])
                
                if files:
                    st.success(f"Found {len(files)} files in {selected_folder}")
                    
                    # Display files in a grid
                    cols_per_row = 3
                    rows = [files[i:i+cols_per_row] for i in range(0, len(files), cols_per_row)]
                    
                    for row in rows:
                        cols = st.columns(cols_per_row)
                        
                        for i, file in enumerate(row):
                            with cols[i]:
                                # Display file card
                                with st.container():
                                    # File icon or thumbnail
                                    if 'thumbnailLink' in file:
                                        st.image(file.get('thumbnailLink'), width=100)
                                    elif 'iconLink' in file:
                                        st.image(file.get('iconLink'), width=50)
                                    
                                    # File name and details
                                    st.markdown(f"**{file.get('name')}**")
                                    
                                    # Format modified time
                                    mod_time = datetime.fromisoformat(file.get('modifiedTime').replace('Z', '+00:00'))
                                    st.markdown(f"Modified: {mod_time.strftime('%Y-%m-%d %H:%M')}")
                                    
                                    # File size if available
                                    if 'size' in file:
                                        size_bytes = int(file.get('size'))
                                        if size_bytes < 1024:
                                            size_str = f"{size_bytes} B"
                                        elif size_bytes < 1024 * 1024:
                                            size_str = f"{size_bytes / 1024:.1f} KB"
                                        else:
                                            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                                        
                                        st.markdown(f"Size: {size_str}")
                                    
                                    # Link to file
                                    st.markdown(f"[Open]({file.get('webViewLink')})")
                else:
                    st.info(f"No files found in {selected_folder} matching the selected criteria.")
            
            elif drive_tab == "Search Files":
                st.markdown("<h2 class='page-header'>Search Google Drive Files</h2>", unsafe_allow_html=True)
                
                # Search query
                search_query = st.text_input("Enter search terms:")
                
                # Advanced search options
                show_advanced = st.checkbox("Show advanced search options")
                
                if show_advanced:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        file_type = st.selectbox(
                            "File type:",
                            ["All Files", "Documents", "Spreadsheets", "Presentations", "Images", "Videos", "Audio", "PDFs"]
                        )
                    
                    with col2:
                        modified_time = st.selectbox(
                            "Modified time:",
                            ["Any time", "Today", "Yesterday", "Last 7 days", "Last 30 days", "Last 90 days"]
                        )
                
                if st.button("Search") and search_query:
                    with st.spinner("Searching..."):
                        # Build query
                        query = f"fullText contains '{search_query}' and trashed=false"
                        
                        # Add file type filter
                        if show_advanced:
                            if file_type == "Documents":
                                query += " and (mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType='application/msword')"
                            elif file_type == "Spreadsheets":
                                query += " and (mimeType='application/vnd.google-apps.spreadsheet' or mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='application/vnd.ms-excel')"
                            elif file_type == "Presentations":
                                query += " and (mimeType='application/vnd.google-apps.presentation' or mimeType='application/vnd.openxmlformats-officedocument.presentationml.presentation' or mimeType='application/vnd.ms-powerpoint')"
                            elif file_type == "Images":
                                query += " and (mimeType contains 'image/')"
                            elif file_type == "Videos":
                                query += " and (mimeType contains 'video/')"
                            elif file_type == "Audio":
                                query += " and (mimeType contains 'audio/')"
                            elif file_type == "PDFs":
                                query += " and mimeType='application/pdf'"
                            
                            # Add time filter
                            if modified_time != "Any time":
                                now = datetime.now()
                                
                                if modified_time == "Today":
                                    date_filter = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
                                elif modified_time == "Yesterday":
                                    yesterday = now - timedelta(days=1)
                                    date_filter = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
                                elif modified_time == "Last 7 days":
                                    date_filter = (now - timedelta(days=7)).isoformat() + 'Z'
                                elif modified_time == "Last 30 days":
                                    date_filter = (now - timedelta(days=30)).isoformat() + 'Z'
                                elif modified_time == "Last 90 days":
                                    date_filter = (now - timedelta(days=90)).isoformat() + 'Z'
                                
                                query += f" and modifiedTime > '{date_filter}'"
                        
                        # Execute search
                        files_result = drive_service.files().list(
                            q=query,
                            spaces='drive',
                            fields="files(id, name, mimeType, modifiedTime, size, webViewLink, iconLink, thumbnailLink, parents)",
                            orderBy="modifiedTime desc"
                        ).execute()
                        
                        files = files_result.get('files', [])
                    
                    if files:
                        st.success(f"Found {len(files)} results for '{search_query}'")
                        
                        # Get parent folder names for each file
                        for file in files:
                            if 'parents' in file and file['parents']:
                                parent_id = file['parents'][0]
                                
                                try:
                                    parent = drive_service.files().get(
                                        fileId=parent_id,
                                        fields="name"
                                    ).execute()
                                    
                                    file['parent_name'] = parent.get('name', 'Unknown folder')
                                except:
                                    file['parent_name'] = 'Unknown folder'
                            else:
                                file['parent_name'] = 'Root'
                        
                        # Display search results
                        for file in files:
                            with st.container():
                                col1, col2 = st.columns([1, 5])
                                
                                with col1:
                                    # File icon or thumbnail
                                    if 'thumbnailLink' in file:
                                        st.image(file.get('thumbnailLink'), width=100)
                                    elif 'iconLink' in file:
                                        st.image(file.get('iconLink'), width=50)
                                
                                with col2:
                                    # File name and details
                                    st.markdown(f"**{file.get('name')}**")
                                    
                                    # Format modified time
                                    mod_time = datetime.fromisoformat(file.get('modifiedTime').replace('Z', '+00:00'))
                                    
                                    # File location
                                    st.markdown(f"Location: {file.get('parent_name')}")
                                    
                                    # Modified time
                                    st.markdown(f"Modified: {mod_time.strftime('%Y-%m-%d %H:%M')}")
                                    
                                    # File size if available
                                    if 'size' in file:
                                        size_bytes = int(file.get('size'))
                                        if size_bytes < 1024:
                                            size_str = f"{size_bytes} B"
                                        elif size_bytes < 1024 * 1024:
                                            size_str = f"{size_bytes / 1024:.1f} KB"
                                        else:
                                            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                                        
                                        st.markdown(f"Size: {size_str}")
                                    
                                    # Link to file
                                    st.markdown(f"[Open in Google Drive]({file.get('webViewLink')})")
                                
                                st.markdown("---")
                    else:
                        st.info(f"No results found for '{search_query}'")
            
            elif drive_tab == "Manage Folders":
                st.markdown("<h2 class='page-header'>Manage Google Drive Folders</h2>", unsafe_allow_html=True)
                
                # Folder management options
                folder_action = st.radio(
                    "Select action:",
                    ["Create Folder", "Browse Folders", "Move Files"],
                    horizontal=True
                )
                
                if folder_action == "Create Folder":
                    st.markdown("<h3 class='section-header'>Create New Folder</h3>", unsafe_allow_html=True)
                    
                    # Folder name
                    new_folder_name = st.text_input("Enter folder name:")
                    
                    # Parent folder selection
                    folders_result = drive_service.files().list(
                        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                        spaces='drive',
                        fields='files(id, name)'
                    ).execute()
                    
                    folders = folders_result.get('files', [])
                    
                    # Add root folder
                    folders = [{'id': 'root', 'name': 'Root'}] + folders
                    
                    parent_folder = st.selectbox(
                        "Select parent folder:",
                        [folder['name'] for folder in folders]
                    )
                    
                    parent_id = next(folder['id'] for folder in folders if folder['name'] == parent_folder)
                    
                    # Create folder button
                    if st.button("Create Folder") and new_folder_name:
                        try:
                            # Create the folder
                            folder_metadata = {
                                'name': new_folder_name,
                                'mimeType': 'application/vnd.google-apps.folder',
                                'parents': [parent_id]
                            }
                            
                            folder = drive_service.files().create(
                                body=folder_metadata,
                                fields='id,name,webViewLink'
                            ).execute()
                            
                            st.success(f"Folder '{new_folder_name}' created successfully!")
                            st.markdown(f"[Open folder in Google Drive]({folder.get('webViewLink')})")
                        except Exception as e:
                            st.error(f"Error creating folder: {str(e)}")
                
                elif folder_action == "Browse Folders":
                    st.markdown("<h3 class='section-header'>Browse Folders</h3>", unsafe_allow_html=True)
                    
                    # Get all folders
                    folders_result = drive_service.files().list(
                        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                        spaces='drive',
                        fields='files(id, name, parents, modifiedTime)'
                    ).execute()
                    
                    folders = folders_result.get('files', [])
                    
                    if folders:
                        # Build folder hierarchy
                        folder_dict = {folder['id']: folder for folder in folders}
                        
                        # Add root as a special case
                        root_folder = {'id': 'root', 'name': 'Root', 'level': 0}
                        folder_dict['root'] = root_folder
                        
                        # Determine folder levels
                        for folder in folders:
                            folder['level'] = 0
                            
                            if 'parents' in folder:
                                parent_id = folder['parents'][0]
                                current_id = parent_id
                                level = 1
                                
                                while current_id != 'root' and current_id in folder_dict and 'parents' in folder_dict[current_id]:
                                    current_id = folder_dict[current_id]['parents'][0]
                                    level += 1
                                
                                folder['level'] = level
                        
                        # Sort folders by level and name
                        sorted_folders = sorted(folders, key=lambda x: (x.get('level', 0), x.get('name', '')))
                        
                        # Display folders
                        st.markdown("<h4>Folder Structure</h4>", unsafe_allow_html=True)
                        
                        for folder in sorted_folders:
                            # Format indentation based on level
                            indent = "&nbsp;" * (folder['level'] * 4)
                            folder_icon = "📁"
                            
                            # Format modified time if available
                            if 'modifiedTime' in folder:
                                mod_time = datetime.fromisoformat(folder['modifiedTime'].replace('Z', '+00:00'))
                                time_str = mod_time.strftime('%Y-%m-%d')
                            else:
                                time_str = ""
                            
                            st.markdown(f"{indent}{folder_icon} {folder['name']} <span style='color: #888; font-size: 0.8em;'>{time_str}</span>", unsafe_allow_html=True)
                    else:
                        st.info("No folders found in your Google Drive.")
                
                elif folder_action == "Move Files":
                    st.markdown("<h3 class='section-header'>Move Files Between Folders</h3>", unsafe_allow_html=True)
                    
                    # Get all folders
                    folders_result = drive_service.files().list(
                        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                        spaces='drive',
                        fields='files(id, name)'
                    ).execute()
                    
                    folders = folders_result.get('files', [])
                    
                    # Add root folder
                    folders = [{'id': 'root', 'name': 'Root'}] + folders
                    
                    # Source folder selection
                    source_folder = st.selectbox(
                        "Select source folder:",
                        [folder['name'] for folder in folders],
                        key="source_folder"
                    )
                    
                    source_id = next(folder['id'] for folder in folders if folder['name'] == source_folder)
                    
                    # Get files in the source folder
                    files_result = drive_service.files().list(
                        q=f"'{source_id}' in parents and trashed=false",
                        spaces='drive',
                        fields="files(id, name, mimeType)"
                    ).execute()
                    
                    files = files_result.get('files', [])
                    
                    if files:
                        # Select files to move
                        selected_files = st.multiselect(
                            "Select files to move:",
                            [file['name'] for file in files]
                        )
                        
                        if selected_files:
                            # Get file IDs
                            file_ids = [file['id'] for file in files if file['name'] in selected_files]
                            
                            # Destination folder selection
                            destination_folder = st.selectbox(
                                "Select destination folder:",
                                [folder['name'] for folder in folders if folder['name'] != source_folder],
                                key="destination_folder"
                            )
                            
                            destination_id = next(folder['id'] for folder in folders if folder['name'] == destination_folder)
                            
                            # Move files button
                            if st.button("Move Files"):
                                try:
                                    with st.spinner(f"Moving {len(file_ids)} files..."):
                                        for file_id in file_ids:
                                            # Get the file's parents
                                            file = drive_service.files().get(
                                                fileId=file_id,
                                                fields='parents'
                                            ).execute()
                                            
                                            # Move the file
                                            previous_parents = ",".join(file.get('parents'))
                                            
                                            drive_service.files().update(
                                                fileId=file_id,
                                                addParents=destination_id,
                                                removeParents=previous_parents,
                                                fields='id, parents'
                                            ).execute()
                                    
                                    st.success(f"Successfully moved {len(file_ids)} files to {destination_folder}")
                                except Exception as e:
                                    st.error(f"Error moving files: {str(e)}")
                    else:
                        st.info(f"No files found in {source_folder}")
        except Exception as e:
            st.error(f"Error accessing Google Drive: {str(e)}")
    else:
        st.info("Please authenticate to use Google Drive features.")

# Footer for all pages
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Google Services Dashboard | Developed with Streamlit</p>
    <p><small>This app demonstrates integration with Google Sheets, Calendar, and Drive.</small></p>
</div>
""", unsafe_allow_html=True)
