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
            },
            "maternity_leave": {
                "question": "What is the Maternity Leave policy?",
                "answer": """Maternity Leave Policy:

1. **Eligibility**:
   - Permanent Female Employees: Must have worked for at least 80 days in the past 12 months.
   - Contract Employees: Eligible for up to 12 weeks of leave (subject to contract terms); typically unpaid unless specified otherwise in your contract.

2. **Duration**: 
   - Standard: 26 Weeks (Max 8 weeks can be taken before the expected delivery date).
   - Miscarriage/Medical Termination: 6 weeks of paid leave immediately following the incident.

3. **Required Documents**:
   - Medical Certificate confirming pregnancy and Expected Date of Delivery (EDD).
   - For post-delivery extension: Birth Certificate.

4. **How to Apply**:
   - Apply at least 8 weeks in advance.
   - Go to 'Leave Management' -> 'Apply Leave' -> Select 'Maternity Leave'.
   - Upload the required medical documents.
"""
            },
            "paternity_leave": {
                "question": "What is the Paternity Leave policy?",
                "answer": """Paternity Leave Policy:

1. **Eligibility**:
   - Permanent Male Employees (probationers included).
   - Contract Employees: Eligible for 3 days of unpaid leave.

2. **Duration**: 
   - 10 Working Days.
   - Must be availed within 1 month of the child's birth.

3. **Required Documents**:
   - Child's Birth Certificate or Hospital Discharge Summary.

4. **How to Apply**:
   - Notify manager at least 1 week in advance if possible.
   - Go to 'Leave Management' -> 'Apply Leave' -> Select 'Paternity Leave'.
"""
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
            "maternity": ["maternity_leave"],
            "paternity": ["paternity_leave"],
            "pregnancy": ["maternity_leave"],
            "mother": ["maternity_leave"],
            "father": ["paternity_leave"],
            "baby": ["maternity_leave", "paternity_leave"],
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
ROLE: Attendance Pro Assistant

You are strictly an assistant for the "Attendance Pro" portal.
You are NOT a general AI.

SCOPE (ONLY answer if related to):
- Attendance records (check-in/out, late, early exit)
- Leave balances/history
- Shift schedules
- Overtime
- Payroll data derived from attendance
- Employee profiles stored in Attendance Pro
- Workforce/admin reports
- Company Data Snapshot (Admin mode)

OUT-OF-SCOPE RULE:
If a question is unrelated to Attendance Pro (programming, coding, general knowledge, jokes, personal advice, politics, etc.), respond ONLY with:
"I am designed to assist only with Attendance Pro portal-related information."
No explanation. No apology. No extra text.

DATA RULE:
Use only provided attendance data.
If data is missing, say:
"I don't have that specific information in my records."
Do not guess.

HR RULE:
Suggest contacting HR only for actions requiring manual HR intervention (e.g., bank account change).

-------------------------
ADMIN REPORT MODE (Role = Admin)

- Act as a Professional Workforce Data Analyst.
- Use ONLY the Company Data Snapshot.
- If greeted, immediately provide one key attendance insight.
- If asked for "Summary", give concise executive summary:
  attendance %, lateness trends, leave patterns, overtime, anomalies, positives.
- Refuse unrelated questions using the standard refusal sentence.
- Keep responses concise, professional, data-driven.
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
        return {
            "total_days": 20,
            "present": 18,
            "absent": 1,
            "late": 2,
            "percentage": 90.0
        }
    
    async def get_leave_balance(self, employee_id: str) -> Dict:
        """Get leave balance for employee"""
        return {
            "casual": 8,
            "sick": 7,
            "annual": 15
        }

    async def generate_official_letter(
        self,
        doc_type: str,
        employee: Employee,
        custom_instructions: str = "",
        base64_image: Optional[str] = None,
        pdf_text_content: Optional[str] = None,
        salary_breakdown_json: Optional[str] = None,
        company_name: str = "My Company",
        company_logo: Optional[str] = None,
        hr_signature: Optional[str] = None
    ) -> str:
        """Generate official HR letters using LLM"""
        
        # 1. Prepare Context
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Prepare Visual Assets
        if company_logo:
            header_html = f"<div style='text-align: center; margin-bottom: 20px;'><img src='{company_logo}' alt='Logo' style='height: 60px; vertical-align: middle; margin-right: 15px;' /><span style='font-size: 24px; font-weight: bold; vertical-align: middle; font-family: sans-serif;'>{company_name}</span></div>"
        else:
            header_html = f"<div style='text-align: center; margin-bottom: 20px;'><h1 style='margin: 0;'>{company_name}</h1></div>"

        if hr_signature:
            footer_html = f"<div style='margin-top: 50px;'>Sincerely,<br><b>HR Manager</b><br><img src='{hr_signature}' alt='Signature' style='height: 50px; margin: 5px 0;' /><br><b>{company_name}</b></div>"
        else:
            footer_html = f"<div style='margin-top: 50px;'>Sincerely,<br><b>HR Manager</b><br><br><br><b>{company_name}</b></div>"
        
        prompt = f"""
        You are an expert HR Manager at '{company_name}'.
        Your task is to write a professional, legally-sound, and formatted Official Letter.
        
        DETAILS:
        - Document Type: {doc_type.replace('_', ' ').title()}
        - Date: {current_date}
        - COMPANY NAME: {company_name} (See Override Rule below)
        - Employee Name: {employee.first_name} {employee.last_name}
        - Employee ID: {employee.employee_id}
        - Designation: {employee.designation}
        - Department: {employee.department}
        - Joining Date: {employee.joining_date}
        
        CUSTOM INSTRUCTIONS FROM HR:
        {custom_instructions}
        
        *** CRITICAL NAMING RULE ***: 
        If the 'CUSTOM INSTRUCTIONS' above explicitly mention a different company name (e.g. 'We are TData Solutions'), 
        you MUST use THAT name throughout the document instead of '{company_name}'.
        
        HTML STYLE GUIDE (CRITICAL):
        - Use a professional font (font-family: 'Times New Roman', serif) for the body.
        - Use `<br>` for spacing.
        - Use `<p style='text-align: justify;'>` for body paragraphs.
        - Wrap the entire content in a `<div style="padding: 40px; border: 1px solid #ddd; background: white;">`.
        
        MANDATORY HEADER & FOOTER (You MUST include these exactly as HTML):
        1. **HEADER**: Start the document with this exact HTML block (Do not alter):
           `{header_html}`
           
        2. **FOOTER**: End the document with this exact HTML block for the HR Signature:
           `{footer_html}`
           
        CONTENT STRUCTURE:
        1. **Insert HEADER Code** (as verified above).
        
        {
            """
        2. **Title**: "OFFER LETTER" (Bold, Underlined, Centered).
        3. **Date**: Top Right.
        4. **Salutation**: "Dear [Name],"
        5. **Body**: 
           - Opening: "We are pleased to invite you..."
           - Role Confirmation: "You have been selected for [Role]..."
           - CTC/Salary: Clear mention of numbers.
           - Terms: Probation, Leave, etc.
        6. **Closing**: "We look forward to..."
            """ if doc_type == "offer_letter" else
            
            """
        2. **Title**: "TO WHOM IT MAY CONCERN" or "EXPERIENCE CERTIFICATE" (Bold, Underlined, Centered).
        3. **Date**: Top Right.
        4. **Body**: 
           - Opening: "This is to certify that [Name] was employed with us..."
           - Tenure: "From [Joining Date] to [Current Date]..."
           - Role: "He/She served as [Designation]..."
           - Performance: "During his/her tenure, we found him/her to be..."
           - Standing: "He/She has shown great sincerity and dedication..."
        6. **Closing**: "We wish him/her all the best..."
            """ if doc_type == "experience_letter" else

            """
        2. **Title**: "SALARY REVISION LETTER" (Bold, Underlined, Centered).
        3. **Date**: Top Right.
        4. **Salutation**: "Dear [Name],"
        5. **Body**: 
           - Opening: "We are pleased to inform you that your salary has been revised..."
           - Effective Date: "This revision is effective from [Effective Date] (as mentioned in Custom Instructions)..."
           - New CTC/Salary: Clear mention of the new numbers.
           - Appreciation: "We appreciate your hard work and dedication..."
        6. **Closing**: "We look forward to your continued contribution..."
            """ if doc_type == "salary_revision" else

            """
        2. **Title**: "OFFICIAL LETTER" (Bold, Underlined, Centered).
        3. **Date**: Top Right.
        4. **Salutation**: "Dear [Name],"
        5. **Body**: Use the 'CUSTOM INSTRUCTIONS' provided to determine the content and purpose of this letter.
        6. **Closing**: Professional closing.
            """
        }
        
        7. **Insert FOOTER Code** (as verified above).
        """

        if salary_breakdown_json:
            try:
                salary_data = json.loads(salary_breakdown_json)
                if isinstance(salary_data, list) and len(salary_data) > 0:
                    table_html = "<table style='width:100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #000;'>"
                    table_html += "<tr style='background:#f0f0f0;'><th style='border:1px solid #000; padding:8px;'>Category</th><th style='border:1px solid #000; padding:8px; text-align:right;'>Amount (INR)</th></tr>"
                    total = 0
                    for row in salary_data:
                         amount = row.get('amount', '0')
                         try:
                             # Try to clean amount string for total calc
                             clean_amt = float(str(amount).replace(',','').replace(' ',''))
                             total += clean_amt
                         except:
                             pass
                         table_html += f"<tr><td style='border:1px solid #000; padding:8px;'>{row.get('category')}</td><td style='border:1px solid #000; padding:8px; text-align:right;'>{amount}</td></tr>"
                    
                    # Total Row
                    table_html += f"<tr style='font-weight:bold;'><td style='border:1px solid #000; padding:8px;'>TOTAL</td><td style='border:1px solid #000; padding:8px; text-align:right;'>{total:,.2f}</td></tr>"
                    table_html += "</table>"
                    
                    prompt += f"""
                    
                    MANDATORY SALARY BREAKDOWN TABLE:
                    Please INSERT the following HTML Table explicitly into the document where the Salary/Compensation is mentioned. 
                    
                    DISPLAY RULE (CRITICAL):
                    - INSERT the table below.
                    - Do NOT list the salary components (Basic, HRA, etc.) or amounts in the paragraph text.
                    - Instead, simply write: "The detailed salary structure is annexed below:" and then show the table.
                    
                    {table_html}
                    """
            except Exception as e:
                print(f"Error parsing salary json: {e}")

        if pdf_text_content:
            prompt += f"""
            
            --------------------------------------------------
            REFERENCE TEMPLATE (FROM UPLOADED PDF):
            {pdf_text_content[:4000]} # Limit characters context
            --------------------------------------------------
            
            CRITICAL INSTRUCTIONS FOR TEMPLATE USAGE:
            1. **Analyze the Structure**: The text above is a raw extraction from a PDF directly. It may contain sample names (e.g., "Rahul", "Employee Name") and sample amounts.
            2. **IDENTIFY & REPLACE**: You must identify the 'Sample Data' in the template and REPLACE it with the actual Employee Details provided at the top of this prompt.
               - IF the template reads "Dear Rahul", CHANGE it to "Dear {employee.first_name} {employee.last_name}".
               - IF the template reads "Salary: 10 LPA", CHANGE it to the salary mentioned in 'CUSTOM INSTRUCTIONS'.
               - IF the template has an old date, CHANGE it to "{current_date}".
               - IF the template mentions "Saigo Systems" or any other company name, CHANGE it to the Target Company Name found in 'DETAILS' (or Overridden by instructions).
            3. **RESTORE FORMATTING**: Raw PDF text loses alignment. You MUST restore it using HTML:
               - **USE THE MANDATORY HEADER defined above** instead of the PDF's text header.
               - Right align dates.
               - Justify paragraphs.
               - Use <b>Table</b> tags if the template implies a table structure (e.g. for Salary Breakdown).
               - **USE THE MANDATORY FOOTER defined above** for the signature block.
            4. **IGNORE JUNK**: Ignore page numbers or header/footer artifacts like "Page 1 of 2".
            """

        if base64_image:
             prompt += "\n\nIMPORTANT: I have attached an image of a template/sample letter. PLEASE FOLLOW THE STRUCTURE, TONE, AND FORMATTING of this image exactly, but strictly replace the placeholder details with the Employee Details provided above."

        messages = [
            {"role": "system", "content": "You are a professional HR Document Generator. Return ONLY valid HTML code. Do NOT wrap in markdown code blocks."}
        ]

        if base64_image:
            # Vision API format
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            })
        else:
            # Text-only format
            messages.append({"role": "user", "content": prompt})

        # Call LLM
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2500
            )
            content = response.choices[0].message.content
            
            # Post-processing to remove markdown
            content = content.replace("```html", "").replace("```", "").strip()
            return content
            
        except Exception as e:
            print(f"Error generating document: {e}")
            return f"<p style='color:red;'>Error generating document: {str(e)}</p>"


# Global chatbot instance
chatbot_service = ChatbotService()
