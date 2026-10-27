# Self-hosted live webinars

## Architecture

Flask remains the control plane: it authenticates the site administrator, checks completed event registrations, creates room metadata, issues short-lived LiveKit JWTs, and persists Q&A, chat, hand raises, polls, invitations, and event status. Media flows directly between browsers and a separate LiveKit WebRTC SFU. A viewer JWT is receive-only and cannot publish data; host and invited-speaker JWTs can publish audio/video but cannot bypass Flask to publish room data. Flask validates interactions, rate limits them, persists them, and fans them out using LiveKit RoomService `SendData`.

LiveKit is selected because an SFU forwards a small number of host/speaker tracks to many subscribers. A peer-to-peer mesh would require each publisher to upload a separate stream to every attendee and is unsuitable for a webinar audience. This implementation does not claim capacity for 4,000 viewers; actual capacity depends on stream count, bitrates, region, NIC throughput, UDP connectivity, client devices, and the AWS instance/network setup.

## Local development

1. Install Python dependencies: `python -m pip install -r requirements.txt`.
2. Start the separate media service: `docker compose -f compose.livekit.yaml up -d`.
3. Configure the Flask process environment (do not commit credentials):

   ```powershell
   $env:LIVEKIT_URL = "ws://127.0.0.1:7880"
   $env:LIVEKIT_API_KEY = "devkey"
   $env:LIVEKIT_API_SECRET = "devsecret"
   py -m flask --app app db upgrade
   py app.py
   ```

4. Sign in as an administrator, open **Admin → Edit Event**, enable **Live Webinar**, and save. Re-open edit and click **Open host studio**. Attendees go to `/events/<event-id>/live`, then authenticate with the event registration ID and mobile number. A completed/paid registration is required. The host enters an attendee's registration ID to invite them to publish for 30 minutes.
5. Development config uses a fixed local-only key pair and no TLS/TURN. Never reuse these keys outside a laptop. The browser SDK is pinned in the templates; use a production asset pipeline/CDN allowlist before deployment.

## Controls and safety

- Flask admin session is the host authority. Other users must match registration ID and mobile number for the same event and have a completed registration.
- Meeting tokens expire after ten minutes. Viewers cannot publish tracks or room data. Invited speakers receive publish permission only for their invitation window. Rejoin to refresh after an invitation.
- Mutations use the app's Flask-WTF CSRF protection and Flask-Limiter. Interaction text is length limited; poll options are capped; room names are server-generated. Secrets remain in the Flask server environment/Secrets Manager.
- Chat, Q&A, hand raises, poll choices, and lifecycle updates are persisted in the app database and distributed over LiveKit room data, avoiding periodic viewer polling. Review retention and moderation policy before opening the feature publicly.
- `GET /events/livekit-health` checks Flask control-plane configuration and LiveKit's HTTP signaling endpoint. Add a synthetic WebRTC connection probe and alert on it in each deployed region; signaling health does not prove UDP/TURN media connectivity.

## Deployment shape on AWS

