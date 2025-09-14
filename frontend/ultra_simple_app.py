# frontend/ultra_simple_app.py
import streamlit as st
import sys
import os
import json
import uuid
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, backend_dir)

from ultra_simple_backend import UltraSimpleEmailService, EmailBrief

# Initialize the service
@st.cache_resource
def get_email_service():
    try:
        return UltraSimpleEmailService()
    except ValueError as e:
        st.error(f"Configuration Error: {e}")
        st.info("Make sure GOOGLE_API_KEY is set in your .env file")
        st.stop()

def main():
    st.set_page_config(
        page_title="AI Email Drafting Assistant",
        page_icon="📧",
        layout="wide"
    )
    
    st.title("📧 AI Email Drafting Assistant")
    st.markdown("*Ultra Simple Version - Direct Google Gemini API*")
    st.markdown("---")
    
    email_service = get_email_service()
    
    # Initialize session state
    if "current_step" not in st.session_state:
        st.session_state.current_step = "create"
    if "current_draft" not in st.session_state:
        st.session_state.current_draft = None
    if "current_subject" not in st.session_state:
        st.session_state.current_subject = None
    if "current_brief" not in st.session_state:
        st.session_state.current_brief = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    
    # Sidebar for history
    with st.sidebar:
        st.header("📁 Email History")
        
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
        
        history = email_service.get_email_history()
        
        if history:
            for email in history[:5]:  # Show last 5 emails
                with st.expander(f"📧 {email['subject'][:25]}..." if email['subject'] else f"📧 {email['purpose'][:25]}..."):
                    st.write(f"**To:** {json.loads(email['recipients'])}")
                    st.write(f"**Purpose:** {email['purpose'][:50]}...")
                    st.write(f"**Status:** {email['status']}")
                    
                    if st.button(f"Load", key=f"load_{email['id']}", use_container_width=True):
                        st.session_state.current_draft = email['draft']
                        st.session_state.current_subject = email['subject']
                        st.session_state.thread_id = email['thread_id']
                        st.session_state.current_step = "review"
                        st.rerun()
        else:
            st.info("No history yet")
        
        # Email settings
        st.markdown("---")
        st.subheader("⚙️ Email Settings")
        if st.button("🔗 Test Connection", use_container_width=True):
            test_email_connection()
    
    # Main content
    if st.session_state.current_step == "create":
        show_create_form(email_service)
    elif st.session_state.current_step == "review":
        show_review_form(email_service)
    elif st.session_state.current_step == "sent":
        show_sent_status()

def show_create_form(email_service):
    """Show email creation form"""
    st.header("✉️ Create New Email")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        recipients = st.text_area(
            "📬 Recipients (one per line)",
            placeholder="john.doe@company.com\njane.smith@company.com",
            height=80
        )
        
        purpose = st.text_area(
            "🎯 What do you want to communicate?",
            placeholder="I need to schedule a team meeting for next week to discuss the project timeline...",
            height=120
        )
    
    with col2:
        tone = st.selectbox(
            "🎭 Tone", 
            ["professional", "friendly", "formal", "casual", "urgent"],
            help="How should the email sound?"
        )
        
        constraints = st.text_input(
            "📏 Special requests (optional)", 
            placeholder="Keep it short, mention deadline, etc."
        )
    
    col_create, col_reset = st.columns(2)
    
    with col_create:
        if st.button("🚀 Create Email Draft", use_container_width=True, type="primary"):
            if not recipients.strip():
                st.error("Please enter at least one recipient")
                return
            if not purpose.strip():
                st.error("Please describe the email purpose")
                return
            
            recipient_list = [email.strip() for email in recipients.split('\n') if email.strip()]
            
            brief = EmailBrief(
                recipients=recipient_list,
                purpose=purpose,
                tone=tone,
                constraints=constraints if constraints else None
            )
            
            with st.spinner("🤖 AI is creating your email draft..."):
                try:
                    # Process requirements
                    req_result = email_service.process_requirements(brief)
                    
                    # Create draft
                    draft_result = email_service.create_draft(brief, req_result["context"], req_result["subject"])
                    
                    # Save to session
                    st.session_state.current_brief = brief
                    st.session_state.current_draft = draft_result["draft"]
                    st.session_state.current_subject = draft_result["subject"]
                    st.session_state.current_step = "review"
                    
                    # Save to database
                    email_service.save_email(
                        st.session_state.thread_id, 
                        brief, 
                        draft_result["subject"], 
                        draft_result["draft"]
                    )
                    
                    st.success("✅ Draft created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error creating draft: {str(e)}")
    
    with col_reset:
        if st.button("🔄 Clear Form", use_container_width=True):
            st.session_state.current_step = "create"
            st.session_state.current_draft = None
            st.session_state.current_subject = None
            st.session_state.current_brief = None
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

