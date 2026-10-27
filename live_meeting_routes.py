"""Authenticated control plane for self-hosted LiveKit webinar rooms."""
from datetime import datetime, timedelta
import json
import os
import re
import secrets
import requests
import base64

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.orm import joinedload

from extensions import limiter
from models import db, Event, LiveMeeting, LiveMeetingInteraction, LiveMeetingSpeaker, Participant

live_bp = Blueprint("live", __name__, url_prefix="/events")
ROOM_RE = re.compile(r"^[a-zA-Z0-9_-]{1,120}$")
MAX_ACTIVE_STAGE_SPEAKERS = 12


def _admin():
    return bool(session.get("admin"))


def _current_participant(event):
    participant_id = session.get("live_participant_id") or session.get("exam_participant_id")
    participant = db.session.get(Participant, participant_id) if participant_id else None
    if not participant or participant.event_id != event.id:
        return None
    if not registration_complete(participant):
        return None
    return participant


def registration_complete(participant):
    event = participant.event
    return not (event.payment_enabled and event.payment_gateway == "razorpay" and participant.payment_status != "paid")


def _meeting(event):
    meeting = LiveMeeting.query.filter_by(event_id=event.id).first()
    if meeting or not event.live_meeting_enabled:
        return meeting
    room = f"event-{event.id}-{secrets.token_hex(6)}"
    meeting = LiveMeeting(event_id=event.id, room_name=room)
    db.session.add(meeting)
    db.session.commit()
    return meeting


def _authorize_viewer(event):
    if _admin():
        if not session.get("live_host_identity"):
            session["live_host_identity"] = f"host-{secrets.token_hex(8)}"
        return {"identity": session["live_host_identity"], "name": "Host", "role": "host", "participant": None}
    participant = _current_participant(event)
    if not participant:
        abort(403, description="A completed registration for this event is required.")
    return {"identity": f"attendee-{participant.id}", "name": participant.teacher_name, "role": "viewer", "participant": participant}


def _host_required():
    if not _admin():
        abort(403)


def _livekit_token(identity, name, room, can_publish, ttl=600):
    api_key = os.getenv("LIVEKIT_API_KEY", "").strip()
    api_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    server_url = os.getenv("LIVEKIT_URL", "").strip()
    if not (api_key and api_secret and server_url.startswith(("ws://", "wss://"))):
        raise RuntimeError("LiveKit is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET on the Flask server.")
    try:
        from livekit import api
    except ImportError as error:
        raise RuntimeError("Install the livekit-api package to issue meeting tokens.") from error
    token = (api.AccessToken(api_key, api_secret)
             .with_identity(identity)
             .with_name(name[:80])
             .with_ttl(timedelta(seconds=ttl))
             .with_grants(api.VideoGrants(room_join=True, room=room, can_publish=can_publish, can_subscribe=True, can_publish_data=False)))
    return server_url, token.to_jwt()


@live_bp.get("/<int:event_id>/live")
@limiter.limit("30 per minute")
def viewer(event_id):
    event = Event.query.get_or_404(event_id)
    meeting = _meeting(event)
    if not event.live_meeting_enabled or not meeting or meeting.status == "ended":
        abort(404)
    participant = _current_participant(event)
    if not _admin() and not participant:
        return render_template("live/access.html", event=event)
    actor = _authorize_viewer(event)
    return render_template("live/viewer.html", event=event, meeting=meeting, actor=actor)


@live_bp.post("/<int:event_id>/live/access")
@limiter.limit("5 per minute")
def access(event_id):
    event = Event.query.get_or_404(event_id)
    if not event.live_meeting_enabled:
        abort(404)
    payload = request.get_json(silent=True) or request.form
    reg_id = str(payload.get("reg_id", "")).strip().upper()[:30]
    mobile = str(payload.get("mobile", "")).strip()[:10]
    participant = Participant.query.filter_by(event_id=event.id, reg_id=reg_id, mobile=mobile).first()
    if not participant or not registration_complete(participant):
        return jsonify(ok=False, message="Registration ID and mobile number did not match an eligible registration."), 403
    session.clear()
    session["live_participant_id"] = participant.id
    session.permanent = True
    return jsonify(ok=True, redirect=url_for("live.viewer", event_id=event.id))


@live_bp.get("/<int:event_id>/live/host")
@limiter.limit("30 per minute")
def host_page(event_id):
    _host_required()
    event = Event.query.get_or_404(event_id)
    if not event.live_meeting_enabled:
        abort(404)
    return render_template("live/host.html", event=event, meeting=_meeting(event))