- Flask: existing web tier behind an Application Load Balancer, multiple stateless workers, existing relational database and Redis-backed Flask-Limiter/session storage where required.
- Media: separate EC2 instances with public IPv4 and high network bandwidth; initially one LiveKit node per room placement. Use an NLB for TCP/TLS and UDP/TURN paths where supported. LiveKit needs API/WebSocket TCP 7880 behind TLS termination; ICE UDP 50000–60000 (or a deliberately configured UDP mux such as 7882); ICE/TCP 7881; optional TURN/UDP 3478 and TURN/TLS 5349. Configure advertised public IPs and security groups narrowly to these ports. Do not put SFU media on Flask/Gunicorn workers. LiveKit's self-hosting guidance recommends compute-optimized hosts and 10 Gbps networking or faster for production media nodes.
- TLS: public HTTPS/WSS certificate and reverse proxy/load balancer for signaling. Configure TURN/TLS for restrictive corporate networks and TURN/UDP where useful. TURN relay traffic consumes media egress and must be included in bandwidth and cost estimates.
- Scale-out: use Redis as LiveKit’s distributed room/message bus and deploy LiveKit nodes across availability zones/regions only after validating room placement and network LB behavior. Do not scale a node down while it owns active rooms. Viewers must be distributed across SFU nodes/regions only using LiveKit supported room placement/egress topology; one room is not automatically sharded merely by adding EC2 instances.
- Secrets: provision unique production LiveKit API key/secret in AWS Secrets Manager; inject only to Flask and LiveKit. Keep the API secret out of JS, static assets, images, logs, Compose files, and git. Rotate the development key before staging.
- Observability: ship LiveKit and Flask structured logs to CloudWatch; scrape LiveKit Prometheus metrics privately; alarm on CPU, network out, packet loss, reconnects, room/participant counts, Redis health, DB latency, token failures, and 5xx. Avoid participant names/registration IDs in metric labels.
- Availability: add RDS/Aurora multi-AZ as chosen for the app, ElastiCache Redis for rate limits and LiveKit cluster messaging, NLB/ALB health checks, and capacity-aware node draining. Store meeting interaction records under an explicit retention policy.

## Bandwidth and capacity assumptions

Viewer egress is roughly concurrent subscribers × delivered bitrate × protocol overhead. For example, 4,000 viewers receiving one 1.5 Mbps video layer is about 6 Gbps before overhead; adaptive layers, audio, retransmissions, TURN relay, and regional distribution alter that number. Estimate with actual resolutions/bitrates and measure the NIC and provider egress ceilings. Publisher upload remains limited to hosts and invited speakers, but each publisher track is forwarded many times.

The local Compose file is a single-node development service, not a production or 4,000-viewer deployment. LiveKit official self-hosting guidance documents required signaling, ICE and TURN firewall paths and distributed Redis operation; see [ports and firewall](https://docs.livekit.io/transport/self-hosting/ports-firewall/), [distributed multi-region](https://docs.livekit.io/transport/self-hosting/distributed/), [self-hosting overview](https://docs.livekit.io/transport/self-hosting/), [token grants](https://docs.livekit.io/frontends/reference/tokens-grants/), and [data packets](https://docs.livekit.io/transport/data/packets/).

## Incremental capacity validation

1. Verify one host publisher plus 10 viewers, TURN fallback, browser/device coverage, and host moderation.
2. Increase to 50, 100, and 250 viewers with realistic 720p/480p adaptive layers; measure server CPU, NIC throughput, packet loss, reconnects, Redis, and egress.
3. Repeat on the selected AWS instance type/region, with expected UDP success and forced TURN cohorts. Load tests must use real WebRTC clients; HTTP request generators do not measure SFU capacity.
4. Move through 500, 1,000, and 2,000 viewers, capacity-test node failure/draining, then target 4,000 only after topology and room placement are designed and monitored. At each step retain headroom and abort on agreed QoE thresholds.
5. Record tested bitrate profile, publisher count, region, instance sizes, packet loss/reconnect SLOs, peak egress, and cost. Publish a 4,000-viewer claim only after that exact deployed configuration passes the test.

## Current scope limits / decisions

- No production AWS infrastructure, DNS, certificates, or media service has been deployed.
- Polls enforce one vote per attendee registration and display live aggregate counts. Decide whether votes should be changeable and whether results should remain visible after a poll closes.
- “Mute speaker” uses the LiveKit RoomService mute-track API; verify the exact SDK/server version behavior in staging. Host must have a separate explicit co-host role if non-admin event organizers need control.
- Session lookup by registration ID and mobile is rate limited but shares the site's existing registration credential pattern. Consider attendee OTP verification before production at large public scale.
- Viewer estimate/attendance counts and recording/egress are not implemented. LiveKit Egress is a separate service and should be added only with storage, consent, and retention requirements.
