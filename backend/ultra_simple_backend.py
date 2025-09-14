# backend/ultra_simple_backend.py
# Ultra simplified version using direct Google Gemini API - no LangChain dependencies

import os
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlite3
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailBrief:
    def __init__(self, recipients: List[str], purpose: str, tone: str = "professional", constraints: Optional[str] = None):
        self.recipients = recipients
        self.purpose = purpose
        self.tone = tone
        self.constraints = constraints

class UltraSimpleEmailService:
    """Ultra simple email drafting service using direct Google Gemini API"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        
        # Setup database
        self.db_path = Path("email_drafting.db")
        self.setup_database()
    
    def setup_database(self):
        """Setup SQLite database for storing email drafts and history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_history (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                recipients TEXT,
                subject TEXT,
                purpose TEXT,
                tone TEXT,
                draft TEXT,
                final_email TEXT,
                status TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def call_gemini_api(self, prompt: str) -> str:
        """Call Google Gemini API directly"""
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            
            if 'candidates' in result and len(result['candidates']) > 0:
                if 'content' in result['candidates'][0]:
                    if 'parts' in result['candidates'][0]['content']:
                        return result['candidates'][0]['content']['parts'][0]['text']
            
            return "Error: Could not generate response"
            
        except requests.exceptions.RequestException as e:
            return f"API Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def process_requirements(self, brief: EmailBrief) -> Dict[str, Any]:
        """Process email requirements and generate context"""
        prompt = f"""
        You are an assistant that prepares email drafting requirements.
        
        Here is the initial brief:
        Recipients: {brief.recipients}
        Purpose: {brief.purpose}
        Tone: {brief.tone}
        Constraints: {brief.constraints}
        
        Tasks:
        1. Rephrase the purpose in 4-5 clear sentences.
        2. Suggest a subject line that matches the purpose and tone.
        3. List any constraints as actionable rules (max words, tone, etc.).
        4. Output everything in JSON format with keys: "purpose", "subject_suggestion", "constraints".
        """
        
        response = self.call_gemini_api(prompt)
        
        # Try to parse JSON from response
        try:
            # Clean the response to extract JSON
            if '```json' in response:
                json_start = response.find('```json') + 7
                json_end = response.find('```', json_start)
                json_str = response[json_start:json_end].strip()
            elif '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
            else:
                json_str = response
            
            parsed_context = json.loads(json_str)
            subject = parsed_context.get("subject_suggestion", "")
        except:
            subject = f"Regarding: {brief.purpose[:50]}..."
            parsed_context = {"purpose": brief.purpose, "subject_suggestion": subject}
        
        return {
            "context": json.dumps(parsed_context),
            "subject": subject
        }
    
    def create_draft(self, brief: EmailBrief, context: str, subject: str) -> Dict[str, Any]:
        """Create email draft"""
        prompt = f"""
        Act as a professional email writer. Generate a polite and professional email draft.
        
        Context: {context}
        Purpose: {brief.purpose}
        Recipients: {', '.join(brief.recipients)}
        Tone: {brief.tone}
        Subject: {subject}
        Constraints: {brief.constraints or 'None'}
        
        Requirements:
        - Keep it concise (≤150 words for body).
        - Maintain a {brief.tone} tone.
        - Include only one clear call-to-action.
        - End with an appropriate signature placeholder.
        - Return only the email body (no subject line).
        - Do not include any formatting markers or extra text.
        """
        
        draft_content = self.call_gemini_api(prompt)
        
        return {
            "draft": draft_content.strip(),
            "subject": subject
        }
    
    def improve_draft(self, original_draft: str, feedback: str, brief: EmailBrief) -> str:
        """Improve draft based on feedback"""
        prompt = f"""
        You are helping to improve an email draft based on user feedback.
        
        Original Draft: {original_draft}
        User Feedback: {feedback}
        
        Email Purpose: {brief.purpose}
        Tone: {brief.tone}
        Recipients: {', '.join(brief.recipients)}
        
        Please create an improved version that addresses the feedback while maintaining the professional tone and purpose.
        Return only the improved email body with no extra formatting or explanations.
        """
        
        response = self.call_gemini_api(prompt)
        return response.strip()
    
    def send_email(self, subject: str, body: str, recipients: List[str]) -> Dict[str, Any]:
        """Send email using email service"""
        try:
            from email_service import email_service
            
            result = email_service.send_email(
                subject=subject,
                body=body,
                recipients=recipients
            )
            
            return result
        except ImportError:
            return {
                "success": False,
                "message": "Email service not available. Create email_service.py file with your email configuration."
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error sending email: {str(e)}"
            }
    
    def save_email(self, thread_id: str, brief: EmailBrief, subject: str, draft: str, status: str = "draft") -> None:
        """Save email to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO email_history 
            (id, thread_id, recipients, subject, purpose, tone, draft, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            thread_id,
            thread_id,
            json.dumps(brief.recipients),
            subject,
            brief.purpose,
            brief.tone,
            draft,
            status,
            datetime.now(),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def update_email_status(self, thread_id: str, status: str, final_email: dict = None):
        """Update email status in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        final_email_json = json.dumps(final_email) if final_email else None
        
        cursor.execute('''
            UPDATE email_history 
            SET status = ?, final_email = ?, updated_at = ?
            WHERE thread_id = ?
        ''', (status, final_email_json, datetime.now(), thread_id))
        
        conn.commit()
        conn.close()
    
    def get_email_history(self) -> List[Dict]:
        """Get email history from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM email_history 
            ORDER BY created_at DESC
        ''')
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_thread_by_id(self, thread_id: str) -> Optional[Dict]:
        """Get specific thread by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM email_history 
            WHERE thread_id = ?
        ''', (thread_id,))
        
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            result = dict(zip(columns, row))
            conn.close()
            return result
        
        conn.close()
        return None

# Initialize the service
email_service = UltraSimpleEmailService()