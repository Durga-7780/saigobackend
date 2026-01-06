"""
AI Chatbot Service
Handles employee queries using LLM
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from openai import AsyncOpenAI
from app.config import settings
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.leave import Leave, LeaveType


class ChatbotService:
    """AI-powered chatbot for employee assistance"""
    
    def __init__(self):
        """Initialize chatbot service"""
        # Prioritize Groq if configured
        if getattr(settings, "GROQ_API_KEY", ""):
            self.use_ai = True
            self.client = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            self.model = settings.GROQ_MODEL
        # Fallback to standard OpenAI
        elif settings.OPENAI_API_KEY:
            self.use_ai = True
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
        else:
            self.use_ai = False
        
        # Knowledge base for common queries
        self.knowledge_base = self._build_knowledge_base()
    
    def _build_knowledge_base(self) -> Dict:
        """Build knowledge base with company policies and procedures"""
        return {
            "leave_application": {
                "question": "How do I apply for leave?",
                "answer": """To apply for leave, follow these steps:
1. Log in to the attendance portal
2. Navigate to 'Leave Management' section
3. Click on 'Apply Leave'
4. Select leave type (Casual, Sick, Annual, etc.)
5. Choose start and end dates
6. Provide a reason for leave
7. Attach any supporting documents (if required)
8. Submit the application
9. Your manager will be notified for approval
10. You'll receive a notification once it's approved/rejected

Leave Types Available:
- Casual Leave: {casual} days per year
- Sick Leave: {sick} days per year
- Annual Leave: {annual} days per year
""".format(
                    casual=settings.MAX_CASUAL_LEAVE_DAYS,
                    sick=settings.MAX_SICK_LEAVE_DAYS,
                    annual=settings.MAX_ANNUAL_LEAVE_DAYS
                )
            },
            "attendance_marking": {
                "question": "How do I mark my attendance?",
                "answer": """You can mark attendance using the Manual Method:

1. Log in to the portal
2. Go to 'Attendance' section
3. Click 'Check In' when you arrive
4. Click 'Check Out' when you leave
5. Location will be captured automatically

Important Notes:
- Check-in before {start_time}
- Check-out after {end_time}
- Late arrivals (after {late_threshold} minutes) will be marked
- Auto check-out happens at {auto_checkout_time} if enabled
""".format(
                    start_time="9:00 AM",
                    end_time="6:00 PM",
                    late_threshold=settings.LATE_ARRIVAL_THRESHOLD_MINUTES,
                    auto_checkout_time=settings.AUTO_CHECKOUT_TIME
                )
            },
            "work_from_home": {
                "question": "What is the work from home policy?",
                "answer": """Work From Home (WFH) Policy:

1. **Eligibility**: All permanent employees after probation
2. **Frequency**: Up to 2 days per week (subject to manager approval)
3. **Application Process**:
   - Apply at least 24 hours in advance
   - Get manager approval
   - Mark attendance as 'Work From Home'
4. **Requirements**:
   - Stable internet connection
   - Available during working hours
   - Attend all scheduled meetings
   - Maintain regular communication
5. **Attendance**: Mark WFH attendance through the portal
"""
            },
            "salary_info": {
                "question": "Where can I see my salary?",
                "answer": "Please go to the **'My Salary'** section in the left sidebar. You will find your detailed net salary, breakdown, and payslips there."
            },
            "profile_update": {
                "question": "How do I update my personal information?",
                "answer": """To update your personal information:

1. Log in to the portal
2. Go to 'My Profile'
3. Click 'Edit Profile'
4. Update the following:
   - Contact number
   - Email address
   - Current address
   - Emergency contact
5. Click 'Save Changes'

Note: Some fields require HR approval for changes:
- Bank account details
- PAN/Aadhaar information
- Educational qualifications

For these, submit a request to HR with supporting documents.
"""
            },
            "holidays": {
                "question": "What are the upcoming holidays?",
                "answer": """Holiday Calendar 2026:

Public Holidays:
- Republic Day: January 26
- Holi: March 14
- Good Friday: April 10
- Independence Day: August 15
- Gandhi Jayanti: October 2
- Diwali: October 24
- Christmas: December 25