@live_bp.post("/<int:event_id>/live/token")
@limiter.limit("12 per minute")
def token(event_id):
    event = Event.query.get_or_404(event_id)
    meeting = _meeting(event)
    if not event.live_meeting_enabled or not meeting or meeting.status == "ended":
        return jsonify(ok=False, message="This meeting is not available."), 404
    actor = _authorize_viewer(event)
    can_publish = actor["role"] == "host"
    speaker_invitation = None
    if actor["participant"]:
        speaker_invitation = LiveMeetingSpeaker.query.filter(
            LiveMeetingSpeaker.meeting_id == meeting.id,
            LiveMeetingSpeaker.participant_id == actor["participant"].id,
            LiveMeetingSpeaker.status.in_(["invited", "accepted"]),
            LiveMeetingSpeaker.expires_at > datetime.utcnow(),
        ).first()
        can_publish = bool(speaker_invitation)
        if can_publish:
            actor["role"] = "speaker"
    try:
        server_url, jwt = _livekit_token(actor["identity"], actor["name"], meeting.room_name, can_publish)
    except RuntimeError as error:
        return jsonify(ok=False, message=str(error)), 503
    if speaker_invitation and speaker_invitation.status == "invited":
        speaker_invitation.status = "accepted"
        db.session.commit()
    return jsonify(ok=True, server_url=server_url, token=jwt, role=actor["role"], room=meeting.room_name)


@live_bp.post("/<int:event_id>/live/start")
@limiter.limit("10 per minute")
def start(event_id):
    _host_required()
    event = Event.query.get_or_404(event_id)
    if not event.live_meeting_enabled:
        abort(404)
    meeting = _meeting(event)
    if meeting.status != "live":
        meeting.status = "live"
        meeting.started_at = datetime.utcnow()
        meeting.ended_at = None
        db.session.commit()
        _livekit_broadcast(meeting.room_name, {"type":"lifecycle","status":"live"})
    return jsonify(ok=True, status=meeting.status)


@live_bp.post("/<int:event_id>/live/end")
@limiter.limit("10 per minute")
def end(event_id):
    _host_required()
    event = Event.query.get_or_404(event_id)
    if not event.live_meeting_enabled:
        abort(404)
    meeting = _meeting(event)
    meeting.status = "ended"
    meeting.ended_at = datetime.utcnow()
    for speaker in meeting.speakers:
        if speaker.status in {"invited", "accepted"}:
            speaker.status = "revoked"
    _livekit_broadcast(meeting.room_name, {"type":"lifecycle","status":"ended"})
    result = _livekit_admin_request("ListParticipants", {"room": meeting.room_name})
    if result and result.ok:
        for connected in result.json().get("participants", []):
            if connected.get("identity"):
                _livekit_remove_participant(meeting.room_name, connected["identity"])
    db.session.commit()
    _livekit_admin_request("DeleteRoom", {"room": meeting.room_name})
    return jsonify(ok=True, status="ended")


@live_bp.get("/<int:event_id>/live/state")
@limiter.limit("60 per minute")
def state(event_id):
    event = Event.query.get_or_404(event_id)
    actor = _authorize_viewer(event)
    meeting = _meeting(event)
    if not meeting:
        abort(404)
    interactions = LiveMeetingInteraction.query.options(joinedload(LiveMeetingInteraction.participant)).filter_by(meeting_id=meeting.id).order_by(LiveMeetingInteraction.created_at.desc()).limit(100).all()
    speakers = LiveMeetingSpeaker.query.filter(LiveMeetingSpeaker.meeting_id==meeting.id, LiveMeetingSpeaker.status.in_(["invited","accepted"])).all() if actor["role"] == "host" else []
    return jsonify(ok=True, status=meeting.status, role=actor["role"], interactions=[{"id":item.id,"kind":item.kind,"body":item.body,"metadata":json.loads(item.metadata_json or "{}"),"status":item.status,"created_at":item.created_at.isoformat(),"name":item.participant.teacher_name if item.participant else "Host"} for item in reversed(interactions)], speakers=[{"participant_id":item.participant_id,"name":item.participant.teacher_name,"status":item.status} for item in speakers])


