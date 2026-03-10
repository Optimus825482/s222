"""
Email Sender Service — SMTP client with template support, attachments, HTML/plain text emails.
Supports multiple SMTP providers (Gmail, Outlook, Yahoo, custom SMTP).
"""

from __future__ import annotations

import base64
import io
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from string import Template
from typing import Any, Optional

# ── Data Classes ─────────────────────────────────────────────────────

@dataclass
class SMTPConfig:
    """SMTP server configuration."""
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False  # For SMTP_SSL (port 465)
    
    @classmethod
    def gmail(cls, username: str, password: str) -> "SMTPConfig":
        """Create Gmail SMTP config. Password should be an App Password."""
        return cls(
            host="smtp.gmail.com",
            port=587,
            username=username,
            password=password,
            use_tls=True,
        )
    
    @classmethod
    def outlook(cls, username: str, password: str) -> "SMTPConfig":
        """Create Outlook/Microsoft 365 SMTP config."""
        return cls(
            host="smtp.office365.com",
            port=587,
            username=username,
            password=password,
            use_tls=True,
        )
    
    @classmethod
    def yahoo(cls, username: str, password: str) -> "SMTPConfig":
        """Create Yahoo SMTP config. Password should be an App Password."""
        return cls(
            host="smtp.mail.yahoo.com",
            port=587,
            username=username,
            password=password,
            use_tls=True,
        )


@dataclass
class EmailAttachment:
    """Email attachment representation."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    content_id: Optional[str] = None  # For inline images


@dataclass
class EmailTemplate:
    """Email template with variable substitution."""
    name: str
    subject: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    variables: list[str] = field(default_factory=list)
    
    def render(
        self,
        variables: dict[str, Any],
        fallback_text: bool = True,
    ) -> tuple[str, Optional[str]]:
        """
        Render template with variable substitution.
        
        Returns:
            Tuple of (subject, text_body, html_body)
        """
        # Render subject
        subject_template = Template(self.subject)
        rendered_subject = subject_template.safe_substitute(variables)
        
        rendered_text = None
        rendered_html = None
        
        # Render text body
        if self.text_body:
            text_template = Template(self.text_body)
            rendered_text = text_template.safe_substitute(variables)
        
        # Render HTML body
        if self.html_body:
            html_template = Template(self.html_body)
            rendered_html = html_template.safe_substitute(variables)
        
        # If only HTML and fallback_text, generate plain text from HTML
        if fallback_text and rendered_html and not rendered_text:
            rendered_text = _html_to_text(rendered_html)
        
        return rendered_subject, rendered_text, rendered_html


# ── Built-in Templates ────────────────────────────────────────────────

BUILTIN_TEMPLATES: dict[str, EmailTemplate] = {
    "welcome": EmailTemplate(
        name="welcome",
        subject="Welcome to ${company_name}!",
        text_body="""Hello ${user_name},

Welcome to ${company_name}! We're excited to have you on board.

Your account has been created successfully. Here are your login details:
- Email: ${user_email}
- Username: ${username}

If you have any questions, feel free to reach out to our support team.

Best regards,
The ${company_name} Team
""",
        html_body="""<!DOCTYPE html>
<html>
<head><title>Welcome</title></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h1 style="color: #333;">Hello ${user_name},</h1>
<p>Welcome to <strong>${company_name}</strong>! We're excited to have you on board.</p>
<p>Your account has been created successfully. Here are your login details:</p>
<ul>
<li>Email: ${user_email}</li>
<li>Username: ${username}</li>
</ul>
<p style="color: #666;">If you have any questions, feel free to reach out to our support team.</p>
<p>Best regards,<br>The ${company_name} Team</p>
</body>
</html>
""",
        variables=["user_name", "company_name", "user_email", "username"],
    ),
    "password_reset": EmailTemplate(
        name="password_reset",
        subject="Reset Your Password - ${company_name}",
        text_body="""Hello ${user_name},

We received a request to reset your password for your ${company_name} account.

