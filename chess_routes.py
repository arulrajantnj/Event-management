"""Chess tournament workflow: setup, pairing, score approval and public standings."""
from datetime import datetime, timedelta
from io import BytesIO
import base64, hashlib, hmac, json, os, secrets, zipfile
import pandas as pd
import qrcode
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, send_file, session, url_for
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from werkzeug.security import check_password_hash, generate_password_hash
from models import (db, ChessAgeGroup, ChessAnnouncement, ChessAuditLog, ChessOrbiter,
                    ChessPairing, ChessParticipant, ChessRoom, ChessRoomAssignment,
                    ChessRound, ChessStanding, ChessTournament, ChessApiToken, ChessCertificate,
                    ChessNotification, ChessStaff, ChessStaffAssignment)

chess_bp = Blueprint("chess", __name__)
RESULTS = {"white_win", "black_win", "draw", "walkover", "bye", "absent", "not_played"}


def admin_required():
    if "admin" not in session:
        return False
    return True


def staff_for_tournament(tournament_id, age_group_id=None, roles=None):
    """Global site admins are chess super-admins; staff are limited by assignment."""
    if "admin" in session:
        return True
    staff_id = session.get("chess_staff")
    if not staff_id:
        return False
    staff = ChessStaff.query.filter_by(id=staff_id, is_active=True).first()
    if not staff or (roles and staff.role not in roles):
        return False
    assignment = ChessStaffAssignment.query.filter_by(staff_id=staff.id, tournament_id=tournament_id).filter(
        (ChessStaffAssignment.age_group_id == None) | (ChessStaffAssignment.age_group_id == age_group_id)
    ).first()
    return bool(assignment)


