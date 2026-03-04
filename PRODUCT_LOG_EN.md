## Nbook.ai – Product & Dev Log (for testers on Reddit)

> This post-friendly log summarizes everything that has been built so far for **Nbook.ai**, a scheduling app designed for nail techs.  
> You can pair this text with screenshots of the client booking flow, the nail tech calendar, and the settings page.

---

## 1. What is Nbook.ai?

**Nbook.ai** is a lightweight booking and calendar system for independent **nail technicians / small nail salons**.

- **Client side**: clients can book standard services directly or request a custom design quote (with reference photos).
- **Tech side (dashboard)**: nail techs can:
  - manage bookings and quotes
  - configure weekly working hours (multiple time ranges per day)
  - see an Apple Calendar–style overview of their schedule
  - add offline / external bookings into the same calendar

**Tech stack**
- Backend: Flask (Python)
- Database: SQLite with SQLAlchemy ORM
- Frontend: Jinja + Bootstrap 5 + vanilla JavaScript
- Charts: Chart.js

---

## 2. Who I’m looking for (for this Reddit post)

I’m looking for **real nail techs / salon owners** who:

- want a simple way to manage their schedule across channels (online bookings + DMs + walk-ins)
- like the **Apple Calendar** style week/month view
- are okay with testing an early product and giving feedback

You’ll get:

- Free early access
- Priority on feature requests
- Direct contact with the solo dev (me) to tune the product for nail workflows

---

## 3. Current status – what’s already working

### 3.1 Authentication & accounts
- Email/password registration and login for nail techs
- Session management via Flask-Login
- Each nail tech gets:
  - a **public booking page** for clients
  - a **private dashboard** for managing everything

### 3.2 Client-side (what your clients see)
- **Standard booking flow**
  - Choose a service type (e.g. simple mani, gel, extension) with a base duration and price
  - Pick a date
  - System loads only **available time slots** based on your work schedule + existing bookings
  - Optional: tick **“removal”** and/or **“builder/extension”** → each adds **+30 min** to the booking duration; the slot calculation respects this
  - Optional: client name, contact info, notes
  - Optional: upload up to **9 reference images** (inspiration photos)
- **Custom quote flow**
  - Client uploads inspiration photos and writes free-form requirements
  - Can tick *removal* / *builder* flags
  - Creates a **Quotation Request** for the nail tech side to review & reply with price + duration
- **After booking**
  - Client gets a **booking detail page** with:
    - date & time
    - type (standard vs from quote)
    - their own contact info
    - their notes
    - all uploaded reference images (clickable thumbnails)
    - **your contact info** from your shop profile (e.g. WeChat / phone)
- **My Orders (client history)**
  - Simple list of recent quotes and bookings, grouped by status

### 3.3 Nail tech dashboard (what you see)

#### 3.3.1 Overview (Apple Calendar–style)
- Top stats:
  - **Today’s bookings**
  - **This week’s bookings**
  - **Pending quotes**
- 30-day bookings trend chart:
  - Chart.js bar chart for bookings from *15 days before today* to *14 days after today*
  - Y-axis is integer-only
- **Calendar view**
  - Toggle between:
    - **Month view** (full month grid, Mon–Sun)
    - **Week view** (time-grid from 06:00–23:00 across 7 days)
  - Date navigation:
    - Previous/next month or week
    - “Today” shortcut
  - Each booking is a colored block:
    - Blue = standard booking
    - Cyan = custom (from quote)
    - Grey = “external” (offline/other channel)
  - **Click any block → opens booking detail page**
- **Add external bookings directly in the calendar**
  - Small form above the calendar:
    - pick date, start time, end time, client label, note
  - Saves as a booking with a special `[外部渠道]` tag in notes
  - Uses the same conflict-check logic as normal bookings:
    - converts times to 30-min slots
    - rejects overlapping intervals with a warning

#### 3.3.2 Shop & schedule settings
- **Shop profile**
  - Shop name
  - Description
  - Contact (WeChat / phone etc.) – this auto-syncs to the client booking detail page
- **Service list**
  - For each service type:
    - base duration (minutes)
    - base price (integer currency)
  - Used as defaults when:
    - calculating standard booking durations
    - creating quotes (base duration can be extended by removal/builder)
- **Work schedule (weekly availability)**
  - One table showing **all existing work slots**, sorted by weekday and start time
  - Each row:
    - Day of week (Mon–Sun)
    - Start time + end time
    - Enabled checkbox
  - Supports **multiple slots per day**, e.g.:
    - Monday 08:00–12:00
    - Monday 14:00–18:00
  - Add new slot row:
    - Choose weekday (Mon–Sun)
    - Default time range (10:00–20:00, editable)
    - Enabled checkbox
  - You can add **as many slots as you want** before saving.

#### 3.3.3 Bookings & quotes
- **Bookings list**
  - Shows last 100 bookings
  - Columns: date, time, status, client name, type (standard/custom), images, actions
  - Thumbnails for reference images:
    - Click → opens Bootstrap modal with large view
    - Modal includes **“Download image”** button
  - “View details” button → opens **nail-tech booking detail page**
