# frontend/app.py
import streamlit as st
import sys
import os
import json
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, backend_dir)

# Import the simplified service
from simple_backend import SimpleEmailDraftingService, EmailBrief
import uuid

# Initialize the service
@st.cache_resource
def get_email_service():
    return SimpleEmailDraftingService()

def main():
    st.set_page_config(
        page_title="AI Email Drafting Assistant",
        page_icon="📧",
        layout="wide"
    )
    
    st.title("📧 AI Email Drafting Assistant")
    st.markdown("---")
    
    email_service = get_email_service()
    
    # Initialize session state
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None
    if "workflow_step" not in st.session_state:
        st.session_state.workflow_step = "start"
    if "current_draft" not in st.session_state:
        st.session_state.current_draft = None
    if "current_subject" not in st.session_state:
        st.session_state.current_subject = None
    if "show_email_settings" not in st.session_state:
        st.session_state.show_email_settings = False
    
    # Sidebar for navigation and history
    with st.sidebar:
        st.header("📁 Email History")
        
        # Load previous emails button
        if st.button("🔄 Refresh History", use_container_width=True):
            st.rerun()
        
        # Get email history
        history = email_service.get_email_history()
        
        if history:
            st.subheader("Previous Emails")
            for email in history[:10]:  # Show last 10 emails
                with st.expander(f"📧 {email['subject'][:30]}..." if email['subject'] else f"📧 {email['purpose'][:30]}..."):
                    st.write(f"**Recipients:** {json.loads(email['recipients'])}")
                    st.write(f"**Purpose:** {email['purpose']}")
                    st.write(f"**Status:** {email['status']}")
                    st.write(f"**Created:** {email['created_at']}")
                    
                    if st.button(f"Load Thread", key=f"load_{email['id']}"):
                        st.session_state.current_thread_id = email['thread_id']
                        thread_data = email_service.get_thread_by_id(email['thread_id'])
                        if thread_data:
                            st.session_state.current_draft = thread_data['draft']
                            st.session_state.current_subject = thread_data['subject']
                            st.session_state.workflow_step = "loaded_from_history"
                        st.rerun()
        else:
            st.info("No email history found.")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Check current workflow step
        if st.session_state.workflow_step == "start" or st.session_state.workflow_step == "loaded_from_history":
            show_email_creation_form(email_service)
        elif st.session_state.workflow_step == "awaiting_permission":
            show_permission_form(email_service)
        elif st.session_state.workflow_step == "awaiting_approval":
            show_approval_form(email_service)
        elif st.session_state.workflow_step == "completed":
            show_completion_status(email_service)
    
    with col2:
        show_workflow_status()

