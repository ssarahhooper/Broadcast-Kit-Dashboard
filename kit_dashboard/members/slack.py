import os
import re
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from django.conf import settings
from models import Kit, PostMortem

# Slack setup
client = WebClient(token=settings.SLACK_BOT_TOKEN)
CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "C09T3SPD01J")  # Global fixed channel


def find_postmortem_threads():
    """Fetch messages containing 'Post-Mort' or 'Postmortem' and their first thread replies."""
    try:
        response = client.conversations_history(channel=CHANNEL_ID, limit=200)
        messages = response.get('messages', [])
        postmortem_threads = []

        for msg in messages:
            text = msg.get("text", "").lower()
            if "post-mort" in text or "postmortem" in text:
                thread_ts = msg.get("ts")
                if thread_ts:
                    thread = client.conversations_replies(channel=CHANNEL_ID, ts=thread_ts)
                    first_reply = thread['messages'][1] if len(thread['messages']) > 1 else None
                    if first_reply:
                        postmortem_threads.append({
                            "main_message": msg['text'],
                            "first_reply": first_reply['text'],
                            "ts": msg['ts']
                        })
        return postmortem_threads

    except SlackApiError as e:
        print(f"Slack API Error: {e.response['error']}")
        return []


def parse_postmortem_message(message_text):
    """Extract Kit name, Event name, and Event date from a Slack postmortem message."""
    kit_match = re.search(r"Kit\s*(\d+)", message_text, re.IGNORECASE)
    event_match = re.search(r":thread:\s*(.+)", message_text)
    date_match = re.search(r"Game:\s*([0-9/]+)", message_text)

    kit_name = f"Kit {kit_match.group(1)}" if kit_match else "Unknown Kit"
    event_name = event_match.group(1).strip() if event_match else "Unknown Event"

    if date_match:
        try:
            event_date = datetime.strptime(date_match.group(1), "%m/%d").date()
            event_date = event_date.replace(year=datetime.today().year)
        except ValueError:
            event_date = datetime.today().date()
    else:
        event_date = datetime.today().date()

    return kit_name, event_name, event_date


def update_dashboard_with_postmortems(postmortems):
    """Create or update PostMortem entries in the database."""
    for pm in postmortems:
        kit_name, event_name, event_date = parse_postmortem_message(pm["main_message"])
        summary_text = pm["first_reply"]

        def normalize_kit_name(name: str) -> str:
            """Standardize kit names like 'Kit 06' → 'Kit 6'"""
            match = re.search(r"kit\s*0*(\d+)", name, re.IGNORECASE)
            if match:
                return f"Kit {int(match.group(1))}"  # int() strips leading zeros
            return name.strip()

        kit_name = normalize_kit_name(kit_name)
        kit, _ = Kit.objects.get_or_create(name=kit_name)

        existing = PostMortem.objects.filter(kit=kit, event_name=event_name).first()
        if existing:
            existing.summary = summary_text
            existing.save()
            print(f"🔁 Updated existing PostMortem for {kit_name} - {event_name}")
        else:
            PostMortem.objects.create(
                kit=kit,
                name=f"{kit_name} Postmortem",
                event_name=event_name,
                event_date=event_date,
                summary=summary_text,
            )
            print(f"✅ Added new PostMortem for {kit_name} - {event_name}")


def main():
    postmortems = find_postmortem_threads()
    update_dashboard_with_postmortems(postmortems)