- **Booking detail (nail tech side)**
  - Booking info: date, time, duration, status, type, service
  - Client info: name, contact, notes
  - Flags: “needs removal”, “needs builder”
  - Reference images with the same full-size + download modal as in the list
- **Quotes list & details**
  - See incoming custom quotes with status:
    - pending
    - quoted
    - converted
    - expired
  - Quote detail:
    - client request text
    - flags: removal / builder
    - your reply: price + duration
  - When you send a quote:
    - Total duration = **service base duration + 30 min if removal + 30 min if builder**
    - Stored as `quoted_duration_minutes`
  - Client later books from this quote:
    - `available_slots` uses `quoted_duration_minutes` to generate valid slots

---

## 4. Scheduling & time logic (how conflicts are avoided)

### 4.1 Time slots
- Internal time unit = **30 minutes**
- Every work schedule and booking is converted to discrete slots:
  - e.g. 10:00–11:30 → 3 slots
- Conflict check:
  - new booking slots must not overlap with any existing booking slots on the same day

### 4.2 Work schedule → available slots
For each day:

1. Get **all enabled work schedules** for that weekday (supports multiple ranges).
2. If none are enabled but there are saved schedules, it falls back to all saved ones (for debugging / safety).
3. For each schedule:
   - Convert start/end times to slots.
   - Slide a window of `slots_needed` across the range.
   - Check if any of those slots are already occupied by other bookings.
   - If free → add as an available option: `"HH:MM – HH:MM"`.

### 4.3 Extra time for removal / builder
- Standard service has a **base duration** (e.g. 60 min).
- If client ticks:
  - “removal” → +30 min
  - “builder/extension” → +30 min
- `available_slots` receives these flags via query parameters and adjusts the **duration** before generating slots:
  - duration = base_duration [+30] [+30]
- The booking record stores the **actual total duration** in `duration_minutes`.

---

## 5. Implementation log – major steps (grouped)

This is a grouped summary of the actual code changes we made while building Nbook.ai.

### Step 1 – Core models & app factory
- **File:** `app/models.py`
  - Added models:
    - `User`, `ServiceType`, `WorkSchedule`, `QuotationRequest`, `Booking`, `ShopProfile`, `Event`, `DailyStats`, `Reminder`
  - Key field:
    - `Booking.image_paths` – comma-separated filenames for reference images
- **File:** `app/__init__.py`
  - App factory `create_app()`
  - Initialize DB, migrations, login manager, i18n
  - Ensure instance folder and upload folder exist
  - **Lightweight auto migration**:
    - On startup, inspect `booking` table
    - If `image_paths` column is missing, run `ALTER TABLE ... ADD COLUMN image_paths TEXT`

### Step 2 – Basic booking & public pages
- **File:** `app/routes/booking.py`
  - `booking_home`:
    - Shows services
    - Standard booking form
    - Custom quote form
  - `standard_booking`:
    - Validates service + date + time slot
    - Checks conflicts
    - Saves `Booking` entry
  - `custom_quote`:
    - Stores `QuotationRequest` with text + flags
  - `booking_detail` (client side):
    - Shows booking info + reference images
    - Fetches shop contact from `ShopProfile` and passes to template
- **File:** `templates/public/booking_home.html`
  - Form for standard booking:
    - service select, date, time slot select
    - removal/builder checkboxes
    - client info, notes
    - file input for reference images
  - Form for custom quotes:
    - images + notes + flags
  - JS:
    - handles dynamic loading of available slots via `/available-slots`

### Step 3 – Work schedule editor (multi-range per day)
- **File:** `app/routes/dashboard.py` (`settings` route)
  - Query all `WorkSchedule` entries for current user, ordered by weekday + start time
  - On POST:
    - Update each existing schedule’s start/end/enabled
    - Optionally add **a new schedule row** based on `new_schedule_day`, `new_schedule_start`, `new_schedule_end`, `new_schedule_enabled`
    - No restriction on “one schedule per day” → supports multiple ranges for the same weekday
- **File:** `templates/dashboard/settings.html`
  - Work schedule table:
    - One row **per schedule entry**
    - Shows weekday label (Mon–Sun), time inputs, enabled checkbox
  - “Add new schedule” row:
    - Dropdown for weekday
    - Time inputs with defaults
    - Enabled checkbox

### Step 4 – Available slots logic & debugging
- **File:** `app/routes/booking.py`
  - `_generate_available_slots`:
    - Handles multiple `WorkSchedule` entries per day
    - Builds `occupied` slot set from existing bookings
    - Generates non-conflicting time windows
  - `available_slots`:
    - Accepts `service_id`, `date`, optional `duration` override
    - For standard bookings:
      - uses service base duration
      - adds 30/30 min based on `needs_removal` / `needs_builder`
    - For quotes:
      - uses `quoted_duration_minutes` from `QuotationRequest`
  - `_agent_debug_log` helper:
    - Writes NDJSON logs to `.cursor/debug.log`
    - Logs:
      - current schedules
      - slot generation details
      - reasons for “no available slots”