@live_bp.post("/<int:event_id>/live/interactions")
@limiter.limit("15 per minute")
def interaction(event_id):
    event = Event.query.get_or_404(event_id)
    actor = _authorize_viewer(event)
    meeting = _meeting(event)
    if not meeting or meeting.status == "ended":
        return jsonify(ok=False, message="The meeting has ended."), 409
    payload = request.get_json(silent=True) or {}
    kind = str(payload.get("kind", "")).strip().lower()
    body = str(payload.get("body", "")).strip()
    if kind not in {"chat", "question", "hand", "poll", "poll_vote"}:
        return jsonify(ok=False, message="Unsupported interaction."), 400
    if kind in {"chat", "question"} and not body:
        return jsonify(ok=False, message="Message is required."), 400
    if len(body) > 1000:
        return jsonify(ok=False, message="Message is too long."), 400
    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        return jsonify(ok=False, message="Invalid interaction metadata."), 400
    if kind == "poll":
        if not _admin():
            abort(403)
        options = metadata.get("options")
        if not body or not isinstance(options, list) or not 2 <= len(options) <= 8 or any(not isinstance(option, str) or not option.strip() or len(option) > 120 for option in options):
            return jsonify(ok=False, message="A poll needs a question and 2–8 valid options."), 400
        metadata = {"options":[option.strip() for option in options]}
    if kind == "poll_vote":
        try:
            poll_id = int(metadata.get("poll_id"))
        except (TypeError, ValueError):
            return jsonify(ok=False, message="Invalid poll."), 400
        poll = LiveMeetingInteraction.query.filter_by(id=poll_id, meeting_id=meeting.id, kind="poll", status="open").first()
        option = str(metadata.get("option", ""))
        if not poll or option not in json.loads(poll.metadata_json or "{}").get("options", []):
            return jsonify(ok=False, message="That poll option is unavailable."), 400
        if actor["participant"]:
            prior_votes = LiveMeetingInteraction.query.filter_by(meeting_id=meeting.id, participant_id=actor["participant"].id, kind="poll_vote").all()
            if any(json.loads(vote.metadata_json or "{}").get("poll_id") == poll_id for vote in prior_votes):
                return jsonify(ok=False, message="You have already voted in this poll."), 409
        metadata = {"poll_id": poll_id, "option": option}
    elif kind != "poll":
        metadata = {}
    item = LiveMeetingInteraction(meeting_id=meeting.id, participant_id=actor["participant"].id if actor["participant"] else None, kind=kind, body=body, metadata_json=json.dumps(metadata)[:2000])
    db.session.add(item)
    db.session.commit()
    _livekit_broadcast(meeting.room_name, {"type":"interaction","id":item.id,"kind":item.kind,"body":item.body,"metadata":json.loads(item.metadata_json),"status":item.status,"created_at":item.created_at.isoformat(),"name":actor["name"]})
    return jsonify(ok=True, id=item.id), 201


@live_bp.post("/<int:event_id>/live/invite")
@limiter.limit("30 per minute")
def invite(event_id):
    _host_required()
    event = Event.query.get_or_404(event_id)
    if not event.live_meeting_enabled:
        abort(404)
    meeting = _meeting(event)
    payload = request.get_json(silent=True) or {}
    registration_id = str(payload.get("registration_id", "")).strip().upper()[:30]
    participant = Participant.query.filter_by(event_id=event.id, reg_id=registration_id).first() if registration_id else None
    if not participant or participant.event_id != event.id or not registration_complete(participant):
        return jsonify(ok=False, message="Choose a completed attendee registration for this event."), 400
    invitation = LiveMeetingSpeaker.query.filter_by(meeting_id=meeting.id, participant_id=participant.id).first()
    if not invitation:
        active_speakers = LiveMeetingSpeaker.query.filter(
            LiveMeetingSpeaker.meeting_id == meeting.id,
            LiveMeetingSpeaker.status.in_(["invited", "accepted"]),
            LiveMeetingSpeaker.expires_at > datetime.utcnow(),
        ).count()
        if active_speakers >= MAX_ACTIVE_STAGE_SPEAKERS:
            return jsonify(ok=False, message=f"The stage is full ({MAX_ACTIVE_STAGE_SPEAKERS} attendee speakers). Remove a speaker or wait for an invitation to expire."), 409
    if not invitation:
        invitation = LiveMeetingSpeaker(meeting_id=meeting.id, participant_id=participant.id, invited_by="admin", expires_at=datetime.utcnow()+timedelta(minutes=30))
        db.session.add(invitation)
    else:
        invitation.status = "invited"
        invitation.expires_at = datetime.utcnow()+timedelta(minutes=30)
    db.session.commit()
    _livekit_broadcast(meeting.room_name, {"type":"speaker_invited","participant_id":participant.id,"name":participant.teacher_name})
    return jsonify(ok=True, participant_id=participant.id, name=participant.teacher_name, expires_at=invitation.expires_at.isoformat())