def signed_jwt(payload):
    """Small HS256 JWT issuer for external integrations without an extra runtime dependency."""
    def encode(value): return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=")
    header, body = encode({"alg": "HS256", "typ": "JWT"}), encode(payload)
    signature = hmac.new(current_app.secret_key.encode(), header + b"." + body, hashlib.sha256).digest()
    return (header + b"." + body + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")).decode()


def jwt_claims():
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    try:
        header, body, signature = token.split(".")
        signed = f"{header}.{body}".encode()
        expected = base64.urlsafe_b64encode(hmac.new(current_app.secret_key.encode(), signed, hashlib.sha256).digest()).rstrip(b"=").decode()
        if not hmac.compare_digest(expected, signature): raise ValueError("signature")
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(claims.get("exp", 0)) < int(datetime.utcnow().timestamp()): raise ValueError("expired")
        return claims
    except (ValueError, TypeError, json.JSONDecodeError):
        abort(401)


def json_rows(group_id):
    return [{"rank": row.rank, "player_id": row.participant_id, "name": row.participant.name,
             "district": row.participant.district, "points": row.points, "buchholz": row.buchholz,
             "wins": row.wins, "draws": row.draws, "losses": row.losses}
            for row in ChessStanding.query.filter_by(age_group_id=group_id).order_by(ChessStanding.rank).all()]


def audit(tournament_id, action, entity_type="", entity_id=None, details=""):
    db.session.add(ChessAuditLog(tournament_id=tournament_id, action=action,
        entity_type=entity_type, entity_id=entity_id, actor=str(session.get("admin") or session.get("chess_orbiter") or "system"),
        ip_address=request.remote_addr, details=details))


def player_points(pairing, player_id):
    if pairing.result in {"bye", "walkover", "absent"} and pairing.white_player_id == player_id:
        return 1.0
    if pairing.result == "draw":
        return .5
    if pairing.result == "white_win":
        return 1.0 if pairing.white_player_id == player_id else 0.0
    if pairing.result == "black_win":
        return 1.0 if pairing.black_player_id == player_id else 0.0
    return 0.0


def rebuild_standings(age_group_id):
    players = ChessParticipant.query.filter_by(age_group_id=age_group_id).all()
    scores = {p.id: {"points": 0.0, "wins": 0, "draws": 0, "losses": 0, "opponents": []} for p in players}
    pairings = ChessPairing.query.join(ChessRound).filter(ChessRound.age_group_id == age_group_id,
        ChessPairing.score_status == "approved").all()
    for game in pairings:
        for pid in (game.white_player_id, game.black_player_id):
            if pid and pid in scores:
                point = player_points(game, pid)
                scores[pid]["points"] += point
                if game.result == "draw": scores[pid]["draws"] += 1
                elif point == 1: scores[pid]["wins"] += 1
                elif game.result not in {"bye", "walkover", "absent", "not_played"}: scores[pid]["losses"] += 1
                other = game.black_player_id if pid == game.white_player_id else game.white_player_id
                if other: scores[pid]["opponents"].append(other)
    for pid, item in scores.items():
        item["buchholz"] = sum(scores[opponent]["points"] for opponent in item["opponents"] if opponent in scores)
    ordered = sorted(players, key=lambda p: (-scores[p.id]["points"], -scores[p.id]["buchholz"], p.name.lower(), p.id))
    for rank, player in enumerate(ordered, 1):
        row = ChessStanding.query.filter_by(age_group_id=age_group_id, participant_id=player.id).first()
        if not row:
            row = ChessStanding(age_group_id=age_group_id, participant_id=player.id); db.session.add(row)
        row.points, row.wins, row.draws, row.losses = scores[player.id]["points"], scores[player.id]["wins"], scores[player.id]["draws"], scores[player.id]["losses"]
        row.buchholz, row.rank = scores[player.id]["buchholz"], rank
    db.session.flush()


def generate_pairings(age_group):
    existing = ChessRound.query.filter_by(age_group_id=age_group.id).order_by(ChessRound.round_number.desc()).first()
    if existing and existing.status != "closed":
        raise ValueError("Close the current round before generating the next one.")
    number = (existing.round_number if existing else 0) + 1
    rebuild_standings(age_group.id)
    eligible = ChessParticipant.query.filter_by(age_group_id=age_group.id, status="verified", checked_in=True, withdrawn=False).all()
    standings = {s.participant_id: s for s in ChessStanding.query.filter_by(age_group_id=age_group.id).all()}
    history = set(); colour_history = {}
    for p in ChessPairing.query.join(ChessRound).filter(ChessRound.age_group_id == age_group.id).order_by(ChessRound.round_number).all():
        if p.black_player_id: history.add(frozenset((p.white_player_id, p.black_player_id)))
        colour_history.setdefault(p.white_player_id, []).append("W")
        if p.black_player_id: colour_history.setdefault(p.black_player_id, []).append("B")
    eligible.sort(key=lambda p: (-(standings.get(p.id).points if standings.get(p.id) else 0), p.name.lower()))
    round_row = ChessRound(age_group_id=age_group.id, round_number=number); db.session.add(round_row); db.session.flush()
    rooms = ChessRoom.query.filter_by(age_group_id=age_group.id).order_by(ChessRoom.board_start, ChessRoom.id).all()
    def room_for_board(board_number):
        if not rooms:
            return None
        return next((room.id for room in rooms if room.board_start <= board_number <= room.board_end), rooms[(board_number - 1) % len(rooms)].id)
    board = 1
    while len(eligible) >= 2:
        white = eligible.pop(0)
        # Prefer same-score players without repeat games, then avoid school/district conflicts where possible.
        candidates = sorted(range(len(eligible)), key=lambda i: (
            frozenset((white.id, eligible[i].id)) in history,
            bool(white.school and eligible[i].school and white.school.strip().lower() == eligible[i].school.strip().lower()),
            bool(white.district and eligible[i].district and white.district.strip().lower() == eligible[i].district.strip().lower()), i))
        opponent_index = candidates[0]
        black = eligible.pop(opponent_index)
        # Alternate colours based on prior white games.
        white_count = ChessPairing.query.join(ChessRound).filter(ChessRound.age_group_id == age_group.id, ChessPairing.white_player_id == white.id).count()
        black_count = ChessPairing.query.join(ChessRound).filter(ChessRound.age_group_id == age_group.id, ChessPairing.black_player_id == white.id).count()
        white_streak = colour_history.get(white.id, [])[-2:]
        black_streak = colour_history.get(black.id, [])[-2:]
        if white_count > black_count or white_streak == ["W", "W"] or black_streak == ["B", "B"]:
            white, black = black, white
        db.session.add(ChessPairing(round_id=round_row.id, board_number=board, table_number=board,
            room_id=room_for_board(board), white_player_id=white.id, black_player_id=black.id)); board += 1
    if eligible:
        db.session.add(ChessPairing(round_id=round_row.id, board_number=board, table_number=board,
            room_id=room_for_board(board), white_player_id=eligible[0].id, result="bye", score_status="approved", remarks="Automatic bye"))
    db.session.flush(); rebuild_standings(age_group.id)
    return round_row


@chess_bp.route("/admin/chess", methods=["GET", "POST"])
def admin_tournaments():
    if not admin_required(): return redirect(url_for("routes.login"))
    if request.method == "POST":
        tournament = ChessTournament(name=request.form.get("name", "").strip(), venue=request.form.get("venue", "").strip(),
            organizer=request.form.get("organizer", "").strip(), chief_arbiter=request.form.get("chief_arbiter", "").strip(),
            system=request.form.get("system", "swiss"), number_of_rounds=max(1, request.form.get("number_of_rounds", 5, type=int) or 5))
        if tournament.name:
            db.session.add(tournament); db.session.flush(); audit(tournament.id, "tournament_created", "tournament", tournament.id); db.session.commit()
        return redirect(url_for("chess.admin_tournaments"))
    return render_template("admin/chess_tournaments.html", tournaments=ChessTournament.query.order_by(ChessTournament.created_at.desc()).all())


@chess_bp.route("/admin/chess/<int:tournament_id>", methods=["GET", "POST"])
def admin_tournament(tournament_id):
    tournament = ChessTournament.query.get_or_404(tournament_id)
    if not staff_for_tournament(tournament.id, roles={"tournament_admin", "age_group_admin"}): return redirect(url_for("chess.staff_login"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "age_group":
            name = request.form.get("name", "").strip()
            if name and not ChessAgeGroup.query.filter_by(tournament_id=tournament.id, name=name).first():
                db.session.add(ChessAgeGroup(tournament_id=tournament.id, name=name, gender_rule=request.form.get("gender_rule", "open"))); audit(tournament.id, "age_group_created", details=name)
        elif action == "announcement":
            title, message = request.form.get("title", "").strip(), request.form.get("message", "").strip()
            if title and message:
                db.session.add(ChessAnnouncement(tournament_id=tournament.id, title=title, message=message, is_pinned=bool(request.form.get("is_pinned"))))
                db.session.add(ChessNotification(tournament_id=tournament.id, title=title, body=message, category="announcement"))
        elif action == "publish": tournament.is_published = bool(request.form.get("is_published")); audit(tournament.id, "tournament_publish_changed", "tournament", tournament.id)
        elif action == "staff":
            name, username, password = request.form.get("name", "").strip(), request.form.get("username", "").strip(), request.form.get("password", "")
            role, age_group_id = request.form.get("role", "tournament_admin"), request.form.get("age_group_id", type=int)
            if name and username and password and role in {"tournament_admin", "age_group_admin"} and not ChessStaff.query.filter_by(username=username).first():
                staff = ChessStaff(name=name, username=username, password_hash=generate_password_hash(password), role=role); db.session.add(staff); db.session.flush()
                db.session.add(ChessStaffAssignment(staff_id=staff.id, tournament_id=tournament.id, age_group_id=age_group_id if role == "age_group_admin" else None)); audit(tournament.id, "staff_assigned", "staff", staff.id, role)
        db.session.commit(); return redirect(url_for("chess.admin_tournament", tournament_id=tournament.id))
    return render_template("admin/chess_tournament.html", tournament=tournament, announcements=ChessAnnouncement.query.filter_by(tournament_id=tournament.id).order_by(ChessAnnouncement.is_pinned.desc(), ChessAnnouncement.created_at.desc()).all())


@chess_bp.route("/admin/chess/age-groups/<int:age_group_id>", methods=["GET", "POST"])
def admin_age_group(age_group_id):
    group = ChessAgeGroup.query.get_or_404(age_group_id); tournament = group.tournament
    if not staff_for_tournament(tournament.id, group.id, {"tournament_admin", "age_group_admin"}): return redirect(url_for("chess.staff_login"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "participant":
            name = request.form.get("name", "").strip()
            if name:
                code = f"CH{group.id}-{ChessParticipant.query.filter_by(age_group_id=group.id).count()+1:05d}"
                db.session.add(ChessParticipant(age_group_id=group.id, player_code=code, name=name, gender=request.form.get("gender", ""), mobile=request.form.get("mobile", ""), school=request.form.get("school", ""), district=request.form.get("district", ""), fide_id=request.form.get("fide_id", ""), status="verified", checked_in=True)); audit(tournament.id, "participant_added", details=name)
        elif action == "room":
            name = request.form.get("name", "").strip()
            if name: db.session.add(ChessRoom(age_group_id=group.id, name=name))
        elif action == "orbiter":
            name, username, password = request.form.get("name", "").strip(), request.form.get("username", "").strip(), request.form.get("password", "")
            room_id = request.form.get("room_id", type=int)
            if name and username and password and room_id and not ChessOrbiter.query.filter_by(username=username).first():
                orbiter = ChessOrbiter(name=name, username=username, password_hash=generate_password_hash(password)); db.session.add(orbiter); db.session.flush()
                db.session.add(ChessRoomAssignment(orbiter_id=orbiter.id, room_id=room_id)); audit(tournament.id, "orbiter_assigned", "orbiter", orbiter.id, username)
        elif action == "pair":
            try:
                round_row = generate_pairings(group); audit(tournament.id, "pairings_generated", "round", round_row.id, f"Round {round_row.round_number}")
            except ValueError: pass
        elif action == "publish_round":
            round_row = ChessRound.query.get_or_404(request.form.get("round_id", type=int)); round_row.is_published = True; round_row.status = "published"; round_row.published_at = datetime.utcnow(); audit(tournament.id, "round_published", "round", round_row.id)
            db.session.add(ChessNotification(tournament_id=tournament.id, age_group_id=group.id, title=f"{group.name}: Round {round_row.round_number} pairings published", body="Open the live pairings page to find your board.", category="pairing"))
        elif action == "approve":
            pairing = ChessPairing.query.get_or_404(request.form.get("pairing_id", type=int)); pairing.score_status = "approved"; pairing.approved_by = str(session.get("admin")); pairing.approved_at = datetime.utcnow(); rebuild_standings(group.id); audit(tournament.id, "score_approved", "pairing", pairing.id)
            db.session.add(ChessNotification(tournament_id=tournament.id, age_group_id=group.id, title=f"{group.name}: Board {pairing.board_number} result approved", body=f"{pairing.white_player.name} vs {pairing.black_player.name if pairing.black_player else 'Bye'} — {pairing.result}", category="result"))
        elif action == "close":
            round_row = ChessRound.query.get_or_404(request.form.get("round_id", type=int)); round_row.status = "closed"; rebuild_standings(group.id); audit(tournament.id, "round_closed", "round", round_row.id)
        db.session.commit(); return redirect(url_for("chess.admin_age_group", age_group_id=group.id))
    rebuild_standings(group.id); db.session.commit()
    return render_template("admin/chess_age_group.html", group=group, participants=ChessParticipant.query.filter_by(age_group_id=group.id).order_by(ChessParticipant.name).all(), rooms=ChessRoom.query.filter_by(age_group_id=group.id).all(), rounds=ChessRound.query.filter_by(age_group_id=group.id).order_by(ChessRound.round_number.desc()).all(), standings=ChessStanding.query.filter_by(age_group_id=group.id).order_by(ChessStanding.rank).all())


@chess_bp.route("/chess-staff-login", methods=["GET", "POST"])
def staff_login():
    error = ""
    if request.method == "POST":
        staff = ChessStaff.query.filter_by(username=request.form.get("username", "").strip(), is_active=True).first()
        if staff and check_password_hash(staff.password_hash, request.form.get("password", "")):
            session["chess_staff"] = staff.id
            assignment = ChessStaffAssignment.query.filter_by(staff_id=staff.id).first()
            return redirect(url_for("chess.admin_tournament", tournament_id=assignment.tournament_id) if assignment else url_for("chess.public_tournaments"))
        error = "Invalid chess staff credentials."
    return render_template("chess_orbiter_login.html", error=error, staff_login=True)


@chess_bp.route("/admin/chess/age-groups/<int:age_group_id>/participants/import", methods=["POST"])
def import_participants(age_group_id):
    group = ChessAgeGroup.query.get_or_404(age_group_id)
    if not staff_for_tournament(group.tournament_id, group.id, {"tournament_admin", "age_group_admin"}): abort(403)
    upload = request.files.get("file")
    if not upload: return redirect(url_for("chess.admin_age_group", age_group_id=group.id))
    try:
        frame = pd.read_excel(upload) if upload.filename.lower().endswith((".xlsx", ".xls")) else pd.read_csv(upload)
        frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
        if "name" not in frame.columns: raise ValueError("name column is required")
        next_number = ChessParticipant.query.filter_by(age_group_id=group.id).count() + 1
        for _, row in frame.fillna("").iterrows():
            name = str(row.get("name", "")).strip()
            if not name: continue
            code = str(row.get("player_code", "")).strip() or f"CH{group.id}-{next_number:05d}"; next_number += 1
            if ChessParticipant.query.filter_by(age_group_id=group.id, player_code=code).first(): continue
            db.session.add(ChessParticipant(age_group_id=group.id, player_code=code, name=name, fide_id=str(row.get("fide_id", "")), gender=str(row.get("gender", "")), district=str(row.get("district", "")), state=str(row.get("state", "")), school=str(row.get("school", "")), club=str(row.get("club", "")), mobile=str(row.get("phone", row.get("mobile", ""))), email=str(row.get("email", "")), status=str(row.get("status", "pending")).lower(), checked_in=str(row.get("checked_in", "")).lower() in {"1", "true", "yes"}))
        audit(group.tournament_id, "participants_imported", "age_group", group.id, upload.filename); db.session.commit()
    except Exception as error:
        db.session.rollback(); current_app.logger.warning("Chess import rejected: %s", error)
    return redirect(url_for("chess.admin_age_group", age_group_id=group.id))


@chess_bp.route("/admin/chess/age-groups/<int:age_group_id>/export.xlsx")
def export_participants(age_group_id):
    group = ChessAgeGroup.query.get_or_404(age_group_id)
    if not staff_for_tournament(group.tournament_id, group.id, {"tournament_admin", "age_group_admin"}): abort(403)
    data = [{"Player Code": p.player_code, "Name": p.name, "FIDE ID": p.fide_id, "Gender": p.gender, "District": p.district, "School": p.school, "Phone": p.mobile, "Status": p.status, "Checked In": p.checked_in} for p in ChessParticipant.query.filter_by(age_group_id=group.id).order_by(ChessParticipant.name)]
    output = BytesIO(); pd.DataFrame(data).to_excel(output, index=False); output.seek(0)
    audit(group.tournament_id, "participants_exported", "age_group", group.id); db.session.commit()
    return send_file(output, as_attachment=True, download_name=f"{group.name}-participants.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@chess_bp.route("/admin/chess/age-groups/<int:age_group_id>/standings.pdf")
def standings_pdf(age_group_id):
    group = ChessAgeGroup.query.get_or_404(age_group_id)
    if not staff_for_tournament(group.tournament_id, group.id, {"tournament_admin", "age_group_admin"}): abort(403)
    buffer = BytesIO(); pdf = canvas.Canvas(buffer, pagesize=A4); y = 800
    pdf.setFont("Helvetica-Bold", 15); pdf.drawString(45, y, f"{group.tournament.name} — {group.name} Standings"); y -= 28
    pdf.setFont("Helvetica", 10)
    for row in ChessStanding.query.filter_by(age_group_id=group.id).order_by(ChessStanding.rank):
        pdf.drawString(45, y, f"{row.rank}. {row.participant.name}  |  {row.points:.1f} pts  |  Buchholz {row.buchholz:.1f}"); y -= 18
        if y < 50: pdf.showPage(); y = 800
    pdf.save(); buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{group.name}-standings.pdf", mimetype="application/pdf")


@chess_bp.route("/admin/chess/participants/<int:participant_id>/certificate.pdf")
def chess_certificate(participant_id):
    participant = ChessParticipant.query.get_or_404(participant_id); group = participant.age_group
    if not staff_for_tournament(group.tournament_id, group.id, {"tournament_admin", "age_group_admin"}): abort(403)
    certificate = ChessCertificate.query.filter_by(participant_id=participant.id, certificate_type="participation").first()
    if not certificate:
        certificate = ChessCertificate(participant_id=participant.id, certificate_number=f"CHESS-{group.tournament_id}-{participant.id:06d}")
        db.session.add(certificate); audit(group.tournament_id, "certificate_generated", "participant", participant.id); db.session.commit()
    verification = url_for("chess.verify_certificate", certificate_number=certificate.certificate_number, _external=True)
    qr_image = qrcode.make(verification); qr_buffer = BytesIO(); qr_image.save(qr_buffer, format="PNG"); qr_buffer.seek(0)
    buffer = BytesIO(); pdf = canvas.Canvas(buffer, pagesize=A4); width, height = A4
    pdf.setFont("Helvetica-Bold", 28); pdf.drawCentredString(width/2, height-130, "Certificate of Participation")
    pdf.setFont("Helvetica", 16); pdf.drawCentredString(width/2, height-220, "This certifies that")
    pdf.setFont("Helvetica-Bold", 25); pdf.drawCentredString(width/2, height-270, participant.name)
    pdf.setFont("Helvetica", 15); pdf.drawCentredString(width/2, height-320, f"participated in {group.tournament.name} — {group.name}")
    pdf.drawCentredString(width/2, height-350, f"Certificate No: {certificate.certificate_number}")
    pdf.drawImage(ImageReader(qr_buffer), width-130, 45, 80, 80); pdf.save(); buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{participant.player_code}-certificate.pdf", mimetype="application/pdf")


@chess_bp.route("/chess/certificates/<certificate_number>")
def verify_certificate(certificate_number):
    certificate = ChessCertificate.query.filter_by(certificate_number=certificate_number).first_or_404()
    return jsonify({"valid": True, "certificate_number": certificate.certificate_number, "participant": certificate.participant.name, "tournament": certificate.participant.age_group.tournament.name, "type": certificate.certificate_type, "issued_at": certificate.issued_at.isoformat()})


@chess_bp.route("/admin/chess/<int:tournament_id>/backup.zip")
def download_backup(tournament_id):
    tournament = ChessTournament.query.get_or_404(tournament_id)
    if not staff_for_tournament(tournament.id, roles={"tournament_admin"}): abort(403)
    payload = {
        "tournament": {"id": tournament.id, "name": tournament.name, "venue": tournament.venue, "system": tournament.system, "rounds": tournament.number_of_rounds},
        "age_groups": [{"id": group.id, "name": group.name, "participants": [{"code": p.player_code, "name": p.name, "fide_id": p.fide_id, "district": p.district, "school": p.school, "status": p.status, "checked_in": p.checked_in} for p in group.participants]} for group in tournament.age_groups],
        "standings": {str(group.id): json_rows(group.id) for group in tournament.age_groups},
        "exported_at": datetime.utcnow().isoformat(),
    }
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("chess-tournament-backup.json", json.dumps(payload, indent=2, default=str))
    output.seek(0); audit(tournament.id, "backup_downloaded", "tournament", tournament.id); db.session.commit()
    return send_file(output, as_attachment=True, download_name=f"chess-{tournament.id}-backup.zip", mimetype="application/zip")


@chess_bp.route("/api/chess/tournaments")
def api_tournaments():
    return jsonify([{"id": item.id, "name": item.name, "venue": item.venue, "system": item.system, "rounds": item.number_of_rounds} for item in ChessTournament.query.filter_by(is_published=True).all()])


@chess_bp.route("/api/chess/tournaments/<int:tournament_id>/age-groups/<int:group_id>/standings")
def api_standings(tournament_id, group_id):
    group = ChessAgeGroup.query.filter_by(id=group_id, tournament_id=tournament_id).first_or_404()
    if not group.tournament.is_published: abort(404)
    return jsonify({"tournament_id": tournament_id, "age_group": group.name, "standings": json_rows(group.id)})


@chess_bp.route("/api/chess/tournaments/<int:tournament_id>/live")
def api_live(tournament_id):
    tournament = ChessTournament.query.filter_by(id=tournament_id, is_published=True).first_or_404()
    since = request.args.get("since", type=int) or 0
    notifications = ChessNotification.query.filter(ChessNotification.tournament_id == tournament.id, ChessNotification.id > since).order_by(ChessNotification.id).limit(100).all()
    return jsonify({"notifications": [{"id": n.id, "title": n.title, "body": n.body, "category": n.category, "age_group_id": n.age_group_id, "created_at": n.created_at.isoformat()} for n in notifications], "server_time": datetime.utcnow().isoformat()})


@chess_bp.route("/api/chess/token", methods=["POST"])
def api_token():
    staff = ChessStaff.query.filter_by(username=request.form.get("username", "").strip(), is_active=True).first()
    if not staff or not check_password_hash(staff.password_hash, request.form.get("password", "")): abort(401)
    assignment = ChessStaffAssignment.query.filter_by(staff_id=staff.id).first()
    if not assignment: abort(403)
    return jsonify({"access_token": signed_jwt({"sub": staff.id, "role": staff.role, "tournament_id": assignment.tournament_id, "exp": int((datetime.utcnow()+timedelta(hours=8)).timestamp())}), "token_type": "Bearer", "expires_in": 28800})


@chess_bp.route("/api/chess/admin/tournaments/<int:tournament_id>/rounds")
def api_admin_rounds(tournament_id):
    claims = jwt_claims()
    if claims.get("tournament_id") != tournament_id or claims.get("role") not in {"tournament_admin", "age_group_admin"}: abort(403)
    rounds = ChessRound.query.join(ChessAgeGroup).filter(ChessAgeGroup.tournament_id == tournament_id).order_by(ChessRound.round_number).all()
    return jsonify([{"id": row.id, "age_group_id": row.age_group_id, "round": row.round_number, "status": row.status, "published": row.is_published, "pairings": [{"board": game.board_number, "white": game.white_player.name, "black": game.black_player.name if game.black_player else None, "result": game.result, "score_status": game.score_status} for game in row.pairings]} for row in rounds])


@chess_bp.route("/chess-orbiter-login", methods=["GET", "POST"])
def orbiter_login():
    error = ""
    if request.method == "POST":
        orbiter = ChessOrbiter.query.filter_by(username=request.form.get("username", "").strip(), is_active=True).first()
        if orbiter and check_password_hash(orbiter.password_hash, request.form.get("password", "")):
            session["chess_orbiter"] = orbiter.id; return redirect(url_for("chess.orbiter_dashboard"))
        error = "Invalid username or password."
    return render_template("chess_orbiter_login.html", error=error)


@chess_bp.route("/chess-orbiter", methods=["GET", "POST"])
def orbiter_dashboard():
    orbiter_id = session.get("chess_orbiter")
    if not orbiter_id: return redirect(url_for("chess.orbiter_login"))
    assignments = ChessRoomAssignment.query.filter_by(orbiter_id=orbiter_id).all(); room_ids = [a.room_id for a in assignments]
    if request.method == "POST":
        pairing = ChessPairing.query.get_or_404(request.form.get("pairing_id", type=int))
        if pairing.room_id not in room_ids or pairing.score_status != "pending": abort(403)
        result = request.form.get("result")
        if result not in RESULTS: abort(400)
        pairing.result, pairing.remarks, pairing.score_status = result, request.form.get("remarks", "").strip(), "submitted"
        pairing.submitted_by, pairing.submitted_at = str(orbiter_id), datetime.utcnow(); audit(pairing.round.age_group.tournament_id, "score_submitted", "pairing", pairing.id); db.session.commit()
        return redirect(url_for("chess.orbiter_dashboard"))
    games = ChessPairing.query.filter(ChessPairing.room_id.in_(room_ids), ChessPairing.round.has(ChessRound.status.in_(["published", "draft"]))).order_by(ChessPairing.round_id.desc(), ChessPairing.board_number).all() if room_ids else []
    return render_template("chess_orbiter.html", games=games, assignments=assignments)


@chess_bp.route("/chess")
def public_tournaments():
    return render_template("chess_public.html", tournaments=ChessTournament.query.filter_by(is_published=True).order_by(ChessTournament.tournament_date.desc(), ChessTournament.id.desc()).all(), selected=None, group=None, standings=[])


@chess_bp.route("/chess/<int:tournament_id>")
@chess_bp.route("/chess/<int:tournament_id>/<int:group_id>")
def public_tournament(tournament_id, group_id=None):
    tournament = ChessTournament.query.filter_by(id=tournament_id, is_published=True).first_or_404()
    group = ChessAgeGroup.query.filter_by(id=group_id, tournament_id=tournament.id).first() if group_id else (tournament.age_groups[0] if tournament.age_groups else None)
    standings = ChessStanding.query.filter_by(age_group_id=group.id).order_by(ChessStanding.rank).all() if group else []
    pairings = ChessPairing.query.join(ChessRound).filter(ChessRound.age_group_id == group.id, ChessRound.is_published == True).order_by(ChessRound.round_number.desc(), ChessPairing.board_number).all() if group else []
    announcements = ChessAnnouncement.query.filter_by(tournament_id=tournament.id, is_published=True).order_by(ChessAnnouncement.is_pinned.desc(), ChessAnnouncement.created_at.desc()).all()
    return render_template("chess_public.html", tournaments=[], selected=tournament, group=group, standings=standings, pairings=pairings, announcements=announcements)
