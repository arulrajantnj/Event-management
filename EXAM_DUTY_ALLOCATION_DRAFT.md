# Exam Duty Allocation Portal — Requirements Draft

## Purpose

Allocate examination duties to approved staff, publish their assignment, and retain an auditable record of acceptance and attendance.

## Roles

- **Super admin:** creates exam sessions, duty posts, staff records, and final allocations.
- **Exam coordinator:** proposes allocations and manages changes for assigned events.
- **Duty staff:** views, accepts or declines, and downloads the duty acknowledgement.

## Core workflow

1. Create an exam session: event, date, shift, reporting time, venue, and coordinator.
2. Add duty posts: chief superintendent, invigilator, hall superintendent, relief staff, flying squad, and data entry.
3. Import eligible staff from Excel or select registered participants.
4. Set eligibility rules: subject, school, block, availability, maximum duties, and conflict dates.
5. Allocate staff manually or using an automatic balanced allocation.
6. Review conflicts and vacancies, then publish allocations.
7. Staff receive a portal link/QR code, acknowledge the duty, and can download their duty order.
8. Coordinator records reporting/attendance and exports allocation, acceptance, and attendance reports.

## Minimum data fields

- Staff: name, mobile, email, school, designation, subject, block, availability, and optional staff ID.
- Session: event, exam name, date, shift, venue, reporting time, exam time, coordinator.
- Assignment: staff, duty type, room/hall, session, status (draft/published/accepted/declined/completed), notes.

## Decisions needed before development

1. Should duty staff use the existing participant login/QR system, or a dedicated OTP login?
2. Which duty types and hall/room allocation rules are mandatory?
3. Should staff be allowed to decline or request a swap after publication?
4. Is automatic allocation required in phase one, and which fairness/conflict rules apply?
5. What acknowledgement must be captured: checkbox, digital signature, OTP, or all three?

## Suggested phase one

Admin creates sessions and duty posts, imports/selects staff, assigns them manually, publishes a downloadable duty acknowledgement, and exports reports. Automatic allocation, swaps, SMS/WhatsApp notifications, and multi-level approval can follow in phase two.