@live_bp.post("/<int:event_id>/live/speaker/<int:participant_id>/remove")
@limiter.limit("30 per minute")
def remove_speaker(event_id, participant_id):
    _host_required()
    event = Event.query.get_or_404(event_id)
    if not event.live_meeting_enabled:
        abort(404)
    meeting = _meeting(event)
    speaker = LiveMeetingSpeaker.query.filter_by(meeting_id=meeting.id, participant_id=participant_id).first_or_404()
    removed = _livekit_remove_participant(meeting.room_name, f"attendee-{participant_id}")
    if not removed:
        return jsonify(ok=False, message="Could not remove the speaker from the LiveKit room."), 503
    speaker.status = "revoked"
    db.session.commit()
    _livekit_broadcast(meeting.room_name, {"type":"speaker_removed","participant_id":participant_id})
    return jsonify(ok=True)


@live_bp.post("/<int:event_id>/live/speaker/<int:participant_id>/mute")
@limiter.limit("30 per minute")
def mute_speaker(event_id, participant_id):
    _host_required()
    event = Event.query.get_or_404(event_id)
    if not event.live_meeting_enabled:
        abort(404)
    meeting = _meeting(event)
    LiveMeetingSpeaker.query.filter_by(meeting_id=meeting.id, participant_id=participant_id, status="accepted").first_or_404()
    ok = _livekit_mute_participant(meeting.room_name, f"attendee-{participant_id}")
    return jsonify(ok=ok, message="Mute command sent." if ok else "LiveKit moderation is unavailable.")


def _livekit_admin_request(path, body):
    api_key = os.getenv("LIVEKIT_API_KEY", "").strip()
    api_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    server_url = os.getenv("LIVEKIT_URL", "").strip()
    if not (api_key and api_secret and server_url.startswith(("ws://", "wss://"))):
        return None
    try:
        from livekit import api
        jwt = api.AccessToken(api_key, api_secret).with_grants(api.VideoGrants(room_admin=True, room=body.get("room"))).with_ttl(timedelta(minutes=1)).to_jwt()
        http_url = re.sub(r"^ws", "http", server_url).rstrip("/")
        return requests.post(f"{http_url}/twirp/livekit.RoomService/{path}", json=body, headers={"Authorization": f"Bearer {jwt}"}, timeout=5)
    except (ImportError, requests.RequestException, ValueError):
        current_app.logger.exception("LiveKit management request failed")
        return None


def _livekit_remove_participant(room, identity):
    response = _livekit_admin_request("RemoveParticipant", {"room": room, "identity": identity})
    return bool(response and response.ok)


def _livekit_mute_participant(room, identity):
    response = _livekit_admin_request("ListParticipants", {"room": room})
    if not response or not response.ok:
        return False
    person = next((item for item in response.json().get("participants", []) if item.get("identity") == identity), None)
    if not person:
        return False
    audio_tracks = [item.get("sid") for item in person.get("tracks", []) if str(item.get("type", "")).lower() in {"audio", "0"} and item.get("sid")]
    return bool(audio_tracks) and all((lambda result: result is not None and result.ok)(_livekit_admin_request("MutePublishedTrack", {"room": room, "identity": identity, "track_sid": sid, "muted": True})) for sid in audio_tracks)


@live_bp.post("/<int:event_id>/live/moderate/<int:item_id>")
@limiter.limit("60 per minute")
def moderate(event_id, item_id):
    _host_required()
    event = Event.query.get_or_404(event_id)
    if not event.live_meeting_enabled:
        abort(404)
    meeting = _meeting(event)
    item = LiveMeetingInteraction.query.filter_by(id=item_id, meeting_id=meeting.id).first_or_404()
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    if action not in {"answer", "hide", "close"}:
        return jsonify(ok=False, message="Unsupported moderation action."), 400
    item.status = {"answer":"answered", "hide":"hidden", "close":"closed"}[action]
    db.session.commit()
    _livekit_broadcast(meeting.room_name, {"type":"interaction_moderated","id":item.id,"status":item.status})
    return jsonify(ok=True)


@live_bp.get("/livekit-health")
@limiter.limit("30 per minute")
def health():
    server_url=os.getenv("LIVEKIT_URL", "").strip()
    configured=bool(server_url and os.getenv("LIVEKIT_API_KEY") and os.getenv("LIVEKIT_API_SECRET"))
    reachable=False
    if configured:
        try:
            http_url=re.sub(r"^ws", "http", server_url).rstrip("/")
            probe=requests.get(http_url, timeout=2)
            reachable=probe.status_code in {200,404}
        except requests.RequestException:
            reachable=False
    status=200 if configured and reachable else 503
    return jsonify(ok=bool(configured and reachable), service="flask-live-control", livekit_configured=configured, livekit_reachable=reachable), status


def _livekit_broadcast(room, message):
    response = _livekit_admin_request("SendData", {"room": room, "data": base64.b64encode(json.dumps(message).encode()).decode(), "kind": 0})
    if not response or not response.ok:
        current_app.logger.warning("LiveKit room data fanout failed for room %s", room)