Click the link below to reset your password:
${reset_link}

This link will expire in ${expiry_hours} hours.

If you didn't request this password reset, you can safely ignore this email.

Best regards,
The ${company_name} Team
""",
        html_body="""<!DOCTYPE html>
<html>
<head><title>Password Reset</title></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Hello ${user_name},</h2>
<p>We received a request to reset your password for your ${company_name} account.</p>
<p><a href="${reset_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
<p style="color: #666;">This link will expire in ${expiry_hours} hours.</p>
<p style="color: #999;">If you didn't request this password reset, you can safely ignore this email.</p>
<p>Best regards,<br>The ${company_name} Team</p>
</body>
</html>
""",
        variables=["user_name", "company_name", "reset_link", "expiry_hours"],
    ),
    "notification": EmailTemplate(
        name="notification",
        subject="${subject}",
        text_body="""Hello ${user_name},

${message}

---
This is an automated notification from ${company_name}.
""",
        html_body="""<!DOCTYPE html>
<html>
<head><title>Notification</title></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<p>Hello ${user_name},</p>
<div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0;">
${message}
</div>
<hr style="border: none; border-top: 1px solid #ddd;">
<p style="color: #999; font-size: 12px;">This is an automated notification from ${company_name}.</p>
</body>
</html>
""",
        variables=["user_name", "subject", "message", "company_name"],
    ),
    "weekly_report": EmailTemplate(
        name="weekly_report",
        subject="Weekly Report - ${report_title} (${date_range})",
        text_body="""Hello ${recipient_name},

Here is your weekly report for ${report_title}.

Period: ${date_range}

Summary:
${summary}

Key Metrics:
${metrics}

Top Items:
${top_items}

---
Generated automatically by ${system_name}.
""",
        html_body="""<!DOCTYPE html>
<html>
<head><title>Weekly Report</title></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Weekly Report: ${report_title}</h2>
<p><strong>Period:</strong> ${date_range}</p>

<h3 style="color: #555;">Summary</h3>
<p>${summary}</p>

<h3 style="color: #555;">Key Metrics</h3>
<table style="width: 100%; border-collapse: collapse;">
${metrics_html}
</table>

<h3 style="color: #555;">Top Items</h3>
<ul>
${top_items_html}
</ul>

