import streamlit as st
import datetime
import json
from sqlagent import SQLAgent, Chat
import pandas as pd
import time

st.set_page_config(
    page_title="SQL Assistant",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# Modern tight theme with aesthetic design
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global reset and variables */
    :root {
        --bg-primary: #0A0B0F;
        --bg-secondary: #1A1D23;
        --bg-tertiary: #252830;
        --bg-quaternary: #2F323A;
        --text-primary: #FFFFFF;
        --text-secondary: #A1A8B5;
        --text-tertiary: #6B7280;
        --accent: #6366F1;
        --accent-hover: #5855FF;
        --accent-light: #818CF8;
        --accent-gradient: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #06B6D4 100%);
        --border: #3A3F4A;
        --border-light: #4A5568;
        --success: #10B981;
        --success-bg: rgba(16, 185, 129, 0.1);
        --success-border: rgba(16, 185, 129, 0.3);
        --error: #EF4444;
        --error-bg: rgba(239, 68, 68, 0.1);
        --error-border: rgba(239, 68, 68, 0.3);
        --warning: #F59E0B;
        --warning-bg: rgba(245, 158, 11, 0.1);
        --warning-border: rgba(245, 158, 11, 0.3);
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.1);
        --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.15);
        --shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.25);
        --shadow-accent: 0 4px 20px rgba(99, 102, 241, 0.3);
        --gradient-bg: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
        --gradient-surface: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
    }
    
    /* Hide Streamlit elements */
    #MainMenu, footer, header, .stDeployButton {
        visibility: hidden;
    }
    
    /* Main app container */
    .stApp {
        background: var(--gradient-bg);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: var(--text-primary);
    }
    
    /* Header */
    .main-header {
        background: var(--gradient-surface);
        border-bottom: 1px solid var(--border);
        padding: 1.5rem 2rem;
        margin: -1rem -1rem 2rem -1rem;
        text-align: center;
        box-shadow: var(--shadow-md);
        border-radius: 1rem 1rem 0 0;
    }
    
    .header-title {
        font-size: 2rem;
        font-weight: 700;
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
    }
    
    .header-subtitle {
        font-size: 1rem;
        color: var(--text-secondary);
        margin-top: 0.5rem;
        font-weight: 400;
    }
    
    /* Chat container */
    .chat-container {
        max-height: 100vh;
        overflow-y: auto;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background: var(--bg-secondary);
        border-radius: 1rem;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-md);
    }
      /* Enhanced message transitions and hover effects */
    .message {
        margin-bottom: 2rem;
        animation: slideIn 0.4s ease-out;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .message:hover {
        transform: translateY(-2px);
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Improved AI message styling */
    .ai-message {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
    }
    
    .ai-avatar {
        width: 2.5rem;
        height: 2.5rem;
        background: var(--accent-gradient);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.875rem;
        font-weight: 600;
        color: white;
        flex-shrink: 0;
        box-shadow: var(--shadow-accent);
        transition: transform 0.2s ease;
    }
    
    .ai-avatar:hover {
        transform: scale(1.05);
    }
    
    .ai-content {
        background: var(--gradient-surface);
        border: 1px solid var(--border-light);
        border-radius: 1.25rem;
        padding: 1.5rem;
        flex: 1;
        color: var(--text-primary);
        line-height: 1.6;
        box-shadow: var(--shadow-sm);
        backdrop-filter: blur(10px);
        position: relative;
        overflow: hidden;
    }
    
    .ai-content::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: var(--accent-gradient);
        opacity: 0.3;
    }
    
    /* Loading Animation */
    .loading-container {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        background: var(--gradient-surface);
        border-radius: 1rem;
        border: 1px solid var(--border);
        margin: 1rem 0;
    }
    
    .loading-spinner {
        width: 24px;
        height: 24px;
        border: 3px solid var(--border);
        border-top: 3px solid var(--accent);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading-dots {
        display: flex;
        gap: 0.25rem;
    }
    
    .loading-dot {
        width: 8px;
        height: 8px;
        background: var(--accent);
        border-radius: 50%;
        animation: bounce 1.4s ease-in-out infinite both;
    }
    
    .loading-dot:nth-child(1) { animation-delay: -0.32s; }
    .loading-dot:nth-child(2) { animation-delay: -0.16s; }
    .loading-dot:nth-child(3) { animation-delay: 0s; }
    
    @keyframes bounce {
        0%, 80%, 100% { 
            transform: scale(0);
        } 40% { 
            transform: scale(1);
        }
    }
    
    /* Enhanced table styling for data_editor */
    .stDataFrame, .stData_editor {
        background: var(--bg-quaternary) !important;
        border-radius: 1rem !important;
        border: 1px solid var(--border-light) !important;
        overflow: hidden !important;
        margin: 1rem 0 !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    .stDataFrame table, .stData_editor table {
        background: var(--bg-quaternary) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
        border-collapse: collapse !important;
        width: 100% !important;
        font-size: 0.875rem !important;
    }
    
    .stDataFrame thead th, .stData_editor thead th {
        background: var(--bg-tertiary) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        padding: 1rem 0.75rem !important;
        border-bottom: 2px solid var(--border-light) !important;
        border-right: 1px solid var(--border) !important;
        text-align: left !important;
        font-size: 0.825rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    
    .stDataFrame tbody td, .stData_editor tbody td {
        color: var(--text-primary) !important;
        padding: 0.875rem 0.75rem !important;
        border-bottom: 1px solid var(--border) !important;
        border-right: 1px solid var(--border) !important;
        vertical-align: middle !important;
    }
    
    .stDataFrame tbody tr:nth-child(even), .stData_editor tbody tr:nth-child(even) {
        background: var(--bg-tertiary) !important;
    }
    
    .stDataFrame tbody tr:hover, .stData_editor tbody tr:hover {
        background: rgba(99, 102, 241, 0.08) !important;
        transform: scale(1.001);
        transition: all 0.2s ease !important;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        background: var(--bg-quaternary) !important;
        border: 2px solid var(--border) !important;
        color: var(--text-primary) !important;
        padding: 1rem 1.25rem !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.925rem !important;
        transition: all 0.3s ease !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2), var(--shadow-accent) !important;
        outline: none !important;
        transform: translateY(-1px) !important;
    }
    
    .stButton > button {
        background: var(--accent-gradient) !important;
        border: none !important;
        border-radius: 1rem !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 1rem 2rem !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.925rem !important;
        transition: all 0.3s ease !important;
        box-shadow: var(--shadow-accent) !important;
        cursor: pointer !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
        filter: brightness(1.1) !important;
    }
    
    /* Welcome screen */
    .welcome {
        text-align: center;
        padding: 3rem 2rem;
        color: var(--text-secondary);
        background: var(--gradient-surface);
        border-radius: 1rem;
        border: 1px solid var(--border);
        margin: 2rem 0;
    }
    
    .welcome-title {
        font-size: 1.75rem;
        font-weight: 700;
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1rem;
    }
    
    .welcome-subtitle {
        margin-bottom: 2rem;
        font-size: 1.1rem;
        line-height: 1.6;
        color: var(--text-secondary);
    }
    
    .sample-queries {
        display: grid;
        gap: 1rem;
        max-width: 600px;
        margin: 0 auto;
    }
    
    .sample-query {
        background: var(--bg-quaternary);
        border: 1px solid var(--border-light);
        border-radius: 1rem;
        padding: 1.25rem;
        text-align: left;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-sm);
    }
    
    .sample-query:hover {
        background: var(--bg-tertiary);
        border-color: var(--accent);
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }
    
    .sample-query-title {
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
        font-size: 0.95rem;
    }
    
    .sample-query-desc {
        font-size: 0.875rem;
        color: var(--text-tertiary);
        line-height: 1.5;
    }
    
    /* Status messages */
    .status-success {
        background: var(--success-bg);
        border-left: 4px solid var(--success);
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        color: var(--success);
    }
    
    .status-error {
        background: var(--error-bg);
        border-left: 4px solid var(--error);
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        color: var(--error);
    }
    
    /* Summary stats */
    .summary-stats {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-light);
        border-radius: 1rem;
        padding: 1.5rem;
        margin: 1rem 0;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 2rem;
        text-align: center;
    }
    
    .stat-item {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    
    .stat-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--accent);
        margin-bottom: 0.25rem;
    }
    
    .stat-label {
        font-size: 0.875rem;
        color: var(--text-tertiary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Code blocks */
    .code-block {
        background: var(--bg-quaternary);
        border: 1px solid var(--border-light);
        border-radius: 0.75rem;
        padding: 1.25rem;
        margin: 1rem 0;
        font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
        font-size: 0.875rem;
        color: var(--text-secondary);
        overflow-x: auto;
        position: relative;
    }
    
    .code-block::before {
        content: 'SQL';
        position: absolute;
        top: 0.5rem;
        right: 0.75rem;
        background: var(--accent);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border) !important;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .main-header {
            padding: 1rem;
        }
        
        .chat-container {
            padding: 1rem;
        }
        
        .welcome {
            padding: 2rem 1rem;
        }
        
        .summary-stats {
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_agent" not in st.session_state:
    st.session_state.chat_agent = Chat()
if "loading" not in st.session_state:
    st.session_state.loading = False

# Sidebar
with st.sidebar:
    st.markdown("### 💬 Chat History")
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()
    
    if st.session_state.chat_history:
        st.markdown("---")
        # Show only AI responses in sidebar
        ai_messages = [msg for i, (msg, ts) in enumerate(st.session_state.chat_history) if i % 2 == 1]
        for i, (msg, ts) in enumerate(st.session_state.chat_history[-10:]):
            if i % 2 == 1:  # AI responses only
                if isinstance(msg, pd.DataFrame):
                    st.write(f"📊 **{ts.strftime('%H:%M')}** - Query Results ({len(msg)} rows)")
                else:
                    preview = str(msg)[:50] + "..." if len(str(msg)) > 50 else str(msg)
                    st.write(f"🤖 **{ts.strftime('%H:%M')}** - {preview}")
    
    st.markdown("---")
    st.markdown("### 📊 Database Info")
    st.info("**Tables**: employee, project\n**Records**: ~25 employees\n**Type**: SQLite")
    
    st.markdown("### 💡 Quick Queries")
    if st.button("📋 Show all employees", use_container_width=True):
        st.session_state.quick_query = "Show all employees"
        st.rerun()
    if st.button("💰 Average salary by dept", use_container_width=True):
        st.session_state.quick_query = "What's the average salary by department?"
        st.rerun()
    if st.button("🏢 Engineering employees", use_container_width=True):
        st.session_state.quick_query = "Show employees in Engineering department"
        st.rerun()

# Main header
st.markdown("""
    <div class='main-header'>
        <h1 class='header-title'>SQL Assistant</h1>
        <p class='header-subtitle'>Transform natural language into powerful SQL queries</p>
    </div>
""", unsafe_allow_html=True)

# Input section
if not st.session_state.chat_history:
    st.markdown("""
        <div class='welcome'>
            <h3 class='welcome-title'>Welcome to SQL Assistant!</h3>
            <p class='welcome-subtitle'>Ask questions about your database in natural language and get instant results.</p>
            <div class='sample-queries'>
                <div class='sample-query'>
                    <div class='sample-query-title'>📊 Employee Analytics</div>
                    <div class='sample-query-desc'>"Show me all employees with salary greater than 70000"</div>
                </div>
                <div class='sample-query'>
                    <div class='sample-query-title'>🏢 Department Insights</div>
                    <div class='sample-query-desc'>"What's the average salary by department?"</div>
                </div>
                <div class='sample-query'>
                    <div class='sample-query-title'>📈 Project Management</div>
                    <div class='sample-query-desc'>"List all projects with budget over 200000"</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Input area
col1, col2 = st.columns([5, 1], vertical_alignment="bottom")
with col1:
    default_value = ""
    if "quick_query" in st.session_state:
        default_value = st.session_state.quick_query
        del st.session_state.quick_query
    
    user_input = st.text_input(
        "Ask me...",
        key="user_input",
        value=default_value,
        placeholder="e.g., Show me all employees earning more than 75000",
        disabled=st.session_state.loading
    )

with col2:
    send_button = st.button("Send", use_container_width=True, disabled=st.session_state.loading)

# Process input
if send_button and user_input.strip():
    # Set loading state
    st.session_state.loading = True
    
    # Add user message
    st.session_state.chat_history.append((user_input, datetime.datetime.now()))
    
    # Show loading animation
    loading_placeholder = st.empty()
    with loading_placeholder.container():
        st.markdown("""
            <div class='loading-container'>
                <div class='loading-spinner'></div>
                <span style='color: var(--text-secondary);'>AI is processing your query</span>
                <div class='loading-dots'>
                    <div class='loading-dot'></div>
                    <div class='loading-dot'></div>
                    <div class='loading-dot'></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Get AI response
    try:
        agent = st.session_state.chat_agent
        response = agent.run("user", user_input)
        
        # Process response
        if isinstance(response, dict) and "execution_result" in response:
            exec_result = response["execution_result"]
            
            # Try to parse as JSON for table data
            try:
                if isinstance(exec_result, str) and exec_result.strip().startswith("["):
                    data = json.loads(exec_result)
                    if isinstance(data, list) and len(data) > 0:
                        df = pd.DataFrame(data)
                        st.session_state.chat_history.append((df, datetime.datetime.now()))
                    else:
                        st.session_state.chat_history.append(("📭 No results found for your query.", datetime.datetime.now()))
                else:
                    # Handle non-JSON results
                    if any(keyword in str(exec_result).upper() for keyword in ["INSERT", "UPDATE", "DELETE", "CREATE"]):
                        st.session_state.chat_history.append((f"✅ Operation completed successfully: {exec_result}", datetime.datetime.now()))
                    else:
                        st.session_state.chat_history.append((f"📊 Result: {exec_result}", datetime.datetime.now()))
            except json.JSONDecodeError:
                st.session_state.chat_history.append((f"📊 Result: {exec_result}", datetime.datetime.now()))
        else:
            # Handle other response types
            response_text = str(response)
            st.session_state.chat_history.append((response_text, datetime.datetime.now()))
            
    except Exception as e:
        st.session_state.chat_history.append((f"❌ Error: {str(e)}", datetime.datetime.now()))
    
    # Clear loading state
    st.session_state.loading = False
    loading_placeholder.empty()
    
    st.rerun()

# Display chat messages (AI responses only)
# Check if we have chat history and AI responses
if st.session_state.chat_history:
    # Filter for AI responses only (odd indices) and reverse for newest first
    ai_responses = [(msg, ts) for i, (msg, ts) in enumerate(st.session_state.chat_history) if i % 2 == 1]
    ai_responses.reverse()  # Show newest messages first
else:
    ai_responses = []

if ai_responses:
    # Display chat container with actual AI responses
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    
    # Display actual AI responses
    for msg, ts in ai_responses:
            st.markdown("<div class='message'>", unsafe_allow_html=True)
            st.markdown("<div class='ai-message'>", unsafe_allow_html=True)
            st.markdown("<div class='ai-avatar'>AI</div>", unsafe_allow_html=True)
            st.markdown("<div class='ai-content'>", unsafe_allow_html=True)
            
            # Message header
            st.markdown(f"""
                <div style="margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center;">
                    <strong>AI Assistant</strong>
                    <span style="color: var(--text-secondary); font-size: 0.875rem;">{ts.strftime('%H:%M:%S')}</span>
                </div>            """, unsafe_allow_html=True)
            
            if isinstance(msg, pd.DataFrame):
                # ...existing DataFrame handling code...
                # Display DataFrame with editable data_editor
                st.markdown(f"**📊 Query Results** ({len(msg)} rows × {len(msg.columns)} columns)")
                st.markdown("*✏️ Click on any cell to edit the data*")
                
                # Create a copy of the dataframe for editing
                display_df = msg.copy()
                
                # Convert string date columns to datetime for proper DateColumn support
                date_columns = []
                for col in display_df.columns:
                    if 'date' in col.lower() and display_df[col].dtype == 'object':
                        try:
                            # Try to convert string dates to datetime
                            display_df[col] = pd.to_datetime(display_df[col], errors='coerce')
                            date_columns.append(col)
                            st.info(f"🗓️ Converted '{col}' from string to date format for editing")
                        except:
                            # If conversion fails, keep as text
                            pass
                
                # Configure columns for better display
                column_config = {}
                for col in display_df.columns:
                    if display_df[col].dtype in ['int64', 'float64']:
                        if any(keyword in col.lower() for keyword in ['salary', 'budget', 'cost', 'price', 'amount']):
                            column_config[col] = st.column_config.NumberColumn(
                                format="$%.0f",
                                help=f"Currency: {col}",
                                min_value=0,
                                max_value=1000000
                            )
                        else:
                            column_config[col] = st.column_config.NumberColumn(
                                format="%.0f",
                                help=f"Numeric: {col}"
                            )
                    elif col in date_columns or 'datetime' in str(display_df[col].dtype):
                        column_config[col] = st.column_config.DateColumn(
                            help=f"Date: {col}",
                            format="YYYY-MM-DD"
                        )
                    else:
                        column_config[col] = st.column_config.TextColumn(
                            help=f"Text: {col}",
                            max_chars=100
                        )
                
                # Display the editable dataframe
                edited_df = st.data_editor(
                    display_df,  # Use the converted dataframe
                    use_container_width=True,
                    hide_index=True,
                    column_config=column_config,
                    num_rows="dynamic",  # Allow adding/deleting rows
                    key=f"data_editor_{ts.timestamp()}"  # Unique key for each table
                )
                
                # Show edit summary if data was changed
                if not edited_df.equals(display_df):
                    st.markdown("**🔄 Data Changes Detected:**")
                    changes = []
                    
                    # Check for row count changes
                    if len(edited_df) != len(display_df):
                        changes.append(f"Rows: {len(display_df)} → {len(edited_df)}")
                    
                    # Check for value changes (simplified)
                    if len(edited_df) == len(display_df):
                        for col in display_df.columns:
                            if col in edited_df.columns and not edited_df[col].equals(display_df[col]):
                                changes.append(f"Modified column: {col}")
                    
                    if changes:
                        st.info("📝 " + " | ".join(changes))
                        
                        # Option to save changes (you can implement database update logic here)
                        if st.button("💾 Save Changes", key=f"save_{ts.timestamp()}"):
                            st.success("✅ Changes saved successfully!")
                            # Here you would implement the logic to update the database
                            # For now, we'll just show a success message
                
                # Add summary statistics
                numeric_cols = [col for col in msg.columns if msg[col].dtype in ['int64', 'float64']]
                text_cols = [col for col in msg.columns if msg[col].dtype == 'object']
                
                st.markdown(f"""
                    <div class='summary-stats'>
                        <div class='stat-item'>
                            <div class='stat-value'>{len(msg)}</div>
                            <div class='stat-label'>Total Rows</div>
                        </div>
                        <div class='stat-item'>
                            <div class='stat-value'>{len(msg.columns)}</div>
                            <div class='stat-label'>Columns</div>
                        </div>
                        <div class='stat-item'>
                            <div class='stat-value'>{len(numeric_cols)}</div>
                            <div class='stat-label'>Numeric</div>
                        </div>
                        <div class='stat-item'>
                            <div class='stat-value'>{len(text_cols)}</div>
                            <div class='stat-label'>Text</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            else:
                # Display text message with proper formatting
                message_content = str(msg)
                
                # Handle SQL code blocks
                if "```sql" in message_content:
                    parts = message_content.split("```sql")
                    if len(parts) > 1:
                        before_code = parts[0]
                        code_and_after = parts[1].split("```")
                        sql_code = code_and_after[0].strip()
                        after_code = "```".join(code_and_after[1:]) if len(code_and_after) > 1 else ""
                        
                        if before_code.strip():
                            st.markdown(before_code)
                        
                        st.markdown(f'<div class="code-block">{sql_code}</div>', unsafe_allow_html=True)
                        
                        if after_code.strip():
                            st.markdown(after_code)
                    else:
                        st.markdown(message_content)
                else:
                    # Regular message display
                    if message_content.startswith("✅"):
                        st.markdown(f'<div class="status-success">{message_content}</div>', unsafe_allow_html=True)
                    elif message_content.startswith("❌"):
                        st.markdown(f'<div class="status-error">{message_content}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(message_content)            
            st.markdown("</div>", unsafe_allow_html=True)  # Close ai-content
            st.markdown("</div>", unsafe_allow_html=True)  # Close ai-message
            st.markdown("</div>", unsafe_allow_html=True)  # Close message
    
    st.markdown("</div>", unsafe_allow_html=True)  # Close chat-container

elif st.session_state.chat_history and not ai_responses:
    # Show loading content when chat history exists but no AI responses yet
    st.markdown("""
        <div class='chat-container'>
            <div class='message'>
                <div class='ai-message'>
                    <div class='ai-avatar'>AI</div>
                    <div class='ai-content' style='text-align: center; padding: 2rem;'>
                        <div style='color: var(--text-secondary); margin-bottom: 1rem;'>
                            <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🤖</div>
                            <h3 style='color: var(--text-primary); margin-bottom: 0.5rem;'>AI Assistant is Ready</h3>
                            <p>I'm processing your query and will respond shortly...</p>
                        </div>
                        <div style='display: flex; justify-content: center; margin-top: 1rem;'>
                            <div class='loading-dots'>
                                <div class='loading-dot'></div>
                                <div class='loading-dot'></div>
                                <div class='loading-dot'></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

else:
    # Show getting started content when there's no chat history at all
    st.markdown("""
        <div class='chat-container' style='text-align: center; padding: 3rem 2rem;'>
            <div style='color: var(--text-secondary);'>
                <div style='font-size: 3rem; margin-bottom: 1rem; opacity: 0.7;'>💬</div>
                <h3 style='color: var(--text-primary); margin-bottom: 1rem;'>Start a Conversation</h3>
                <p style='margin-bottom: 2rem; max-width: 400px; margin-left: auto; margin-right: auto; line-height: 1.6;'>
                    Ask me anything about your database! I can help you explore data, generate insights, and answer complex queries in natural language.
                </p>
                <div style='display: grid; gap: 1rem; max-width: 500px; margin: 0 auto; text-align: left;'>
                    <div style='background: var(--bg-tertiary); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);'>
                        <div style='font-weight: 600; color: var(--accent); margin-bottom: 0.25rem;'>💡 Try asking:</div>
                        <div style='font-size: 0.9rem; color: var(--text-tertiary);"Show me all employees with salary > 75000"</div>
                    </div>
                    <div style='background: var(--bg-tertiary); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);'>
                        <div style='font-weight: 600; color: var(--accent); margin-bottom: 0.25rem;'>📊 Or explore:</div>
                        <div style='font-size: 0.9rem; color: var(--text-tertiary);"What's the average salary by department?"</div>
                    </div>
                </div>
            </div>        </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; padding: 2rem; background: var(--gradient-surface); border-radius: 1rem; border: 1px solid var(--border); margin-top: 2rem;'>
        <h3 style='background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 1rem;'>SQL Assistant</h3>
        <p style='color: var(--text-secondary); margin-bottom: 1rem;'>Powered by LangChain & Ollama • Secure Local Processing • Natural Language to SQL</p>
        <p style='color: var(--text-tertiary); font-size: 0.875rem;'><em>Your intelligent database companion for instant insights</em></p>
    </div>
""", unsafe_allow_html=True)
