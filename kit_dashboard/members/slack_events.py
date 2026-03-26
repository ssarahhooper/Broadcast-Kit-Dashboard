import json
import os
import re
from datetime import datetime

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from slack_sdk.signature import SignatureVerifier

from .models import Kit, PostMortem


CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
signature_verifier = SignatureVerifier(signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""))


def normalize_kit_name(name: str) -> str:
    match = re.search(r"kit\s*0*(\d+)", name, re.IGNORECASE)
    return f"Kit {int(match.group(1))}" if match else name.strip()


def parse_postmortem_message(message_text: str):
    kit_match = re.search(r"Kit\s*0*(\d+)", message_text, re.IGNORECASE)
    eic_match = re.search(r"EIC:\s*@?(.+?)(?:\n|$)", message_text)
    date_match = re.search(r"Games?:\s*([0-9/]+)", message_text)
    event_match = re.search(r"Post-?Mort(?:em)?\s+(.+?)(?:\n|Broadcast)", message_text, re.IGNORECASE)

    kit_name = f"Kit {int(kit_match.group(1))}" if kit_match else "Unknown Kit"
    eic_name = eic_match.group(1).strip() if eic_match else "Unknown EIC"
    event_name = event_match.group(1).strip() if event_match else "Unknown Event"
    event_name = re.sub(r"^:[a-z_]+:\s*", "", event_name)

    if date_match:
        try:
            event_date = datetime.strptime(date_match.group(1), "%m/%d").date()
            event_date = event_date.replace(year=datetime.today().year)
        except ValueError:
            event_date = datetime.today().date()
    else:
        event_date = datetime.today().date()

    return normalize_kit_name(kit_name), eic_name, event_name, event_date


@csrf_exempt
def slack_events(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    raw_body = request.body.decode("utf-8")

    # if not signature_verifier.is_valid_request(raw_body, request.headers):
    #     return HttpResponse(status=401)

    payload = json.loads(raw_body)

    if payload.get("type") == "url_verification":
        return JsonResponse({"challenge": payload.get("challenge")})

    if payload.get("type") != "event_callback":
        return HttpResponse(status=200)

    event = payload.get("event", {})

    if event.get("type") != "message":
        return HttpResponse(status=200)

    if event.get("subtype") in {"bot_message", "message_changed", "message_deleted"}:
        return HttpResponse(status=200)

    if CHANNEL_ID and event.get("channel") != CHANNEL_ID:
        return HttpResponse(status=200)

    text = (event.get("text") or "").strip()
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    if not text:
        return HttpResponse(status=200)

    ts = event.get("ts")
    thread_ts = event.get("thread_ts")
    lower = text.lower()

    is_root = (thread_ts is None) or (thread_ts == ts)
    if is_root and ("post-mort" in lower or "postmortem" in lower):
        kit_name, eic_name, event_name, event_date = parse_postmortem_message(text)

        try:
            kit = Kit.objects.get(name=kit_name)
        except Kit.DoesNotExist:
            return HttpResponse(status=200)  # ignore if kit doesn't exist

        pm, created = PostMortem.objects.get_or_create(
            kit=kit,
            event_name=event_name,
            defaults={
                "name": eic_name,
                "event_date": event_date,
                "summary": "",
                "slack_thread_ts": ts,
            },
        )

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

    if thread_ts:
        pm = PostMortem.objects.filter(slack_thread_ts=thread_ts).first()
        if not pm:
            return HttpResponse(status=200)

        if pm.slack_first_reply_ts:
            return HttpResponse(status=200)

        pm.summary = text
        pm.slack_first_reply_ts = ts
        pm.save()
        return HttpResponse(status=200)

    return HttpResponse(status=200)