### Step 5 – Image upload, display, and migration
- **File:** `app/routes/booking.py`
  - `standard_booking`:
    - accepts multiple files `booking_images`
    - saves up to 9 images under `static/uploads`
    - concatenates filenames into `Booking.image_paths`
  - `custom_quote`:
    - same idea for `QuotationRequest.image_paths`
  - `book_from_quote`:
    - when a quote is converted to a booking:
      - copies `image_paths` & `client_notes` into the `Booking`
- **File:** `templates/dashboard/bookings.html`
  - Shows image thumbnails in the bookings list
  - On click:
    - opens modal with large image and “Download” button
- **File:** `templates/public/booking_detail.html`
  - Shows images for the client (clickable thumbnails)

### Step 6 – Apple Calendar–style overview
- **File:** `app/routes/dashboard.py` (`overview` route)
  - Computes:
    - `today_count`, `week_count`, `pending_quotes`
    - 30-day bookings chart data
  - Calendar-specific:
    - `view_type` (month/week)
    - `view_date` (current date in focus)
    - Calculates:
      - `calendar_start`, `calendar_end`
      - `calendar_bookings` (bookings in visible range)
      - `bookings_by_date` (dict keyed by ISO date)
      - `calendar_dates` (month grid cells, including blanks)
      - `week_dates` (7 days for week view)
      - `prev_nav_date`, `next_nav_date` for navigation
- **File:** `templates/dashboard/overview.html`
  - Top stats + 30-day Chart.js bar chart
  - **Calendar header**:
    - month/week toggle buttons
    - prev/next buttons
    - Today button
  - **External booking form** above the calendar
  - **Month view:**
    - 7-column table, Monday-first
    - Each cell:
      - day number (today highlighted)
      - badge with booking count
      - up to 3 event pills with time + mini label
      - “+N more” indicator when there are many bookings
  - **Week view:**
    - Left column = hour labels
    - 7 columns = week days
    - For each booking:
      - computes relative top/height inside hour cell based on minutes
      - draws a colored block with start time + name
  - All event blocks are clickable `<a>` elements to the booking detail page.

### Step 7 – Nail-tech booking detail page
- **File:** `app/routes/dashboard.py`
  - Added:
    - `@dashboard_bp.route("/bookings/<order_no>")`
    - Fetches `Booking` by `order_no` and `current_user.id`
    - Renders `dashboard/booking_detail.html`
- **File:** `templates/dashboard/booking_detail.html`
  - Shows:
    - booking meta
    - client info
    - flags (removal / builder)
    - reference images with modal & download
  - Links back to:
    - bookings list
    - calendar overview

### Step 8 – Contact sync to client view
- **File:** `app/models.py` (`ShopProfile`)
  - `contact` field for WeChat/phone etc.
- **File:** `app/routes/booking.py` (`booking_detail` for client)
  - Fetches `artist.shop_profile.contact` as `shop_contact`
  - Passes it to `public/booking_detail.html`
- **File:** `templates/public/booking_detail.html`
  - Shows:
    - client contact (“Your contact”)
    - nail tech contact (“Nail tech contact”)

---

## 6. How to test (what I’d like you to try)

When I share the demo link + credentials with you, here’s what you can try:

- As a **nail tech**:
  - Set up your **shop profile** and contact info
  - Configure a realistic weekly schedule:
    - multiple time ranges per day (e.g. morning + afternoon)
    - some days off
  - Create a few **services** with different durations
  - Add some **external bookings** from DMs / walk-ins
  - Play with the **month/week calendar**, clicking into bookings
  - Check if the layout feels close enough to **Apple Calendar**
- As a **client** (or fake client):
  - Go to the public booking page
  - Make:
    - a simple standard booking
    - a booking with removal + builder checked
    - a custom quote request with reference images
  - Confirm:
    - available time slots match your configured schedule
    - durations look reasonable
    - images show up both for you and on the nail-tech side

Then, please tell me:
- What feels confusing?
- What’s missing for your real workflow?
- Would you actually switch from your current method (notes app, paper, etc.)?

---

## 7. Roadmap / next steps

### Short term
- Booking status management (e.g. complete/cancel)
- Basic reminders (e.g. daily agenda)
- Better mobile layout for both client & dashboard

### Medium term
- Notification system (email / WhatsApp / SMS, depending on region)
- Export / backup bookings data
- More flexible pricing/discount logic

### Long term
- Multi-tech / multi-seat support (for small salons)
- Analytics (retention, popular designs, etc.)
- Optional online payment integration (if testers actually want it)

---

## 8. How this doc is meant to be used on Reddit

- You can copy-paste most of this into a Reddit post.  
- Before posting, I suggest you:
  - Add **2–4 screenshots** (calendar view, client booking, settings).
  - Add:
    - how testers can get access (DM you, link to form, etc.)
    - any language/region focus (e.g. primarily Chinese-speaking nail techs, time zone).

If you tell me your exact subreddit and angle (e.g. “solo nail techs who want better scheduling”), I can also help you draft the post title and intro paragraph. 

