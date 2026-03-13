"""
ai.play notify engine — ai.notify()
Sends notifications via email, SMS, webhook, Discord.
Auto-attaches vision frames when ai.vision is active.

Usage:
    ai.notify(email, you@example.com)
    ai.notify(sms, +441234567890)
    ai.notify(webhook, https://yoursite.com/alert)
    ai.notify(discord, https://discord.com/api/webhooks/...)

Then in event hooks:
    on.detect(stranger):
        notify.email("Intruder detected", frame)
        notify.sms("Intruder at front door")
        notify.webhook("alert", frame)
        notify.discord("Intruder detected", frame)
"""

import json
import urllib.request
import urllib.parse
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import time

class NotifyEngine:
    def __init__(self):
        self.channels = {}  # type -> config

    def register(self, channel_type, target):
        self.channels[channel_type] = target
        print(f"[ai.play] Notify: {channel_type} → {target}")

    def _send_async(self, fn, *args):
        t = threading.Thread(target=fn, args=args, daemon=True)
        t.start()

    # ─── EMAIL ───────────────────────────────────────────
    def email(self, subject, body='', attachment_path=None):
        target = self.channels.get('email')
        if not target:
            print("[ai.play] notify.email: no email configured")
            return
        self._send_async(self._send_email, target, subject, body, attachment_path)

    def _send_email(self, to, subject, body, attachment_path):
        try:
            # Uses local SMTP or env vars AIPLAY_SMTP_HOST, AIPLAY_SMTP_USER, AIPLAY_SMTP_PASS
            host = os.environ.get('AIPLAY_SMTP_HOST', 'localhost')
            port = int(os.environ.get('AIPLAY_SMTP_PORT', 25))
            user = os.environ.get('AIPLAY_SMTP_USER', '')
            pw   = os.environ.get('AIPLAY_SMTP_PASS', '')
            frm  = os.environ.get('AIPLAY_SMTP_FROM', 'aiplay@localhost')

            msg = MIMEMultipart()
            msg['From']    = frm
            msg['To']      = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body or subject, 'plain'))

            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',
                                f'attachment; filename={os.path.basename(attachment_path)}')
                msg.attach(part)

            with smtplib.SMTP(host, port) as s:
                if user and pw:
                    s.starttls()
                    s.login(user, pw)
                s.send_message(msg)
            print(f"[ai.play] Email sent to {to}: {subject}")
        except Exception as e:
            print(f"[ai.play] Email failed: {e}")

    # ─── SMS (via generic HTTP SMS gateway) ──────────────
    def sms(self, message):
        target = self.channels.get('sms')
        if not target:
            print("[ai.play] notify.sms: no SMS number configured")
            return
        gateway = os.environ.get('AIPLAY_SMS_GATEWAY', '')
        api_key = os.environ.get('AIPLAY_SMS_KEY', '')
        if not gateway:
            print("[ai.play] notify.sms: set AIPLAY_SMS_GATEWAY env var to your SMS provider URL")
            return
        self._send_async(self._send_sms, gateway, api_key, target, message)

    def _send_sms(self, gateway, api_key, to, message):
        try:
            payload = json.dumps({
                'to': to,
                'message': message,
                'api_key': api_key,
            }).encode()
            req = urllib.request.Request(
                gateway,
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=5)
            print(f"[ai.play] SMS sent to {to}")
        except Exception as e:
            print(f"[ai.play] SMS failed: {e}")

    # ─── WEBHOOK ─────────────────────────────────────────
    def webhook(self, event, attachment_path=None):
        target = self.channels.get('webhook')
        if not target:
            print("[ai.play] notify.webhook: no webhook configured")
            return
        self._send_async(self._send_webhook, target, event, attachment_path)

    def _send_webhook(self, url, event, attachment_path):
        try:
            payload = json.dumps({
                'event':     event,
                'timestamp': time.time(),
                'source':    'ai.play',
            }).encode()
            req = urllib.request.Request(
                url,
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=5)
            print(f"[ai.play] Webhook sent: {event}")
        except Exception as e:
            print(f"[ai.play] Webhook failed: {e}")

    # ─── DISCORD ─────────────────────────────────────────
    def discord(self, message, attachment_path=None):
        target = self.channels.get('discord')
        if not target:
            print("[ai.play] notify.discord: no Discord webhook configured")
            return
        self._send_async(self._send_discord, target, message, attachment_path)

    def _send_discord(self, webhook_url, message, attachment_path):
        try:
            payload = json.dumps({'content': message}).encode()
            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=5)
            print(f"[ai.play] Discord notified: {message[:50]}")
        except Exception as e:
            print(f"[ai.play] Discord failed: {e}")

    def send(self, channel, message, attachment_path=None):
        """Generic send — routes to correct channel."""
        if channel == 'email':
            self.email(message, attachment_path=attachment_path)
        elif channel == 'sms':
            self.sms(message)
        elif channel == 'webhook':
            self.webhook(message, attachment_path)
        elif channel == 'discord':
            self.discord(message, attachment_path)
        else:
            print(f"[ai.play] Unknown notify channel: {channel}")
