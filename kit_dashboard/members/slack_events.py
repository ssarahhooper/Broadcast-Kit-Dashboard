import json
import os
import re
from datetime import datetime

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from slack_sdk.signature import SignatureVerifier

from models import Kit, PostMortem


CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
signature_verifier = SignatureVerifier(signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""))


def normalize_kit_name(name: str) -> str:
    match = re.search(r"kit\s*0*(\d+)", name, re.IGNORECASE)
    return f"Kit {int(match.group(1))}" if match else name.strip()


def parse_postmortem_message(message_text: str):
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

    return normalize_kit_name(kit_name), event_name, event_date


@csrf_exempt
def slack_events(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    raw_body = request.body.decode("utf-8")

    # Verify Slack signature
    if not signature_verifier.is_valid_request(raw_body, request.headers):
        return HttpResponse(status=401)

    payload = json.loads(raw_body)

    # URL verification challenge
    if payload.get("type") == "url_verification":
        return JsonResponse({"challenge": payload.get("challenge")})

    if payload.get("type") != "event_callback":
        return HttpResponse(status=200)

    event = payload.get("event", {})

    # Only message events
    if event.get("type") != "message":
        return HttpResponse(status=200)

    # Ignore bot messages + edits (you can expand this list)
    if event.get("subtype") in {"bot_message", "message_changed", "message_deleted"}:
        return HttpResponse(status=200)

    # Optional: restrict to a single channel
    if CHANNEL_ID and event.get("channel") != CHANNEL_ID:
        return HttpResponse(status=200)

    text = (event.get("text") or "").strip()
    if not text:
        return HttpResponse(status=200)

    ts = event.get("ts")               # this message ts
    thread_ts = event.get("thread_ts") # parent thread ts, if reply

    lower = text.lower()

    # Root message: identify a postmortem post, and store the thread ts for later reply matching
    is_root = (thread_ts is None) or (thread_ts == ts)
    if is_root and ("post-mort" in lower or "postmortem" in lower):
        kit_name, event_name, event_date = parse_postmortem_message(text)
        kit, _ = Kit.objects.get_or_create(name=kit_name)

        pm, created = PostMortem.objects.get_or_create(
            kit=kit,
            event_name=event_name,
            defaults={
                "name": f"{kit_name} Postmortem",
                "event_date": event_date,
                "summary": "",
                "slack_thread_ts": ts,
            },
        )

        # If it already exists, keep it in sync and ensure thread ts is stored
        changed = False
        if pm.event_date != event_date:
            pm.event_date = event_date
            changed = True
        if not pm.slack_thread_ts:
            pm.slack_thread_ts = ts
            changed = True
        if changed:
            pm.save()

        return HttpResponse(status=200)

    # Thread reply: save ONLY the first reply
    if thread_ts:
        pm = PostMortem.objects.filter(slack_thread_ts=thread_ts).first()
        if not pm:
            return HttpResponse(status=200)

        # first reply only: if we already recorded one, ignore everything else
        if pm.slack_first_reply_ts:
            return HttpResponse(status=200)

        pm.summary = text
        pm.slack_first_reply_ts = ts
        pm.save()
        return HttpResponse(status=200)

    return HttpResponse(status=200)