<hr style="border: none; border-top: 1px solid #ddd;">
<p style="color: #999; font-size: 12px;">Generated automatically by ${system_name}.</p>
</body>
</html>
""",
        variables=["recipient_name", "report_title", "date_range", "summary", "metrics", "top_items", "metrics_html", "top_items_html", "system_name"],
    ),
    "simple": EmailTemplate(
        name="simple",
        subject="${subject}",
        text_body="${body}",
        html_body=None,
        variables=["subject", "body"],
    ),
}

# Global template registry
_TEMPLATE_REGISTRY: dict[str, EmailTemplate] = dict(BUILTIN_TEMPLATES)


# ── Helper Functions ─────────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    """Convert HTML to plain text (basic implementation)."""
    import re
    # Remove script and style elements
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Replace common block elements with newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '• ', text, flags=re.IGNORECASE)
    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    import html as html_module
    text = html_module.unescape(text)
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def _parse_attachment(data: dict[str, Any]) -> EmailAttachment:
    """Parse attachment from dict input."""
    filename = data.get("filename", "attachment")
    content_type = data.get("content_type", "application/octet-stream")
    content_id = data.get("content_id")
    
    # Handle content
    content_raw = data.get("content") or data.get("file_bytes") or data.get("content_base64")
    file_path = data.get("file_path")
    
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            content = f.read()
        # Guess content type from extension
        if content_type == "application/octet-stream":
            import mimetypes
            guessed, _ = mimetypes.guess_type(file_path)
            if guessed:
                content_type = guessed
    elif content_raw:
        if isinstance(content_raw, str):
            # Assume base64 encoded
            content = base64.b64decode(content_raw)
        else:
            content = bytes(content_raw)
    else:
        raise ValueError(f"Attachment '{filename}' has no content or file_path")
    
    return EmailAttachment(
        filename=filename,
        content=content,
        content_type=content_type,
        content_id=content_id,
    )


# ── Main Email Functions ─────────────────────────────────────────────

async def send_email(
    smtp_config: SMTPConfig | dict[str, Any],
    to: str | list[str],
    subject: str,
    body: str | None = None,
    html_body: str | None = None,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    reply_to: str | None = None,
    from_name: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
    priority: str = "normal",  # low, normal, high
) -> dict[str, Any]:
    """
    Send an email via SMTP.
    
    Args:
        smtp_config: SMTPConfig object or dict with host, port, username, password.
        to: Recipient email address(es).
        subject: Email subject line.
        body: Plain text body.
        html_body: HTML body (optional, for multipart emails).
        cc: CC recipient(s).
        bcc: BCC recipient(s).
        reply_to: Reply-to address.
        from_name: Display name for sender.
        attachments: List of attachment dicts with filename, content/file_path, content_type.
        headers: Additional email headers.
        priority: Email priority (low, normal, high).
    
    Returns:
        dict with keys:
            - success: bool
            - message_id: str (if successful)
            - recipients: list of recipients
            - error: str (if failed)
    """
    # Parse SMTP config
    if isinstance(smtp_config, dict):
        smtp_config = SMTPConfig(
            host=smtp_config.get("host", "localhost"),
            port=smtp_config.get("port", 25),
            username=smtp_config.get("username", ""),
            password=smtp_config.get("password", ""),
            use_tls=smtp_config.get("use_tls", True),
            use_ssl=smtp_config.get("use_ssl", False),
        )
    
    # Normalize recipients to lists
    to_list = [to] if isinstance(to, str) else list(to)
    cc_list = [cc] if isinstance(cc, str) else (cc or [])
    bcc_list = [bcc] if isinstance(bcc, str) else (bcc or [])
    all_recipients = to_list + cc_list + bcc_list
    
    try:
        # Create message
        msg = MIMEMultipart("alternative" if body and html_body else "mixed")
        msg["Subject"] = subject
        msg["From"] = formataddr((from_name, smtp_config.username)) if from_name else smtp_config.username
        msg["To"] = ", ".join(to_list)
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        if reply_to:
            msg["Reply-To"] = reply_to
        
        # Priority header
        if priority == "high":
            msg["X-Priority"] = "1"
            msg["Importance"] = "high"
        elif priority == "low":
            msg["X-Priority"] = "5"
            msg["Importance"] = "low"
        
        # Additional headers
        if headers:
            for key, value in headers.items():
                msg[key] = value
        
        # Add body parts
        if body and html_body:
            # Multipart: text + HTML
            msg.attach(MIMEText(body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))
        elif html_body:
            # HTML only
            msg.attach(MIMEText(html_body, "html", "utf-8"))
        elif body:
            # Plain text only
            msg.attach(MIMEText(body, "plain", "utf-8"))
        else:
            return {
                "success": False,
                "message_id": None,
                "recipients": all_recipients,
                "error": "No email body provided (body or html_body required)",
            }
        
        # Add attachments
        if attachments:
            for att_data in attachments:
                try:
                    att = _parse_attachment(att_data)
                    
                    part = MIMEBase(*att.content_type.split("/", 1))
                    part.set_payload(att.content)
                    encoders.encode_base64(part)
                    
                    if att.content_id:
                        # Inline attachment
                        part.add_header(
                            "Content-Disposition",
                            "inline",
                            filename=att.filename,
                        )
                        part.add_header("Content-ID", f"<{att.content_id}>")
                    else:
                        # Regular attachment
                        part.add_header(
                            "Content-Disposition",
                            "attachment",
                            filename=att.filename,
                        )
                    
                    msg.attach(part)
                except Exception as e:
                    return {
                        "success": False,
                        "message_id": None,
                        "recipients": all_recipients,
                        "error": f"Failed to process attachment: {e}",
                    }
        
        # Connect and send
        if smtp_config.use_ssl:
            # SMTP over SSL (port 465)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                smtp_config.host,
                smtp_config.port,
                context=context,
            ) as server:
                server.login(smtp_config.username, smtp_config.password)
                server.sendmail(
                    smtp_config.username,
                    all_recipients,
                    msg.as_string(),
                )
        else:
            # SMTP with optional STARTTLS
            with smtplib.SMTP(smtp_config.host, smtp_config.port) as server:
                if smtp_config.use_tls:
                    server.starttls()
                if smtp_config.username:
                    server.login(smtp_config.username, smtp_config.password)
                server.sendmail(
                    smtp_config.username,
                    all_recipients,
                    msg.as_string(),
                )
        
        return {
            "success": True,
            "message_id": msg["Message-ID"],
            "recipients": all_recipients,
            "error": None,
        }
    
    except smtplib.SMTPAuthenticationError as e:
        return {
            "success": False,
            "message_id": None,
            "recipients": all_recipients,
            "error": f"SMTP authentication failed: {e.smtp_code} - {e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else e.smtp_error}",
        }
    except smtplib.SMTPException as e:
        return {
            "success": False,
            "message_id": None,
            "recipients": all_recipients,
            "error": f"SMTP error: {type(e).__name__}: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "message_id": None,
            "recipients": all_recipients,
            "error": f"Failed to send email: {type(e).__name__}: {e}",
        }


async def send_template_email(
    smtp_config: SMTPConfig | dict[str, Any],
    template_name: str,
    to: str | list[str],
    variables: dict[str, Any],
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    reply_to: str | None = None,
    from_name: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    priority: str = "normal",
) -> dict[str, Any]:
    """
    Send an email using a pre-defined template.
    
    Args:
        smtp_config: SMTPConfig object or dict.
        template_name: Name of template (built-in: welcome, password_reset, notification, weekly_report, simple).
        to: Recipient email address(es).
        variables: Dict of template variables to substitute.
        cc: CC recipient(s).
        bcc: BCC recipient(s).
        reply_to: Reply-to address.
        from_name: Display name for sender.
        attachments: List of attachment dicts.
        priority: Email priority.
    
    Returns:
        Same as send_email().
    """
    template = _TEMPLATE_REGISTRY.get(template_name)
    if not template:
        return {
            "success": False,
            "message_id": None,
            "recipients": [],
            "error": f"Template '{template_name}' not found. Available templates: {list(_TEMPLATE_REGISTRY.keys())}",
        }
    
    subject, body, html_body = template.render(variables)
    
    return await send_email(
        smtp_config=smtp_config,
        to=to,
        subject=subject,
        body=body,
        html_body=html_body,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
        from_name=from_name,
        attachments=attachments,
        priority=priority,
    )


def register_template(template: EmailTemplate) -> None:
    """Register a custom email template."""
    _TEMPLATE_REGISTRY[template.name] = template


def get_template(name: str) -> EmailTemplate | None:
    """Get a template by name."""
    return _TEMPLATE_REGISTRY.get(name)


def list_templates() -> list[dict[str, Any]]:
    """List all available templates."""
    return [
        {
            "name": t.name,
            "subject": t.subject,
            "variables": t.variables,
            "has_html": t.html_body is not None,
            "has_text": t.text_body is not None,
        }
        for t in _TEMPLATE_REGISTRY.values()
    ]


async def test_smtp_connection(smtp_config: SMTPConfig | dict[str, Any]) -> dict[str, Any]:
    """
    Test SMTP connection without sending an email.
    
    Returns:
        dict with keys:
            - success: bool
            - message: str
            - server_info: str (if successful)
            - error: str (if failed)
    """
    if isinstance(smtp_config, dict):
        smtp_config = SMTPConfig(
            host=smtp_config.get("host", "localhost"),
            port=smtp_config.get("port", 25),
            username=smtp_config.get("username", ""),
            password=smtp_config.get("password", ""),
            use_tls=smtp_config.get("use_tls", True),
            use_ssl=smtp_config.get("use_ssl", False),
        )
    
    try:
        if smtp_config.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_config.host, smtp_config.port, context=context) as server:
                server.login(smtp_config.username, smtp_config.password)
                server_info = server.noop()
                return {
                    "success": True,
                    "message": "SMTP connection successful (SSL)",
                    "server_info": str(server_info),
                    "error": None,
                }
        else:
            with smtplib.SMTP(smtp_config.host, smtp_config.port) as server:
                if smtp_config.use_tls:
                    server.starttls()
                if smtp_config.username:
                    server.login(smtp_config.username, smtp_config.password)
                server_info = server.noop()
                return {
                    "success": True,
                    "message": "SMTP connection successful" + (" (STARTTLS)" if smtp_config.use_tls else ""),
                    "server_info": str(server_info),
                    "error": None,
                }
    
    except smtplib.SMTPAuthenticationError as e:
        return {
            "success": False,
            "message": "SMTP authentication failed",
            "server_info": None,
            "error": f"{e.smtp_code} - {e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else e.smtp_error}",
        }
    except smtplib.SMTPException as e:
        return {
            "success": False,
            "message": "SMTP error",
            "server_info": None,
            "error": f"{type(e).__name__}: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Connection failed",
            "server_info": None,
            "error": f"{type(e).__name__}: {e}",
        }


# ── Convenience Functions ────────────────────────────────────────────

async def send_simple_email(
    smtp_config: SMTPConfig | dict[str, Any],
    to: str,
    subject: str,
    body: str,
    from_name: str | None = None,
) -> dict[str, Any]:
    """Send a simple plain text email."""
    return await send_email(
        smtp_config=smtp_config,
        to=to,
        subject=subject,
        body=body,
        from_name=from_name,
    )


async def send_html_email(
    smtp_config: SMTPConfig | dict[str, Any],
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    from_name: str | None = None,
) -> dict[str, Any]:
    """Send an HTML email with optional plain text fallback."""
    return await send_email(
        smtp_config=smtp_config,
        to=to,
        subject=subject,
        body=text_body,
        html_body=html_body,
        from_name=from_name,
    )


async def send_email_with_attachment(
    smtp_config: SMTPConfig | dict[str, Any],
    to: str,
    subject: str,
    body: str,
    attachments: list[dict[str, Any]],
    html_body: str | None = None,
    from_name: str | None = None,
) -> dict[str, Any]:
    """Send an email with file attachments."""
    return await send_email(
        smtp_config=smtp_config,
        to=to,
        subject=subject,
        body=body,
        html_body=html_body,
        attachments=attachments,
        from_name=from_name,
    )


# ── Formatting for LLM Context ───────────────────────────────────────

def format_email_result(result: dict[str, Any]) -> str:
    """Format email result for LLM context."""
    if not result.get("success"):
        return f"<email_result>\n  <status>failed</status>\n  <error>{result.get('error', 'Unknown error')}</error>\n</email_result>"
    
    return (
        f"<email_result>\n"
        f"  <status>sent</status>\n"
        f"  <message_id>{result.get('message_id', 'N/A')}</message_id>\n"
        f"  <recipients>{', '.join(result.get('recipients', []))}</recipients>\n"
        f"</email_result>"
    )


def format_template_list(templates: list[dict[str, Any]]) -> str:
    """Format template list for LLM context."""
    lines = ["<email_templates>"]
    for t in templates:
        vars_str = ", ".join(t["variables"]) if t["variables"] else "none"
        types = []
        if t["has_text"]:
            types.append("text")
        if t["has_html"]:
            types.append("html")
        lines.append(f"  <template name=\"{t['name']}\">")
        lines.append(f"    <subject>{t['subject']}</subject>")
        lines.append(f"    <formats>{', '.join(types)}</formats>")
        lines.append(f"    <variables>{vars_str}</variables>")
        lines.append("  </template>")
    lines.append("</email_templates>")
    return "\n".join(lines)