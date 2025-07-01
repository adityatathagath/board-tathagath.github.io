import streamlit as st

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="INR Analysis Dashboard",
    page_icon="📈"
)

# Initialize session state for navigation
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'INR_Presentation'

# Navigation buttons
st.markdown("### 🇮🇳 INR Analysis Dashboard")
col1, col2 = st.columns(2)
with col1:
    if st.button('📊 INR Presentation', use_container_width=True, type="primary" if st.session_state.current_page == 'INR_Presentation' else "secondary"):
        st.session_state.current_page = 'INR_Presentation'
with col2:
    if st.button('🏦 MPC Comparison', use_container_width=True, type="primary" if st.session_state.current_page == 'MPC_Comparison' else "secondary"):
        st.session_state.current_page = 'MPC_Comparison'

st.markdown("---")

# Display the selected page
if st.session_state.current_page == 'INR_Presentation':
    # Load and execute INR Presentation content (enhanced_app3.py)
    with open('enhanced_app3.py', 'r', encoding='utf-8') as f:
        code = f.read()
        # Remove the st.set_page_config line to avoid conflicts
        lines = code.split('\n')
        filtered_lines = []
        skip_next = False
        for line in lines:
            if 'st.set_page_config(' in line:
                skip_next = True
                continue
            if skip_next and ')' in line and not line.strip().startswith('#'):
                skip_next = False
                continue
            if not skip_next:
                filtered_lines.append(line)
        
        filtered_code = '\n'.join(filtered_lines)
        exec(filtered_code)
    
elif st.session_state.current_page == 'MPC_Comparison':
    # Load and execute MPC Comparison content (mpc.py)
    with open('mpc.py', 'r', encoding='utf-8') as f:
        code = f.read()
        # Remove the st.set_page_config line to avoid conflicts
        lines = code.split('\n')
        filtered_lines = []
        skip_next = False
        for line in lines:
            if 'st.set_page_config(' in line:
                skip_next = True
                continue
            if skip_next and ')' in line and not line.strip().startswith('#'):
                skip_next = False
                continue
            if not skip_next:
                filtered_lines.append(line)
        
        filtered_code = '\n'.join(filtered_lines)
        exec(filtered_code)