def show_review_form(email_service):
    """Show draft review form"""
    st.header("✏️ Review & Edit Your Email")
    
    if not st.session_state.current_draft:
        st.error("No draft found. Please create a new email.")
        if st.button("← Back to Create"):
            st.session_state.current_step = "create"
            st.rerun()
        return
    
    # Email preview and editing
    st.subheader("📄 Email Content")
    
    # Editable subject
    new_subject = st.text_input(
        "✏️ Subject Line:",
        value=st.session_state.current_subject or "",
        placeholder="Enter subject line..."
    )
    st.session_state.current_subject = new_subject
    
    # Editable body
    new_draft = st.text_area(
        "✏️ Email Body:",
        value=st.session_state.current_draft,
        height=250,
        help="You can edit the email content directly"
    )
    st.session_state.current_draft = new_draft
    
    # Preview
    with st.expander("👀 Preview Email"):
        st.markdown("**Subject:** " + (new_subject or "*No subject*"))
        st.markdown("**To:** " + ", ".join(st.session_state.current_brief.recipients))
        st.markdown("**Body:**")
        st.markdown(new_draft)
    
    st.markdown("---")
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📧 Send Email", use_container_width=True, type="primary"):
            if not new_subject.strip():
                st.error("Please add a subject line")
                return
            if not new_draft.strip():
                st.error("Email body cannot be empty")
                return
            
            with st.spinner("📤 Sending email..."):
                try:
                    brief = st.session_state.current_brief
                    result = email_service.send_email(
                        new_subject,
                        new_draft,
                        brief.recipients
                    )
                    
                    if result["success"]:
                        email_service.update_email_status(
                            st.session_state.thread_id, 
                            "sent",
                            {
                                "subject": new_subject,
                                "body": new_draft,
                                "recipients": brief.recipients
                            }
                        )
                        st.session_state.current_step = "sent"
                        st.success("✅ " + result["message"])
                        st.rerun()
                    else:
                        st.error("❌ " + result["message"])
                
                except Exception as e:
                    st.error(f"Error sending email: {str(e)}")
    
    with col2:
        if st.button("✨ Improve Draft", use_container_width=True):
            st.session_state.show_improvement = True
            st.rerun()
    
    with col3:
        if st.button("💾 Save Draft", use_container_width=True):
            try:
                brief = st.session_state.current_brief
                email_service.save_email(
                    st.session_state.thread_id, 
                    brief, 
                    new_subject, 
                    new_draft,
                    "saved"
                )
                st.success("💾 Draft saved!")
            except Exception as e:
                st.error(f"Error saving: {str(e)}")
    
    with col4:
        if st.button("← Start Over", use_container_width=True):
            st.session_state.current_step = "create"
            st.session_state.current_draft = None
            st.session_state.current_subject = None
            st.session_state.current_brief = None
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
    
    # Improvement section
    if st.session_state.get('show_improvement', False):
        st.markdown("---")
        st.subheader("✨ Improve Your Draft")
        
        feedback = st.text_area(
            "What would you like to change?",
            placeholder="Examples:\n• Make it more formal\n• Add a specific deadline\n• Make it shorter\n• Change the tone to be more friendly",
            height=80
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Apply Improvements", use_container_width=True):
                if not feedback.strip():
                    st.warning("Please describe what you'd like to improve")
                    return
                
                with st.spinner("🤖 Improving your draft..."):
                    try:
                        brief = st.session_state.current_brief
                        improved = email_service.improve_draft(
                            st.session_state.current_draft,
                            feedback,
                            brief
                        )
                        st.session_state.current_draft = improved
                        st.session_state.show_improvement = False
                        st.success("✅ Draft improved!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error improving draft: {str(e)}")
        
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_improvement = False
                st.rerun()

def show_sent_status():
    """Show sent email confirmation"""
    st.header("✅ Email Sent Successfully!")
    st.success("🎉 Your email has been delivered!")
    
    # Show sent email details
    if st.session_state.current_brief:
        brief = st.session_state.current_brief
        st.info(f"📧 Sent to {len(brief.recipients)} recipient(s): {', '.join(brief.recipients)}")
    
    with st.expander("📄 View Sent Email"):
        st.text_input("Subject:", value=st.session_state.current_subject or "", disabled=True)
        st.text_area("Body:", value=st.session_state.current_draft or "", height=200, disabled=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 Create Another Email", use_container_width=True, type="primary"):
            st.session_state.current_step = "create"
            st.session_state.current_draft = None
            st.session_state.current_subject = None
            st.session_state.current_brief = None
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
    
    with col2:
        if st.button("📋 View History", use_container_width=True):
            st.session_state.current_step = "create"
            st.rerun()

def test_email_connection():
    """Test email connection"""
    try:
        from email_service import email_service as es
        result = es.test_connection()
        if result['success']:
            st.success("✅ " + result['message'])
        else:
            st.error("❌ " + result['message'])
            st.info("""
            **Email Setup Required:**
            1. Create `backend/email_service.py`
            2. Add to `.env`:
            ```
            EMAIL_USERNAME=your_email@gmail.com
            EMAIL_PASSWORD=your_app_password
            EMAIL_PROVIDER=gmail
            ```
            """)
    except ImportError:
        st.error("❌ Email service not configured")
        st.info("Create `backend/email_service.py` file with your email settings")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()