# CareerLens — The Complete Project Guide

*A learning guide for the person who built it.*

This guide explains the whole CareerLens project: what every folder and file
is for, how a click in the browser becomes a row in the database, how the AI
parts make their decisions, how the plans and payments work, and how to run,
test, change and deploy it. It also explains the small things, like why a
field is called `sub` or why a wrong job id returns 404 instead of 403.

It is written for a **beginner who wants to understand, not just run** the
project. So besides describing the code, it tells the story of how the
project got here ([Part 0](#part-0--the-story-of-careerlens-from-the-first-line-to-today)),
stops regularly for a **Teacher's note** that explains the idea behind a
piece of code, lists every serious mistake made along the way and what it
taught ([Part 15](#part-15--challenges-we-faced-and-what-to-watch-out-for-next-time)),
and ends with questions to test yourself ([Part 16](#part-16--check-your-understanding)).

Every statement here was checked against the code as it is now (14 September
2026). When the code does something surprising or has a known weakness, the
guide says so; see [Part 12](#part-12--known-issues-and-technical-debt).

---

## Start here: how to learn from this guide

This is a long document, and you are not meant to read it in one sitting.
Pick the path that matches what you want today.

| If you want to… | Read, in this order |
|---|---|
| Understand the project from zero | Part 0 (the story) → Part 1 → Part 2 (words) → Part 3 (big picture) → Part 9 (journeys) |
| Understand how the backend really works | Part 6, especially [6.9](#69-code-lessons-reading-the-backend-line-by-line) (code lessons) → Part 5 (database) → Part 10 (security) |
| Understand the AI | Part 7, then [7.13](#713-code-lessons-the-maths-in-the-code) (the maths in the code) |
| Understand the frontend | Part 8, especially [8.6](#86-reading-one-pages-code-job-detail) and [8.7](#87-the-react-lessons-that-cost-us-a-bug) |
| Understand plans, limits and payments | [Part 14](#part-14--payments-and-subscriptions-every-stage) (every stage, from pricing page to database) |
| Avoid repeating past mistakes | [Part 15](#part-15--challenges-we-faced-and-what-to-watch-out-for-next-time) |
| Change something | Part 13 (recipes) + Appendices |

**How to study code with this guide** (the method that works best):

1. **Follow one request end to end.** Choose one thing a user does, for
   example "upload a CV". Find the page that does it (Part 8), the API route
   it calls (Appendix A), the route's code in `main.py`, the services it
   uses, and the tables it writes (Part 5). Once you can follow one request
   all the way, every other request looks familiar.
2. **Read with the code open beside you.** Every section names the file and
   function. Open it and read along. The guide explains *why*; the code shows
   *exactly how*.
3. **Change something small and watch it break.** Change a threshold,
   rename a field, remove a check, then run the tests (Part 11.5). A failing
   test tells you what that line was protecting. Then undo it.
4. **Use `/docs`.** With the backend running, <http://127.0.0.1:8000/docs>
   lets you call every route by hand and see the exact JSON.

> **Teacher's note.** Beginners often try to understand a project by reading
> files from top to bottom. That rarely works, because a file is organised
> for the computer, not for a learner. Organise your reading around
> *questions* instead: "what happens when I click Apply?", "who is allowed to
> see this CV?", "where does the match score come from?". Each question pulls
> you through exactly the code you need, in the order it runs.

---

## Contents

- [Start here: how to learn from this guide](#start-here-how-to-learn-from-this-guide)
- [Part 0 — The story of CareerLens, from the first line to today](#part-0--the-story-of-careerlens-from-the-first-line-to-today)
- [Part 1 — What CareerLens is](#part-1--what-careerlens-is)
- [Part 2 — Words you need (glossary)](#part-2--words-you-need-glossary)
- [Part 3 — The big picture: how the pieces connect](#part-3--the-big-picture-how-the-pieces-connect)
- [Part 4 — Every folder and file](#part-4--every-folder-and-file)
- [Part 5 — The database](#part-5--the-database)
- [Part 6 — The backend (FastAPI)](#part-6--the-backend-fastapi)
- [Part 7 — The AI and matching engine](#part-7--the-ai-and-matching-engine)
- [Part 8 — The frontend (Next.js)](#part-8--the-frontend-nextjs)
- [Part 9 — Every user journey, step by step](#part-9--every-user-journey-step-by-step)
- [Part 10 — Security: what is protected and how](#part-10--security-what-is-protected-and-how)
- [Part 11 — Running, testing and deploying](#part-11--running-testing-and-deploying)
- [Part 12 — Known issues and technical debt](#part-12--known-issues-and-technical-debt)
- [Part 13 — How to change things (recipes)](#part-13--how-to-change-things-recipes)
- [Part 14 — Payments and subscriptions, every stage](#part-14--payments-and-subscriptions-every-stage)
- [Part 15 — Challenges we faced, and what to watch out for next time](#part-15--challenges-we-faced-and-what-to-watch-out-for-next-time)
- [Part 16 — Check your understanding](#part-16--check-your-understanding)
- [Appendix A — Every API route](#appendix-a--every-api-route)
- [Appendix B — Every environment variable](#appendix-b--every-environment-variable)
- [Appendix C — Every test file](#appendix-c--every-test-file)

---

## Part 0 — The story of CareerLens, from the first line to today

Before looking at any code, it helps to know *how the project became what it
is*. Almost every odd-looking detail in the code (a comment warning about
something, a check that seems paranoid, a table that seems unnecessary) is
there because something went wrong once. Knowing the story turns those
details from mysteries into lessons.

The dates below come from the Git history and the working notes kept during
development. Most of the early work happened **before** the project was put
on GitHub, which is why the repository has only a handful of commits.

### Stage 1: the first working version (before 23 August 2026)

The first version already did the core job:

- a **Next.js** frontend and a **FastAPI** backend;
- **CV upload** with PDF text extraction;
- **AI analysis**: skills pulled from the CV, a match score against a job,
  missing skills and recommendations, with Google **Gemini** helping;
- **embeddings** (with the `sentence-transformers` library) for
  "meaning-based" matching;
- a dashboard, analysis history, and login.

It worked when used the intended way. That is the normal state of a first
version: the *happy path* works, and the problems are hidden in the paths
nobody has tried yet. Several were serious, and they were found one by one
over the following weeks.

> **Teacher's note.** "It works" usually means "it works for me, the way I
> use it". A real application also has to survive users who mistype, send
> strange input, use it at the same time, or try to break it on purpose. Most
> of the rest of this story is the project learning that difference.

### Stage 2: rules of the road and the first security pass (23 August)

Two things happened on 23 August.

**A way of working was agreed.** From then on, every change followed the same
rules: *inspect the existing code first, explain the plan before
implementing, prefer small increments to rewrites, and explain what changed
and why* (teaching mode). Many decisions in this project, such as extending
existing pages instead of building new ones, come from those rules.

**The first security holes were closed:**

- The JWT signing key was **hardcoded** in `services/auth.py` as the text
  `"change-this-in-production"`. Anyone who read the code could have created
  a valid login token for *any* account, including an admin. It now comes
  from the environment, and the app refuses to start with a weak or
  placeholder key (see [6.2](#62-configpy--settings-and-secrets)). Changing it
  logged everyone out once, which was the fix working.
- `.gitignore` was **almost empty**. It did not cover `.env`, which holds the
  Gemini key and the database password. Nothing had been committed yet, but
  the first `git add .` would have published them.
- Start-up was **silently broken** by a PostgreSQL detail: the `users` table
  belonged to the `postgres` superuser, not to the app's own database user,
  so the start-up code's `ALTER TABLE users …` failed. On PostgreSQL a failed
  statement **aborts the whole transaction**, so every statement after it
  failed too. The fix was to give each schema change its own transaction and
  to stop altering `users` at all. New per-person columns have gone on
  `user_profiles` ever since.

### Stage 3: making it correct, not just running (late August to 4 September)

This stage was about the difference between *producing an answer* and
*producing the right answer*.

- **"Failed to fetch".** Every browser request failed while `curl` worked
  fine. The frontend had moved to port **3001** (port 3000 belongs to another
  project on the development machine), but the backend's allowed origins
  (**CORS**) only listed port 3000. The browser blocked every response. A
  related trap: editing `.env` does *not* restart `uvicorn --reload`, which
  only watches `.py` files.
- **"The skills are in my CV but the AI can't find them."** Three silent
  bugs worked together. The experience section was recognised only if its
  heading started with the word "experience", so "PROFESSIONAL EXPERIENCE"
  or "Work History" produced *nothing*. The skill list was cut to 12 items
  (`combined[:12]`), dropping whichever skills were found last. And the
  vocabulary had only 114 terms. The fix was the section splitter
  (`cv_sections.py`), evidence tracking (`skill_evidence.py`, which records
  *where* each skill was found), and about 390 terms (see 7.2 and 7.3).
- **Honest outputs.** The parser used to *invent* education text ("Bachelor's
  degree in Computer Science or related field") for anyone whose CV contained
  the word "degree". Skills were labelled "advanced / beginner" purely by
  their position in a list. Both were replaced with things the code can
  actually know.
- **Better advice.** The flat list of repetitive recommendations became
  grouped, prioritised guidance (`guidance.py`), plus real learning links
  from public APIs (`learning_resources.py`).
- **Employer features.** Employers could now edit a posted job (a
  "revision ledger" editor showing old → new), and interviews gained real
  joining details (video link, phone, address) instead of one free-text
  field.
- **UI work.** 33 headings were the same 16 px as body text, and 13 pages used
  none of the shared styles. A type scale (`page-title`, `section-title`…)
  was added to `globals.css` and applied to the existing pages. One lesson
  was learned the hard way: when asked for a *UI improvement*, building new
  screens while leaving the existing ones untouched does not count as one.

Around the same time, and before the move to GitHub, a long list of
**hardening** fixes was made. You will meet each one later (Part 12.1 lists
them all): anyone could register as an **admin** by sending `"role":
"admin"`; login answered more than 100× faster for unknown emails, which revealed
who had an account (a **timing attack**); a file called `../../evil.txt`
could be written outside the upload folder (**path traversal**); deleting a
user crashed with a 500 because of **foreign keys**; messages were sent to
the wrong person because a **CV id was treated as a user id**.

### Stage 4: GitHub, PostgreSQL only, migrations and deployment (11–12 September)

- **11 September.** The project went on GitHub (`first commit`, then `Add
  CareerLens application`: 111 files).
- **A near-disaster.** The frontend's `components/` folder (14 files that
  every page depends on) had **never been committed**, and it went missing.
  It was rebuilt byte for byte from the Next.js build caches in `.next/`,
  which happened to contain the source code inside their "source maps". That
  worked by luck. The real lesson: **commit early and often**; code that
  exists only on one disk is one mistake away from gone.
- **PostgreSQL only.** The app used to fall back to a SQLite file when
  `DATABASE_URL` was missing. SQLite behaves differently from PostgreSQL
  (types, constraints, locking), so bugs could hide in development and only
  appear in production. SQLite was removed everywhere; even the tests now use
  a throwaway PostgreSQL *schema* (see 11.5).
- **Real migrations.** The old start-up code could only *add* columns. It
  was replaced by **Alembic** migrations (`0001` baseline, `0002` password
  reset and verification), applied automatically at start-up, with a careful
  hand-over for the existing database (see 6.3).
- **Fit on a small server.** PyTorch (under `sentence-transformers`) pushed
  memory to about 577 MB, over the 512 MB of a small Render instance. The
  same model now runs on **ONNX Runtime** at about 330 MB. The vectors were
  checked to be identical within 0.0000002 before switching (see 7.6).
- **Accounts grew up.** Password reset and email verification were added,
  with hashed one-time links and "sign out everywhere". `passlib`, an
  abandoned library, was replaced by `bcrypt` directly.
- **Deployment.** `render.yaml` for the backend (with a persistent disk for
  uploads), Vercel for the frontend, and 26 new browser tests (Playwright),
  because the original ones had been lost too.

### Stage 5: plans and payments (13 September)

The pricing page had always *shown* Free, Pro and Enterprise plans, but none
of it was real: every button went to the registration page, nothing was
limited, and the FAQ promised things that did not exist (a free trial, PayPal,
refunds, student discounts, cover letters).

A complete subscription system was built with **Stripe in test mode**:
checkout, signed webhooks, a local copy of the subscription state, the
customer portal, and server-side plan limits. The main rule was: **the
browser can never make itself Pro**; only the payment provider, verified by
the server, can. The pricing page was rewritten to tell the truth, and
cover-letter generation is marked "Coming soon" because it does not exist
yet. [Part 14](#part-14--payments-and-subscriptions-every-stage) explains every
stage.

### Stage 6: adjusting the limits, and leaving Stripe (14 September)

- The Free plan was changed to **2 CV uploads, 5 job-match analyses and 2
  Career Insights sessions per month**. Career Insights had been Pro-only;
  now Free users get two 24-hour sessions a month.
- **Stripe accounts cannot be opened from Algeria**, where the project is
  developed. The decision was to **leave Stripe**: the integration stays in
  the code as a working, tested *sample*, but with no Stripe keys configured
  it is switched off. Everyone is on the Free plan, the limits apply, and the
  pricing page shows "Payments not available yet" to signed-in users. A local
  Algerian provider (Chargily Pay, with EDAHABIA and CIB cards) is the
  realistic path if real payments are ever needed (see 14.12).
- This guide was rewritten to teach the project.

### What the story teaches, in one paragraph

Each stage fixed a different kind of problem: *secrets* (stage 2),
*correctness* (stage 3), *safety against misuse* (stage 3's hardening),
*durability and deployment* (stage 4), and *trust boundaries* (stage 5:
never let the client decide what it is allowed to do). Almost none of these
problems showed up when the app was used normally. They showed up only when
someone asked "what if…?": what if the CV's heading is different, what if
someone sends `"role": "admin"`, what if two requests arrive at the same
moment, what if the file is lost? Learning to ask "what if…?" *before* the
problem happens is most of what separates a first version from a real
application. [Part 15](#part-15--challenges-we-faced-and-what-to-watch-out-for-next-time)
turns each of these into a warning for next time.

---

## Part 1 — What CareerLens is

CareerLens is a career platform with **three kinds of user**:

| Role | Who they are | What they can do |
|---|---|---|
| **Job seeker** (`job_seeker`) | Someone looking for work | Upload a CV, see what skills it shows, get matched to jobs, analyse their CV against one job, save jobs, apply, see career insights, chat with the CareerLens assistant, confirm interviews, message employers, edit their profile |
| **Employer** (`employer`) | Someone hiring | Set up a company profile, post jobs, edit postings, see applicants, accept or reject them, search candidates, schedule interviews, message candidates |
| **Admin** (`admin`) | The person running the site | See system statistics, list every user, look at one user in detail, delete users |

There is also a **public** side that needs no account: the landing page,
About, How it works, Pricing, FAQ, Contact, and a **free demo analysis** where
anyone can upload a CV and paste one job description.

### The idea behind the AI

The project deliberately does **not** send everything to a large language model
(LLM). It uses the cheapest tool that gives a trustworthy answer, in layers:

1. **Deterministic rules** (plain Python code): read the text of a CV, split it
   into sections, and find skills from a fixed vocabulary of 390 technical
   terms plus soft and general skills.
2. **Embeddings** (a small neural network, `all-MiniLM-L6-v2`): turn text into
   a list of 384 numbers so that "similar meaning" becomes "numbers that are
   close together". This is how CareerLens finds jobs similar to a CV even
   when they use different words.
3. **An LLM** (Google Gemini `gemini-2.5-flash`), **optional**: used to read
   job descriptions more intelligently, read text from CV images, and write
   chat answers. **Every LLM use has a non-LLM fallback**, so the app works
   with no API key at all.
4. **Retrieval-grounded chat**: the assistant first looks up real facts (your
   CV, real job postings) and only then answers, and it shows you which facts
   it used.

### The plans

Every job seeker is on a **plan**. The server decides which one, from its own
database, on every request (Part 14 explains how).

| | Free | Pro | Enterprise |
|---|---|---|---|
| CV uploads | 2 per month | unlimited | unlimited |
| Job-match analyses (`POST /api/analyze`) | 5 per month | unlimited | unlimited |
| Career Insights | 2 sessions per month (24 h each) | unlimited | unlimited |
| Job recommendations, chat, applying, saving jobs | yes | yes | yes |
| Cover letter generation | – | "Coming soon" (not built) | "Coming soon" |
| How you get it | automatically | Stripe checkout (**currently switched off**) | "Contact Sales" |

Monthly allowances reset on the 1st of each month (UTC). **Right now nobody
can buy Pro**: the Stripe integration is in the code but has no keys, so every
user is on Free. See [Part 14](#part-14--payments-and-subscriptions-every-stage).

---

## Part 2 — Words you need (glossary)

Read this once; the rest of the guide uses these words freely.

**Web basics**

- **Frontend**: the part that runs in the user's browser (the pages you see).
  Here it is a Next.js app.
- **Backend**: the program on a server that stores data and makes decisions.
  Here it is a FastAPI app written in Python.
- **API** (Application Programming Interface): the set of URLs the backend
  offers. The frontend talks to the backend only through the API.
- **Endpoint / route**: one URL plus one method, e.g. `POST /api/auth/login`.
- **HTTP method**: the verb of a request. `GET` = read, `POST` = create or do
  an action, `PUT` = replace, `PATCH` = change part of something, `DELETE` =
  remove.
- **JSON**: the text format used for data sent between frontend and backend,
  e.g. `{"email": "a@b.com"}`.
- **Status code**: the number in every response that says what happened:
  `200` OK · `201` Created · `400` bad input · `401` not logged in / bad token
  · `402` your plan doesn't cover this (see Part 14)
  · `403` logged in but not allowed · `404` not found · `405` wrong method for
  this URL · `413` file too large · `422` the request body has the wrong shape
  · `429` too many requests (rate limited) · `500` server crashed.
- **Origin**: scheme + host + port, e.g. `https://careerlens.vercel.app` or
  `http://localhost:3001`. Two URLs with different origins are "different
  sites" to a browser.
- **CORS** (Cross-Origin Resource Sharing): a browser safety rule. A page from
  origin A may only read responses from origin B if B says "A is allowed".
  The frontend and backend are on different origins, so the backend must list
  the frontend's origin in `CORS_ORIGINS`. If it doesn't, the browser blocks
  every request and the UI shows only "Failed to fetch".

**Security**

- **Hashing**: turning a password into a scrambled string you cannot turn back.
  The database stores only the hash; at login the typed password is hashed
  again and compared.
- **bcrypt**: a hashing method that is deliberately slow (about 0.3 s), so an
  attacker who steals the database cannot try billions of guesses quickly.
- **JWT** (JSON Web Token): a signed piece of text the backend gives you at
  login. It says "this is user 42, valid until tomorrow" and is signed with
  `SECRET_KEY`. Anyone can *read* it, but only someone with the key can
  *create* a valid one.
- **Bearer token**: sending the JWT in every request as the header
  `Authorization: Bearer <token>`.
- **Rate limiting**: refusing requests when one person sends too many too fast
  (e.g. password guessing).

**Data**

- **PostgreSQL**: the database server. It stores data in **tables** made of
  **rows** and **columns**.
- **Primary key**: the unique id of a row (`id`).
- **Foreign key**: a column that points to another table's primary key, e.g.
  `cvs.user_id → users.id`. The database refuses to break these links.
- **Schema (database)**: a named folder of tables inside one database. The
  normal one is `public`. The tests create a throwaway one.
- **ORM** (Object-Relational Mapper): lets Python code use classes instead of
  SQL. This project uses **SQLAlchemy**: `db.get(User, 5)` instead of
  `SELECT * FROM users WHERE id = 5`.
- **Model (SQLAlchemy)**: a Python class that describes one table.
- **Session**: SQLAlchemy's "conversation" with the database. You make changes
  in a session and `commit()` saves them all at once, or `rollback()` undoes
  them.
- **Migration**: a small numbered script that changes the database structure
  (create a table, add a column…). This project uses **Alembic**, and the
  server applies any migrations the database doesn't have yet every time it
  starts (see [6.3](#63-what-happens-when-the-server-starts)).

**Python/FastAPI**

- **Pydantic schema**: a Python class describing the *shape* of JSON the API
  accepts or returns. FastAPI checks every request against it and answers
  `422` automatically if it doesn't fit. (Not the same thing as a database
  schema.)
- **Dependency (`Depends`)**: a function FastAPI runs before your route, e.g.
  `get_current_user_id` reads and checks the token and gives the route the
  user's id.
- **Uvicorn**: the web server program that runs a FastAPI app.
- **Virtual environment (`.venv`)**: a private folder of Python packages for
  one project.
- **`requirements.txt`**: the list of Python packages (with exact versions) to
  install.
- **Environment variable**: a setting given to a program from outside its code,
  e.g. `DATABASE_URL`. Secrets live here, never in the code.
- **`.env` file**: a local text file of environment variables, loaded by
  `python-dotenv`. It is in `.gitignore` and must never be committed.
- **Cache / `lru_cache`**: remembering the result of a slow function so the
  next identical call is instant.

**Frontend**

- **Next.js**: a React framework. Each folder under `app/` becomes a URL.
- **React component**: a function that returns what should be on screen.
- **State (`useState`)**: a value a component remembers; changing it redraws
  the screen.
- **Effect (`useEffect`)**: code that runs after the component appears on
  screen, e.g. "load the job from the API".
- **Context**: a way to share a value (like "who is logged in") with every
  component without passing it by hand.
- **Client component** (`"use client"` at the top): runs in the browser. Every
  page in this project is a client component.
- **`localStorage`**: a small storage area in the browser that survives page
  reloads. CareerLens keeps the login token here.
- **Build time vs run time**: `npm run build` produces the finished site
  (build time). `NEXT_PUBLIC_*` variables are **copied into the code at build
  time**, so changing one requires a rebuild.
- **Tailwind CSS**: styling written as class names, e.g.
  `className="text-sm text-neutral-400"`.

**AI**

- **Embedding / vector**: a list of numbers that represents the meaning of a
  text. Here, 384 numbers per text.
- **Cosine similarity**: a number from -1 to 1 saying how similar two vectors
  are (1 = same meaning). Because every vector here is *normalised* (length
  1), cosine similarity is just a multiply-and-add (a "dot product").
- **LLM**: a large language model (Gemini).
- **Grounding**: making an LLM answer only from facts you give it, so it
  cannot invent things.
- **RAG** (Retrieval-Augmented Generation): look up relevant facts first, then
  generate an answer from them. The CareerLens chat works this way.

**Payments and plans** (used in Part 14)

- **Payment provider**: a company that takes card payments for you, such as
  Stripe or Chargily Pay. The card number is typed on *their* page, never on
  yours.
- **Test mode / sandbox**: a copy of the provider's system that uses fake
  cards and fake money, for development. `4242 4242 4242 4242` is Stripe's
  standard fake card.
- **Checkout session**: a one-time payment page the provider creates when
  your server asks for it. Your server gets back a URL and sends the browser
  there.
- **Subscription**: an agreement to charge automatically every month or
  year, until cancelled.
- **Webhook**: a request the *provider's* server sends to *your* server to
  say "something happened" (a payment succeeded, a card failed, a
  subscription was cancelled). It is the provider calling you, not the
  browser.
- **HMAC signature**: a code computed from a message and a shared secret.
  Only someone who knows the secret can compute it, so a correct signature
  proves who sent the message and that nobody changed it.
- **Idempotent**: safe to do twice. Processing the same webhook twice must
  leave the same result as processing it once, because providers sometimes
  send the same event again.
- **Entitlement**: what a user is allowed to use, given their plan.
- **Quota**: a limit on how much of something you may use in a period ("5
  analyses a month").
- **`402 Payment Required`**: the status code this project returns when you
  are signed in and your request is valid, but your plan does not cover it.
- **Trust boundary**: the line between code you control (the server) and
  code you don't (the browser, which the user can change freely). Anything
  that comes from the browser must be treated as a *claim*, not a fact.

**Concurrency** (things happening at the same moment)

- **Race condition**: a bug that only appears when two operations overlap in
  time, e.g. two requests both reading "4 of 5 used" and both saving a 5th.
- **Transaction**: a group of database changes saved together (`COMMIT`) or
  undone together (`ROLLBACK`). Nothing is half-saved.
- **Advisory lock**: a named lock you ask PostgreSQL for. A second
  transaction asking for the same name waits until the first finishes.
- **Upsert**: "insert this row, or update it if it already exists", in one
  statement (`INSERT … ON CONFLICT … DO UPDATE`).

---

## Part 3 — The big picture: how the pieces connect

```mermaid
flowchart LR
    U["User's browser"] -->|"loads pages"| V["Next.js frontend<br/>(Vercel)"]
    U -->|"JSON over HTTPS<br/>Authorization: Bearer token"| A["FastAPI backend<br/>(Render)"]
    A -->|"SQL via SQLAlchemy"| D[("PostgreSQL")]
    A -->|"writes/reads files"| F["Upload folder<br/>CVs and images"]
    A -.->|"optional"| G["Google Gemini API"]
    A -.->|"learning resources"| X["dev.to · GitHub · Hacker News APIs"]
    A -->|"loaded at start"| M["MiniLM embedding model<br/>(runs on the server's CPU)"]
    A -.->|"payments: switched off<br/>(no keys configured)"| P["Stripe (test mode)"]
    P -.->|"signed webhooks"| A
```

Important points:

- The **browser talks to two servers**. Vercel only serves the page files; all
  data comes straight from the backend. That is why CORS and
  `NEXT_PUBLIC_API_BASE` matter.
- The frontend has **no server-side code of its own**: no API routes, no
  database access. Every page fetches its data in the browser.
- The backend is **one Python process**. The AI model, the rate-limit
  counters and the caches all live in its memory.

### What one request looks like: logging in

```mermaid
sequenceDiagram
    participant B as Browser (login page)
    participant AP as AuthProvider (frontend)
    participant API as FastAPI /api/auth/login
    participant DB as PostgreSQL
    B->>AP: login(email, password)
    AP->>API: POST /api/auth/login {email, password}
    API->>API: rate-limit check (per IP and per email)
    API->>DB: SELECT user WHERE email = ...
    API->>API: bcrypt-verify password (also when user doesn't exist)
    API->>DB: read role from user_profiles
    API-->>AP: 200 {access_token, user_id, email, role}
    AP->>B: save to localStorage, go to /dashboard, /employer/dashboard or /admin/dashboard
```

After this, every API call from the frontend adds the header
`Authorization: Bearer <access_token>`, and the backend's
`get_current_user_id` dependency checks it before running the route.

---

## Part 4 — Every folder and file

```text
FInal project_AI_Prac/                  ← the Git repository root
├── .gitignore                          ← files Git must never track
├── README.md                           ← short project README
├── PROJECT_GUIDE.md                    ← this guide
├── render.yaml                         ← Render deployment blueprint (backend)
└── ai-job-intelligence/                ← the application
    ├── README.md                       ← short backend README
    ├── BILLING.md                      ← Stripe set-up notes (kept for reference)
    ├── pyproject.toml                  ← Python project metadata (see note)
    ├── requirements.in                 ← the packages the code imports (edit this)
    ├── requirements.txt                ← every package, pinned (generated; Render installs it)
    ├── alembic.ini                     ← settings for the Alembic command-line tool
    ├── src/ai_job_intelligence/        ← the backend Python package
    │   ├── __init__.py                 ← marks the folder as a package
    │   ├── config.py                   ← reads settings and secrets
    │   ├── clock.py                    ← one definition of "now" (naive UTC)
    │   ├── database.py                 ← re-exports engine/session/Base
    │   ├── migrate.py                  ← applies migrations at start-up
    │   ├── init_db.py                  ← apply migrations without starting the server
    │   ├── main.py                     ← the FastAPI app and 55 of its 61 routes
    │   ├── billing_routes.py           ← the other 6: /api/billing/* (plans, checkout, webhook…)
    │   ├── schemas.py                  ← Pydantic request/response shapes
    │   ├── conftest.py                 ← shared pytest setup
    │   ├── test_*.py                   ← backend tests (298)
    │   ├── migrations/                 ← Alembic: env.py + versions/0001, 0002, 0003
    │   ├── models/                     ← the database tables (billing.py holds three)
    │   └── services/                   ← the logic: auth, AI, matching, email, billing…
    └── frontend/                       ← the Next.js app
        ├── app/                        ← pages (folders become URLs)
        ├── components/                 ← shared building blocks
        ├── e2e/                        ← Playwright browser tests
        ├── public/                     ← static images (default Next.js SVGs)
        ├── package.json                ← JavaScript packages and scripts
        ├── package-lock.json           ← exact installed versions
        ├── next.config.ts              ← Next.js settings (empty defaults)
        ├── tsconfig.json               ← TypeScript settings
        ├── eslint.config.mjs           ← lint rules
        ├── postcss.config.mjs          ← lets Tailwind run
        └── playwright.config.ts        ← browser-test settings (see 11.5)
```

**Not in Git, only on your computer** (all listed in `.gitignore`): `.env`
(your secrets), `.venv/` (Python packages), `node_modules/` (JavaScript
packages), `.next/` (build output), `uploads/` (uploaded files),
`.model_cache/` (the downloaded embedding model), `src/.secret_key` (the
auto-generated development key), `*.db` files, test caches.

### 4.1 Backend files one by one

| File | What it does |
|---|---|
| `config.py` | Loads `.env`, then works out every setting: upload folders, `DATABASE_URL` (must be PostgreSQL, see [6.2](#62-configpy--settings-and-secrets)), `GOOGLE_API_KEY`, `CORS_ORIGINS`, `FRONTEND_URL`, the `SMTP_*` email settings, `APP_ENV`, and `SECRET_KEY`. Refuses to start if something is unsafe. |
| `clock.py` | `utcnow()`: the current time in UTC *without* a time zone attached, which is what the database columns store. Replaces the deprecated `datetime.utcnow()`. |
| `migrate.py` | `upgrade_database()`, called at start-up: applies any Alembic migrations the database lacks, and hands over databases created before migrations existed. See [6.3](#63-what-happens-when-the-server-starts). |
| `migrations/` | Alembic's folder: `env.py` (how it connects, using the app's own engine) and `versions/`, one file per schema change (`0001_baseline_schema.py`, `0002_auth_tokens_and_session_versioning.py`, `0003_billing_and_usage.py`). |
| `billing_routes.py` | The six `/api/billing/*` routes, grouped with a FastAPI `APIRouter` and attached in `main.py` with `app.include_router(...)`. See Part 14. |
| `database.py` | One line: re-exports `engine`, `SessionLocal`, `Base` from `services/database.py`, so models can write `from ai_job_intelligence.database import Base`. |
| `services/database.py` | Creates the SQLAlchemy **engine** (the connection pool to Postgres), **SessionLocal** (makes sessions) and **Base** (the parent class of every model). |
| `init_db.py` | `python -m ai_job_intelligence.init_db` brings the schema up to date without starting the web server. Rarely needed: the server does the same at start-up. |
| `__init__.py` | Has a `main()` that prints "Hello from ai-job-intelligence!". Left over from the `uv` project template; `pyproject.toml` points a script at it. Harmless. |
| `main.py` | The heart of the backend: creates the app, sets up CORS, runs the start-up work (`lifespan`), defines 55 API routes plus helper functions, and attaches the 6 billing routes from `billing_routes.py`. Details in Part 6. |
| `schemas.py` | Every Pydantic shape: what `/api/auth/register` accepts, what a job looks like when returned, and so on. Also holds validation rules (email format, allowed roles, safe meeting links, interview duration limits). |
| `models/*.py` | One class per table; see Part 5. |
| `services/auth.py` | Password hashing (with the `bcrypt` library directly), constant-time password check, creating JWTs. |
| `services/auth_dependency.py` | `get_current_user_id`: reads the Bearer token, checks the signature, expiry and session version, and returns the user id, or answers 401. |
| `services/account_tokens.py` | One-time links for password reset and email verification; only a hash of each is stored. |
| `services/email_service.py` | Sends email over SMTP (or, in development without SMTP, prints it to the server log). |
| `services/password_policy.py` | Rules for acceptable passwords. |
| `services/rate_limit.py` | The sliding-window rate limiter. |
| `services/pdf_parser.py` | Reads text out of PDF, TXT and image files. |
| `services/cv_sections.py` | Splits CV text into sections (experience, education, skills…) whatever the headings are called. |
| `services/skill_evidence.py` | Finds *where* each skill appears and whether the CV demonstrates it or only lists it. Also "implied skills" (e.g. "containerised" → Docker). |
| `services/ai_service.py` | The skill vocabulary, CV profile extraction, and job-requirement extraction (Gemini or rules). |
| `services/cv_profile.py` | Saves the parsed CV profile on the CV row and reads it back (a cache). |
| `services/embedding_service.py` | Loads the MiniLM model (ONNX Runtime) and turns text into vectors. |
| `services/vector_store.py` | Turns vectors into compact text for the database, and ranks vectors by similarity. |
| `services/semantic_index.py` | Reads and writes vectors on CV and Job rows; "rank jobs for this CV", "rank CVs for this query". |
| `services/matcher.py` | Compares one candidate with one job and produces the match score. |
| `services/guidance.py` | Turns an analysis into a short, prioritised action list. |
| `services/learning_resources.py` | Finds real learning links (official docs, dev.to, GitHub, Hacker News). |
| `services/assistant.py` | The CareerLens chat: detects intent, retrieves facts, then asks Gemini or uses rules. |
| `services/plans.py` | Pure data: what each plan allows (`PLAN_LIMITS`), and the whitelist that turns "Pro, yearly" into a Stripe price id. |
| `services/entitlements.py` | Decides what the signed-in user may do, from the database only: which plan they're on, and the monthly quotas (with a per-user lock). Answers 402. |
| `services/billing.py` | Everything that talks to Stripe: checkout, the customer portal, webhook processing, syncing a subscription, cancelling on account deletion. |
| `models/billing.py` | Three tables: `billing_customers`, `subscriptions`, `stripe_events`. |
| `models/usage_event.py` | The `usage_events` table: one row per metered use (a CV upload, an analysis, a Career Insights session). |

> **Note on dependencies:** `pyproject.toml`'s `dependencies = []` is
> deliberately empty. The real lists are `requirements.in` (the ~18 packages
> the code imports, which you edit) and `requirements.txt` (every package with
> an exact version, generated from it, and what Render installs). Use
> `pip install -r requirements.txt`.

### 4.2 Frontend files one by one

| File | What it does |
|---|---|
| `app/layout.tsx` | The root layout wrapping every page: loads the Inter font, `globals.css`, sets the page title/description, and wraps everything in `<Providers>`. |
| `app/globals.css` | Tailwind import, colour variables, and reusable classes such as `btn-primary`, `btn-secondary`, `btn-danger`, `input-premium`, `section-title`, `label`. |
| `app/page.tsx` | The landing page at `/`. It never redirects, even when you are logged in. |
| `app/(public)/…` | Public pages: about, contact, demo-analysis, faq, how-it-works, login, register, forgot-password, reset-password, verify-email, pricing, plus their layout. |
| `app/(jobseeker)/…` | Job-seeker pages with a sidebar layout that sends you to `/login` if you are not signed in. Includes `billing/` (your plan, usage, and where Stripe sends you after paying). |
| `app/employer/…` | Employer pages; the layout also requires the role `employer`. |
| `app/admin/…` | Admin pages; the layout also requires the role `admin`. |
| `components/Providers.tsx` | Wraps the app in `AuthProvider`. It exists so the root layout (a server component) can include client-only providers. |
| `components/AuthProvider.tsx` | Login state for the whole app: `token`, `userId`, `role`, `email`, `loading`, `login()`, `logout()`, `isAuthenticated`. |
| `components/api.ts` | `API_BASE` (backend address), the session helpers (`clearStoredSession()`…), `getAuthHeaders()`, `apiCall()` (fetch with token; signs out on 401), `viewFile()` (open a protected file). |
| `components/format.ts` | Formatting helpers: scores, "Not specified", salaries, skill-evidence labels, turning API errors into sentences, password hints. |
| `components/MessageDialog.tsx` | The pop-up used everywhere instead of the browser's `alert()`/`confirm()`. |
| `components/Navbar.tsx` / `Footer.tsx` | Top bar and footer on public pages. |
| `components/site.ts` | GitHub and LinkedIn links, defined once for Footer and Contact. |
| `components/LoadingSpinner.tsx` | A small "Loading…" spinner. |
| `components/InterviewsView.tsx` | The whole interviews screen, shared by candidate and employer pages. |
| `components/InterviewScheduler.tsx` | The "schedule / edit interview" form. |
| `components/MessagesView.tsx` | The whole messages screen, shared by both sides. |
| `components/LearningResources.tsx` | The "places to learn this skill" panel. |
| `components/AuthCard.tsx` | The centred card used by forgot-password, reset-password and verify-email. |
| `components/VerifyEmailBanner.tsx` | "Please confirm your email address", with a Resend link, on signed-in pages. |
| `components/unreadMessages.ts` | `useUnreadMessageCount()`: the unread badge on the Messages link. |
| `components/motion.ts` | Animation helpers (anime.js and GSAP), used by the job-edit page and interviews. |
| `components/billing.ts` | Plan and usage types, `useSubscription()` (the plan shown in the sidebar and pages), `startCheckout()`, `openBillingPortal()`, money and date formatting, and `PAYMENT_REQUIRED = 402`. It can *display* a plan, never grant one. |
| `components/UpgradePrompt.tsx` | The card shown when the API answers 402, and `UpgradeDialog`, the same message as a pop-up for uploads and analyses. |

---

## Part 5 — The database

### 5.1 The tables and how they link

```mermaid
erDiagram
    users ||--|| user_profiles : "has one"
    users ||--o{ cvs : "uploads"
    cvs ||--o{ analyses : "analysed against jobs"
    users ||--o{ jobs : "posts (employer)"
    jobs ||--o{ applications : "receives"
    users ||--o{ applications : "makes (job seeker)"
    users ||--o{ saved_jobs : "saves"
    jobs ||--o{ saved_jobs : "is saved"
    users ||--o{ interviews : "employer_id / candidate_user_id"
    users ||--o{ messages : "sender_id / recipient_id"
    users ||--o{ auth_tokens : "reset / verify links"
    users ||--o| billing_customers : "one Stripe customer"
    users ||--o{ subscriptions : "paid plans, with history"
    users ||--o{ usage_events : "metered uses (quotas)"
```

`stripe_events` stands alone: it records which payment-provider events have
already been handled (Part 14.6).

| Table | One row is… | Key columns |
|---|---|---|
| `users` | a login | `id`, `email` (unique), `password_hash` |
| `user_profiles` | everything else about that person | `user_id` (**also its primary key**, so exactly one profile per user), `name`, `role`, the company fields `company`, `description`, `industry`, `company_size`, `website`, `linkedin`, `twitter`, `image_url`, plus `token_version` (see [6.5](#65-authentication-in-detail)) and `email_verified_at` |
| `cvs` | one uploaded CV | `filename` (original name), `file_path` (where it is on disk), `extracted_text`, `user_id`, `profile_json` + `profile_version` + `profile_parsed_at` (cached parsed profile), `embedding` + `embedding_version` (cached vector) |
| `analyses` | one "CV vs job description" result | `cv_id`, `job_title`, `company`, `job_description`, `match_score`, `matched_skills`, `missing_skills`, `experience_match`, `education_match`, `recommendations`, `summary` |
| `jobs` | one job posting | `title`, `description`, `location`, `salary_min/max`, `employment_type`, `required_skills`, `experience_required`, `education_required`, `responsibilities`, `benefits`, `status` (`open`/`closed`/`draft`), `company`, `employer_id`, `views`, `embedding` + `embedding_version` |
| `applications` | one application | `job_id`, `user_id`, `status` (`applied`/`accepted`/`rejected`), `match_score`, `applied_at` |
| `saved_jobs` | one bookmark | `job_id`, `user_id`, `saved_at` |
| `interviews` | one scheduled interview | `employer_id`, `candidate_user_id`, `cv_id`, `job_id`, `scheduled_at`, `status`, `mode` (`video`/`phone`/`onsite`), `meeting_url`, `dial_in`, `contact_email`, `contact_phone`, `duration_minutes`, `timezone`, `location`, `notes` |
| `messages` | one direct message | `sender_id`, `recipient_id`, `body`, `job_id` (optional), `read_at` (empty until opened) |
| `auth_tokens` | one emailed link | `user_id`, `purpose` (`password_reset`/`verify_email`), `token_hash` (SHA-256; never the token itself), `expires_at`, `used_at` |
| `billing_customers` | the link between a user and their Stripe customer | `user_id` (**primary key**, so at most one per user), `stripe_customer_id` (unique) |
| `subscriptions` | one paid subscription, as last reported by Stripe | `user_id`, `plan` (`pro`/`enterprise`/`unknown`), `status` (Stripe's word: `active`, `past_due`, `canceled`…), `stripe_subscription_id` (**unique**), `stripe_price_id`, `billing_interval`, `current_period_start/end`, `cancel_at_period_end`, `canceled_at`, `ended_at`; index on `(user_id, status)` |
| `stripe_events` | one webhook event already processed | `id` (Stripe's `evt_…` id, the primary key), `type`, `processed_at` |
| `usage_events` | one metered use | `user_id`, `kind` (`cv_upload`, `analysis`, `insight_session`), `created_at`; index on `(user_id, kind, created_at)` |
| `alembic_version` | which migration the database is at | `version_num`, now `0003` (managed by Alembic) |

> **Teacher's note: why four billing tables and not one column?** The
> simplest idea is a `plan` column on the user. It fails in real life. A user
> can start paying, cancel, and pay again; that is *several* subscriptions,
> and you want the history (`subscriptions`, one row each). A Stripe
> customer exists *before* any subscription, as soon as someone opens
> checkout, so it needs its own place (`billing_customers`), or every
> abandoned checkout would create another customer. Webhooks can arrive
> twice, so you need a memory of which ones you've handled (`stripe_events`).
> And quotas need counting that users can't undo by deleting things
> (`usage_events`). Each table exists because of one specific way the simple
> design breaks. That is a good habit: **when you add a table, you should be
> able to name the problem it prevents.**

### 5.2 Small things worth knowing

- **Role lives in `user_profiles`, not `users`.** The `users` table is owned by
  the `postgres` superuser in the original local database, so the app's role
  cannot alter it. That's why new per-person columns (`token_version`,
  `email_verified_at`) also went on `user_profiles`.
- **Lists stored as text.** `required_skills`, `benefits`, `matched_skills`,
  `missing_skills` and `recommendations` are JSON text such as
  `'["Python", "SQL"]'`. The code converts them with `json.dumps` and
  `json.loads` (`_json_dumps` and `_parse_json_list` in `main.py`).
- **`null` vs `0` in scores.** `experience_match = NULL` means "the job never
  asked for experience, so it wasn't scored". `0` means "it asked and you
  don't meet it". The frontend shows `NULL` as "Not specified"
  (`formatScore` in `format.ts`).
- **No conversation table.** A conversation is simply all messages between
  two people, ordered by time.
- **Times are stored without a time zone**, in UTC (`clock.utcnow()`). An
  interview's `timezone` column remembers which zone the employer meant, e.g.
  `Africa/Nairobi`.
- **A job's `company` is copied from the employer's profile**, and renaming
  your company updates all your existing postings too (`_sync_company_name`).
- **Versions on cached data.** `profile_version` and `embedding_version` record
  which version of the code produced the cached value. When the code changes,
  the constant goes up (`PROFILE_VERSION = 4`, `EMBEDDING_VERSION = 1`) and old
  rows are rebuilt automatically the next time they are read.
- **No CHECK constraint on `subscriptions.status`.** It would look tidy to
  allow only known statuses, but this table *copies* what Stripe says. If
  Stripe ever adds a new status, a constraint would make the save fail, and
  Stripe would keep re-sending the event for days. Instead the table accepts
  anything, and the code that grants access only trusts statuses it knows
  (Part 14.8). This idea is called **"permissive storage, strict decisions"**.
- **Quotas count `usage_events`, never `cvs` or `analyses`.** Users can delete
  CVs and analyses. If the quota counted those rows, deleting old ones would
  hand the month's allowance back.

---

## Part 6 — The backend (FastAPI)

### 6.1 How a route is written (a real example)

```python
@app.post("/api/saved-jobs", status_code=status.HTTP_201_CREATED)   # method + URL + success code
def save_job(
    payload: SavedJobCreate,                                        # body must be {"job_id": int}
    current_user_id: int = Depends(get_current_user_id),            # token checked first
) -> dict:
    db = SessionLocal()                                             # open a session
    try:
        job = db.get(Job, payload.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        ...                                                         # refuse duplicates (400)
        saved = SavedJob(job_id=payload.job_id, user_id=current_user_id)
        db.add(saved)
        db.commit()                                                 # write to Postgres
        db.refresh(saved)                                           # read back id and saved_at
        return {"id": saved.id, "job_id": saved.job_id, ...}        # becomes JSON
    finally:
        db.close()                                                  # always give the connection back
```

Every route in `main.py` follows this pattern: open a session in `try`, and
always close it in `finally`, even if an error is raised. `HTTPException`
stops the route and sends that status code and message to the client.

### 6.2 `config.py` — settings and secrets

When anything imports `config.py`, it runs top to bottom:

1. `load_dotenv()` loads `.env` into the environment, **without overwriting
   variables that are already set**. On Render there is no `.env`; the
   variables come from the dashboard.
2. `BASE_DIR` is the `src/` folder. `UPLOAD_DIR` defaults to `src/uploads` and
   `IMAGES_DIR` to `src/uploads/images`; both folders are created.
3. **`DATABASE_URL`** is read and then **normalised**. Render gives URLs such
   as `postgresql://…` or `postgres://…`; SQLAlchemy would try the
   `psycopg2` driver for those, which isn't installed. So the prefix is
   rewritten to `postgresql+psycopg://` (psycopg version 3). If the result
   is not PostgreSQL (empty, `sqlite:…`, `mysql:…`), **the app refuses to
   start**. SQLite is not supported anywhere.
4. `CORS_ORIGINS` is split on commas, and a trailing `/` on each origin is
   removed (browsers never send one). Default:
   `http://localhost:3001,http://127.0.0.1:3001` (the dev frontend's port).
5. `FRONTEND_URL`, used to build the links in emails, defaults to the first
   entry of `CORS_ORIGINS`. In production that is your Vercel address, so it
   rarely needs setting.
6. The `SMTP_*` settings for sending email (see [6.5](#65-authentication-in-detail)).
   `SMTP_SECURITY` defaults to `ssl` on port 465 and `starttls` otherwise.
7. `APP_ENV` (`development` by default) sets `IS_PRODUCTION`.
8. **`SECRET_KEY`** is resolved by `_resolve_secret_key()`:
   - uses `SECRET_KEY` (or the alias `JWT_SECRET_KEY`) if set;
   - refuses known placeholders like `changeme` or `change-this-in-production`;
   - refuses anything shorter than 32 characters;
   - in production, refuses to start if it's missing;
   - in development, if it's missing, generates a random key and saves it in
     `src/.secret_key` with permissions `0600` (only you can read it), so
     restarts don't log everyone out.
9. **Stripe settings** (all optional): `STRIPE_SECRET_KEY` is checked by
   `_resolve_stripe_secret_key()`, which **refuses to start** with a live key
   (`sk_live_…`) or anything that isn't a test key. That makes "accidentally
   charged a real card" impossible by configuration. `STRIPE_WEBHOOK_SECRET`,
   `STRIPE_PRICE_PRO_MONTHLY` and `STRIPE_PRICE_PRO_YEARLY` are read as they
   are. `BILLING_ENABLED` is true only when the key and both prices are set.
   Today none are set, so billing is off.

> **Teacher's note: "fail loudly at start-up".** Look at how many of these
> settings make the app *refuse to start* rather than carry on with a bad
> value: a non-PostgreSQL database, a weak secret, a live Stripe key. A
> program that crashes immediately with a clear message is annoying for ten
> seconds. A program that starts with a wrong setting can run for weeks,
> quietly doing damage (forgeable tokens, real charges) before anyone
> notices. When a setting is dangerous, check it once, at the start, and
> stop if it's wrong.

### 6.3 What happens when the server starts

`lifespan()` in `main.py` runs once, before the first request is served.
(It replaced the deprecated `@app.on_event("startup")`.) It does three things.

**1. Migrations: `migrate.upgrade_database()`.** Schema changes are Alembic
migrations in `migrations/versions/`, numbered in order: `0001` is the
baseline (all nine original tables); `0002` adds `auth_tokens`,
`user_profiles.token_version` and `user_profiles.email_verified_at`; `0003`
adds the four billing tables (`billing_customers`, `subscriptions`,
`stripe_events`, `usage_events`) without touching any existing table. The
database's `alembic_version` table records how far it has got, and the
upgrade runs whatever is missing. Three kinds of database arrive here:

```mermaid
flowchart TD
    S["Server starts"] --> L["Take a PostgreSQL advisory lock<br/>(a second server process waits)"]
    L --> Q{"alembic_version table?"}
    Q -- "yes" --> U["Run newer migrations, if any"]
    Q -- "no, and no tables" --> E["Empty database: run every migration from 0001"]
    Q -- "no, but tables exist" --> G["Legacy database (made before migrations):<br/>create any missing baseline table from 0001's own definitions,<br/>add missing old columns, then STAMP it as 0001"]
    G --> U
    E --> D["Up to date"]
    U --> D
```

*Stamping* means recording "this database already has migration 0001"
without running it, because its tables are already there. The catch-up
deliberately builds only the **0001** schema, never the latest models:
anything newer must be left for migration 0002 onwards to add, or those
migrations would fail finding it already present. That rule is exactly what
`test_migrations.py` checks.

**2. `seed_jobs_if_empty()`, development only.** If the `jobs` table is
empty, it creates two demo accounts, `employer@example.com` / `password123`
and `admin@careerlens.ai` / `admin123`, plus 8 demo jobs (Senior Python
Backend Engineer, Frontend React Developer, Data Scientist, DevOps Engineer,
Product Manager, UX/UI Designer, Salesforce Administrator, Marketing Data
Analyst). These passwords are deliberately weak and public, so **seeding is
skipped when `APP_ENV=production`**. That also means a production database
has **no admin account** until you create one (see [11.6](#116-deploying)).

**3. `embedding_service.warm_up()`** loads the embedding model, so the first
CV upload isn't the request that waits for it. With ONNX Runtime the whole
backend uses about **330 MB** of memory.

### 6.4 CORS

```python
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
```

Before a cross-origin request with an `Authorization` header, the browser sends
an `OPTIONS` "preflight" request asking "may I?". The middleware answers yes
only for origins in `CORS_ORIGINS`.

### 6.5 Authentication in detail

- **Register** (`POST /api/auth/register`):
  1. Rate limit per IP (5 per hour in production, 200 in development).
  2. `RegisterRequest` validation: email must look like `x@y.zz`, role must be
     `job_seeker` or `employer`. **`admin` is refused**: anyone could once
     register as admin by sending `"role": "admin"`.
  3. `validate_password` (see [10.2](#102-password-rules)).
  4. Email already used → 400.
  5. Creates the `users` row (password hashed with bcrypt), then the
     `user_profiles` row, creates a verification link and emails it (in the
     background, after the response), and returns a token immediately.
  6. Note: the frontend's register page does not use this token. It sends you
     to `/login` to sign in.
- **Login** (`POST /api/auth/login`):
  1. Rate limits: per IP (10 per 5 minutes in production) **and** per email
     (5 failures per 15 minutes, in every environment).
  2. Looks up the user and **always** runs a bcrypt check, even when the email
     doesn't exist (against a dummy hash). Without that, a login for an
     unknown email answered in about 2 ms and a real one in about 330 ms, so
     anyone could discover which emails are registered just by timing.
  3. Wrong email or password gives the same message, "Invalid email or
     password", so the response doesn't reveal which one was wrong.
  4. Success clears that email's failure counter and returns
     `{access_token, token_type: "bearer", user_id, email, role}`.
- **The token** (`create_access_token`): payload `{"sub": "42", "ver": 0,
  "exp": …}`. `sub` means "subject", the standard JWT name for "who this token
  is about". `ver` is the account's `token_version` when the token was issued.
  The token is signed with HS256 and `SECRET_KEY` and is valid for **24
  hours**. There are no refresh tokens; after 24 hours you log in again.
- **Checking the token** (`get_current_user_id`): FastAPI's `HTTPBearer` reads
  the header; `jwt.decode` checks the signature and expiry; a bad or expired
  token gets `401 "Invalid authentication token"`, and a missing one is
  rejected as "Not authenticated". Then one quick database lookup compares
  `ver` with the account's current `token_version`. If they differ, or the
  account was deleted, the answer is `401 "Your session has ended…"`. Tokens
  from before versioning have no `ver` and count as 0, every account's
  starting version, so nobody was logged out by the change.
- **Password reset** (all in `main.py`, using `services/account_tokens.py`):
  1. `POST /api/auth/forgot-password {email}` always answers the same
     message, whether or not the account exists, so it can't reveal who is
     registered. For a real account it creates a one-time link (valid 1 hour;
     earlier unused links are cancelled) and emails it **in a background
     task**, so the response time doesn't differ either. It is limited per
     network (10 per hour in production) and per address (3 per hour).
  2. The email links to `FRONTEND_URL/reset-password?token=…`.
  3. `POST /api/auth/reset-password {token, password}` checks the link is
     unused, unexpired and a *reset* link (a verification link can't be used
     here); checks the new password against the policy **before** using up
     the link, so a rejected password doesn't waste it; saves the new hash;
     marks the link used; **raises `token_version`**, which signs the account
     out on every device; marks the email as verified (the user proved they
     can read it); and clears that email's failed-login counter.
- **Email verification:** registering sends a link (valid 48 hours) to
  `FRONTEND_URL/verify-email?token=…`, and `POST /api/auth/verify-email
  {token}` sets `email_verified_at`. `POST /api/auth/resend-verification`
  (signed in; 3 per hour) sends a fresh link. It is **informational**: an
  unverified account can still sign in, and the frontend shows a reminder
  banner. `GET /api/profile` returns `email_verified`.
- **Why tokens are hashed:** the link contains a random 32-byte token; the
  database stores only its SHA-256 hash, the same idea as password hashing.
  A leaked copy of the table can't be turned back into working links. A fast
  hash is fine here because the tokens are random and long, so there is
  nothing to guess.
- **Sending email** (`services/email_service.py`) uses Python's built-in
  `smtplib`, so any SMTP provider works. Without `SMTP_HOST`: in development
  the whole email is written to the server log, so you can click the link
  locally; in production **nothing sensitive is logged** (a reset link in a
  log would let anyone who reads the logs take over the account), only a
  warning.
- **Role checks** are done inside routes by reading `user_profiles.role`, e.g.
  `get_candidates` refuses non-employers with 403.

### 6.6 The routes by area

The full table is in [Appendix A](#appendix-a--every-api-route). Here is what
each area does and the non-obvious rules.

**CVs**
- `POST /api/upload-cv`: **Free plan: 2 uploads per month** (checked before
  the file is even stored, then again under a lock just before saving; a
  refusal is `402`). Accepts `.pdf .txt .png .jpg .jpeg`, up to 5 MB. The
  file is saved under a **random name** (e.g. `3f9c…e1.pdf`), never the
  name the user sent, because a name like `../../evil.txt` could otherwise
  write outside the upload folder. The text is extracted (an empty result
  gives a helpful 400 and the file is deleted), the profile is parsed and
  cached, the vector is computed and cached, and a summary is returned.
- `GET /api/cvs`: your CVs, newest first.
- `GET /api/cvs/{id}`: one CV including its extracted text (owner or admin).
- `GET /api/cvs/{id}/analysis`: the full CV report: skills, each labelled
  with how strongly the CV evidences it (`demonstrated`, `mentioned` or
  `listed`, see [7.3](#73-sections-and-evidence-cv_sectionspy-skill_evidencepy));
  strengths, weaknesses, recommendations based on what open jobs ask for,
  formatting/ATS tips, and `learn_next`.
- `GET /api/cvs/{id}/download`: the original file. Allowed for the owner, an
  admin, or an **employer when the CV belongs to a job seeker** (the same
  people candidate search already shows employers). Anyone else gets 404
  (`_may_open_cv`).
- `GET /api/cvs/{id}/analyses`: all saved job analyses for that CV.

**Analyses**
- `POST /api/analyze` `{cv_id, job_title, company?, job_description}`:
  parses the job (Gemini if available), matches, **saves** an `analyses` row,
  and returns the scores plus `analysis_id`. **Free plan: 5 per month**; the
  use is recorded in the same transaction as the analysis, so a failed
  analysis costs nothing.
- `GET /api/analyses/{id}`: one saved analysis plus freshly built `guidance`
  (the prioritised action list).
- `DELETE /api/analyses/{id}`: remove one.
- `POST /api/demo/analyze` (no login, form upload): the same analysis without
  saving anything. Max 2 MB; rate limited per IP (5 per hour in production,
  30 in development); the job description must be at least 30 characters;
  the uploaded file is **always deleted** afterwards, even on error.
- `POST /api/reset-data`: deletes all your CVs, their analyses and the stored
  files. Interviews booked from one of those CVs are kept but lose the CV link.

**Jobs**
- `GET /api/jobs`: **employers see only their own postings (any status)**;
  everyone else sees open jobs, and job seekers also get a `match_score`,
  `skill_gaps` and `match_breakdown` for each, computed against their
  latest CV. Up to 20 per page (`limit`, `offset`). The application counts
  for the whole page come from one grouped query (`_application_counts`),
  not one query per job.
- `POST /api/jobs`: create (company name copied from your profile; embedding
  computed immediately).
- `PATCH /api/jobs/{id}`: partial edit of **your own** posting. Only fields you
  send are changed (`exclude_unset`). Minimum salary can't exceed maximum. If
  title, description or skills change, the embedding is recomputed.
- `GET /api/jobs/{id}`: one job; **adds 1 to `views`**; job seekers get their
  match against it.
- `GET /api/jobs/{id}/applications`: applicants for your posting.

> **Why 404 instead of 403 when editing someone else's job?** A 403 ("you may
> not") would confirm the job exists. By answering 404 ("no such job"),
> nobody can probe ids to discover other employers' postings.

**Applications**
- `POST /api/applications` `{job_id}`: apply once per job (second time → 400).
  Your match score is computed and stored with the application.
- `GET /api/applications`: your applications.
- `POST /api/applications/{id}/accept` and `/reject`: only the employer who
  owns the job.

**Saved jobs**
- `GET /api/saved-jobs`, `POST /api/saved-jobs` `{job_id}` (201; saving twice →
  400 "Job already saved"), `DELETE /api/saved-jobs/{job_id}` (uses the
  **job** id, not the bookmark id).

**Insights and chat**
- `GET /api/user/stats`: numbers for the dashboards (different fields for
  employers and job seekers).
- `GET /api/job-recommendations?cv_id=`: best-matching jobs (see [7.7](#77-job-recommendations-retrieve-then-rerank)).
- `GET /api/career-insights`: your field, gaps, salary range (see [7.8](#78-career-insights)).
  **Free plan: 2 sessions per month**, each open for 24 hours (see 14.9).
- `POST /api/career-lens/chat` `{message, cv_id?}`: the assistant (see [7.10](#710-the-careerlens-assistant-chat)).
- `GET /api/learning-resources?skills=a,b&limit=4`: learning links (see [7.9](#79-learning-resources)).

**Accounts** (see [6.5](#65-authentication-in-detail))
- `POST /api/auth/register`, `POST /api/auth/login`,
  `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`,
  `POST /api/auth/verify-email`, `POST /api/auth/resend-verification`.

**Profile and images**
- `GET/PUT /api/profile`: your name and profile fields, plus `email_verified`.
  `PUT` only changes fields you send (anything not `null`).
- `POST /api/upload-image`: PNG/JPG/GIF/WEBP up to 5 MB; saves it under a
  random name, puts the URL `/api/images/<name>` on your profile, and deletes
  your previous picture.
- `GET /api/images/{name}`: serves an image. **No login needed**, so an `<img>`
  tag can load it; the random names make the URLs unguessable. Only a real
  file directly inside the images folder is served (`..` and the like get
  404).

**Employer**
- `GET/POST /api/company`: the company profile. `POST` uses the key `name` for
  the company name, stored in `user_profiles.company`; renaming updates the
  company shown on all your existing postings.
- `GET /api/candidates?skills=&q=`: job seekers who uploaded a CV.
  `skills` is an exact filter (the candidate must list at least one); `q` is
  a *meaning-based* search (embeddings), so "someone to run our cloud
  infrastructure" finds DevOps people. The `id` of each candidate is a **CV
  id**; `user_id` is the person; `cv_url` is `/api/cvs/{id}/download` (never
  the server's file path). The `match_score` field is a profile-completeness
  estimate (skills 40 %, experience level 25 %, education 20 %, depth 15 %),
  **not** a match to one of your jobs, so the UI labels it "profile score".
- `GET /api/candidates/{cv_id}`: one candidate.

**Interviews** (see [7.11](#711-interviews-rules-and-states))
- `POST /api/interviews`, `GET /api/interviews`,
  `PATCH /api/interviews/{id}/details` (employer edits time or joining
  details), `PATCH /api/interviews/{id}` (status change).

**Messages**
- `POST /api/messages` `{recipient_user_id, content, job_id?}`,
  `GET /api/messages` (conversation list with unread counts),
  `GET /api/messages/{other_user_id}` (the thread; marks it read),
  `GET /api/messages/unread/count`.
- Old frontend code identified people by CV id, so `recipient_id` (and, for
  interviews, `candidate_id`) are treated as **CV ids** and converted to the
  CV's owner (`_resolve_target_user`). Using them as user ids would have
  delivered the message to whichever unrelated user happened to have that
  number.

**Billing** (in `billing_routes.py`; all explained in Part 14)
- `GET /api/billing/plans` (no login): each plan's limits, and live prices
  from Stripe (an empty list while Stripe is off).
- `GET /api/billing/subscription`: your plan, status, renewal date and this
  month's usage.
- `POST /api/billing/checkout` `{plan: "pro", interval: "month"|"year"}`:
  returns a Stripe Checkout URL. Currently answers `503` ("Payments are not
  set up on this server yet").
- `POST /api/billing/checkout/confirm` `{session_id}`: the success page asks
  the server to check a finished checkout with Stripe.
- `POST /api/billing/portal`: a link to Stripe's page for cancelling or
  changing a subscription.
- `POST /api/billing/webhook` (no login; Stripe's signature instead):
  where Stripe reports payments and changes.

**Admin** (role `admin` required, else 403)
- `GET /api/admin/stats`, `GET /api/admin/users`,
  `GET /api/admin/users/{id}`, `DELETE /api/admin/users/{id}` (removes the
  person and everything that belongs to them; see [6.8](#68-deleting-data-safely);
  you can't delete yourself).

### 6.7 Uploads and files

- CVs: `UPLOAD_DIR/<random>.<ext>`. Images: `IMAGES_DIR/<random>.<ext>`, with
  the extension taken from the checked content type. Neither ever includes
  the name the user's file had.
- Text extraction (`pdf_parser.py`):
  - **PDF**: PyMuPDF (`fitz`) reads the text of every page. A
    password-protected PDF gets a clear 400. Any other library error becomes
    a friendly 400, and the server's file path is logged, **never sent to
    the user**.
  - **TXT**: read as UTF-8 (bad bytes replaced).
  - **Images**: three attempts in order: PyMuPDF, then Gemini Vision
    (`ocr_image`; skipped entirely without `GOOGLE_API_KEY`), then Tesseract
    (`pytesseract`, only if installed; it isn't in `requirements.txt`). With
    no key and no Tesseract, image CVs give "No text could be read from this
    image".
  - A scanned PDF (only pictures) has no text, so it gets a message
    suggesting a text-based PDF.

### 6.8 Deleting data safely

PostgreSQL won't delete a row that another row still points at (a *foreign
key*). A user is pointed at by their profile, CVs, jobs, applications, saved
jobs, interviews and messages, so deleting only the `users` row failed with a
500. Two helpers in `main.py` now delete in the right order, inside **one
transaction** (all or nothing):

- `_delete_cvs(db, cv_ids)`: deletes the CVs' analyses, sets `cv_id` to empty
  on any interview booked from those CVs, then deletes the CVs. Used by
  `POST /api/reset-data`.
- `_delete_user_and_data(db, user_id)`: deletes their CVs (as above); their job
  postings with those postings' applications and bookmarks (interviews and
  messages *about* a deleted posting lose the `job_id` link); their own
  applications and bookmarks; every interview and message they took part in;
  their emailed links (`auth_tokens`); their billing rows (`usage_events`,
  `subscriptions`, `billing_customers`); their profile; and finally the user.
  Used by `DELETE /api/admin/users/{id}`. Any token the deleted user still
  holds stops working at once (see 6.5).
- **Before** any of that, `delete_user` calls
  `billing.cancel_subscriptions_for_user`, which asks Stripe to cancel any
  live subscription. Deleting our rows alone would not stop Stripe charging
  the card every month. If Stripe can't be reached, the deletion is refused
  with a `502`, so an account never disappears while its subscription keeps
  charging. (With Stripe off, no user has a subscription, so this does
  nothing.)

The rule: rows that exist only because of the deleted thing go with it;
rows that record something between two people either go (if one of the two
people is deleted) or just lose the link.

Uploaded files (CVs, profile picture) are removed **after** the commit
succeeds (`_remove_files`). If the database step failed, you would otherwise
be left with rows pointing at missing files. Only files inside `UPLOAD_DIR`
or `IMAGES_DIR` are ever removed.

### 6.9 Code lessons: reading the backend line by line

The sections above say *what* the backend does. This section shows *how*,
with real code from the project (sometimes shortened; `…` marks a cut). Read
each lesson with the file open.

#### Lesson 1: the database connection (`services/database.py`)

```python
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

Three lines, three ideas:

- **`engine`** is the *connection pool*: a small set of open connections to
  PostgreSQL that are reused, because opening a new connection for every
  request is slow. There is one engine for the whole app.
- **`SessionLocal`** is a *factory*: calling `SessionLocal()` gives you a new
  session, which borrows a connection from the pool. `autocommit=False`
  means nothing is saved until you call `db.commit()`.
- **`Base`** is the parent class of every model. When a class inherits from
  it, SQLAlchemy registers its table in `Base.metadata`, which Alembic reads
  to compare models with the database.

Every route then follows the same life cycle:

```python
db = SessionLocal()      # borrow a connection
try:
    ...                  # read and change things
    db.commit()          # save everything, all at once
finally:
    db.close()           # give the connection back, ALWAYS
```

> **Teacher's note.** The `finally` is not decoration. If a route raised an
> error and never closed its session, that connection would stay borrowed.
> After enough errors the pool is empty and *every* request waits forever;
> the whole site freezes, and the cause is far away from the symptom.
> `finally` runs whether the code succeeded, returned early or raised.

#### Lesson 2: a model (`models/auth_token.py`)

```python
class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- `Mapped[int]` is the Python type; `mapped_column(...)` describes the
  database column. `Mapped[datetime | None]` plus `nullable=True` means "may
  be empty".
- `ForeignKey("users.id")`: PostgreSQL will refuse a token for a user that
  doesn't exist, and refuse to delete a user who still has tokens. That's
  why deletion has to go in the right order (6.8).
- `index=True` makes lookups by that column fast (like the index at the
  back of a book). `token_hash` is looked up on every "reset password" click,
  so it has one; `unique=True` also guarantees no two rows share a hash.
- `default=utcnow` (no brackets!) passes the *function*, so it's called for
  each new row. Writing `default=utcnow()` would call it once, when the file
  is imported, and every row would get the same time. A classic beginner bug.

#### Lesson 3: who is calling? (`services/auth_dependency.py`)

```python
security = HTTPBearer()

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        token_version = int(payload.get("ver", 0))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail=_INVALID)

    db = SessionLocal()
    try:
        profile = db.get(UserProfile, user_id)
        if profile is None and db.get(User, user_id) is None:
            raise HTTPException(status_code=401, detail=_SESSION_ENDED)
        current_version = (profile.token_version or 0) if profile else 0
    finally:
        db.close()

    if token_version != current_version:
        raise HTTPException(status_code=401, detail=_SESSION_ENDED)
    return user_id
```

Read it as three gates:

1. **`HTTPBearer`** takes the `Authorization: Bearer …` header. No header →
   FastAPI refuses the request before your code runs.
2. **`jwt.decode`** checks the signature (was this made with our
   `SECRET_KEY`?) and the expiry (`exp`). A fake or old token fails here.
   Notice `algorithms=[ALGORITHM]`: accepting only HS256 closes a known trick
   where an attacker sends a token that claims "no algorithm".
3. **The version check.** A valid signature isn't enough: after a password
   reset, `token_version` goes up, so tokens made before the reset no longer
   match. This is how "sign out everywhere" works without storing a list of
   tokens.

A route uses it like this: `current_user_id: int =
Depends(get_current_user_id)`. FastAPI runs the dependency first and hands
the result to the route. **The route never trusts a user id from the request
body**; the id always comes from the verified token.

#### Lesson 4: logging in (`main.py`, `login`)

```python
def login(payload: LoginRequest, request: Request) -> AuthResponse:
    ip = _client_ip(request)
    account_key = payload.email
    _enforce(_login_ip_limiter, ip, "Too many sign-in attempts from this network…")
    _enforce(_login_account_limiter, account_key, "Too many sign-in attempts for this account…")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == payload.email).first()

        # Always run a hash comparison, even when no such account exists.
        password_ok = verify_password_constant_time(
            payload.password, user.password_hash if user else None,
        )
        if not user or not password_ok:
            _login_ip_limiter.record(ip)
            _login_account_limiter.record(account_key)
            raise HTTPException(status_code=401, detail="Invalid email or password")

        _login_account_limiter.reset(account_key)
        profile = _get_user_profile(db, user.id)
        token = create_access_token(user.id, (profile.token_version or 0) if profile else 0)
        return AuthResponse(access_token=token, token_type="bearer", user_id=user.id,
                            email=user.email, role=_get_user_role(db, user.id))
    finally:
        db.close()
```

Four security ideas in twenty lines:

- **Two rate limits.** Per IP stops one machine guessing many passwords;
  per account stops many machines guessing *one* password. Either alone
  leaves a gap.
- **Constant time.** bcrypt takes about 0.3 s. If the code skipped it for
  unknown emails, those answers would come back almost instantly, and an
  attacker could time the responses to learn which emails are registered.
  So it always hashes, against a dummy hash if there's no user.
- **One message for both mistakes.** "Invalid email or password" doesn't say
  which was wrong.
- **Only failures count.** `record()` is called on failure, and a success
  `reset()`s the account's counter, so a user who mistypes twice isn't
  locked out after getting it right.

#### Lesson 5: one-time links (`services/account_tokens.py`)

```python
def issue(db, user_id: int, purpose: str, ttl: timedelta) -> str:
    revoke(db, user_id, purpose)              # older links stop working
    raw = secrets.token_urlsafe(32)           # 32 random bytes, URL-safe
    db.add(AuthToken(user_id=user_id, purpose=purpose,
                     token_hash=_hash(raw),   # store ONLY the hash
                     expires_at=utcnow() + ttl))
    return raw                                # the raw value goes in the email

def find_valid(db, raw: str, purpose: str) -> AuthToken | None:
    token = (db.query(AuthToken)
             .filter(AuthToken.token_hash == _hash(raw), AuthToken.purpose == purpose)
             .first())
    if token is None or token.used_at is not None or token.expires_at < utcnow():
        return None
    return token
```

- **`secrets`, not `random`.** Python's `random` module is predictable if you
  see enough outputs; `secrets` is made for security.
- **Hash in the database, raw value in the email.** Same idea as passwords:
  someone who steals the table can't turn a hash back into a working link.
  A fast hash (SHA-256) is fine here because the value is long and random,
  so there's nothing to guess.
- **The `purpose` filter** means a "verify email" link can never be used as a
  "reset password" link.
- **Four ways to be invalid:** not found, wrong purpose, already used,
  expired. All return the same `None`, so the caller can't leak which.

#### Lesson 6: the rate limiter (`services/rate_limit.py`)

```python
class SlidingWindowLimiter:
    def __init__(self, rule: Rule, *, max_keys: int = 10_000) -> None:
        self._rule = rule
        self._hits: dict[str, list[float]] = {}   # key -> times of recent attempts
        self._lock = threading.Lock()

    def check(self, key: str) -> float | None:
        now = time.monotonic()
        with self._lock:
            recent = self._prune(key, now)        # forget attempts older than the window
            if len(recent) < self._rule.limit:
                return None                       # allowed
            return max(self._rule.window_seconds - (now - recent[0]), 1.0)  # seconds to wait
```

- **A sliding window** keeps the *times* of recent attempts and counts those
  in the last N seconds. A fixed window ("5 per clock hour") lets someone
  send 5 at 11:59 and 5 more at 12:00.
- **`time.monotonic()`**, not the wall clock: it never jumps backwards when
  the computer's clock is adjusted.
- **`threading.Lock`**: FastAPI runs normal `def` routes in several threads
  at once. Without the lock, two threads could update the same list at the
  same moment and lose an attempt.
- **`max_keys`**: without a cap, an attacker could send requests from
  millions of fake keys and fill the server's memory.

#### Lesson 7: validating input (`schemas.py`)

```python
class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: Literal["pro"]
    interval: Literal["month", "year"]
```

Pydantic checks every request body against its class *before* your route
runs. Here, `Literal["month", "year"]` means any other value is refused with
`422`, and `extra="forbid"` means **unknown fields are refused too**. So if
someone adds `"price_id": "price_cheap"` to the request, they get an error
rather than having it silently ignored. Part 14.3 explains why that matters
for payments.

> **Teacher's note.** Validation is your first wall, and it's cheap: a
> single class declares what a correct request looks like, and FastAPI
> enforces it everywhere. The rule of thumb: **validate the shape at the
> door (Pydantic), and check permissions inside the route (ownership,
> role, plan).** Validation answers "is this a well-formed request?";
> permissions answer "is *this user* allowed to do it?". They are different
> questions and you need both.

#### Lesson 8: a migration (`migrations/versions/0003_billing_and_usage.py`)

```python
revision = '0003'
down_revision = '0002'          # "I come after 0002"

def upgrade() -> None:
    op.create_table('usage_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_usage_events_user_kind_created', 'usage_events',
                    ['user_id', 'kind', 'created_at'])
    ...

def downgrade() -> None:
    op.drop_index('ix_usage_events_user_kind_created', table_name='usage_events')
    op.drop_table('usage_events')
    ...
```

- Migrations form a **chain** through `down_revision`. Alembic follows it
  from the database's current version (`alembic_version`) to the newest.
- `upgrade()` moves forward; `downgrade()` undoes it exactly, in reverse
  order.
- This file was produced by `alembic revision --autogenerate`, run against a
  *throwaway* empty schema. Running it against the real development database
  would have mixed in its four old, harmless differences (12.2, item 10).
- **The model and the migration must agree.** `test_migrations.py` builds a
  database from the migrations and compares it with the models; if you
  change a model and forget the migration, that test fails.

> **Teacher's note: never edit a migration that has already run.** Once
> `0003` has been applied to a database (your laptop's, or Render's), editing
> the file changes nothing there: Alembic sees the version number and skips
> it. The databases then silently disagree about the schema. To change
> something, always write a *new* migration (`0004`).

---

## Part 7 — The AI and matching engine

### 7.1 From uploaded file to structured profile

```mermaid
flowchart TD
    A["Uploaded file"] --> B["pdf_parser: extract text"]
    B --> C["CV row saved (extracted_text)"]
    C --> D["analyze_cv_text(text)"]
    D --> D1["_extract_skills: vocabulary scan"]
    D --> D2["skill_evidence: where each skill appears + implied skills"]
    D --> D3["experience / education / certifications / projects"]
    D1 & D2 & D3 --> E["CandidateProfile"]
    E --> F["store_profile: profile_json + PROFILE_VERSION on the CV row"]
    E --> G["set_cv_embedding: 384-number vector on the CV row"]
```

A **`CandidateProfile`** (in `schemas.py`) has: `technical_skills`,
`soft_skills`, `experience`, `education`, `certifications`, `projects`,
`keywords`, and `skill_evidence` (a list of `{skill, source, context}`).

Because building this is not free, it is done **once at upload** and stored as
JSON on the CV row. Every other endpoint calls `get_candidate_profile(db, cv)`
(`cv_profile.py`), which returns the stored copy, or rebuilds and saves it if
it's missing or was made by an older `PROFILE_VERSION`.
`analyze_cv_text` is also wrapped in `lru_cache(maxsize=512)`, so the same text
is never parsed twice while the server is running.

### 7.2 Finding skills (`ai_service._extract_skills`)

- **Vocabularies:** `_TECH_VOCAB` (390 technical terms: languages,
  frameworks, databases, cloud, DevOps, testing, data/ML, design, security,
  business tools), `_SOFT_SKILLS` (16), `_GENERAL_SKILLS` (39, e.g. SEO,
  Excel, CRM). **A skill not in these lists cannot be detected**, however
  clearly it's written.
- **Multi-word skills first**, longest first, so "apache spark" is taken
  before "spark", and its words are then blocked from matching again alone.
- **Ambiguous words** (21 of them, such as `go`, `r`, `swift`, `excel`,
  `express`, `spring`, `slack`) are also normal English. "Ready to **go** the
  extra mile" must not count as the Go language. These only count if a clear
  alias appears ("golang", "microsoft excel") or they appear as an item in a
  list (`Python, Go, Kubernetes`).
- **Display names** come from `_FRAMEWORK_MAP` (185 entries) so a recruiter
  sees `PostgreSQL`, `CI/CD`, `GraphQL`, not `Postgresql` or `Ci/Cd`.
- There is **no cap** on how many skills are kept. An old `[:12]` cap
  silently dropped skills from long CVs.

### 7.3 Sections and evidence (`cv_sections.py`, `skill_evidence.py`)

- `split_sections` walks through the lines. A short line (≤ 46 characters)
  that exactly matches a known heading synonym starts a section:
  "PROFESSIONAL EXPERIENCE", "Work History", "Employment" and so on all mean
  `experience`. Text before any heading goes to `header`. Decoration like
  `== Skills ==`, `SKILLS:` and `Experience (2019–2024)` is handled, and so
  are **compound headings**: "Licenses & Certifications", "Education and
  Training" and "Skills / Tools" count, with the first part that names a
  section winning. Each part must still match exactly, so a job title like
  "Research and Development Engineer" is never mistaken for a heading.
- `collect_evidence` scans each section separately and records **where** each
  skill was found, with a weight for how believable that is:

  | Source | Weight | Meaning |
  |---|---|---|
  | `experience` | 1.0 | used in a described job |
  | `projects` | 0.95 | used in a described project |
  | `certifications` | 0.9 | certified |
  | `summary` | 0.7 | mentioned in the summary |
  | `declared` | 0.6 | only in the Skills list |
  | `other` | 0.5 | somewhere else |

  It also keeps the sentence where the skill was found (the `context`), so the
  UI can show "we counted Docker because you wrote: *containerised twelve
  services…*".
- **Implied skills** (`SKILL_IMPLICATIONS`, 15 skills): phrases that prove a
  skill without naming it. "containeris…" means Docker; "release pipeline"
  means CI/CD; "led a team" means Leadership; "sprint" and "retrospective"
  mean Agile. These are hand-written on purpose, so every decision can be
  explained.
- The final skill list is ordered **strongest evidence first**. If anything
  must be shortened, the weakest skills are the ones cut.
- The CV report and upload response turn the source into a plain **evidence
  label** for each skill (`_skills_with_evidence` in `main.py`):
  **demonstrated** (experience, projects, certifications), **mentioned**
  (summary or elsewhere) or **listed** (only in a Skills section). This
  replaced an "advanced / intermediate / beginner" label that was assigned
  purely by position in the list: the parser never measures proficiency, and
  no CV can tell it.

Experience, education, certifications and projects all come from their
sections, found by the same heading detection (`_section_lines`; at most 20,
5, 5 and 10 lines). If a CV has no heading for one of them, the fallback
quotes **the CV's own lines** (`_lines_mentioning`): lines naming a degree,
university or diploma count as education; a certification or "certified"
counts as a certification; "N years" counts as experience. It used to insert
text the CV never contained ("Bachelor's degree in Computer Science or
related field" for anyone who wrote the word "degree"), which then counted as
their education. Because this changed the parser's output, `PROFILE_VERSION`
went from 3 to 4, so every cached profile is rebuilt the next time it's read.

### 7.4 Reading a job description (`analyze_job_description`)

Two ways, returning the same `JobRequirements` shape (`technical_skills`,
`soft_skills`, `required_experience`, `education_requirements`,
`certifications`, `keywords`):

1. **Gemini** (`use_llm=True` and a working `GOOGLE_API_KEY`): the prompt asks
   it to extract only what the text supports, and `response_schema` forces
   the answer into exactly that JSON shape. Results are cached per
   description (`lru_cache(512)`).
2. **Rules** (always available): the same skill scanner; years from the
   pattern "`5+`", "`3 years`"; an education requirement if words like
   "degree", "bachelor" or "computer science" appear ("master"/"phd" means an
   advanced degree); AWS/Kubernetes certifications if "certified" is nearby.

**Which one is used where:** bulk lists (`GET /api/jobs`,
`/api/job-recommendations`) always use **rules**, because one LLM call per
job would be far too slow for a list. Single-job actions (`GET
/api/jobs/{id}`, applying, `/api/analyze`, the demo) try **Gemini first**
(only when `GOOGLE_API_KEY` is set).

For a **stored job**, `_job_requirements(job)` then adds the skills the
employer typed into the posting's "required skills" field, spelled the usual
way (`python` becomes `Python`) and without duplicates. So a skill listed
there counts towards the match even if the description never mentions it.
The result is a copy, never an edit: the extractor caches its results, and
changing one in place would leak one job's skills into another.

### 7.5 The match score (`matcher.analyze_match`)

```mermaid
flowchart TD
    S["For each skill the job requires"] --> A{"1. In your extracted skills?"}
    A -- yes --> M["Matched (records whether described or only listed)"]
    A -- no --> B{"2. Whole phrase appears in your CV text?<br/>(not for ambiguous words)"}
    B -- yes --> M
    B -- no --> C{"3. Very similar to one of your skills?<br/>embedding similarity ≥ 0.75"}
    C -- yes --> M
    C -- no --> D{"4a. An implied-skill phrase in your experience/projects?"}
    D -- yes --> M
    D -- no --> E{"4b. One experience line is about it?<br/>similarity ≥ 0.55"}
    E -- yes --> M
    E -- no --> X["Missing"]
```

Then:

- **Skills score** = matched ÷ required × 100. If you match **fewer than
  half**, it is capped at 50.
- **Experience score**: if both the job and your CV mention years ("5 years"),
  it's your years ÷ required years × 100 (max 100). Otherwise it's the
  embedding similarity between the texts. If the job states no experience,
  the score is `None` (not scored).
- **Education score**: embedding similarity between the job's requirement and
  your education lines; `0` if you have none listed; `None` if the job
  doesn't ask.
- **Final score** = weighted average of **only the parts the job specifies**:
  skills 50 %, experience 30 %, education 20 %, re-scaled so the weights
  used add up to 100 %. A job that only lists skills is scored on skills
  alone, instead of handing out free points for requirements it never
  mentioned.
- It also returns `recommendations` (at most 8), `match_evidence` (how each
  skill was matched) and a one-sentence `summary`.

**Worked example** (checked by running the real code, with the rule-based job
reader):

```text
CV:   Skills
      Python, AWS
      Experience
      Backend engineer at Acme for 3 years
      Containerised our services and shipped them to production

Job:  "We need an engineer with Python, Docker, Kubernetes and AWS. 5+ years required."
```

The job needs Python, Docker, Kubernetes and AWS, plus 5 years, and states no
education requirement. Python and AWS match at step 1 (recorded as
`declared`, because they're only in the Skills list). Docker **also** matches at step 1: when the
CV was uploaded, the implied-skill phrase "containerised" already added Docker
to your skills, with the source `experience`. (Step 4a is the safety net for
older cached profiles and activity lines.) Kubernetes is missing.
Skills = 3/4 = 75. Experience = 3/5 = 60. Education = not scored.
Final = (75×0.5 + 60×0.3) ÷ 0.8 = 55.5 ÷ 0.8 = **69 %** (rounded).

### 7.6 Embeddings and semantic search

- **Model:** `all-MiniLM-L6-v2`, run with **ONNX Runtime** on the CPU. The
  model's official ONNX file is downloaded from Hugging Face (about 90 MB)
  into `.model_cache/`, at a pinned revision (`MODEL_REVISION`) so the files
  and therefore the vectors can never change underneath the stored ones. The
  Render build downloads it in advance: `python -m
  ai_job_intelligence.services.embedding_service`.
- **How a vector is made** (`_embed`): the tokenizer splits the text into at
  most 256 tokens; the model gives one vector per token; those are averaged,
  ignoring padding ("mean pooling"); and the average is scaled to length 1.
  These are exactly the three steps the `sentence-transformers` library does
  around the same model.
- **Why ONNX Runtime and not PyTorch:** the same model under PyTorch pushed
  the backend to about 577 MB of memory, over the 512 MB of a small Render
  instance, and made every install about 1.5 GB. Under ONNX Runtime the
  backend uses about 330 MB and installs in about 30 seconds. Before
  switching, the vectors were compared on the project's own CVs and job
  texts: the largest difference was 0.0000002, which is floating-point
  rounding. So stored vectors stayed valid and no threshold moved. (The
  `fastembed` package was tried first and rejected: its vectors differed
  for texts longer than 128 tokens, and CVs are long.)
- **What gets embedded:**
  - a CV = its skills (written **twice**, to give them more weight), soft
    skills, experience, projects, education and certifications;
  - a job = title, required skills and description.
- **Storage** (`vector_store.py`): 384 `float32` numbers become about 2 KB of
  base64 text in the `embedding` column. That's about 4× smaller than JSON,
  and it loads straight into numpy.
- **Search:** every vector has length 1, so similarity is a dot product.
  Ranking all rows is **one matrix multiplication** (`matrix @ query`). This
  is exact and instant for thousands of rows; for far more, the planned
  upgrade is the `pgvector` Postgres extension, and all vector code goes
  through `semantic_index.py`, so only that file would change.
- **Caching:** `_cached_embedding` remembers up to 4,096 texts.
- **Fallback:** if the model can't be loaded (for example, no internet on the
  very first start), a simple word-count "embedding" is used so the app still
  runs, with much weaker meaning-based matching.

### 7.7 Job recommendations: retrieve, then rerank

```mermaid
flowchart LR
    CV["Your CV vector"] --> R["Stage 1: rank ALL open jobs by similarity<br/>(fast, one matrix multiply)"]
    R --> T["Keep top 50"]
    T --> Q["Stage 2: full analyze_match on each<br/>(slow, precise, rules only)"]
    Q --> S["Sort by match score → return top 20 + tips"]
```

Stage 1 answers "is this the right *kind* of job?" cheaply. Stage 2 answers
"which exact skills are missing?", which is too expensive to run on the whole
job board. This two-stage shape is standard in search systems.

### 7.8 Career insights

`GET /api/career-insights` avoids a common mistake. If it counted skills over
**every** job on the board, an accountant would be told to learn Docker just
because the board has many developer jobs. So:

1. It takes the 15 open jobs closest to your CV vector and keeps those with
   similarity ≥ 0.25. These are **"your field"**.
2. Skill demand, gaps (up to 6), "in demand %", recommended roles (up to 4
   titles) and the salary range are computed **only inside your field**.
3. **Profile strength** = the percentage of 7 checks you pass (have skills; 5+
   skills; have experience; 2+ experience entries; education; projects;
   certifications).
4. If nothing is close enough, it says so honestly instead of showing generic
   numbers.
5. A `sources` list explains where every number came from.
6. **Plan check.** Right after the "no CV yet" answer (which is free), the
   route calls `entitlements.open_insight_session`: on the Free plan that
   starts or continues a 24-hour session and answers `402` when both of the
   month's sessions are used. The usage row is saved only after the insights
   were computed successfully (see 14.9).

### 7.9 Learning resources

`learning_resources.resources_for_skill(skill)` collects, for one skill:

1. **Official docs** from a hand-made map of 52 entries (react.dev, the Python
   docs, Kubernetes basics…), always listed first.
2. **dev.to** articles, **GitHub** repositories and **Hacker News**
   discussions, from their public JSON APIs. These are APIs, not HTML
   scraping, which would silently break whenever a site's page design
   changed.

The three network sources run **in parallel** threads, each with a 6-second
timeout. Results are cached in memory for 6 hours. There are at most 3 per
source and 8 in total, ordered docs → course → article → repo → discussion.
If every network source fails, `degraded: true` is returned, so the UI can say
"sources unavailable" instead of pretending nothing exists. The endpoint looks
up at most `limit` (default 4, max 8) skills per call. It is kept **separate**
from the analysis endpoints so analysis pages load instantly even if those
sites are slow.

### 7.10 The CareerLens assistant (chat)

```mermaid
flowchart LR
    Q["Your question"] --> I["1. Detect intent<br/>gaps / salary / jobs / experience / cv / skills / general"]
    I --> R["2. Retrieve facts<br/>your CV profile + top 5 relevant open jobs + skill demand"]
    R --> C["3. Build a text context from those facts"]
    C --> G{"4. Gemini available?"}
    G -- yes --> L["Gemini answers ONLY from the context"]
    G -- "no / error" --> D["Rule-based answer from the same facts"]
    L & D --> O["5. Reply + sources + learning links"]
```

- **Intent:** keyword lists, where longer matching phrases score higher. So
  "what skills am I missing" is a *gaps* question, not a *skills* question.
- **Retrieval:** the question is embedded and compared with open jobs. For
  questions about *your fit* (jobs, gaps, salary), the question vector is
  **blended with your CV vector**, because "which jobs suit me?" by itself
  says nothing about you. Jobs must reach similarity 0.20, except for fit
  questions, which always return the closest 5.
- **Rules given to Gemini** (`_SYSTEM_RULES`): never invent job titles,
  companies, salaries or skills; if the facts don't answer the question, say
  so; be brief.
- **Response fields:** `response`, `intent`, `sources` (your CV, each job used
  with its relevance, the market data), `generated_by` (`"model"` or
  `"rules"`), and `links` (official docs for your top missing skills).

### 7.11 Interviews: rules and states

```mermaid
stateDiagram-v2
    [*] --> scheduled: employer books
    scheduled --> confirmed: candidate
    scheduled --> declined: candidate
    confirmed --> scheduled: employer changes the TIME
    scheduled --> cancelled: employer
    confirmed --> cancelled: employer
    scheduled --> completed: employer
    confirmed --> completed: employer
```

- Only **employers** can book. The candidate is given by `candidate_user_id`
  (or the older `candidate_id`, a CV id). You can't book yourself, and a
  `job_id` must be one of your own jobs.
- `contact_email` defaults to the employer's email, so there's always a way to
  reach someone.
- `meeting_url` must start with `http://` or `https://`. The frontend shows it
  as a "Join" link, and a `javascript:` link would run code in the
  candidate's browser when clicked. Duration must be 5–480 minutes; `mode`
  must be `video`, `phone` or `onsite`.
- Editing details is employer-only and impossible once the interview is
  cancelled, declined or completed. **Moving the time of a confirmed
  interview sets it back to `scheduled`**, because the candidate agreed to
  the old time, not the new one.
- Status changes check **who** is acting: candidates confirm or decline;
  employers cancel or complete. Nothing changes after cancelled/declined.
- The frontend's "Add to calendar" button builds an `.ics` calendar file in
  the browser (`downloadIcs` in `InterviewsView.tsx`).

### 7.12 Post-analysis guidance

`guidance.build_guidance` replaces a long, repetitive list ("Add X to your
skills… Complete a project using X…" for every missing skill) with a few
**grouped and ordered actions**. Each action has:

- a `title` and `detail`;
- a `group`: *Close the gap*, *Strengthen your CV*, *Frame your experience*,
  or *Position yourself*;
- a `priority`: 1 = likely the reason you'd be filtered out, 2 = materially
  improves your chances, 3 = polish;
- the `skills` it concerns (so the UI can attach learning links);
- an `effort`: "An hour", "A weekend", "Weeks, not days"…

Examples: "Start with X and Y" for the top 3 gaps; "Move what already matches
to the top"; "Rewrite your bullets around outcomes" if experience is under
50 %; "Apply now" at 75 % or more; "Treat this posting as a target" under
40 %.

### 7.13 Code lessons: the maths in the code

The AI parts sound mysterious until you see how little code they are. Here
are the three pieces of maths that everything else rests on.

#### From text to 384 numbers (`embedding_service._embed`)

```python
encodings = _tokenizer.encode_batch(texts)                       # 1. text -> token ids
ids  = np.array([e.ids for e in encodings], dtype=np.int64)
mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)

token_vectors = _session.run(None, feeds)[0]                     # 2. (texts, tokens, 384)
weights = mask[..., None].astype(np.float32)                     #    1 for real tokens, 0 for padding
pooled = (token_vectors * weights).sum(axis=1) / np.clip(
    weights.sum(axis=1), 1e-9, None)                             # 3. average the real tokens
norms = np.linalg.norm(pooled, axis=1, keepdims=True)
return pooled / np.clip(norms, 1e-12, None)                      # 4. scale to length 1
```

1. **Tokenize.** The text is cut into pieces the model knows ("contain",
   "##erised"…), each with a number. Texts in one batch are padded to the
   same length, and the *attention mask* marks which positions are real (1)
   and which are padding (0).
2. **Run the model.** It produces one 384-number vector *per token*, each
   describing that token in its context.
3. **Mean pooling.** The sentence's vector is the average of its tokens'
   vectors, counting only real tokens (multiply by the mask, divide by the
   number of real tokens). `np.clip(…, 1e-9, None)` avoids dividing by zero
   for an empty text.
4. **Normalise.** Divide by the vector's length so every vector has length
   1. That's what makes the next step so simple.

#### Comparing everything at once (`vector_store.rank`)

```python
ids = list(candidates.keys())
matrix = np.vstack([candidates[i] for i in ids])   # one row per job: shape (jobs, 384)
scores = matrix @ query                            # one number per job
order = np.argsort(-scores)                        # best first
```

For two vectors of length 1, the *cosine similarity* (how closely they point
the same way) is just the **dot product**: multiply matching numbers and add
them up. `matrix @ query` does that for every row at once, a *matrix
multiplication*, which numpy runs in optimised C code. Ranking a thousand
jobs is one line and takes about a millisecond. No loop in Python, no vector
database needed at this size.

#### Weighting only what the job asks for (`matcher.analyze_match`)

```python
match_ratio = len(matched_skills) / max(len(requirements.technical_skills), 1)
if match_ratio < 0.5:
    skills_score = min(skills_score, 50.0)          # under half the skills: cap at 50

weighted: list[tuple[float, float]] = []
if requirements.technical_skills:
    weighted.append((skills_score, 0.50))
if experience_match is not None:
    weighted.append((float(experience_match), 0.30))
if education_match is not None:
    weighted.append((float(education_match), 0.20))

if weighted:
    total_weight = sum(w for _, w in weighted)
    final_score = round(sum(v * w for v, w in weighted) / total_weight)
```

A job that doesn't mention education leaves `education_match` as `None`, so
education is simply **left out**, and dividing by `total_weight` (0.8
instead of 1.0) rescales the remaining weights to add up to 100 %. The
worked example in 7.5 is exactly this: (75 × 0.5 + 60 × 0.3) ÷ 0.8 = 69.

> **Teacher's note: every number in code is a decision.** `0.75`, `0.55`,
> `0.25`, `0.50`… none of these came from a textbook. Each was chosen by
> *measuring* on real CVs and jobs (for example, a relevant experience line
> scores about 0.6 against an expanded skill query, an unrelated one under
> 0.1, hence 0.55). When you see a threshold, ask two questions: *how was
> it chosen?* and *what breaks if it moves?* And when you change the
> embedding model, every one of these numbers must be measured again,
> because each model scores on its own scale.

---

## Part 8 — The frontend (Next.js)

### 8.1 Technology

Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS 4,
Framer Motion (most animations), react-icons, and anime.js + GSAP (only for
the job-edit screen and interview cards). The Inter font is loaded with
`next/font/google`. The dev server runs on **port 3001** (`next dev -p 3001`)
because port 3000 is used by another project on the development machine.

### 8.2 How URLs map to files

| URL | File |
|---|---|
| `/` | `app/page.tsx` |
| `/login` | `app/(public)/login/page.tsx` |
| `/jobs/7` | `app/(jobseeker)/jobs/[id]/page.tsx` |
| `/employer/jobs/7/edit` | `app/employer/jobs/[id]/edit/page.tsx` |

- A folder name in **parentheses**, like `(public)` or `(jobseeker)`, is a
  **route group**. It groups pages under one layout but **doesn't appear in
  the URL**.
- A folder in **square brackets**, `[id]`, is a **dynamic segment**. The page
  reads it with `useParams()`.
- `layout.tsx` wraps every page in its folder and below.

### 8.3 Layouts and page protection

- **Root layout** (`app/layout.tsx`): font, CSS, `<Providers>`.
- **Public layout**: adds Navbar + Footer, **except** on `/login`,
  `/register`, `/forgot-password`, `/reset-password` and `/verify-email`,
  which are full-screen pages.
- **Job seeker layout**: sidebar with Dashboard, Find Jobs, My Applications,
  Saved Jobs, Career Insights, Interviews, Messages (with an **unread
  badge**), CareerLens Chat, My CV, **Billing**, Profile and Logout (on phones, a slide-in
  menu and a "Sign out" icon). Below the links, a **plan card**: on Free it
  shows "N of 5 analyses left this month" and "Upgrade to Pro"; on Pro, a
  "CareerLens Pro" badge (with "Payment issue" if a renewal failed). Above the page it shows the
  `VerifyEmailBanner` until the email is confirmed. If there's no token, it
  sends you to `/login`.
- **Employer layout**: Dashboard, My Jobs, Post a Job, Candidates,
  Interviews, Messages (with the unread badge), Company, plus the same
  banner. No token → `/login`; not an employer → `/dashboard`.
- **Small detail, the phone menu:** it closes when you navigate, without an
  effect. The layout remembers *which page the menu was opened on* and treats
  it as open only while you're still on that page, so the value is derived
  during rendering instead of being reset after every navigation.
- **Admin layout**: Dashboard, Users. Not an admin → `/dashboard`.

> These layout checks are for **convenience only**. Anyone can edit
> `localStorage` in their browser and see an empty admin page. The real
> protection is the backend, which checks the token and role on every
> request.

### 8.4 The shared building blocks

**`AuthProvider`**. The session is four `localStorage` keys: `access_token`,
`user_id`, `careerLens_role`, `user_email`. `localStorage` is an *external
store*: React doesn't own it, and it doesn't exist on the server, where pages
are first rendered. React's tool for reading such a store is
**`useSyncExternalStore`**. It renders "signed out" on the server and during
hydration, then switches to the browser's real value without a mismatch
warning. `loading` is `true` until then (and while a sign-in is running), so
layouts don't redirect you before the token has been read. The store listens
for the browser's `storage` event, so **signing out in one tab updates your
other tabs** too. `login()` calls the API, stores the keys, shows "Login
successful!", and navigates by role. `logout()` clears the keys and goes to
`/login`. It also shows "Your session has ended" when `api.ts` reports one.

**`api.ts`**

```ts
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000").replace(/\/+$/, "");
```

- Uses `NEXT_PUBLIC_API_BASE` if set (production), otherwise the local
  backend. A trailing `/` is removed so URLs never become `…//api/…`.
- `apiCall(endpoint, options)` = `fetch(API_BASE + endpoint)` with
  `Content-Type: application/json`, the Bearer token if you have one, and
  `cache: "no-store"` (always fresh data). **If a signed-in request comes
  back 401**, the session is over (the token expired after 24 hours, or a
  password reset revoked it), so it clears the stored session. The layouts
  then send you to `/login`, and `AuthProvider` explains why.
- **File uploads don't use `apiCall`**, because it forces the JSON content
  type. The CV page, profile image upload and demo use `fetch` directly with
  `FormData`, and the browser sets the correct multipart type itself.
- `viewFile(endpoint)` downloads a protected file **with** the token, turns it
  into a temporary `blob:` URL, opens it in a new tab, and frees it after 60
  seconds. (A plain link can't send the `Authorization` header.)
- The session helpers (`SESSION_KEYS`, `clearStoredSession()`,
  `notifySessionChanged()`) live here too, because `AuthProvider` already
  imports `api.ts`; importing the other way round would be circular.

**`format.ts`**: `formatScore` (`null` → "Not specified"), `scoreWidth` (bar
width), `isSpecified`, `formatSalary`, the evidence labels (`EVIDENCE_LABEL`:
Demonstrated / Mentioned / Listed only, `EVIDENCE_HELP`, `evidenceWidth`),
`describeApiError`, and `passwordHint`. `describeApiError` exists because FastAPI's 422 errors are an
**array** of objects; printing one directly shows "[object Object]", so this
turns it into readable sentences.

**`MessageDialog`**: a dimmed full-screen overlay with a card. It's an info
pop-up (one "OK" button) or, when given `onConfirm`, a confirmation with a
confirm button (the text is set by the page, e.g. "Yes") and "Cancel".
Clicking outside the card closes it. Used for every success, error
and "Are you sure?" in the app.

**`InterviewsView`** (`side="candidate"` or `"employer"`): loads
`/api/interviews`; shows upcoming and past cards with time, mode, a Join
button (only for safe http/https links), dial-in, contact details, notes and
**Add to calendar**; candidates get *Confirm/Decline*, employers get *Mark
complete/Cancel* and *Edit details* (opens `InterviewScheduler`). Cards tilt
slightly with the mouse (`attachTilt`).

**`InterviewScheduler`**: the form (date/time, duration, mode tabs, link or
address or phone, contact email/phone, notes). It defaults to one week from
now on the hour, 45 minutes, video, in your browser's time zone. The form is
only mounted while it's open, so it always starts fresh from its props.

**`MessagesView`**: a conversation list (initials, name, last message, unread
badge) plus the open thread, and a "Write a message…" box with Send. On
phones the list and thread take turns on screen. There's no push channel
(such as a WebSocket), so it **polls**: the list every 15 seconds, and an
open conversation every 5 seconds. Polling pauses while the browser tab is
hidden, and a thread is only replaced (and scrolled) when something in it
actually changed. Reading a thread fires `notifyMessagesRead()`, so the
sidebar badge updates at once.

**`unreadMessages.ts`**: `useUnreadMessageCount()` asks
`GET /api/messages/unread/count` every 30 seconds (paused in a hidden tab)
and whenever messages are read. The layouts show the number on the Messages
link.

**`AuthCard`** is the centred card used by the three account pages;
**`VerifyEmailBanner`** fetches your profile once and, if the email isn't
confirmed, shows the reminder with a **Resend link** button (you can dismiss
it for the visit).

**`LearningResources`** (`skills=[…]`): asks
`/api/learning-resources` for up to 4 skills. It shows tabs per skill and
labels each link (Documentation, Course, Repository, Article, Discussion). It
loads *after* the page, so it never slows the analysis down, and it says
honestly when sources are unavailable.

**`billing.ts`**: the frontend's side of plans. `useSubscription()` loads
`GET /api/billing/subscription` and reloads whenever the window receives the
custom event `PLAN_CHANGED_EVENT` (fired after an upload, an analysis, opening
Career Insights, or a finished checkout), so the sidebar card, the dashboard
strip and the Billing page all stay in step without talking to each other.
`startCheckout(interval)` sends only `{plan: "pro", interval}` and then does
a full-page redirect to the URL the server returns;
`openBillingPortal()` does the same for Stripe's portal. The file's opening
comment says it plainly: this code can *show* a plan but never *grant* one.

**`UpgradePrompt`** (`title`, `message`, `perks`, `badge`): the card shown
where the API answered `402`, with "See Pro plans" and "View my usage".
**`UpgradeDialog`** is the same message as a `MessageDialog` pop-up, used on
the CV and analyse pages when a monthly limit is reached.

**`motion.ts`**: `revealFields` (form fields fly in), `flipCard` (the
published/draft card flips in 3-D on the edit page), `revealLedgerRow`,
`playPublishSequence` (a GSAP timeline that returns a promise, so the page
only moves on after the animation finishes), and `attachTilt`. **All of them
do nothing** if the user asked their system for reduced motion.

### 8.5 Every page

**Public**

| URL | What it shows / does | API |
|---|---|---|
| `/` | Landing: hero "Find Your Perfect Career Match with AI", features, sections for job seekers and employers, CTAs. **Never redirects.** | — |
| `/about`, `/how-it-works`, `/faq`, `/contact` | Static information pages (Contact uses the links in `site.ts`). | — |
| `/pricing` | The three plans with a Monthly/Annual switch. Prices come from Stripe when it's configured; otherwise the page shows built-in fallback prices ($29 / $23). The "Save N%" badge is *computed* from the two prices. The Pro button depends on who's looking: signed out → register; signed in, Stripe off → "Payments not available yet" (today's state); signed in, Stripe on → **Upgrade to Pro** (checkout); already Pro → "Manage subscription"; employer → "For job seekers". Cover letters are marked "Coming soon". The FAQ only describes what the app actually does. | `GET /api/billing/plans`, `/subscription`, `POST /api/billing/checkout` |
| `/demo-analysis` | Drag-and-drop CV + job title + description → score, matched/missing skills, "How this score was calculated". | `POST /api/demo/analyze` |
| `/login` | Email + password → `AuthProvider.login`. | `POST /api/auth/login` |
| `/register` | Step 1: pick "I'm looking for a job" or "I'm hiring". Step 2: name, email, password (live hints) → then go to login. | `POST /api/auth/register` |
| `/forgot-password` | Email → the same "if an account exists…" answer for everyone. Linked from the login page. | `POST /api/auth/forgot-password` |
| `/reset-password?token=` | New password twice (live hints) → "Password changed", sign in. A bad or expired link offers "Request a new link". | `POST /api/auth/reset-password` |
| `/verify-email?token=` | Confirms the address as soon as it opens. | `POST /api/auth/verify-email` |

**Job seeker**

| URL | What it shows / does | API |
|---|---|---|
| `/dashboard` | Stats, a **plan strip** (Free: "2/5 analyses · 1/2 CV uploads · 0/2 insight sessions this month"; Pro: renewal date), quick actions, recommended jobs. | `/api/user/stats`, `/api/jobs`, `/api/billing/subscription` |
| `/cv` | Upload a CV (then go to `/analyze?cv_id=…`), list CVs, view a file. A `402` opens the "Plan limit reached" dialog. | `/api/upload-cv`, `/api/cvs`, `/api/cvs/{id}/download` |
| `/analyze?cv_id=` | Your parsed profile, including "Skills & Evidence" (each skill labelled Demonstrated, Mentioned or Listed only); **Find Matching Jobs** → list; **Analyze This Job** → saves an analysis and opens `/results/{id}` (a `402` opens the "Plan limit reached" dialog). | `/api/cvs/{id}/analysis`, `/api/job-recommendations`, `/api/jobs/{id}`, `POST /api/analyze` |
| `/results/[id]` | One saved analysis: score, "Requirements your CV already evidences", "Asked for, not found", **What to do next** (guidance), learning resources. | `/api/analyses/{id}` |
| `/analysis/[id]` (a CV id) | Full CV report: profile strength, "Where we found your skills", experience/education, tips, learning resources for `learn_next`. | `/api/cvs/{id}/analysis`, `/api/cvs/{id}/download` |
| `/jobs` | Open jobs with your match score. | `/api/jobs` |
| `/jobs/[id]` | Job detail, match breakdown, **Save / [OK] Saved** toggle, **Apply Now**. | `/api/jobs/{id}`, `/api/saved-jobs`, `POST /api/applications` |
| `/saved-jobs` | Your bookmarks; remove one (with confirmation). | `/api/saved-jobs` |
| `/applications` | Your applications and their status. | `/api/applications` |
| `/career-insights` | Profile strength, gaps, market value, recommended roles, skills in demand, salary, "How these figures were calculated", a reset-data button. On Free, a line "Career Insights session 1 of 2 this month · open until …"; when both sessions are used, the upgrade card instead (the Reset button stays). | `/api/career-insights`, `/api/reset-data` |
| `/billing` | Current plan and status, renewal or end date, a warning if a payment failed, "Upgrade to Pro" or "Manage subscription", and usage bars for uploads, analyses and insight sessions. It's also where Stripe sends you after paying (`?checkout=success&session_id=…`): the page then shows "Confirming your payment…" and waits for the **server** to report Pro (see 14.5). | `/api/billing/subscription`, `/checkout/confirm`, `/portal` |
| `/career-lens` | The chat, with suggested "Start here" questions and a Show/Hide sources panel. | `POST /api/career-lens/chat` |
| `/interviews` | `<InterviewsView side="candidate" />` | `/api/interviews` |
| `/messages` | `<MessagesView />` | `/api/messages…` |
| `/profile` | Edit name and fields, upload a photo (replaces the old one). | `/api/profile`, `/api/upload-image` |

**Employer**

| URL | What it shows / does | API |
|---|---|---|
| `/employer/dashboard` | Stats, your postings, recent applications (from your first 3 jobs). | `/api/user/stats`, `/api/jobs`, `/api/jobs/{id}/applications` |
| `/employer/company` | Company profile form. | `/api/company` |
| `/employer/jobs` | Your postings. | `/api/jobs` |
| `/employer/jobs/new` | Post a job (skills and benefits are comma-separated). | `POST /api/jobs` |
| `/employer/jobs/[id]` | One posting: stats and the applicants table with **Accept/Reject** (each asks "Yes/Cancel"). | `/api/jobs/{id}`, `/applications`, `/accept`, `/reject` |
| `/employer/jobs/[id]/edit` | The "revision ledger" editor: a published/draft card that flips, a list of unpublished changes with Revert per field, and **Publish changes** sending only the changed fields. | `GET`/`PATCH /api/jobs/{id}` |
| `/employer/candidates` | Skills filter and "Min. profile score" → **Search** → click a candidate. | `/api/candidates` |
| `/employer/candidates/[id]` | Candidate profile with a "Profile score", **Schedule Interview**, **Send Message**, **View CV** (opens the original file). | `/api/candidates/{id}`, `/api/interviews`, `/api/messages`, `/api/cvs/{id}/download` |
| `/employer/interviews` | `<InterviewsView side="employer" />` | `/api/interviews` |
| `/employer/messages` | `<MessagesView />` | `/api/messages…` |

**Admin**

| URL | What it shows / does | API |
|---|---|---|
| `/admin/dashboard` | System statistics and recent users. | `/api/admin/stats`, `/api/admin/users` |
| `/admin/users` | All users; view details; delete (with confirmation). | `/api/admin/users…` |

### 8.6 Reading one page's code (job detail)

`app/(jobseeker)/jobs/[id]/page.tsx`, simplified:

```tsx
"use client";                                     // runs in the browser
export default function JobDetailPage() {
  const jobId = useParams().id as string;         // "7" from /jobs/7
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);   // starts true: we're about to load
  const [saved, setSaved] = useState(false);

  // Load when the page appears, and again if jobId changes.
  useEffect(() => {
    let active = true;                            // becomes false when we leave
    (async () => {
      const res = await apiCall(`/api/jobs/${jobId}`);          // token added for us
      if (res.ok && active) setJob(await res.json());
      const savedRes = await apiCall("/api/saved-jobs");        // is it already saved?
      if (savedRes.ok && active) setSaved((await savedRes.json()).some((s) => s.job_id === parseInt(jobId)));
      if (active) setLoading(false);
    })();
    return () => { active = false; };             // "cleanup": runs when leaving
  }, [jobId]);

  const handleSave = async () => {                // an event handler: setState freely
    const res = saved
      ? await apiCall(`/api/saved-jobs/${jobId}`, { method: "DELETE" })
      : await apiCall("/api/saved-jobs", { method: "POST", body: JSON.stringify({ job_id: parseInt(jobId) }) });
    if (res.ok) setSaved(!saved);                  // the button redraws
  };
  // ...render: title, match breakdown, Save button, Apply Now button, MessageDialog
}
```

Almost every page follows this shape: **state → load in `useEffect` →
`apiCall` → `setState` → the screen redraws**, with `MessageDialog` for
feedback. Two details in the effect are deliberate, and they are what the
strict React lint rules (`npm run lint`) check:

1. **State is set only after an `await`**, never synchronously at the top of
   the effect. `loading` simply *starts* as `true` instead of the effect
   calling `setLoading(true)`, which would force an immediate extra render.
2. **The `active` flag.** If you leave the page, or `jobId` changes, before a
   slow request finishes, React runs the cleanup function, `active` becomes
   `false`, and the late response is ignored instead of overwriting newer
   data. This is the pattern React's documentation recommends for fetching
   in an effect.

When a page needs to *reload* after an action (e.g. the employer's
applicants list after Accept), the fetching part is a separate function that
**returns** the data (`loadApplications()`); the effect and the button
handler each decide what to do with it.

### 8.7 The React lessons that cost us a bug

These are the frontend ideas most likely to trip you up, each learned from a
real bug in this project.

**1. In development, React runs every effect twice, on purpose.**
React's *Strict Mode* (on by default in `next dev`) mounts each component,
immediately unmounts it (running your cleanup), and mounts it again. It does
this to expose effects that can't survive being stopped and restarted.
Production doesn't do it.

The Billing page first had this "protection" against running twice:

```tsx
const started = useRef(false);
useEffect(() => {
  if (started.current) return;   // ← the bug
  started.current = true;
  let active = true;
  load().then((data) => { if (active) setInfo(data); });
  return () => { active = false; };
}, []);
```

In development: run 1 sets `started = true` and starts loading; Strict Mode's
cleanup sets run 1's `active = false`; run 2 sees `started === true` and
returns immediately. So run 1's result is ignored *and* run 2 never loads
anything, and the page sat on "Loading…" forever. The fix was to **delete the
guard**: each run has its own `active` flag, the cancelled run's result is
dropped, and the second run does the work. It worked in production only by
luck.

> **Teacher's note.** If an effect breaks when it runs twice, the effect is
> wrong, not React. Write effects so that "start, stop, start again" is
> harmless: each run cleans up after itself, and anything it triggers on the
> server is safe to trigger twice. That second part matters on the backend
> too; see how Career Insights sessions survive a double request (14.9).

**2. `useSearchParams()` needs a `<Suspense>` boundary.** Pages that read the
URL's `?query` (`/reset-password`, `/pricing` for `?checkout=canceled`,
`/billing` for `?checkout=success`) wrap their content like this:

```tsx
export default function BillingPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <BillingContent />       {/* the part that calls useSearchParams() */}
    </Suspense>
  );
}
```

Next.js pre-renders pages at build time, when there is no URL yet. The
`Suspense` boundary tells it "render everything else now, and this part in
the browser". Without it, `npm run build` fails.

**3. Components that don't know about each other can still stay in sync.**
The sidebar's plan card, the dashboard strip and the Billing page each load
the plan separately. When you upload a CV, the CV page fires one browser
event:

```ts
window.dispatchEvent(new Event(PLAN_CHANGED_EVENT));
```

and every `useSubscription()` listening for it reloads. The same pattern is
used for messages (`notifyMessagesRead()`) and for the login session
(`AUTH_CHANGED_EVENT`). It's a simple alternative to a global state library,
fine at this size.

**4. Hiding a button is not security.** The layouts redirect employers away
from job-seeker pages, and the pricing page hides "Upgrade" from Pro users.
All of that is *convenience*: anyone can open the browser's developer tools
and call the API directly. Every rule that matters is checked again on the
server. The frontend's job is to show the server's decisions clearly, never
to make them.

---

## Part 9 — Every user journey, step by step

**A. A job seeker from zero to interview**

1. `/register` → choose "I'm looking for a job" → name, email, password →
   `POST /api/auth/register` (a confirmation email goes out) → go to `/login`.
2. `/login` → token stored → `/dashboard`, with a "please confirm your email"
   banner until the link is clicked.
3. `/cv` → upload a PDF → the backend saves it, extracts text, parses the
   profile, computes the vector → the browser goes to `/analyze?cv_id=5`.
4. **Find Matching Jobs** → retrieve-then-rerank list → **Analyze This Job** →
   `POST /api/analyze` (Gemini reads the job if configured) → `/results/12`
   with guidance and learning links.
5. `/jobs/3` → **Save** (`POST /api/saved-jobs`) → **Apply Now**
   (`POST /api/applications`, stores your match score) → `/applications`.
6. The employer accepts → your application shows *accepted*.
7. The employer books an interview → it appears in `/interviews` → **Confirm**.
8. The Messages link shows an unread badge → the employer's message is in
   `/messages` → reply.
9. Forgot the password? `/login` → **Forgot password?** → email link →
   `/reset-password` → new password → signed out everywhere → sign in again.

**B. An employer**

1. Register as "I'm hiring" → login → `/employer/dashboard`.
2. `/employer/company` → save the company name. (Renaming it later updates
   all your postings.)
3. `/employer/jobs/new` → post → the vector is computed immediately, so the
   job appears in job seekers' recommendations.
4. `/employer/jobs/7` → see applicants → **Accept/Reject**.
5. `/employer/jobs/7/edit` → change the title → **Publish changes** (only the
   changed fields are sent; the vector is recomputed).
6. `/employer/candidates` → **Search** → a candidate → **View CV**,
   **Schedule Interview** and **Send Message**.

**C. The public demo**: `/demo-analysis` → upload + paste → an instant result,
nothing saved, the file deleted straight away.

**D. The admin**: log in with an admin account → `/admin/dashboard` →
`/admin/users`.

**E. A Free user reaching the limits** (this works today)

1. A new job seeker uploads two CVs: both accepted (`usage_events` gets two
   `cv_upload` rows). The third upload → `402` → "Plan limit reached" dialog,
   and the file is never stored.
2. They open Career Insights: session 1 of 2 starts, and refreshing is free
   for 24 hours. The next day, session 2 of 2. After that → `402` → the
   upgrade card.
3. Five analyses work; the sixth → `402`. Deleting old analyses does **not**
   give any back (the count comes from `usage_events`).
4. `/billing` shows three usage bars and "Free allowances reset on 1
   October 2026".
5. On the 1st of the month, all three counts start from zero, because the
   quota only counts rows created since midnight UTC on the 1st. Nothing is
   deleted; old rows just stop counting.

**F. Buying Pro** (only once Stripe keys are configured; switched off today)

1. `/pricing` → Annual → **Upgrade to Pro** → `POST /api/billing/checkout
   {plan: "pro", interval: "year"}`.
2. The server picks the yearly price from its whitelist, creates (or reuses)
   the user's Stripe customer, and returns a Checkout URL. The browser leaves
   for Stripe's page.
3. The user pays with the fake card `4242 4242 4242 4242`.
4. Stripe sends signed webhooks to `/api/billing/webhook`, and redirects the
   browser to `/billing?checkout=success&session_id=cs_test_…`.
5. The server verifies the webhook, asks Stripe for the subscription's current
   state, and saves a `subscriptions` row with `status = active`, `plan =
   pro`.
6. The Billing page, which has been politely waiting, sees the server
   report Pro: "Welcome to CareerLens Pro". All limits are gone.
7. Later, **Manage subscription** → Stripe's portal → Cancel → a webhook
   records `cancel_at_period_end = true` → Pro continues until the paid
   period ends → Stripe sends `customer.subscription.deleted` → back to Free.

Part 14 explains each of these steps and why it is built that way.

---

## Part 10 — Security: what is protected and how

### 10.1 Protections in place

| Threat | Protection | Where |
|---|---|---|
| Stolen database reveals passwords | bcrypt hashes only | `services/auth.py` |
| Stolen database reveals reset/verify links | only SHA-256 hashes of the tokens are stored | `services/account_tokens.py` |
| A stolen session outliving a password reset | the reset raises `token_version`, which invalidates every older token | `auth_dependency.py`, `reset_password` |
| "Forgot password" revealing who is registered, or flooding an inbox | same reply for every address; email sent in the background; limited per network and per address | `forgot_password` |
| A reset link used twice, or late | single-use, expires after 1 hour; a verify link can't reset a password | `account_tokens.find_valid` |
| Password guessing | per-IP **and** per-account rate limits | `main.py`, `rate_limit.py` |
| Discovering which emails exist | same response time and same message either way | `verify_password_constant_time` |
| Forged login tokens | JWT signed with a strong secret; placeholders and short keys refused; required in production | `config.py` |
| Making yourself admin at sign-up | only `job_seeker`/`employer` are accepted | `schemas.SELF_ASSIGNABLE_ROLES` |
| Uploads escaping the folder (`../../`), or client-chosen names in URLs | CVs and images get random names; the image route serves only files directly in its folder | `_save_upload`, `upload_image`, `get_image` |
| Huge uploads filling the disk | 5 MB limit (2 MB for the demo) | `main.py` |
| Abuse of the free demo | 5 per hour per IP in production; file always deleted | `demo_analyze` |
| Leaking server paths | PDF errors logged, generic message returned; `cv_url` is a download link, not a path | `pdf_parser.py`, `get_candidates` |
| `javascript:` links in meeting URLs | only http/https accepted; the UI renders only safe links | `schemas._validate_meeting_url`, `InterviewsView` |
| Reading or changing other people's data | ownership checked on CVs, analyses, jobs, applications, interviews; 404 instead of 403 where an id could be probed | throughout `main.py` |
| Other websites calling the API from a browser | CORS allows only listed origins | `config.CORS_ORIGINS` |
| Secrets in Git | `.env` and `.secret_key` are gitignored; Render generates `SECRET_KEY` | `.gitignore`, `render.yaml` |
| Test data leaking into real data | tests run in a throwaway PostgreSQL schema | `conftest.py` |
| Making yourself Pro from the browser | no route accepts a plan; only a verified webhook, or the server asking Stripe itself, writes `subscriptions` | `billing_routes.py`, `services/billing.py` |
| Paying a cheaper price by editing the request | the browser sends a plan *name*; the server picks the price from its whitelist, and unknown fields are refused | `services/plans.py`, `schemas.CheckoutRequest` |
| Fake or replayed payment notifications | webhook HMAC signature checked on the raw body; signatures older than 5 minutes refused | `stripe_webhook` |
| The same payment event applied twice | event ids stored in the same transaction as the change | `billing.process_event` |
| Charging a real card by mistake | live Stripe keys refused at start-up | `config._resolve_stripe_secret_key` |
| Beating a quota with simultaneous requests | per-user PostgreSQL advisory lock around check-and-record | `services/entitlements.py` |
| A deleted account still being charged | the subscription is cancelled with Stripe first; deletion refused if Stripe can't be reached | `delete_user` |
| Card numbers leaking | cards are typed on the provider's page only; nothing about a card is ever stored here | Checkout redirect |

### 10.2 Password rules

`password_policy.validate_password` follows the NIST guidance (SP 800-63B):
length matters more than "must contain a symbol" rules, which mostly produce
`Password1!`. A password must be **10–128 characters** and must **not** be:

- on the common-password list (`password`, `qwerty`, `careerlens`, …);
- one of those with digits added (`password2024`);
- made of 2 or fewer different characters (`aaaaaaaaaa`);
- a run of 8+ letters or digits in order (`abcdefghij`, `12345678…`);
- containing your email's name part (`jane.doe` for `jane.doe@x.com`, if it's
  4+ characters).

The register page gives instant hints for the length and repetition rules
(`passwordHint` in `format.ts`); the server checks all of them and is the
final judge.

### 10.3 Rate limits

| Limit | Production | Development |
|---|---|---|
| Login attempts per IP | 10 per 5 min | 200 per 5 min |
| Failed logins per email | 5 per 15 min | 5 per 15 min |
| Registrations per IP | 5 per hour | 200 per hour |
| Demo analyses per IP | 5 per hour | 30 per hour |
| "Forgot password" per IP | 10 per hour | 200 per hour |
| Reset emails per address | 3 per hour (later requests get the same reply, no email) | same |
| Verification re-sends per account | 3 per hour | same |

They use a **sliding window** (count attempts in the last N seconds) rather
than a fixed window. A fixed window would let someone send a full batch at
11:59 and another at 12:00. Exceeding a limit returns **429** with a
`Retry-After` header.

### 10.4 Honest limitations

- The token is kept in **`localStorage`**. If an attacker ever managed to run
  JavaScript on the site (an XSS bug), they could read it. An `HttpOnly`
  cookie is the usual alternative, but with the frontend and API on
  different domains (Vercel and Render), the browser would treat it as a
  third-party cookie, which many browsers now block. It needs both on one
  domain first.
- **Logout only forgets the token in this browser.** A copied token stays
  valid until its 24 hours are up, unless the password is reset, which
  revokes every token at once.
- Rate limits live in **one process's memory**. They reset on restart and
  aren't shared between several servers (Redis would fix this).
- **Profile images are public** to anyone who knows the URL; the random
  32-character names make the URLs impractical to guess.
- Email verification is informational: an unverified account can still sign
  in. Requiring it would be a one-line check at login, if you ever want it.

---

## Part 11 — Running, testing and deploying

### 11.1 What you need

Python 3.12, Node.js 20+, and PostgreSQL 16 (any recent version works).

### 11.2 Create the database (once)

```sql
-- in psql as the postgres superuser
CREATE USER ai_user WITH PASSWORD 'choose-a-password';
CREATE DATABASE ai_job_intelligence OWNER ai_user;
```

The app's user must **own** the database, or at least be allowed to create
schemas in it, because the tests create a throwaway schema.

### 11.3 Run the backend

```bash
cd ai-job-intelligence
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # about 30 seconds, ~360 MB
```

Create `ai-job-intelligence/.env` (never commit it):

```env
DATABASE_URL=postgresql+psycopg://ai_user:choose-a-password@localhost:5432/ai_job_intelligence
APP_ENV=development
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
# Optional:
# SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
# GOOGLE_API_KEY=<your Gemini key>
# SMTP_HOST=smtp.example.com   (plus SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM)
#   Without SMTP, reset and verification emails are printed in this terminal.
# STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET / STRIPE_PRICE_PRO_MONTHLY / STRIPE_PRICE_PRO_YEARLY
#   Leave these out: payments stay switched off and everyone is on Free (Part 14).
```

Start it:

```bash
uvicorn ai_job_intelligence.main:app --app-dir src --reload --port 8000
```

- `--app-dir src` tells Uvicorn the package is inside `src/`.
- `--reload` restarts when you save a file (development only). **Changes to
  `.env` need a restart.**
- Open <http://127.0.0.1:8000/docs> for FastAPI's automatic, clickable API
  documentation. It's the fastest way to try a route.
- Each start first applies any database migrations (on a database created
  before migrations existed, the first start hands it over; see 6.3).
- The first start downloads the embedding model (about 90 MB) into
  `.model_cache/`; later starts take a few seconds. To download it in
  advance: `PYTHONPATH=src .venv/bin/python -m ai_job_intelligence.services.embedding_service`.
- With `APP_ENV=development` and an empty database you get the demo accounts
  `employer@example.com` / `password123` and `admin@careerlens.ai` /
  `admin123`.

### 11.4 Run the frontend

```bash
cd ai-job-intelligence/frontend
npm install
npm run dev              # http://localhost:3001
```

No configuration is needed locally: `API_BASE` defaults to
`http://127.0.0.1:8000`. To point elsewhere, create `frontend/.env.local`
with `NEXT_PUBLIC_API_BASE=…` and restart.

Other scripts: `npm run build` (production build), `npm run start` (serve
that build), `npm run lint` (ESLint).

### 11.5 Tests

**Backend:**

```bash
cd ai-job-intelligence
.venv/bin/pip install pytest      # once; it isn't a runtime dependency
.venv/bin/python -m pytest -q
```

- 298 tests. They use `TEST_DATABASE_URL` if set, otherwise your
  `DATABASE_URL`.
- Billing is tested **without any network**. `conftest.py` gives the test
  app made-up Stripe settings, and an automatic fixture
  (`_no_real_stripe_calls`) makes any real Stripe call fail the test.
  `test_billing.py` replaces Stripe with an in-memory fake (`FakeStripe`) and
  signs its webhooks exactly the way Stripe does, so the real signature check
  runs. A `grant_plan(headers)` fixture puts a test user on Pro by writing a
  subscription row directly (the test plays Stripe's part); the shared
  `seeker` user is Pro, so tests about uploads or insights aren't stopped by
  the Free limits.
- To run just one file: `.venv/bin/python -m pytest src/ai_job_intelligence/test_billing.py -v`.
- `conftest.py` sets `APP_ENV=development`, creates a schema named like
  `test_1789209097_7497f6ad` (with the time it was made), points every
  connection at it (`options=-csearch_path=…`), builds it **by running the
  migrations**, and **drops it when the run ends**, even if tests fail.
  Your real `public` tables are never touched. A run that is killed outright
  can't clean up, so each run also removes test schemas more than 6 hours
  old.
- Uploads during tests go to a temporary folder, and emails are captured
  instead of sent.

**Browser (Playwright), 26 tests in `frontend/e2e/`:**

```bash
# once: a schema for browser tests, in your usual database
psql "postgresql://ai_user:…@localhost:5432/ai_job_intelligence" -c 'CREATE SCHEMA e2e'

cd ai-job-intelligence/frontend
npx playwright install chromium   # once
E2E_DATABASE_URL='postgresql://ai_user:…@localhost:5432/ai_job_intelligence?options=-csearch_path%3De2e' \
  npm run test:e2e
```

Playwright builds the frontend and starts both servers itself (API on 8111,
site on 3111). The specs cover the public pages and demo, accounts
(registration, login, logout, forgot/reset/verify pages), the full
job-seeker journey, the full employer journey (post, edit, accept/reject,
view CV, interview, message, unread badge) and the admin area. Every test
also fails on any JavaScript error or any 5xx response. Tests create their
own uniquely named accounts, so the `e2e` schema never needs resetting.
Playwright's backend runs with the Stripe variables forced empty, so browser
tests never touch Stripe, whatever your `.env` contains. The job-seeker spec
checks that a Free user's first visit to Career Insights starts "session 1 of
2". (The browser tests were last run before the billing work; they need
`E2E_DATABASE_URL`, which isn't set on the development machine.)

**Frontend checks:** `npm run lint` (no errors or warnings) and
`npm run build`.

### 11.6 Deploying

**Backend on Render.** The Blueprint `render.yaml` at the repository root
defines everything:

| Setting | Value |
|---|---|
| Root directory | `ai-job-intelligence` |
| Plan | Starter (512 MB is enough: the API uses about 330 MB; a disk needs a paid plan) |
| Build command | `pip install -r requirements.txt && PYTHONPATH=src python -m ai_job_intelligence.services.embedding_service` (installs, then downloads the model into the build) |
| Start command | `uvicorn ai_job_intelligence.main:app --app-dir src --host 0.0.0.0 --port $PORT` |
| Health check | `/` (answers `{"message": "AI Job Intelligence API is running"}`) |
| `PYTHON_VERSION` | `3.12.3` |
| `APP_ENV` | `production` |
| Disk | `careerlens-uploads`, 1 GB, mounted at `/var/data` |
| `UPLOAD_DIR` / `IMAGES_DIR` | `/var/data/uploads` / `/var/data/uploads/images` |
| `SECRET_KEY` | generated by Render |
| `DATABASE_URL`, `CORS_ORIGINS`, `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `GOOGLE_API_KEY` | you enter these (`SMTP_PORT` defaults to 587) |

- `render.yaml` also lists `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PRICE_PRO_MONTHLY` and `STRIPE_PRICE_PRO_YEARLY` as values to
  enter. **Leave them empty**: payments stay off and the site runs with
  everyone on Free. (If they were ever used, the production webhook secret
  would come from an endpoint registered in the Stripe dashboard, not from
  `stripe listen`; `BILLING.md` has the details.)
- `--host 0.0.0.0` accepts connections from outside the machine; `$PORT` is
  the port Render assigns.
- **Migrations** run automatically when the app starts; nothing to configure.
- **Files:** a Render service's own disk is wiped on every deploy, which is
  why uploads go to the persistent disk. A service with a disk runs as a
  single instance and can't do zero-downtime deploys, which is fine at this
  scale.
- **Email:** any SMTP provider works (Brevo, Resend, Mailgun, or Gmail with an
  app password). Links in emails point at the first `CORS_ORIGINS` entry; set
  `FRONTEND_URL` only if that isn't your site's address. Without SMTP the app
  still works, but reset and verification emails aren't sent.
- **First admin:** production creates no demo accounts. Register normally,
  then run on the database:
  ```sql
  UPDATE user_profiles SET role = 'admin'
  WHERE user_id = (SELECT id FROM users WHERE email = 'you@example.com');
  ```

**Frontend on Vercel.**

| Setting | Value |
|---|---|
| Root directory | `ai-job-intelligence/frontend` |
| Framework | Next.js (detected automatically) |
| Build command | `npm run build` |
| Environment variable | `NEXT_PUBLIC_API_BASE=https://<your-render-service>.onrender.com` |

**Order:** deploy Render first (to get its URL) → deploy Vercel with that URL
→ put the Vercel URL into Render's `CORS_ORIGINS` → redeploy Render.
`NEXT_PUBLIC_API_BASE` is built into the site, so after changing it you must
**redeploy** Vercel. Vercel's *preview* deployments have different URLs; add
them to `CORS_ORIGINS` if you want previews to reach the API.

---

## Part 12 — Known issues and technical debt

Checked against the current code.

### 12.1 Fixed (all covered by tests)

| What was wrong | What changed |
|---|---|
| Employers couldn't open a candidate's CV | allowed for job seekers' CVs (`_may_open_cv`) |
| Admin "delete user" crashed (500) when the user had data; "reset my data" crashed if an interview used the CV | ordered, all-or-nothing deletion (6.8) |
| No database migrations | Alembic, applied at start-up, with a safe hand-over for old databases (6.3) |
| ~577 MB of memory and 1.5 GB installs (PyTorch) | the same model on ONNX Runtime: ~330 MB, 30-second installs, identical vectors (7.6) |
| `passlib` (abandoned, breaks on Python 3.13) and a mis-pinned `bcrypt` | `bcrypt` used directly; old password hashes still verify (`test_auth_hardening.py`) |
| The employer's "required skills" field didn't count in the match | added to the job's requirements (`_job_requirements`, 7.4) |
| Education, certifications and projects found only under exact headings; invented education text | same section detection as experience, compound headings, the CV's own lines as fallback (7.3) |
| "advanced / beginner" labels assigned by list position | evidence labels: Demonstrated / Mentioned / Listed only (7.3) |
| Candidate "match score" wasn't a match | shown honestly as "profile score" |
| No password reset or email verification | both, with hashed one-time links and sign-out-everywhere (6.5) |
| Messages only updated on reload; unread count unused | polling and an unread badge (8.4) |
| `/api/jobs` ran one count query per job | one grouped query |
| Renaming a company left old postings under the old name | postings follow the profile |
| Image files named after the user's file; `cv_url` exposed a server path | random names; a download URL |
| Deprecated `on_event`, `datetime.utcnow`, Pydantic `class Config` | `lifespan`, `clock.utcnow()`, `ConfigDict` |
| 36 lint errors, 47 warnings | none |
| Loaders could overwrite newer data with a slow response | the `active` pattern (8.6) |
| An expired session left pages half-broken | 401 → signed out with an explanation |
| Browser tests lost | 26 new Playwright tests (11.5) |
| `test_ai.py` / `test_embeddings.py` were scripts | real tests |
| Gemini client created with no key (log noise) | skipped without `GOOGLE_API_KEY` |
| The pricing page was decoration: no limits, every button went to register, and the FAQ promised a free trial, PayPal, refunds and discounts that didn't exist | real server-side limits, a working (test-mode) checkout, and honest copy (Part 14) |
| "Cover letter generation" advertised but not built | labelled "Coming soon" |
| `upload_cv` turned *every* error, including deliberate ones, into "500 Failed to save CV" | deliberate refusals (`HTTPException`) are passed through unchanged |

### 12.2 Still open

1. **Messages poll rather than push.** Every 5 to 30 seconds is fine at this
   scale; instant delivery would need WebSockets or Server-Sent Events.
2. **Rate limits live in one process's memory** (10.3). Correct for one
   Render instance; several instances would need a shared store like Redis.
3. **The token lives in `localStorage`, and logout is local** (10.4).
4. **Uploads are on one Render disk.** Right for a single instance; running
   several would need object storage (S3, Cloudflare R2).
5. **The chat assistant has no conversation memory.** Each question is
   answered on its own (retrieval + grounding, 7.10). Conversation history is
   the next step on the assistant roadmap.
6. **Employer candidate search ranks by profile completeness** (or by
   meaning, with `q`), not against a specific job. Ranking candidates for
   one posting would be a new feature.
7. **Job lists score each job for the viewer on request** (rules, cached),
   20 at a time. Fine now; a very large board would want scores precomputed.
8. **Image CVs need `GOOGLE_API_KEY`** (or Tesseract installed) to be read.
9. **Email verification is informational**, not enforced (10.4).
10. **The original local database** keeps 4 harmless differences from the
    models: on `users`, a unique *constraint* instead of a unique *index* and
    one missing index; and `cvs.user_id` allows NULL. The app's role can't
    alter `users` there. Databases built by the migrations (tests, Render)
    match the models exactly.
11. **Payments are switched off.** The Stripe integration is complete and
    tested but has no keys, because Stripe accounts can't be opened from
    Algeria. Nobody can buy Pro; everyone is on Free. The realistic
    alternative (Chargily Pay) would need a second provider adapter (14.12).
12. **Quotas follow the calendar month (UTC)**, not each user's own billing
    date. Simple and predictable, but a user who joins on the 30th gets a
    fresh allowance two days later.
13. **Usage recorded while on Pro still counts after downgrading** in the
    same month (the ledger doesn't care which plan you were on). Pro users'
    Career Insights sessions aren't recorded at all.
14. **A second live subscription is logged, not refunded.** Checkout makes it
    very unlikely (14.4), but if Stripe ever reports two, the server logs an
    error for a human to refund one rather than refusing Stripe's data.
15. **"Priority support" and "Dedicated account manager"** are promises made
    by people, not features in the code.
16. **The landing page's pricing section has "$29" written into it**; only
    `/pricing` reads live prices.
17. **The browser tests haven't been re-run since the billing work** (they
    need `E2E_DATABASE_URL`).

---

## Part 13 — How to change things (recipes)

**Add a new API route**
1. If it takes or returns JSON, add a Pydantic class to `schemas.py`.
2. Add the function to `main.py` near related routes, following the
   `SessionLocal()` / `try` / `finally: db.close()` pattern and
   `Depends(get_current_user_id)` if login is needed.
3. Check ownership or role **inside** the route.
4. Add a test in the matching `test_*.py` using the `client` fixture and a
   user fixture from `conftest.py` (`seeker`, and so on).
5. Call it from the frontend with `apiCall("/api/…")`.

**Change the database structure (add a column, a table…)**
1. Edit the model in `models/…py`.
2. Generate a migration:
   ```bash
   cd ai-job-intelligence
   .venv/bin/alembic revision --autogenerate -m "add a column to jobs"
   ```
   Alembic compares the models with your database and writes the difference
   into a new file in `migrations/versions/`.
3. **Read the file and correct it.** Autogenerate is a draft. The usual fix:
   a new `NOT NULL` column on a table that already has rows needs a
   `server_default`, or existing rows would violate it (see how
   `token_version` does it in `0002`).
4. Run the tests. `test_models_and_migrations_describe_the_same_schema`
   fails if a model and the migrations disagree, for example if you forgot
   step 2.
5. That's all: your server applies it at its next start, and Render at the
   next deploy.
6. On the original local database, `users` belongs to `postgres`, so put new
   per-person columns on `user_profiles`.

**Add a skill the parser should recognise**
1. Add it (lowercase) to `_TECH_VOCAB` or `_GENERAL_SKILLS` in
   `ai_service.py`.
2. If `.title()` would spell it wrongly, add its correct spelling to
   `_FRAMEWORK_MAP`.
3. If it's also an ordinary English word, add it to `_AMBIGUOUS_SKILLS` (and
   aliases to `_SKILL_ALIASES`).
4. **Increase `PROFILE_VERSION`**, so every cached CV profile is rebuilt with
   the new vocabulary.
5. Optionally add an official docs link to `OFFICIAL_DOCS` in
   `learning_resources.py`.

**Change the embedding model**
Pick a model whose Hugging Face repository has an ONNX export, then change
`MODEL_NAME`, `MODEL_REPO` and `MODEL_REVISION` in `embedding_service.py`,
set `EMBEDDING_DIM` in `vector_store.py` to the new size, and **increase
`EMBEDDING_VERSION`**. Stored vectors are then ignored and recomputed as
they are read. Re-check the matcher's similarity thresholds (0.55, 0.75)
against the new model, since each model scores on its own scale.

**Add or upgrade a Python package**
Edit `requirements.in`, then regenerate `requirements.txt` in a fresh virtual
environment, as its header explains. `requirements.txt` is what Render
installs, so this keeps local and deployed versions identical.

**Add a page**
Create `app/(jobseeker)/your-page/page.tsx` (it inherits the job-seeker
layout and its login check), start it with `"use client"`, load data in
`useEffect` with `apiCall` using the pattern in [8.6](#86-reading-one-pages-code-job-detail),
and add a sidebar entry to `navItems` in `app/(jobseeker)/layout.tsx`. A
page that reads `useSearchParams()` must be wrapped in `<Suspense>` (see
`reset-password/page.tsx`), or `npm run build` refuses to pre-render it.
Run `npm run lint`: it enforces the effect rules.

**Add a setting**
Read it in `config.py` with `os.getenv("NAME", default)`, document it in
Appendix B, and add it to `render.yaml` (use `sync: false` for secrets).

**Change the Free plan's limits**
1. Edit `PLAN_LIMITS` in `services/plans.py`, e.g.
   `PlanLimits(cv_uploads_per_month=3, analyses_per_month=5, insight_sessions_per_month=2)`.
   `None` means unlimited.
2. Update the words people read: the Free card and comparison table in
   `app/(public)/pricing/page.tsx`, the Starter list in `app/page.tsx`, and
   the sentence on `app/(jobseeker)/billing/page.tsx`.
3. Update the numbers asserted in `test_billing.py` (search for
   `cv_uploads_per_month`, `"uploaded 2 CVs"`, `range(5)`), then run it.
   No migration: limits are code, not data.

**Add a new metered action** (say, "5 chat questions a month")
1. Add a kind in `models/usage_event.py`: `USAGE_CHAT = "chat"`.
2. Add a field to `PlanLimits` (and a value for every plan) and a line to
   `_LIMIT_FIELD` and `_LIMIT_MESSAGE` in `services/entitlements.py`.
3. Add `check_chat_quota` / `reserve_chat` wrappers (copy the analysis ones).
4. In the route: the fast `check_…` near the top, then `reserve_…` right
   before the commit that saves the result, so a failure costs nothing.
5. Frontend: handle `response.status === PAYMENT_REQUIRED` with
   `UpgradeDialog`; add the new kind to `usage_summary` in
   `entitlements.py` (so the API reports it) and a usage bar on `/billing`.
6. Tests: the limit is refused at N+1, deleting doesn't refund, Pro is
   unlimited.

**Make a feature Pro-only** (for example cover letters, when they exist)
1. Add a name to `PLAN_FEATURES` in `services/plans.py` for Pro and
   Enterprise, e.g. `frozenset({"cover_letters"})`.
2. Protect the route: `current_user_id: int =
   Depends(entitlements.require_feature("cover_letters"))`. It
   authenticates (401) and then checks the plan (402).
3. On the page, show `UpgradePrompt` when the API answers 402, and remove
   "Coming soon" from the pricing page.

**Turn Stripe payments on** (if you ever can)
Follow `ai-job-intelligence/BILLING.md`: a Stripe account in test mode, one
product with two recurring prices, the customer portal saved, the Stripe CLI
forwarding webhooks, four variables in `.env`, then restart the backend.
Nothing in the code needs to change.

**Use a different payment provider** (such as Chargily Pay)
Read 14.12 first; it explains what stays and what changes. In short: keep
`plans.py`, `entitlements.py`, `usage_events` and the frontend's 402
handling as they are; write a new provider module next to
`services/billing.py` with its own checkout call and signed-webhook handler
that writes the same `subscriptions` rows; and add the provider's settings
to `config.py`.

---

## Part 14 — Payments and subscriptions, every stage

**Where things stand today.** The code contains a complete subscription
system built on **Stripe in test mode**: checkout, signed webhooks, a local
copy of each subscription, the customer portal, and plan limits enforced on
the server. It has 39 tests. But Stripe accounts can't be opened from
Algeria, so it was decided to **leave Stripe**: no keys are configured,
`BILLING_ENABLED` is `False`, checkout answers `503`, and every user is on
Free. **The plan limits are fully active** regardless, because they don't
depend on Stripe at all.

So why study this part carefully? Because the *shape* of this system is the
same for every payment provider, and it's one of the most instructive
pieces of backend engineering in the project: it deals with money, with a
second server you don't control, with messages that arrive late, twice or
out of order, and with users who might try to cheat. Everything here would
carry over to Chargily Pay or any other provider (14.12).

### 14.1 The one rule that shapes everything

> **The browser is never trusted to say what a user has paid for.**

Everything the browser sends can be changed by the user: open the
developer tools, edit the request, send it again. So if the frontend could
tell the backend "this user is Pro now", anyone could make themselves Pro
for free. The same goes for the *price*: if the browser chose which price to
charge, a user could pick a cheaper one.

So the design has exactly **two trusted sources** of payment information:

1. **Webhooks from the provider**, which carry a signature only the
   provider can produce.
2. **The server asking the provider itself**, over its own authenticated
   connection with the secret API key.

Nothing else ever writes to the `subscriptions` table. There is no "set my
plan" route anywhere in the API. That absence is the most important security
feature of this whole part.

> **Teacher's note: the trust boundary.** Draw a line around the code you
> control: your server and your database. Everything outside the line (the
> browser, the request body, URL parameters, even the redirect after
> payment) is a *claim* someone is making. Claims can be useful hints ("this
> session id might be finished"), but the server must turn every hint into a
> fact by checking it with a trusted source before acting on it. You'll see
> this pattern at every stage below.

### 14.2 The whole flow in one picture

```mermaid
sequenceDiagram
    participant B as Browser
    participant API as FastAPI (our server)
    participant DB as PostgreSQL
    participant S as Stripe
    B->>API: POST /api/billing/checkout {plan: "pro", interval: "year"}
    API->>API: whitelist: (pro, year) → price_… ; already subscribed? → 409
    API->>S: create customer (once) + create Checkout Session
    S-->>API: checkout URL
    API-->>B: {url}
    B->>S: user types the card on Stripe's page
    S-->>B: redirect to /billing?checkout=success&session_id=cs_…
    S->>API: POST /api/billing/webhook (signed)
    API->>API: verify signature on raw bytes
    API->>DB: INSERT event id (skip if already there)
    API->>S: retrieve the subscription's CURRENT state
    API->>DB: upsert subscriptions row, COMMIT
    B->>API: GET /api/billing/subscription (the success page polls)
    API->>DB: read subscriptions
    API-->>B: {plan: "pro"} → "Welcome to CareerLens Pro"
```

The code is split so that each file has one job:

| File | Job | Talks to Stripe? |
|---|---|---|
| `services/plans.py` | what each plan includes; the price whitelist | no |
| `services/billing.py` | checkout, portal, webhook processing, sync | **yes, the only file that does** |
| `services/entitlements.py` | what the user may do *now*, from the database | no |
| `billing_routes.py` | the six HTTP routes | no (calls `billing`) |
| `models/billing.py`, `models/usage_event.py` | the four tables | no |

Because only `billing.py` knows about Stripe, replacing Stripe means
replacing one file, not the whole system.

### 14.3 Stage 1: the pricing page and the price whitelist

The pricing page's toggle says Monthly or Annual. When the user clicks
**Upgrade to Pro**, the browser sends only this:

```json
{"plan": "pro", "interval": "year"}
```

It's a plan **name**, never a Stripe price id. The server turns the name
into a price id with a table built from environment variables
(`services/plans.py`):

```python
def _price_table() -> dict[tuple[str, str], str]:
    table = {
        (PLAN_PRO, INTERVAL_MONTH): STRIPE_PRICE_PRO_MONTHLY,
        (PLAN_PRO, INTERVAL_YEAR): STRIPE_PRICE_PRO_YEARLY,
    }
    return {key: price for key, price in table.items() if price}

def price_id_for(plan: str, interval: str) -> str | None:
    return _price_table().get((plan, interval))
```

If the pair isn't in the table, the answer is `None` and checkout is
refused. It never falls back to "some other price". And because
`CheckoutRequest` has `extra = "forbid"` (6.9, Lesson 7), a request that tries
to add a `price_id` is refused with `422` before any of this runs.

The same table works **backwards** for webhooks: `plan_for_price(price_id)`
turns a price id from Stripe into `("pro", "year")`. A price that isn't in
the table becomes the plan `"unknown"`, which is saved but grants nothing.

**The prices on the page come from Stripe too.** `billing.price_catalog()`
asks Stripe for both prices (cached for 10 minutes), so the page can't show
$29 while Stripe charges something else. It also checks the *configuration*:
if `STRIPE_PRICE_PRO_MONTHLY` were accidentally set to the yearly price, the
Monthly button would charge for a year. The catalog compares each price's
real billing interval with its slot and leaves out any mismatch or archived
price, and checkout refuses anything not in the catalog. With Stripe off, the
catalog is empty and the page shows its built-in fallback prices.

### 14.4 Stage 2: creating the checkout

`POST /api/billing/checkout` → `billing.create_checkout_session`:

```python
price_id = price_id_for(plan, interval)
offered = {(p["plan"], p["interval"]) for p in price_catalog()}
if price_id is None or (plan, interval) not in offered:
    raise BillingError("That plan is not available right now.", 400)

# Duplicate prevention, part 1: no second subscription while one is live.
if active_subscription(db, user.id) is not None:
    raise BillingError("You already have an active subscription. …", 409)

customer_id = get_or_create_customer(db, user)
_expire_open_checkouts(customer_id)
session = stripe_client().v1.checkout.sessions.create(params={
    "mode": "subscription",
    "customer": customer_id,
    "line_items": [{"price": price_id, "quantity": 1}],
    "client_reference_id": str(user.id),
    "metadata": {"user_id": str(user.id)},
    "subscription_data": {"metadata": {"user_id": str(user.id)}},
    "success_url": f"{FRONTEND_URL}/billing?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
    "cancel_url": f"{FRONTEND_URL}/pricing?checkout=canceled",
})
db.commit()
return session.url
```

Step by step:

1. **The user id comes from the token**, never from the body (6.9,
   Lesson 3). The route also refuses employers and admins (`403`): Pro's
   features are job-seeker features, so an employer paying for them would
   get nothing.
2. **Whitelist and catalog**: explained above.
3. **Duplicate prevention, part 1**: someone who already has Pro can't
   start a second subscription; they're sent to the portal to change the
   existing one.
4. **One Stripe customer per user.** `get_or_create_customer` takes a
   per-user lock, looks in `billing_customers`, and only creates a customer
   at Stripe if there is none. Without the table, every abandoned checkout
   would leave another customer behind. Without the lock, two quick clicks
   could create two.
5. **Duplicate prevention, part 2.** `_expire_open_checkouts` closes any
   checkout page this customer still has open. Part 1 can't see a checkout
   that's open but not yet paid, so without this a user could open
   checkout in two tabs and pay in both.
6. **Three ways to find the user again later**: the customer id (the main
   one), `client_reference_id`, and `metadata.user_id` on the subscription.
   When a webhook arrives days later, the server needs to know whose
   subscription it is.
7. **`{CHECKOUT_SESSION_ID}`** is literal text: Stripe replaces it with the
   real id when it redirects. (The double braces in the Python f-string
   produce single braces.)
8. **A stale customer.** In test mode you can press "Delete all test data"
   in Stripe, and the stored customer no longer exists there. The code
   catches Stripe's "No such customer" error once, forgets the stored id,
   and creates a new customer.

The route returns `{"url": …}`, and `startCheckout()` in the browser does a
full-page redirect to it with `window.location.assign(url)`.

### 14.5 Stage 3: paying on the provider's page, and coming back

The card is typed on **Stripe's** page, on Stripe's domain. It never passes
through the browser code of CareerLens, the backend, or the database. This
is on purpose: handling card numbers yourself brings heavy legal and
security obligations (the PCI DSS standard). Using the provider's page
keeps the project out of all that.

After paying, Stripe redirects the browser to
`/billing?checkout=success&session_id=cs_test_…`. Here is the trap every
beginner falls into:

> **The success page must not grant anything.** Anyone can type that URL
> into their address bar. If the page (or the backend, when the page calls
> it) treated "I'm on the success page" as proof of payment, everyone could
> be Pro by visiting a URL.

So the Billing page does two careful things (`BillingContent` in
`app/(jobseeker)/billing/page.tsx`):

1. It calls `POST /api/billing/checkout/confirm {session_id}` once. On the
   server (`confirm_checkout_session`), the id is only a **hint**: the
   server fetches that session **from Stripe**, checks that it belongs to
   this user (`client_reference_id == user id`, otherwise `404`), and if
   Stripe says it's complete, runs exactly the same sync as a webhook. The
   worst anyone can do with a made-up or stolen id is ask the server to
   re-read Stripe.
2. It **polls** `GET /api/billing/subscription` every 2 seconds for up to 30
   seconds, and only when the server reports a paid plan does it show
   "Welcome to CareerLens Pro". After 30 seconds it says honestly that it's
   still waiting.

Why both? The webhook usually arrives within a second or two, but it can lag
behind the redirect, and locally it only arrives while `stripe listen` is
running. The confirm call makes the page correct in both cases, and it's safe
because it only *asks Stripe*.

### 14.6 Stage 4: the webhook, where the truth arrives

A **webhook** is Stripe calling *your* server. It's the only way to learn
about things that happen when the user isn't on your site: the renewal next
month, a declined card, a cancellation in the portal.

```python
@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, "Webhook signing secret is not configured.")

    payload = await request.body()                      # the RAW bytes
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(400, "Missing Stripe-Signature header.")
    try:
        event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(400, "Invalid payload.")
    except stripe.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature.")

    event_data = event.to_dict()
    try:
        outcome = await run_in_threadpool(billing.process_event, event_data)
    except Exception:
        raise HTTPException(500, "Event processing failed; it will be retried.")
    return {"received": True, "outcome": outcome}
```

**Part A: is it really from Stripe?** There's no login: Stripe isn't a user.
Instead, Stripe signs every delivery. The header looks like
`t=1789300000,v1=5f2c…`, where `v1` is an **HMAC-SHA256** of the text
`"<t>.<raw body>"` computed with the endpoint's signing secret (`whsec_…`),
which only Stripe and this server know. `construct_event` recomputes it and
compares. If one byte of the body was changed, or the sender doesn't know
the secret, it doesn't match. It also refuses a timestamp older than **5
minutes**, so a captured request can't be replayed next week.

Two details that break signatures when done differently:

- **Read the raw bytes** (`await request.body()`). Parsing the JSON and
  re-serialising it can reorder keys or change spaces, and then the
  signature no longer matches.
- **`async def` only to read the body.** The real work (database, Stripe
  API) blocks, so it runs in a worker thread (`run_in_threadpool`) and
  doesn't freeze the server.

**What the response code means to Stripe.** `2xx` = delivered, done.
Anything else = "try again later": Stripe retries with growing gaps for up
to about three days. So a bad signature gets `400` (it wasn't Stripe, there
is nothing to retry), and a processing failure gets `500` (please send it
again).

**Part B: have we seen this event before?** (`billing.process_event`)

```python
inserted = db.execute(
    pg_insert(StripeEvent)
    .values(id=event["id"], type=event.get("type") or "", processed_at=utcnow())
    .on_conflict_do_nothing(index_elements=["id"])
    .returning(StripeEvent.id)
).first()
if inserted is None:
    db.rollback()
    return "duplicate"                    # an earlier delivery already committed

subscription_id = subscription_id_from_event(event)
if subscription_id is None:
    db.commit()
    return "ignored"                      # not about a subscription

sync_subscription(db, subscription_id)   # fetch from Stripe, save
db.commit()                               # event id + new state, together
return "processed"
```

Stripe delivers webhooks **at least once**: after a timeout, a network blip
or a deploy, the same event (same `evt_…` id) can arrive again. The event id
is inserted in the **same transaction** as the change it causes. So either
both are saved or neither is:

- a second delivery finds the id and stops (`duplicate`);
- if the sync fails, the rollback removes the id too, so Stripe's retry is
  processed properly instead of being skipped;
- if two deliveries arrive at the same instant, PostgreSQL makes the second
  `INSERT` wait for the first transaction, then skip.

**Part C: don't trust the event's snapshot; ask Stripe.** Events aren't
guaranteed to arrive in order. An old "created" event can arrive after a
newer "canceled" one, and each event carries a snapshot of the subscription
*at the time of that event*. If the server saved snapshots, the late old
event would bring a canceled subscription back to life. So the event is used
only to learn **which** subscription changed (`subscription_id_from_event`),
and `sync_subscription` **fetches its current state** from Stripe:

```python
def sync_subscription(db, stripe_subscription_id: str) -> Subscription | None:
    _lock(db, _SUBSCRIPTION_LOCK_NAMESPACE, stripe_subscription_id)
    sub = _as_dict(stripe_client().v1.subscriptions.retrieve(stripe_subscription_id))
    return upsert_subscription(db, sub)
```

Whatever order events arrive in, the row ends up matching what Stripe says
*now*. The lock makes two events about the same subscription, processed at
the same moment, run one after the other; otherwise the one that fetched
first could save last and overwrite newer data with older.

Each event type keeps the subscription id in a different place:
`customer.subscription.*` → the object itself; `invoice.*` →
`parent.subscription_details.subscription`; `checkout.session.completed` →
`subscription`.

**Part D: saving it** (`upsert_subscription`). It finds the user (by
customer id first, then the `user_id` metadata), turns the price into a plan
through the whitelist, and runs one **upsert**: `INSERT … ON CONFLICT
(stripe_subscription_id) DO UPDATE`. The first event inserts the row; every
later one updates the same row. Running it twice with the same data changes
nothing, and that is exactly what idempotency needs.

> **Teacher's note: tutorials go out of date.** In Stripe API version
> 2025-03-31, `current_period_start` and `current_period_end` **moved** from
> the subscription to each subscription *item*, and an invoice's subscription
> moved under `parent.subscription_details`. Most tutorials online still read
> `subscription.current_period_end`, which is now simply missing. This
> project reads them from the item, because the SDK's own source code
> (installed in `.venv`) was checked before writing a line. When you integrate
> with an outside service, **read the version you actually installed**, not a
> blog post.

### 14.7 Stage 5: the life of a subscription

A subscription changes status over time, and each change arrives as a
webhook:

```mermaid
stateDiagram-v2
    [*] --> active: first payment succeeds
    active --> active: renewal paid (period moves forward)
    active --> past_due: renewal card declined
    past_due --> active: a retry succeeds / card updated
    past_due --> unpaid: all retries failed (setting)
    past_due --> canceled: all retries failed (setting)
    active --> active: user cancels → cancel_at_period_end = true
    active --> canceled: the paid period ends after cancelling
    canceled --> [*]
```

| Stripe status | Meaning | Grants Pro here? |
|---|---|---|
| `active` | paid and current | **yes** |
| `trialing` | in a free trial (not used; there's no trial) | **yes** |
| `past_due` | a renewal failed; Stripe is retrying the card | **yes**, with a warning on the Billing page |
| `unpaid` | retries failed; kept but not paid | no |
| `canceled` | over | no |
| `incomplete` / `incomplete_expired` | the first payment never completed | no |
| `paused` | paused | no |
| anything new Stripe invents | unknown | **no** (fail closed) |

**Why keep access during `past_due`?** Cards expire and banks decline for
reasons that aren't the user's fault. Cutting access at the first decline
punishes them for their bank's hiccup, so the app shows "Your last payment
failed. Update your card" and waits. If all retries fail, Stripe moves the
subscription to `unpaid` or `canceled` (you choose which in Stripe's
settings), the webhook records it, and access ends.

**Cancelling is not ending.** When a user cancels in the portal, Stripe sets
`cancel_at_period_end = true` and the status stays `active`: they paid for the
month, so they keep it until the month ends. Only then does Stripe send
`customer.subscription.deleted` with status `canceled`. The Billing page
shows "Cancelled. Pro stays active until 13 October, and you won't be charged
again."

### 14.8 Stage 6: deciding what the user may do

`services/entitlements.py` reads the `subscriptions` table and never talks to
Stripe:

```python
ENTITLING_STATUSES = frozenset({"active", "trialing", "past_due"})
STALE_SUBSCRIPTION_GRACE = timedelta(days=7)

def active_subscription(db, user_id: int) -> Subscription | None:
    rows = (db.query(Subscription)
            .filter(Subscription.user_id == user_id,
                    Subscription.status.in_(ENTITLING_STATUSES))
            .order_by(Subscription.current_period_end.desc().nulls_last())
            .all())
    now = utcnow()
    for row in rows:
        if row.plan not in PLAN_LIMITS:          # "unknown" price → nothing
            continue
        if row.current_period_end is not None and \
           row.current_period_end + STALE_SUBSCRIPTION_GRACE < now:
            continue                             # probably a lost webhook
        return row
    return None
```

- **Fail closed.** Access is granted only for statuses on an explicit list.
  An unknown status, or an unknown plan, means no access. The opposite
  ("deny only the statuses we know are bad") would grant access by accident
  the day Stripe adds a new status.
- **Never subscribed** simply means no rows, so `None`, so Free.
- **The safety net for lost webhooks.** If a row still says `active` a week
  after its paid period ended, the renewal or cancellation event must have
  been missed (Stripe stops retrying after about three days). Such a row is
  not trusted. A normal renewal moves `current_period_end` forward long
  before this matters.
- `get_entitlements(db, user_id)` wraps it up: the plan name, its limits
  (from `PLAN_LIMITS`) and features. This is called on every metered
  request.

### 14.9 Stage 7: quotas, the part that works today

Plan limits don't need Stripe at all, which is why they're active right now.
Three things are metered, all per calendar month (UTC):

| Kind (`usage_events.kind`) | Free limit | Where it's recorded |
|---|---|---|
| `cv_upload` | 2 | `POST /api/upload-cv` |
| `analysis` | 5 | `POST /api/analyze` |
| `insight_session` | 2 (24 h each) | `GET /api/career-insights` |

**Why a separate ledger table?** Counting `cvs` or `analyses` rows would let
users delete old ones to get their allowance back. `usage_events` is
append-only: nothing deletes from it except deleting the whole account.

**Every metered action follows the same four steps**, inside the transaction
that performs the action:

```python
def _reserve(db, user_id: int, kind: str) -> None:
    _lock_user_quota(db, user_id)              # 1. one request per user at a time
    _refuse_if_used_up(db, user_id, kind)      # 2. count this month  3. 402 if at the limit
    db.add(UsageEvent(user_id=user_id, kind=kind))   # 4. record; the caller's COMMIT saves it
```

**The race condition, and the lock that stops it.** Imagine a Free user with
4 of 5 analyses used who sends two requests at the same instant:

```text
without a lock                          with the advisory lock
A: count → 4, OK                        A: take lock, count → 4, OK, record
B: count → 4, OK                        B: wait for the lock…
A: record, commit (5)                   A: commit (5), lock released
B: record, commit (6)  ← 6 of 5!        B: take lock, count → 5, refused (402)
```

`pg_advisory_xact_lock(7301, user_id)` is a named lock that PostgreSQL holds
until the transaction ends (`COMMIT` or `ROLLBACK`) and then releases by
itself. Other users are never slowed down, because the name includes the user
id. `test_simultaneous_requests_cannot_both_take_the_last_analysis` runs this
exact race on two real database connections.

**Two checks: a fast one and the real one.** The upload route first calls
`check_cv_quota` (no lock, just a count) **before** storing and parsing the
file, so a refused upload costs nothing. Then, just before saving,
`reserve_cv_upload` does the locked check that actually decides. The fast
check can be wrong in a race; the locked one can't. The same pattern is used
for analyses (the fast check runs before the possibly slow Gemini call).

**Recording in the same transaction.** Because the usage row is added to the
same transaction as the CV or analysis, a failure rolls both back. Nobody is
charged quota for something they never got.

**Career Insights sessions: metering a page that loads itself.** The
Career Insights page calls `GET /api/career-insights` every time it opens or
refreshes, and in development React calls it twice on first load (8.7). If
every request counted, a Free user could use up both insights with one
refresh. So the unit is a **session**:

```python
def open_insight_session(db, user_id: int) -> None:
    if _limit_for(db, user_id, USAGE_INSIGHT_SESSION) is None:
        return                                     # unlimited plan: nothing to count
    _lock_user_quota(db, user_id)
    if current_insight_session(db, user_id) is not None:
        return                                     # opened in the last 24 h: free
    _refuse_if_used_up(db, user_id, USAGE_INSIGHT_SESSION)
    db.add(UsageEvent(user_id=user_id, kind=USAGE_INSIGHT_SESSION))
```

The first request starts a session (one row); every request in the next 24
hours finds that row and costs nothing. The "is a session open?" check
happens *after* taking the lock, so two simultaneous first requests can't
both start one: the second waits, then finds the first's session. The route
calls this only after the "you have no CV yet" answer, so opening the page
without a CV is free, and it commits only after the insights were computed.

> **Teacher's note: be careful what you count.** Metering a `GET` request is
> almost always a mistake: browsers, frameworks and users repeat `GET`s
> freely (refresh, back button, prefetching, React's double effects). Count
> *actions* (an upload, an analysis) or *periods* (a 24-hour session), not
> page loads. Ask yourself: "if this request is repeated by accident, should
> the user lose something?" If the answer is no, don't count it that way.

**What the user sees.** A refusal is `402` with a plain-English `detail`
("You have uploaded 2 CVs this month, the Free plan's allowance…"). The pages
check `response.status === PAYMENT_REQUIRED` and show `UpgradeDialog` (CV
page, analyse page) or the `UpgradePrompt` card (Career Insights). `GET
/api/billing/subscription` returns the usage for the sidebar card, the
dashboard strip and the Billing page's bars:

```json
"usage": {
  "cv_uploads_this_month":       {"used": 1, "limit": 2, "resets_at": "2026-10-01T00:00:00Z"},
  "analyses_this_month":         {"used": 3, "limit": 5, "resets_at": "2026-10-01T00:00:00Z"},
  "insight_sessions_this_month": {"used": 1, "limit": 2, "resets_at": "2026-10-01T00:00:00Z",
                                  "session_expires_at": "2026-09-15T09:12:00Z"}
}
```

### 14.10 Stage 8: managing, cancelling and deleting

- **The customer portal.** `POST /api/billing/portal` asks Stripe for a link
  to its hosted page where the user cancels, switches monthly/yearly,
  updates the card or downloads invoices. Whatever they change there comes
  back the same way as everything else: as a webhook. The app never
  cancels or changes a subscription itself (except on account deletion).
- **Deleting an account** cancels its live subscriptions with Stripe first
  (6.8). If Stripe can't be reached, the deletion stops with `502`, because an
  account that disappears while its card keeps being charged is the worst
  possible outcome.
- **Resetting data** (`/api/reset-data`) deletes CVs and analyses but not
  `usage_events`, so it doesn't restore uploads or analyses.

### 14.11 How the payment code is tested

`test_billing.py` (39 tests) never touches the internet:

- **`FakeStripe`** is a small class with the same methods the app calls
  (`customers.create`, `checkout.sessions.create/list/expire/retrieve`,
  `subscriptions.retrieve/cancel`, `prices.retrieve`,
  `billing_portal.sessions.create`), storing everything in dictionaries. A
  test can then say "the customer paid" (`fake.pay(session_id)`), "the
  renewal failed" (set status to `past_due`), or "Stripe is down"
  (`fail_retrieve = True`).
- **Real signatures.** `_signed(event)` computes
  `HMAC-SHA256(secret, "<t>.<body>")` exactly as Stripe does, so every test
  webhook goes through the real `construct_event` check. Forged,
  tampered and replayed (old timestamp) webhooks are all tested.
- **What's covered:** only whitelisted plans accepted; the server picks the
  price; the success page alone grants nothing; payment + webhook → Pro;
  duplicates processed once; out-of-order events end in Stripe's current
  state; a failed webhook is retried, not lost; `past_due` keeps access and
  `unpaid` removes it; cancelling keeps access until the period ends;
  renewals move the period; unknown prices grant nothing; stale rows are
  distrusted; two tabs can't pay twice; someone else's checkout can't be
  confirmed; every Free limit; deleting doesn't refund; Pro removes limits;
  both races (analysis and insight session) on real connections; deleting a
  subscriber cancels their subscription.

> **Teacher's note: how do you know a test tests anything?** A test that
> has never failed might be checking nothing. While building this part,
> each important protection was **deliberately broken** (signature checking
> removed, the duplicate check disabled, the re-fetch replaced by trusting the
> payload, the lock removed, the session check removed), the tests were run,
> and the right ones failed every time. Then the code was restored. This is
> called **mutation testing**, and doing it by hand on your most important
> checks is one of the best habits you can build.

### 14.12 Why Stripe was left, and what a local provider would change

**The problem.** To open a Stripe account you choose a country, and Stripe
doesn't support accounts in Algeria. (Test mode needs no verification, but the
account itself still needs one of Stripe's countries.) Rather than build on a
service that could never take real payments where the project lives, the
decision was to leave Stripe, keeping its integration as a tested sample.

**The realistic alternative: Chargily Pay**, an Algerian gateway that accepts
**EDAHABIA** (Algérie Poste) and **CIB** (SATIM) cards. According to its
developer documentation (checked September 2026):

- a new account starts in **test mode** with separate test keys and its own
  test API address; verification is only needed for live payments;
- it has checkouts, customers, products, prices and payment links;
- its webhooks carry a `signature` header: an **HMAC-SHA256** of the payload,
  signed with your API secret key, the same idea as Stripe's;
- it has **no recurring subscriptions**: nothing charges a card
  automatically every month.

**What would stay the same.** `plans.py` (limits), `entitlements.py` (access
and quotas), `usage_events`, the `subscriptions` table's meaning, the 402
responses and every frontend page that handles them. That's most of the
system, and it's why the Stripe code was kept separate in one file.

**What would change.** Without automatic renewal, "Pro monthly" becomes a
**prepaid pass**: the user pays once for 30 days (or a year); when the
provider's signed webhook confirms the payment, the server creates or
*extends* a `subscriptions` row with `current_period_end = now + 30 days`
(or the old end + 30 days, if still active); and when that date passes,
access ends by itself, because `active_subscription` already ignores
expired periods. There's no portal to cancel (there's nothing to cancel), and
renewal means paying again, perhaps with a reminder email a few days before.
In code: a new module beside `billing.py` with a checkout call and a
webhook route that verifies Chargily's signature and applies the same
"verify → dedupe → record in one transaction" steps from 14.6.

### 14.13 A checklist for any payment integration

Use this whenever you build payments again, with any provider:

- [ ] The browser sends *what it wants* (a plan name), never *what it
      costs* (a price id or amount).
- [ ] The card is typed on the provider's page; you store no card data.
- [ ] Only the provider (verified webhook) or the server asking the
      provider can grant access. There's no "set plan" route.
- [ ] Webhook signatures are checked on the **raw** body, with a time limit.
- [ ] Webhook processing is idempotent: event ids recorded in the same
      transaction as the change.
- [ ] Out-of-order events can't restore old state (re-fetch, or compare
      timestamps).
- [ ] The success page shows the *server's* answer, not the URL's.
- [ ] Access is decided by an allow-list of good statuses (fail closed).
- [ ] Quotas are counted in an append-only ledger, checked under a lock, and
      recorded in the same transaction as the action.
- [ ] Test keys only in development, and the app refuses live keys where
      they don't belong.
- [ ] Deleting an account stops future charges first.
- [ ] Everything is tested with a fake provider and real signatures, and
      the important checks are mutation-tested.

---

## Part 15 — Challenges we faced, and what to watch out for next time

This part collects every significant problem met while building CareerLens.
Each one has four lines: **what happened** (the symptom you'd notice),
**why** (the real cause), **the fix**, and **the lesson**, the thing to
remember so it doesn't happen again. They're grouped by kind, not by date
(Part 0 has the timeline).

### 15.1 Secrets and configuration

**1. The signing key was in the source code.**
- *What happened:* `services/auth.py` contained `"change-this-in-production"`
  as the JWT key.
- *Why:* a placeholder from early development that nobody replaced.
- *Fix:* the key comes from `SECRET_KEY`; placeholders and short keys are
  refused; production refuses to start without one.
- *Lesson:* **a secret in the code is a published secret.** Anyone who can
  read the repository can use it. Secrets live in environment variables, and
  the app should refuse to run with a weak one.

**2. `.env` was not in `.gitignore`.**
- *What happened:* the file with the Gemini key and the database password
  would have been committed by the first `git add .`.
- *Fix:* `.gitignore` now covers `.env`, `.secret_key`, `uploads/`,
  `node_modules/`, `.next/` and more.
- *Lesson:* **set up `.gitignore` before your first commit**, and check `git
  status` before every commit. Once a secret is pushed, deleting it later
  isn't enough: it stays in the history, and you must change the secret.

**3. "Failed to fetch" everywhere, while `curl` worked.**
- *What happened:* every page's requests failed in the browser.
- *Why:* the frontend ran on port 3001; `CORS_ORIGINS` allowed only 3000. The
  server answered, but the browser refused to hand the answer to the page.
- *Fix:* the right origins in `CORS_ORIGINS`.
- *Lesson:* **when the browser fails and `curl` works, suspect CORS.** Open
  the browser's developer tools, Console tab: it names the blocked origin.

**4. Editing `.env` "did nothing".**
- *Why:* `uvicorn --reload` restarts on `.py` changes only; `.env` is read once
  at start-up.
- *Lesson:* **after changing `.env`, restart the backend by hand.** The same
  goes for `NEXT_PUBLIC_*` variables in the frontend, which are baked in at
  build time: change them, then rebuild and redeploy.

### 15.2 The database

**5. One failed statement broke start-up.**
- *What happened:* start-up migrations failed partway, and later statements
  failed too.
- *Why:* the `users` table was owned by `postgres`, so `ALTER TABLE users`
  was refused; on PostgreSQL a failed statement **aborts the whole
  transaction**, so every later statement in it fails as well.
- *Fix:* each change in its own transaction; never alter `users`; new
  per-person columns go on `user_profiles`.
- *Lesson:* **know who owns your tables**, and remember that one error in a
  PostgreSQL transaction poisons the rest of it.

**6. A SQLite fallback hid real problems.**
- *What happened:* with no `DATABASE_URL`, the app silently used a SQLite
  file.
- *Why it's bad:* SQLite accepts things PostgreSQL rejects (types,
  constraints, concurrent writes), so bugs pass in development and appear in
  production.
- *Fix:* PostgreSQL only, everywhere, including tests (a throwaway schema).
- *Lesson:* **develop and test on the same database you deploy.**

**7. Schema changes by hand at start-up.**
- *What happened:* the old start-up code could only *add* columns, and would
  have pre-created new tables on old databases, breaking later changes.
- *Fix:* Alembic migrations, a baseline for the old database ("stamping"),
  and a test that models and migrations match.
- *Lesson:* **every schema change is a numbered migration**, reviewed
  before it runs, and never edited after it has run anywhere.

**8. Deleting a user crashed with a 500.**
- *Why:* foreign keys: PostgreSQL won't delete a row others still point at.
- *Fix:* delete in dependency order, in one transaction (6.8).
- *Lesson:* **when you add a table with a foreign key to `users`, update
  the deletion code the same day.** (The four billing tables were added
  there at once.)

**9. The job list ran one database query per job.**
- *Why:* counting applications inside a loop (the "N+1 queries" problem).
- *Fix:* one grouped query for the whole page.
- *Lesson:* **a query inside a loop is a warning sign.** Ask the database
  once for everything you need.

### 15.3 Security holes (all found before any real users)

**10. Anyone could register as admin.**
- *Why:* the `role` from the registration form was trusted.
- *Fix:* only `job_seeker` or `employer` can be chosen; admins are made by
  hand in the database.
- *Lesson:* **the request body is the attacker's keyboard.** Every field in it
  is a suggestion, and anything that grants power must be decided by the
  server.

**11. Login timing revealed who has an account.**
- *Why:* unknown emails skipped the slow bcrypt check and answered more than
  100× faster.
- *Fix:* always run bcrypt (against a dummy hash); the same message for every
  failure.
- *Lesson:* **responses can leak through time, not just words.**

**12. Uploads could escape the upload folder.**
- *Why:* the file was saved under the name the user sent, and a name like
  `../../evil.txt` walks up out of the folder ("path traversal").
- *Fix:* every file gets a random name; the image route serves only files
  directly inside its folder.
- *Lesson:* **never build a file path from user input.**

**13. A meeting link could run code.**
- *Why:* `meeting_url` became a clickable link; `javascript:alert(…)` is a
  valid link that runs code in the viewer's browser (XSS).
- *Fix:* only `http://` and `https://` accepted, and the UI renders only
  safe links.
- *Lesson:* **anything a user types that another user will click must be
  checked.**

**14. Messages went to the wrong person.**
- *Why:* old frontend code sent a **CV id** where a **user id** was expected,
  and the numbers overlapped with real, unrelated users.
- *Fix:* those fields are treated as CV ids and converted to the CV's owner.
- *Lesson:* **ids of different things look identical** (they're all
  numbers). Name them clearly (`cv_id`, `user_id`), and never reuse one
  where another is expected.

**15. The server's file paths were shown to users.**
- *Why:* error messages and `cv_url` included real paths on the server.
- *Fix:* errors are logged in full but reported generically; `cv_url` is a
  download URL.
- *Lesson:* **log the details, show the user a sentence.**

### 15.4 AI and correctness

**16. The skills were in the CV but "the AI couldn't find them".**
- *Why:* three silent bugs: an exact-match heading check ("experience"
  only), a hidden `[:12]` cap, and a small vocabulary.
- *Fix:* a heading splitter with synonyms, no cap, about 390 terms, and
  evidence tracking.
- *Lesson:* **silent truncation is the worst kind of bug**: nothing crashes,
  the output just quietly shrinks. Be suspicious of any `[:N]` and of exact
  string matches on text written by people.

**17. The parser invented facts.**
- *Why:* fallbacks inserted text the CV never contained ("Bachelor's degree
  in Computer Science…"), and labelled skill levels by list position.
- *Fix:* fallbacks quote the CV's own lines; labels say only what the
  parser knows (demonstrated / mentioned / listed).
- *Lesson:* **an AI product must never present guesses as facts.** When the
  code can't know something, say so.

**18. The "match score" for candidates wasn't a match.**
- *Why:* it measured profile completeness, not fit to a job.
- *Fix:* renamed "profile score" in the UI.
- *Lesson:* **a number's label is part of its correctness.**

**19. The embedding model didn't fit the server.**
- *Why:* PyTorch pushed memory to about 577 MB, over the 512 MB instance.
- *Fix:* the same model on ONNX Runtime (about 330 MB). Before switching,
  the vectors were compared on real data (identical within 0.0000002). A
  second library, `fastembed`, was tried and **rejected** because its vectors
  differed for long texts.
- *Lesson:* **measure before and after an infrastructure change**, and be
  willing to reject the easy option when the numbers say no.

### 15.5 Frontend

**20. Pages sometimes showed old data.**
- *Why:* a slow response arriving after the user had moved on overwrote
  newer data.
- *Fix:* the `active` flag in every effect (8.6).
- *Lesson:* **every request can come back late.** Decide what should happen
  if it does.

**21. The Billing page hung on "Loading…" in development.**
- *Why:* a `useRef` guard stopped the effect's second run, which React Strict
  Mode needs (8.7).
- *Lesson:* **write effects that survive "start, stop, start again"**; don't
  fight the framework's checks.

**22. "UI improvement" that nobody could see.**
- *What happened:* new screens were built, and every existing page looked the
  same as before.
- *Lesson:* **improve what users already use.** Measure the real problem first
  (here: 33 headings the same size as body text), then change the
  existing pages and compare before and after.

**23. The dev server behaved strangely when opened as `127.0.0.1`.**
- *Why:* Next.js 16's dev server blocks its own scripts (403) for an origin
  it doesn't expect, so the page never came to life.
- *Lesson:* **open the dev site at `http://localhost:3001`.** Also, `next dev`
  writes `CLAUDE.md` and `AGENTS.md` files into `frontend/` when it starts;
  they're harmless and can be deleted.

### 15.6 Payments

**24. The pricing page promised things that didn't exist.**
- *What happened:* a 14-day trial with no card, PayPal, bank transfer,
  refunds, student discounts, cover letters.
- *Fix:* the copy now matches the code; cover letters are "Coming soon".
- *Lesson:* **the pricing page is a contract.** Every line on it must be
  something the code does.

**25. A deliberate "no" became a misleading 500.**
- *Why:* `upload_cv` wrapped its body in `except Exception:` → "Failed to save
  CV", which also caught the `402` "plan limit" refusal.
- *Fix:* `except HTTPException: raise` before the general handler.
- *Lesson:* **catch-all `except` blocks swallow intentional errors too.** Catch
  the specific errors you expect, or let deliberate ones pass through.

**26. A quota can be beaten by two requests at once.**
- *Why:* check-then-act: both requests count before either records.
- *Fix:* a per-user advisory lock around count-and-record (14.9).
- *Lesson:* **any "check, then write" on shared data needs a lock or a
  database constraint.** Tests with one request at a time will never show
  the bug.

**27. Metering a page load would have burned the allowance on refresh.**
- *Fix:* count 24-hour sessions, not requests (14.9).
- *Lesson:* **count actions or periods, never `GET` requests.**

**28. Tutorials described an older Stripe.**
- *Why:* Stripe moved the billing-period fields in 2025.
- *Fix:* read the installed SDK's source before writing code.
- *Lesson:* **trust the version you installed over any article.**

**29. The provider wasn't available in our country.**
- *What happened:* everything was built and tested, and then the Stripe
  account couldn't be opened from Algeria.
- *Lesson:* **check that you can actually use a service (country, currency,
  documents, payouts) before building on it.** Five minutes on the
  provider's sign-up page would have shown this at the start. The
  mitigation that saved the work: keeping all provider-specific code in one
  file.

### 15.7 Working practices

**30. The `components/` folder was never committed, and got lost.**
- *What happened:* 14 files that every page needed disappeared; they were
  recovered only because the Next.js build cache happened to contain them.
- *Lesson:* **commit early, commit often, and push.** `git status` should
  never show a folder of important untracked files for more than a day.

**31. `git push` hung from an automated terminal.**
- *Why:* there were no stored GitHub credentials for that terminal.
- *Lesson:* push from a terminal where you're signed in to GitHub (the VS Code
  one works).

**32. Big changes without a plan went wrong; small explained steps went right.**
- *What happened:* the best results in this project came from the agreed
  way of working: inspect first, explain the plan, change a little, run the
  tests, explain what changed.
- *Lesson:* **the process is part of the code quality.**

### 15.8 Before you start next time: a checklist

Read this before starting a new feature or a new project.

**Before writing code**
- [ ] Can I name the problem, and who has it?
- [ ] Have I read the existing code that this touches? Does something
      similar already exist?
- [ ] If it uses an outside service: can I actually sign up and use it from
      here? Which API version am I installing?
- [ ] What could a user send that I don't expect? What if two requests
      arrive at once? What if a message arrives twice, late, or never?

**While writing code**
- [ ] Secrets only in environment variables; `.gitignore` checked.
- [ ] Validate the request's shape with Pydantic; check permissions in the
      route; take identity from the token only.
- [ ] Every schema change is a new migration.
- [ ] Every new table that points at `users` is added to account deletion.
- [ ] No `[:N]` or exact text match without a reason written next to it.
- [ ] No catch-all `except` that hides deliberate errors.
- [ ] Anything shown to other users is checked (links, HTML).
- [ ] Every "check then write" on shared data is protected.

**Before calling it done**
- [ ] Tests for the normal case **and** the "what if" cases; run the whole
      suite.
- [ ] Break the most important check on purpose: does a test fail?
- [ ] `npm run lint` and `npm run build` pass.
- [ ] Looked at the actual pages (and at phone width).
- [ ] The words on the page (pricing, help, errors) match what the code
      does.
- [ ] `git status` is clean: everything important is committed and pushed.

---

## Part 16 — Check your understanding

Try to answer each question from memory, then open the answer. If you
can't, the section in brackets is where to look. Being able to explain these
out loud (for example, in a project presentation) is a good sign you
understand the system.

**Basics**

1. The browser talks to two servers. Which two, and what does each one
   send? *(Part 3)*
   <details><summary>Answer</summary>Vercel sends the page files (HTML,
   JavaScript, CSS); the FastAPI backend on Render sends all the data as
   JSON. The frontend has no server-side code of its own.</details>

2. A user edits `careerLens_role` in `localStorage` to `admin`. What
   happens? *(8.3, 10.1)*
   <details><summary>Answer</summary>The admin layout lets them see the admin
   pages' frame, but every admin API call checks the role stored in
   `user_profiles` on the server and answers 403. They see empty pages.
   The frontend check is convenience; the server check is security.</details>

3. Why does editing someone else's job return 404, not 403? *(6.6)*
   <details><summary>Answer</summary>403 would confirm that the job exists.
   404 reveals nothing, so ids can't be probed to discover other employers'
   postings.</details>

**Backend and database**

4. What are the three "gates" in `get_current_user_id`? *(6.9, Lesson 3)*
   <details><summary>Answer</summary>1) a Bearer token must be present; 2)
   its signature and expiry must be valid (`jwt.decode`); 3) its `ver` must
   equal the account's current `token_version`, which a password reset
   raises.</details>

5. Why is `default=utcnow` written without brackets? *(6.9, Lesson 2)*
   <details><summary>Answer</summary>It passes the function, so it's called
   for each new row. `utcnow()` would be called once at import, and every row
   would get the same time.</details>

6. You change a model and forget to write a migration. What catches it?
   *(6.9, Lesson 8)*
   <details><summary>Answer</summary>`test_migrations.py`, which builds a
   database from the migrations and compares it with the models.</details>

7. Why are reset-link tokens stored as SHA-256 hashes, but passwords as
   bcrypt hashes? *(6.9, Lesson 5)*
   <details><summary>Answer</summary>Passwords are short and guessable, so
   they need a deliberately slow hash. Tokens are 32 random bytes, so there
   is nothing to guess, and a fast hash is enough.</details>

**AI**

8. A job lists skills and experience but not education. How is the final
   score weighted? *(7.5, 7.13)*
   <details><summary>Answer</summary>Skills 0.5 and experience 0.3, divided by
   their total 0.8, so skills count 62.5 % and experience 37.5 %. Education is
   left out, not scored as 0 or 100.</details>

9. Why is ranking all jobs against a CV only one line of numpy? *(7.13)*
   <details><summary>Answer</summary>All vectors have length 1, so cosine
   similarity is a dot product, and `matrix @ query` computes the dot product
   of every job's vector with the CV's at once.</details>

10. You switch to a different embedding model. What else must you do?
    *(Part 13, 7.13)*
    <details><summary>Answer</summary>Change `EMBEDDING_DIM`, raise
    `EMBEDDING_VERSION` (so stored vectors are recomputed), and re-measure
    every similarity threshold (0.75, 0.55, 0.25…), because each model scores
    on its own scale.</details>

**Payments and limits**

11. Why does the browser send `{"plan": "pro", "interval": "year"}` and not
    a price id? *(14.3)*
    <details><summary>Answer</summary>Anything the browser sends can be
    changed. If it sent a price id, a user could substitute a cheaper price
    from the same Stripe account. The server maps the name to a price from its
    own whitelist.</details>

12. Someone types `/billing?checkout=success&session_id=cs_test_abc` into the
    address bar without paying. What happens? *(14.5)*
    <details><summary>Answer</summary>Nothing is granted. The page asks the
    server to confirm; the server fetches that session from Stripe, finds it
    doesn't belong to this user (404) or isn't complete, and changes nothing.
    The page keeps waiting and then says it's still waiting.</details>

13. The same webhook event arrives twice. Why is the result the same as if
    it had arrived once? *(14.6)*
    <details><summary>Answer</summary>Its id is inserted into `stripe_events`
    in the same transaction as the change; the second delivery finds the id
    already there (`ON CONFLICT DO NOTHING` inserts nothing) and stops. And
    the save itself is an upsert, so even repeating it changes nothing.</details>

14. An old "subscription created" event arrives after the subscription was
    cancelled. Why doesn't it make the user Pro again? *(14.6)*
    <details><summary>Answer</summary>The event is used only to learn which
    subscription changed. The server fetches its current state from Stripe
    (canceled) and saves that.</details>

15. Why is `past_due` treated as Pro, but `unpaid` isn't? *(14.7)*
    <details><summary>Answer</summary>`past_due` means Stripe is still
    retrying a failed renewal, often a temporary bank problem, so the user
    keeps access with a warning. `unpaid` means all retries failed.</details>

16. Draw the race in which a Free user gets 6 analyses out of 5, and explain
    how the lock stops it. *(14.9)*
    <details><summary>Answer</summary>Two requests both count 4, both pass,
    both record. With `pg_advisory_xact_lock`, the second waits until the
    first commits, then counts 5 and is refused.</details>

17. Why is Career Insights metered in 24-hour sessions and not per request?
    *(14.9)*
    <details><summary>Answer</summary>The page sends a `GET` on every open or
    refresh, and twice on first load in development. Per-request counting
    would let a refresh use up the allowance. A session makes repeats free.</details>

18. If you moved to Chargily Pay, which files would you keep, and what
    would a "monthly" plan become? *(14.12)*
    <details><summary>Answer</summary>Keep `plans.py`, `entitlements.py`,
    `usage_events` and all the 402 handling; add a new provider module. With
    no recurring billing, monthly becomes a prepaid 30-day pass that the
    webhook creates or extends, and it ends by itself when
    `current_period_end` passes.</details>

**Practical exercises** (do them on your machine, then undo them)

- **A.** In `services/plans.py`, set the Free plan to 1 analysis a month.
  Run `pytest src/ai_job_intelligence/test_billing.py`. Which tests fail,
  and why? Then undo it.
- **B.** In `services/entitlements.py`, delete the line
  `_lock_user_quota(db, user_id)` inside `_reserve`. Run the tests. Find the
  test that fails and read it. Then undo it.
- **C.** With the backend running, open <http://127.0.0.1:8000/docs>, sign
  in through `/api/auth/login`, copy the token into **Authorize**, and call
  `GET /api/billing/subscription`. Upload a CV and call it again: which
  number changed?
- **D.** Follow one request end to end on paper: "an employer accepts an
  application". Write down the page file, the API route, the function in
  `main.py`, every check it makes, and the table it writes.

---

## Appendix A — Every API route

"Login" = needs `Authorization: Bearer <token>`.

| Method | Path | Login | Who | Purpose |
|---|---|---|---|---|
| GET | `/` | – | anyone | health check |
| POST | `/api/auth/register` | – | anyone | create account (job_seeker/employer) |
| POST | `/api/auth/login` | – | anyone | get a token |
| POST | `/api/auth/forgot-password` | – | anyone | email a reset link (same reply for every address) |
| POST | `/api/auth/reset-password` | – | link holder | set a new password; signs out everywhere |
| POST | `/api/auth/verify-email` | – | link holder | confirm the email address |
| POST | `/api/auth/resend-verification` | ✓ | any | send a new confirmation link |
| POST | `/api/demo/analyze` | – | anyone | one-off demo analysis (form upload) |
| GET | `/api/images/{image_name}` | – | anyone | serve an uploaded image |
| GET | `/api/profile` | ✓ | any | your profile |
| PUT | `/api/profile` | ✓ | any | update your profile |
| POST | `/api/upload-image` | ✓ | any | upload a profile image |
| POST | `/api/upload-cv` | ✓ | any | upload and parse a CV (Free: 2 a month, else 402) |
| GET | `/api/cvs` | ✓ | owner | list your CVs |
| GET | `/api/cvs/{cv_id}` | ✓ | owner/admin | one CV with its text |
| GET | `/api/cvs/{cv_id}/analysis` | ✓ | owner | full CV report |
| GET | `/api/cvs/{cv_id}/analyses` | ✓ | owner | saved job analyses for the CV |
| GET | `/api/cvs/{cv_id}/download` | ✓ | owner/admin/employer* | the original file |
| POST | `/api/analyze` | ✓ | owner | analyse a CV against a job, save the result (Free: 5 a month, else 402) |
| GET | `/api/analyses/{analysis_id}` | ✓ | owner | one analysis + guidance |
| DELETE | `/api/analyses/{analysis_id}` | ✓ | owner | delete an analysis |
| POST | `/api/reset-data` | ✓ | any | delete your CVs and analyses |
| GET | `/api/learning-resources` | ✓ | any | learning links for skills |
| GET | `/api/jobs` | ✓ | any | list jobs (employers: their own) |
| POST | `/api/jobs` | ✓ | any* | create a job |
| GET | `/api/jobs/{job_id}` | ✓ | any | one job (+1 view, + your match) |
| PATCH | `/api/jobs/{job_id}` | ✓ | owner | edit a posting |
| GET | `/api/jobs/{job_id}/applications` | ✓ | owner | applicants |
| GET | `/api/applications` | ✓ | any | your applications |
| POST | `/api/applications` | ✓ | any | apply |
| POST | `/api/applications/{id}/accept` | ✓ | job owner | accept |
| POST | `/api/applications/{id}/reject` | ✓ | job owner | reject |
| GET | `/api/saved-jobs` | ✓ | any | your saved jobs |
| POST | `/api/saved-jobs` | ✓ | any | save a job |
| DELETE | `/api/saved-jobs/{job_id}` | ✓ | any | unsave a job |
| GET | `/api/user/stats` | ✓ | any | dashboard numbers |
| GET | `/api/job-recommendations` | ✓ | owner | ranked job matches |
| GET | `/api/career-insights` | ✓ | any | field, gaps, salary (Free: 2 sessions of 24 h a month, else 402) |
| POST | `/api/career-lens/chat` | ✓ | any | the assistant |
| GET | `/api/company` | ✓ | any | your company profile |
| POST | `/api/company` | ✓ | any | save your company profile |
| GET | `/api/candidates` | ✓ | employer | search candidates |
| GET | `/api/candidates/{candidate_id}` | ✓ | employer | one candidate (by CV id) |
| POST | `/api/interviews` | ✓ | employer | book an interview |
| GET | `/api/interviews` | ✓ | either side | your interviews |
| PATCH | `/api/interviews/{id}/details` | ✓ | booking employer | change time or joining details |
| PATCH | `/api/interviews/{id}` | ✓ | either side | change status |
| POST | `/api/messages` | ✓ | any | send a message |
| GET | `/api/messages` | ✓ | any | conversation list |
| GET | `/api/messages/{other_user_id}` | ✓ | any | one thread (marks it read) |
| GET | `/api/messages/unread/count` | ✓ | any | unread count |
| GET | `/api/admin/stats` | ✓ | admin | system numbers |
| GET | `/api/admin/users` | ✓ | admin | all users |
| GET | `/api/admin/users/{user_id}` | ✓ | admin | one user |
| DELETE | `/api/admin/users/{user_id}` | ✓ | admin | delete a user and their data (cancels their Stripe subscription first) |
| GET | `/api/billing/plans` | – | anyone | plan limits and live prices (empty while Stripe is off) |
| GET | `/api/billing/subscription` | ✓ | any | your plan, status and monthly usage |
| POST | `/api/billing/checkout` | ✓ | job seeker | start paying for Pro → Stripe URL (503 while Stripe is off) |
| POST | `/api/billing/checkout/confirm` | ✓ | checkout owner | sync a finished checkout with Stripe |
| POST | `/api/billing/portal` | ✓ | any with a billing account | link to Stripe's billing portal |
| POST | `/api/billing/webhook` | – (signed) | Stripe | payment and subscription events |

The six billing routes live in `billing_routes.py`; everything else is in
`main.py` (61 routes in total).

\* `POST /api/jobs` doesn't check the role; the UI only offers it to
employers. For CV downloads, "employer" means an employer opening a **job
seeker's** CV.

## Appendix B — Every environment variable

**Backend** (Render dashboard, or `ai-job-intelligence/.env` locally)

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `DATABASE_URL` | **yes** | – | PostgreSQL URL; `postgres://`/`postgresql://` are converted to the psycopg driver automatically |
| `FRONTEND_URL` | no | first `CORS_ORIGINS` entry | the site's address, for links in emails |
| `SMTP_HOST` | for email | empty (email off) | SMTP server; without it, dev prints emails to the log |
| `SMTP_PORT` | no | `587` | `465` switches `SMTP_SECURITY` to `ssl` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | for most providers | – | SMTP login |
| `SMTP_FROM` | no | `SMTP_USERNAME` | the sender address |
| `SMTP_SECURITY` | no | `starttls` (or `ssl` on 465) | `starttls`, `ssl` or `none` |
| `EMBEDDING_CACHE_DIR` | no | `ai-job-intelligence/.model_cache` | where the embedding model is downloaded |
| `SECRET_KEY` | in production | dev: generated into `src/.secret_key` | JWT signing key, 32+ characters |
| `JWT_SECRET_KEY` | no | – | alternative name for `SECRET_KEY` |
| `APP_ENV` | no | `development` | `production` = strict secrets, no demo seeding, tight rate limits |
| `CORS_ORIGINS` | yes when deployed | `http://localhost:3001,http://127.0.0.1:3001` | allowed frontend origins, comma-separated |
| `GOOGLE_API_KEY` | no | empty | enables Gemini (job reading, image OCR, chat wording) |
| `UPLOAD_DIR` | no | `src/uploads` | where CVs are stored (`/var/data/uploads` on Render) |
| `IMAGES_DIR` | no | `src/uploads/images` | where profile images are stored (`/var/data/uploads/images` on Render) |
| `PYTHON_VERSION` | Render only | – | `3.12.3` |
| `TEST_DATABASE_URL` | tests only | uses `DATABASE_URL` | server for the throwaway test schema |
| `STRIPE_SECRET_KEY` | no (payments off without it) | empty | Stripe **test** key `sk_test_…`; a live key stops the app from starting |
| `STRIPE_WEBHOOK_SECRET` | with Stripe | empty | `whsec_…`, used to verify webhook signatures; without it the webhook route answers 503 |
| `STRIPE_PRICE_PRO_MONTHLY` / `STRIPE_PRICE_PRO_YEARLY` | with Stripe | empty | the two `price_…` ids the whitelist maps Pro monthly/yearly to |

**Frontend** (Vercel dashboard, or `frontend/.env.local`)

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE` | yes when deployed | `http://127.0.0.1:8000` | backend address; built into the site at build time |
| `E2E_DATABASE_URL` | browser tests only | – | PostgreSQL database for Playwright runs |

## Appendix C — Every test file

Backend (`ai-job-intelligence/src/ai_job_intelligence/`; 298 tests in total,
counting each parametrised case):

| File | Tests | Covers |
|---|---|---|
| `test_api_smoke.py` | 16 | startup, every major endpoint, evidence labels |
| `test_auth_hardening.py` | 34 | registration, password policy, login throttling, no self-made admins, bcrypt compatibility |
| `test_password_reset_and_verification.py` | 13 | reset flow, sign-out-everywhere, verification, token hashing, email logging rules |
| `test_config_secrets.py` | 17 | secret-key rules, PostgreSQL-only, URL conversion |
| `test_migrations.py` | 5 | models and migrations agree; empty and legacy databases; re-running |
| `test_admin_delete_and_cv_access.py` | 7 | who may open a CV; deleting users; resetting data |
| `test_uploads_and_demo.py` | 24 | upload safety, image naming and serving, `cv_url`, company rename, application counts, demo |
| `test_skill_extraction.py` | 29 | skills in prose, headings (including compound ones), no invented education |
| `test_matching.py` | 12 | skill extraction, the match score, the "required skills" field |
| `test_ai.py` | 3 | the rule-based job-description reader |
| `test_embeddings.py` | 3 | similarity behaves as the matcher assumes |
| `test_cv_profile_cache.py` | 6 | profile caching and rebuilding on version change |
| `test_vector_store.py` | 12 | vector maths and serialisation (no database) |
| `test_semantic_search.py` | 7 | stored embeddings and meaning-based search |
| `test_career_insights.py` | 9 | "your field" selection, gaps, salary |
| `test_assistant.py` | 12 | intent detection, retrieval, grounded answers |
| `test_guidance_and_resources.py` | 17 | guidance actions and learning-resource lookup |
| `test_interviews_messages.py` | 15 | interviews, status rules, messaging |
| `test_job_edit_and_interview_details.py` | 18 | job PATCH, interview detail edits |
| `test_billing.py` | 39 | the whole of Part 14: whitelist, checkout, webhook signatures, idempotency, ordering, lifecycle, entitlements, every Free limit, both races, account deletion |
| `conftest.py` | – | throwaway schema, app client, test users, `grant_plan`, the no-real-Stripe guard |

Browser (`ai-job-intelligence/frontend/e2e/`; 26 tests):

| File | Covers |
|---|---|
| `public.spec.ts` | landing page (no redirect), information pages, demo analysis (including several runs in a row) |
| `auth.spec.ts` | register → sign in → email banner → sign out; wrong password; forgot, reset and verify pages |
| `jobseeker.spec.ts` | CV upload and evidence labels, matching and analysis, save/unsave/apply, insights, chat, profile photo |
| `employer.spec.ts` | company, post and edit a job, accept/reject, candidate search, view CV, interview, message, unread badge, candidate confirms and replies |
| `admin.spec.ts` | admin pages; a non-admin is kept out |
| `support/fixtures.ts` | shared helpers; fails any test on a JavaScript error or a 5xx |