def show_email_creation_form(email_service):
    """Show the initial email creation form"""
    st.header("✉️ Create New Email")
    
    with st.form("email_brief_form", clear_on_submit=False):
        st.subheader("Email Details")
        
        recipients = st.text_area(
            "📬 Recipients (one per line)",
            placeholder="john.doe@company.com\njane.smith@company.com",
            help="Enter email addresses, one per line"
        )
        
        purpose = st.text_area(
            "🎯 Purpose of the email",
            placeholder="I need to schedule a team meeting for next week to discuss the project timeline and deliverables...",
            help="Describe what you want to communicate"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            tone = st.selectbox(
                "🎭 Tone",
                ["professional", "friendly", "formal", "casual", "urgent"],
                help="Select the tone for your email"
            )
        
        with col2:
            constraints = st.text_input(
                "📏 Constraints (optional)",
                placeholder="Keep it under 100 words, mention deadline",
                help="Any specific requirements or limitations"
            )
        
        col_submit, col_new = st.columns(2)
        
        with col_submit:
            submitted = st.form_submit_button("🚀 Create Email Draft", use_container_width=True)
        
        with col_new:
            new_email = st.form_submit_button("📝 New Email", use_container_width=True)
        
        if new_email:
            # Reset session state for new email
            st.session_state.current_thread_id = None
            st.session_state.workflow_step = "start"
            st.session_state.current_draft = None
            st.session_state.current_subject = None
            st.rerun()
        
        if submitted:
            if not recipients.strip() or not purpose.strip():
                st.error("Please fill in both recipients and purpose fields.")
                return
            
            # Parse recipients
            recipient_list = [email.strip() for email in recipients.split('\n') if email.strip()]
            
            # Create email brief
            brief = EmailBrief(
                recipients=recipient_list,
                purpose=purpose,
                tone=tone,
                constraints=constraints if constraints else None
            )
            
            # Start workflow
            with st.spinner("Processing your request..."):
                thread_id = email_service.run_workflow(brief)
                st.session_state.current_thread_id = thread_id
                st.session_state.workflow_step = "awaiting_permission"
            
            st.success("Email requirements processed!")
            st.rerun()

def show_permission_form(email_service):
    """Show permission request form"""
    st.header("🔐 Permission Request")
    
    if st.session_state.current_thread_id:
        # Get current workflow state
        config = {"configurable": {"thread_id": st.session_state.current_thread_id}}
        try:
            current_state = email_service.workflow.get_state(config)
            context = current_state.values.get("context", "")
            
            st.info(context)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Approve - Create Draft", use_container_width=True):
                    with st.spinner("Creating email draft..."):
                        result = email_service.continue_workflow(
                            st.session_state.current_thread_id, 
                            "approved"
                        )
                        st.session_state.current_draft = result.get("draft")
                        st.session_state.current_subject = result.get("subject")
                        st.session_state.workflow_step = "awaiting_approval"
                    st.success("Draft created!")
                    st.rerun()
            
            with col2:
                if st.button("❌ Reject", use_container_width=True):
                    st.session_state.workflow_step = "start"
                    st.session_state.current_thread_id = None
                    st.info("Email creation cancelled.")
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error getting workflow state: {str(e)}")
            st.session_state.workflow_step = "start"

def show_approval_form(email_service):
    """Show draft approval form"""
    st.header("✏️ Review Email Draft")
    
    if st.session_state.current_draft:
        # Display the draft
        st.subheader("📄 Email Preview")
        
        # Subject
        if st.session_state.current_subject:
            st.text_input("Subject:", value=st.session_state.current_subject, disabled=True)
        
        # Body
        st.text_area(
            "Email Body:",
            value=st.session_state.current_draft,
            height=200,
            disabled=True
        )
        
        st.markdown("---")
        st.subheader("📝 Your Decision")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Approve & Send", use_container_width=True):
                with st.spinner("Preparing email for sending..."):
                    result = email_service.continue_workflow(
                        st.session_state.current_thread_id, 
                        "approved"
                    )
                    st.session_state.workflow_step = "completed"
                st.success("Email approved and prepared!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Request Changes", use_container_width=True):
                st.session_state.workflow_step = "request_changes"
                st.rerun()
        
        with col3:
            if st.button("❌ Reject Draft", use_container_width=True):
                st.session_state.workflow_step = "start"
                st.session_state.current_thread_id = None
                st.info("Draft rejected. Starting over.")
                st.rerun()
    
    # Handle change requests
    if st.session_state.workflow_step == "request_changes":
        st.subheader("💬 Request Changes")
        
        feedback = st.text_area(
            "What changes would you like?",
            placeholder="Please make the tone more formal and add a specific deadline...",
            help="Describe what you'd like to change about the draft"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Regenerate Draft", use_container_width=True):
                if feedback.strip():
                    with st.spinner("Creating improved draft..."):
                        result = email_service.continue_workflow(
                            st.session_state.current_thread_id, 
                            "needs_changes",
                            feedback
                        )
                        st.session_state.current_draft = result.get("draft")
                        st.session_state.workflow_step = "awaiting_approval"
                    st.success("New draft created!")
                    st.rerun()
                else:
                    st.warning("Please provide feedback for improvements.")
        
        with col2:
            if st.button("↩️ Back to Review", use_container_width=True):
                st.session_state.workflow_step = "awaiting_approval"
                st.rerun()

def show_completion_status(email_service):
    """Show completion status"""
    st.header("✅ Email Complete")
    
    if st.session_state.current_thread_id:
        # Get final email from database
        thread_data = email_service.get_thread_by_id(st.session_state.current_thread_id)
        
        if thread_data and thread_data.get('final_email'):
            final_email = json.loads(thread_data['final_email'])
            
            # Check if email was actually sent
            if thread_data.get('status') == 'sent':
                st.success("🎉 Your email has been sent successfully!")
            elif thread_data.get('status') == 'send_failed':
                st.error("❌ Email sending failed. See details below.")
            else:
                st.info("📧 Email is ready but not sent yet.")
            
            st.subheader("📧 Final Email")
            st.text_input("Subject:", value=final_email.get('subject', ''), disabled=True)
            st.text_area("Body:", value=final_email.get('body', ''), height=200, disabled=True)
            st.text_input("Recipients:", value=', '.join(final_email.get('recipients', [])), disabled=True)
            
            # Show send status
            if thread_data.get('status') == 'sent':
                st.success(f"✅ Sent successfully to {len(final_email.get('recipients', []))} recipient(s)")
            elif thread_data.get('status') == 'send_failed':
                st.error("❌ Email sending failed. Check your email configuration.")
                
                # Option to retry sending
                if st.button("🔄 Retry Sending", use_container_width=True):
                    with st.spinner("Retrying email send..."):
                        # Re-attempt sending
                        from backend.email_service import email_service as es
                        result = es.send_email(
                            subject=final_email.get('subject', ''),
                            body=final_email.get('body', ''),
                            recipients=final_email.get('recipients', [])
                        )
                        if result['success']:
                            email_service.update_email_status(
                                {'thread_id': st.session_state.current_thread_id}, 
                                'sent'
                            )
                            st.success("✅ Email sent successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ Still failed: {result['message']}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📧 Copy Email Content", use_container_width=True):
                if thread_data and thread_data.get('final_email'):
                    final_email = json.loads(thread_data['final_email'])
                    email_content = f"Subject: {final_email.get('subject', '')}\n\n{final_email.get('body', '')}"
                    st.code(email_content)
                    st.info("Email content displayed above. Copy manually from the code block.")
        
        with col2:
            if st.button("⚙️ Email Settings", use_container_width=True):
                st.session_state.show_email_settings = True
                st.rerun()
        
        with col3:
            if st.button("📝 Create Another Email", use_container_width=True):
                st.session_state.current_thread_id = None
                st.session_state.workflow_step = "start"
                st.session_state.current_draft = None
                st.session_state.current_subject = None
                st.rerun()
        
        # Email settings modal
        if st.session_state.get('show_email_settings', False):
            show_email_settings()

def show_email_settings():
    """Show email configuration settings"""
    st.subheader("⚙️ Email Configuration")
    
    # Test connection
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔗 Test Email Connection", use_container_width=True):
            with st.spinner("Testing email connection..."):
                from backend.email_service import email_service as es
                result = es.test_connection()
                if result['success']:
                    st.success(result['message'])
                else:
                    st.error(result['message'])
    
    with col2:
        if st.button("❌ Close Settings", use_container_width=True):
            st.session_state.show_email_settings = False
            st.rerun()
    
    # Show current configuration
    st.info("""
    **Email Configuration:**
    
    Make sure your `.env` file contains:
    ```
    EMAIL_USERNAME=your_email@gmail.com
    EMAIL_PASSWORD=your_app_password
    EMAIL_PROVIDER=gmail  # or outlook, yahoo, custom
    ```
    
    **For Gmail:**
    1. Enable 2-factor authentication
    2. Generate an App Password
    3. Use the App Password (not your regular password)
    
    **For Outlook:**
    - Use your regular Microsoft account credentials
    
    **For Yahoo:**
    - Use an App Password (similar to Gmail)
    """)
    
    # Provider selection (for future use)
    st.selectbox(
        "Email Provider",
        ["gmail", "outlook", "yahoo", "custom"],
        help="Select your email provider"
    )

def show_workflow_status():
    """Show current workflow status"""
    st.subheader("📊 Workflow Status")
    
    steps = [
        ("📝 Create Brief", "start"),
        ("🔐 Get Permission", "awaiting_permission"),
        ("✏️ Review Draft", "awaiting_approval"),
        ("✅ Complete", "completed")
    ]
    
    current_step = st.session_state.workflow_step
    
    for i, (step_name, step_key) in enumerate(steps):
        if step_key == current_step or (current_step == "loaded_from_history" and step_key == "start"):
            st.success(f"➡️ {step_name}")
        elif i < len(steps) - 1 and steps[i + 1][1] == current_step:
            st.success(f"✅ {step_name}")
        else:
            st.info(f"⏸️ {step_name}")
    
    if st.session_state.current_thread_id:
        st.markdown(f"**Thread ID:** `{st.session_state.current_thread_id[:8]}...`")
    
    # Show current draft info
    if st.session_state.current_draft:
        st.markdown("**Draft Status:** 📄 Draft Ready")
        with st.expander("Preview Current Draft"):
            st.text_area("", value=st.session_state.current_draft, height=100, disabled=True)

if __name__ == "__main__":
    main()