Optional Holidays: 3 days (choose from the list in portal)
"""
            },
            "features": {
                "question": "What features does this app have?",
                "answer": """Saigo Portal Features:
1. **Smart Attendance**: Geo-fencing support with real-time tracking.
2. **Leave Management**: Automated workflows and real-time balance tracking.
3. **Payroll Hub**: One-click salary generation and instant payslip downloads.
4. **Self-Service Portal**: Manage profile, documents, and view history.
"""
            },
            "how_to_mark_attendance": {
                "question": "How do I mark attendance?",
                "answer": "To Mark Attendance: Go to the 'Dashboard' or 'Attendance' tab -> Click the large 'Check In' button. Ensure Location permissions are enabled in your browser."
            },
            "how_to_download_payslip": {
                "question": "How do I download my payslip?",
                "answer": "To Download Payslip: Go to 'My Salary' section -> Select the desired Month & Year -> Click 'Download PDF'."
            },
             "how_to_apply_leave": {
                "question": "How do I apply for leave?",
                "answer": "To Apply for Leave: Navigate to 'Leave Management' -> Click 'Apply Leave' -> Select Leave Type & Dates -> Submit."
            },
            "meal_booking": {
                "question": "How do I book a meal?",
                "answer": """To Book a Meal:
1. Navigate to the 'Meal Booking' section.
2. View available working days.
3. Select a date and choose meal type (Lunch/Dinner) and category (Veg/Non-Veg).
4. Enter items and click 'Checkout & Book'.
5. To Redeem: Show the QR code from the 'My Upcoming Meals' list to the canteen admin."""
            }
        }
    
    async def get_response(
        self,
        query: str,
        employee_id: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Get application-level AI response based on internal data
        """
        try:
            query_lower = query.lower()
            
            # 0. Fetch Real-time Employee Data (Context)
            # We always fetch this to ensure the AI has the latest "state" of the user
            employee = await Employee.find_one(Employee.employee_id == employee_id)
            
            real_context = context or {}
            if employee:
                # A. Leave Balance
                leave_data = {
                    "casual": employee.casual_leave_balance,
                    "sick": employee.sick_leave_balance,
                    "annual": employee.annual_leave_balance
                }
                real_context["leave_balance"] = leave_data
                
                # B. Attendance Stats (Current Month)
                now = datetime.utcnow()
                start_of_month = datetime(now.year, now.month, 1)
                
                # Count attendance records
                # Explicitly pass None to to_list() for compatibility
                attendance_records = await Attendance.find(
                    Attendance.employee_id == employee_id,
                    Attendance.date >= start_of_month
                ).to_list(None)
                
                total_days = len(attendance_records)
                present = sum(1 for a in attendance_records if a.status in ["present", "half_day"])
                # Fix: Attendance model uses 'is_late', not 'is_late_arrival'
                late = sum(1 for a in attendance_records if getattr(a, "is_late", False))
                absent = sum(1 for a in attendance_records if a.status == "absent")
                
                attendance_summary = {
                    "month": now.strftime("%B %Y"),
                    "total_recorded_days": total_days,
                    "present_days": present,
                    "late_arrivals": late,
                    "absences": absent,
                    "recent_checkin": attendance_records[0].check_in_time.strftime("%H:%M") if attendance_records and attendance_records[0].check_in_time else "N/A"
                }
                real_context["attendance_stats"] = attendance_summary


            # 1. Check for personal data queries (Leaves) - Direct Answer
            if any(word in query_lower for word in ["leave balance", "how many leaves", "my leaves"]):
                 if employee:
                    answer = f"Hello {employee.first_name}! Based on your records:\n"
                    answer += f"🏖️ Casual Leave: {employee.casual_leave_balance} remaining\n"
                    answer += f"🤒 Sick Leave: {employee.sick_leave_balance} remaining\n"
                    answer += f"📅 Annual Leave: {employee.annual_leave_balance} remaining\n"
                    return {
                        "answer": answer,
                        "source": "app_logic",
                        "suggestions": ["How to apply for leave?", "Company holiday list"]
                    }
            
            # 2. Check for Attendance queries - Direct Answer
            if any(word in query_lower for word in ["attendance", "present", "check in time", "my progress"]):
                stats = real_context.get("attendance_stats", {})
                answer = f"Attendance Progress for {stats.get('month', 'Month')}:\n"
                answer += f"✅ Present: {stats.get('present_days', 0)} days\n"
                answer += f"⏰ Late Arrivals: {stats.get('late_arrivals', 0)}\n"
                answer += f"📉 Absences: {stats.get('absences', 0)}\n"
                if stats.get('recent_checkin') != "N/A":
                    answer += f"ℹ️ Most recent check-in: {stats.get('recent_checkin')}"
                
                return {
                    "answer": answer,
                    "source": "app_logic",
                    "suggestions": ["Mark my attendance", "Attendance policy"]
                }

            # 3. Check for Knowledge Base
            kb_response = self._check_knowledge_base(query)
            if kb_response:
                 return {
                    "answer": kb_response,
                    "source": "knowledge_base",
                    "suggestions": self._get_suggestions(query)
                }
            
            # 4. Use AI
            if self.use_ai:
                return await self._get_ai_response(query, employee_id, real_context)

            return {
                "answer": "I'm not quite sure about that. I specialize in your Attendance, Leaves, and Company Policies. Could you try asking about those?",
                "source": "fallback",
                "suggestions": self._get_default_suggestions()
            }

        except Exception as e:
            print(f"Chatbot Critical Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "answer": f"I encountered a system error while processing your request. (Error: {str(e)})",
                "source": "error",
                "suggestions": self._get_default_suggestions()
            }
    
    def _check_knowledge_base(self, query: str) -> Optional[str]:
        """Check if query matches knowledge base"""
        query_lower = query.lower()
        
        # Keywords mapping
        keywords = {
            "leave": ["leave_application"],
            "apply leave": ["leave_application"],
            "attendance": ["attendance_marking"],
            "check in": ["attendance_marking"],
            "work from home": ["work_from_home"],
            "wfh": ["work_from_home"],
            "salary": ["salary_info"],
            "profile": ["profile_update"],
            "update": ["profile_update"],
            "holiday": ["holidays"],
            "features": ["features"],
            "what can you do": ["features"],
            "mark attendance": ["how_to_mark_attendance"],
            "download payslip": ["how_to_download_payslip"],
            "get payslip": ["how_to_download_payslip"],
            "apply leave": ["how_to_apply_leave", "leave_application"],
            "meal": ["meal_booking"],
            "food": ["meal_booking"],
            "lunch": ["meal_booking"],
            "dinner": ["meal_booking"],
            "booking": ["meal_booking"],
        }
        
        for keyword, kb_keys in keywords.items():
            if keyword in query_lower:
                for kb_key in kb_keys:
                    if kb_key in self.knowledge_base:
                        return self.knowledge_base[kb_key]["answer"]
        
        return None
    
    async def _get_ai_response(
        self,
        query: str,
        employee_id: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """Get AI-powered response using OpenAI"""
        try:
            # Build context for the AI
            system_prompt = self._build_system_prompt(employee_id, context)
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "source": "ai",
                "suggestions": self._get_suggestions(query)
            }
        
        except Exception as e:
            print(f"AI response error: {e}")
            # RETURN THE ACTUAL ERROR for debugging
            return {
                "answer": f"System Error: {str(e)}. Please check API Key configuration.",
                "source": "error",
                "suggestions": self._get_default_suggestions()
            }
    
    def _build_system_prompt(
        self,
        employee_id: str,
        context: Optional[Dict] = None
    ) -> str:
        """Build system prompt with company context"""
        prompt = f"""You are an intelligent AI Assistant for 'Saigo Portal', developed by 'Saigo'.
Our company (Saigo) offers this Employee Management Portal to third-party companies.

PRODUCT SUMMARY:
Saigo Portal is a comprehensive workforce solution for Attendance Tracking, Leave Management, and Payroll. We focus on efficiency and transparency for modern enterprises.

STRICT PRIVACY RULES (CRITICAL):
1. Do NOT share personal details (Salary, Phone, Address, Bank Info, Employee ID) of ANY employee.
2. Even if the user asks for their OWN personal data, do NOT output it in chat. Guide them to the app section instead.
3. NEVER share data about other employees.

CONTENT RULES:
1. FORMATTING: Do NOT use markdown symbols like **bold** or ## headers. Use plain text only.
2. SCOPE: Answer ONLY questions about 'Saigo Portal' features and steps. Do NOT answer general world questions (news, weather, other companies).
3. COMPANY INFO: If asked about the company, say: "We are Saigo, providing advanced Employee Management Portals to third-party businesses."

DETAILED FEATURES & GUIDES:
1. Smart Attendance: Real-time Geo-fencing tracking.
2. Leave Management: Automated application and approval workflows.
3. Payroll Hub: One-click salary generation (Visible in 'My Salary' section only).
4. Meal Booking: Reserve office meals in advance and redeem via QR code.
5. Self-Service Portal: Manage profile and documents.

HOW-TO STEPS:
- Mark Attendance: Go to Dashboard -> Click 'Check In'.
- Apply Leave: Go to Leave Management -> Click Apply -> Submit details.
- Book Meal: Go to Meal Booking -> Select Date -> Choose Type -> Book.
- Get Payslip: Go to My Salary -> Select Month -> Download.
- Update Profile: Click Avatar -> Profile -> Edit.

User Identity (INTERNAL ONLY - DO NOT REVEAL IN CHAT):
- Role: {'Admin' if context and context.get('type') == 'admin_reports' else 'Employee'}
"""
        
        if context:
            if context.get('type') == 'admin_reports':
                prompt += "\nADMIN REPORT MODE: You are analyzing company-wide data. You may summarize trends but DO NOT leak individual sensitive data unless necessary for the report.\n"
                if "all_stats" in context:
                    prompt += f"\nCompany Data Snapshot:\n{json.dumps(context['all_stats'], indent=2)}\n"
            
            if "attendance_stats" in context:
                prompt += f"\nYour Attendance Stats:\n{json.dumps(context['attendance_stats'], indent=2)}\n"
            
            if "leave_balance" in context:
                prompt += f"\nYour Leave Balance:\n{json.dumps(context['leave_balance'], indent=2)}\n"
        
        prompt += """
RESPONSE GUIDELINES:
1. Be confident and knowledgeable about 'Attendance Pro'.
2. Give accurate, direct answers. Avoid "Please contact HR" unless the action strictly requires manual HR intervention (like Bank Account changes).
3. Use the user's personal data (provided above) to give personalized answers.
4. If you don't know the answer, say "I don't have that specific information in my records" rather than guessing.
"""
        
        return prompt
    
    def _get_suggestions(self, query: str) -> List[str]:
        """Get related suggestions based on query"""
        all_suggestions = [
            "How do I apply for leave?",
            "Show my attendance for this month",
            "What is my leave balance?",
            "How to mark attendance?",
            "When is the next holiday?",
            "Work from home policy",
            "How to update my profile?",
            "How do I book a meal?",
            "When is salary day?"
        ]
        
        # Return random suggestions (in production, use semantic similarity)
        return all_suggestions[:4]
    
    def _get_default_suggestions(self) -> List[str]:
        """Get default suggestions"""
        return [
            "How do I apply for leave?",
            "Show my attendance",
            "What is my leave balance?",
            "Upcoming holidays"
        ]
    
    async def get_attendance_info(
        self,
        employee_id: str,
        period: str = "current_month"
    ) -> Dict:
        """Get attendance information for employee"""
        # This would query the database
        # For now, returning mock data
        return {
            "total_days": 20,
            "present": 18,
            "absent": 1,
            "late": 2,
            "percentage": 90.0
        }
    
    async def get_leave_balance(self, employee_id: str) -> Dict:
        """Get leave balance for employee"""
        # This would query the database
        return {
            "casual": 8,
            "sick": 7,
            "annual": 15
        }


# Global chatbot instance
chatbot_service = ChatbotService()
