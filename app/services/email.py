import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from app.config import settings

class EmailService:
    """Service for handling automated email notifications"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        
        # Path to templates
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "emails")

    def _get_template(self, template_name):
        """Read an HTML template from file"""
        try:
            with open(os.path.join(self.template_dir, f"{template_name}.html"), "r") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading email template {template_name}: {e}")
            return None

    async def send_email(self, to_email, subject, html_content):
        """General method to send an email (Mocked if no credentials)"""
        if not self.smtp_user or not self.smtp_password:
            print(f"MOCK EMAIL to {to_email}:")
            print(f"Subject: {subject}")
            print(f"Body (HTML length {len(html_content)})")
            # In development, we just log it unless credentials are provided
            return True

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_late_arrival_alert(self, employee, check_in_time):
        """Send notification for late arrival"""
        template = self._get_template("late_arrival")
        if not template:
            return False
            
        # Replace placeholders
        content = template.replace("{{name}}", f"{employee.first_name} {employee.last_name}")
        content = content.replace("{{date}}", check_in_time.strftime("%d %b, %Y"))
        content = content.replace("{{shift_start}}", employee.shift_start_time)
        content = content.replace("{{check_in_time}}", check_in_time.strftime("%H:%M:%S"))
        content = content.replace("{{dashboard_url}}", "http://localhost:3000/attendance")
        content = content.replace("{{year}}", str(datetime.now().year))
        
        return await self.send_email(
            employee.email,
            f"Attendance Alert: Late Arrival on {check_in_time.strftime('%d %b')}",
            content
        )

    async def send_short_hours_alert(self, employee, total_hours, date):
        """Send notification for working less than 8 hours"""
        template = self._get_template("short_hours")
        if not template:
            return False
            
        short_by = round(8.0 - total_hours, 2)
        
        # Replace placeholders
        content = template.replace("{{name}}", f"{employee.first_name} {employee.last_name}")
        content = content.replace("{{date}}", date.strftime("%d %b, %Y"))
        content = content.replace("{{total_hours}}", str(total_hours))
        content = content.replace("{{short_by}}", str(short_by))
        content = content.replace("{{dashboard_url}}", "http://localhost:3000/attendance")
        content = content.replace("{{year}}", str(datetime.now().year))
        
        return await self.send_email(
            employee.email,
            f"Attendance Alert: Insufficient Working Hours for {date.strftime('%d %b')}",
            content
        )

    async def send_leave_status_notification(self, employee, leave, status):
        """Send notification for leave approval/rejection"""
        template = self._get_template("leave_status")
        if not template:
            # Fallback to simple HTML if template missing
            return await self.send_email(employee.email, f"Leave Request {status.capitalize()}", f"Your leave from {leave.start_date.strftime('%d %b')} has been {status}.")
            
        # Replace placeholders
        content = template.replace("{{name}}", f"{employee.first_name} {employee.last_name}")
        content = content.replace("{{status}}", status)
        content = content.replace("{{status_class}}", f"status-{status}")
        content = content.replace("{{leave_type}}", leave.leave_type.capitalize())
        content = content.replace("{{start_date}}", leave.start_date.strftime("%d %b, %Y"))
        content = content.replace("{{end_date}}", leave.end_date.strftime("%d %b, %Y"))
        content = content.replace("{{total_days}}", str(leave.total_days))
        content = content.replace("{{comments}}", leave.approvals[-1].comments if leave.approvals else "Processed via portal")
        content = content.replace("{{dashboard_url}}", "http://localhost:3000/leaves")
        content = content.replace("{{year}}", str(datetime.now().year))
        
        return await self.send_email(
            employee.email,
            f"Leave Request {status.capitalize()}: {leave.start_date.strftime('%d %b')}",
            content
        )

    async def send_leave_application_notification(self, manager_email, employee_name, leave):
        """Send notification to manager for new leave request"""
        template = self._get_template("leave_request")
        if not template:
            return False
            
        # Replace placeholders
        content = template.replace("{{employee_name}}", employee_name)
        content = content.replace("{{department}}", leave.department or "N/A")
        content = content.replace("{{leave_type}}", leave.leave_type.capitalize())
        content = content.replace("{{start_date}}", leave.start_date.strftime("%d %b, %Y"))
        content = content.replace("{{end_date}}", leave.end_date.strftime("%d %b, %Y"))
        content = content.replace("{{total_days}}", str(leave.total_days))
        content = content.replace("{{reason}}", leave.reason or "No reason provided")
        content = content.replace("{{admin_url}}", "http://localhost:3000/admin")
        content = content.replace("{{year}}", str(datetime.now().year))
        
        return await self.send_email(
            manager_email,
            f"New Leave Request: {employee_name}",
            content
        )

# Global instance
email_service = EmailService()
