# CivicResolve — Community Problem Reporting & Solution Tracker

CivicResolve is a beginner-friendly Python + MongoDB project based on the community problem-solving idea in SIH 2026 problem statement **SIH26043**. It lets people report local problems, support reports, leave suggestions, and track progress. An admin desk can update status/priority/department, and the analytics page runs MongoDB aggregation pipelines.

> **Important:** This project is built and packaged for you, but it still needs a MongoDB database connection on your computer before it can save data. Follow the steps below in order. The sample names and emails are fictional.

## What is included?

- `app.py` — the Streamlit website/interface.
- `database.py` — PyMongo connection, collections, CRUD functions, indexes, and aggregation queries.
- `validation.py` — Python-side checks for names, emails, titles, descriptions, categories, and priorities.
- `setup_db.py` — creates collections and applies MongoDB JSON Schema validators and indexes.
- `seed_data.py` — inserts example reports so the dashboard is not empty. It will not overwrite an existing reports collection.
- `.env.example` — template for your private MongoDB connection settings.
- `requirements.txt` — Python packages the project needs.

## Features

1. **Community Dashboard:** counts for all reports, active issues, resolved issues, and high-priority issues; charts for categories and statuses.
2. **Report a Problem:** create a report with a category, priority, description, area, landmark, and reporter contact.
3. **Browse & Support:** search and filter reports, support a report once per email, post suggestions, and view progress history.
4. **Admin Desk:** update status, priority, department, and progress notes; delete a report after confirmation.
5. **Analytics & Insights:** MongoDB aggregation pipelines for counts by category/status, unresolved reports by area, and average resolution time.

## Technology used

- Python 3.10 or newer
- MongoDB (MongoDB Atlas is easiest for a first project; a local MongoDB server also works)
- PyMongo
- Streamlit
- Pandas and Plotly for tables and charts

---

# Setup guide for a complete beginner

## Step 1 — Install Python

Install Python 3.10 or newer from <https://www.python.org/downloads/>. On the Windows installer, tick **Add Python to PATH** if that option is shown.

Open **Command Prompt** or the VS Code terminal and run:

```bat
py --version
```

If that command is unavailable, try:

```bat
python --version
```

You should see a Python 3 version number.

## Step 2 — Create a free MongoDB database

The easiest choice is MongoDB Atlas, MongoDB's hosted database service:

1. Open <https://www.mongodb.com/atlas/database> and create/sign in to an account.
2. Create a cluster using a free option if one is available to your account/region.
3. Open **Database Access** and create a database user with a username and password. This is separate from your MongoDB website login.
4. Open **Network Access** and allow the IP address of the computer you will run the project on. Avoid opening access to every IP address unless you understand the security implications.
5. Open the cluster and choose **Connect** → **Drivers** → **Python**. Copy the connection URI shown by Atlas.
6. Replace the username/password placeholders in the URI with the database user's credentials. If your password contains characters such as `@`, `:`, `/`, `?`, or `#`, URL-encode those characters before placing the password in the URI.

Keep the URI private. Do not send it in a screenshot or upload it to GitHub.

**Using local MongoDB instead:** install and start MongoDB Community Server, then use this URI in the next step:

```text
mongodb://localhost:27017
```

## Step 3 — Open the project folder

1. Extract `civicresolve.zip` to a normal folder, such as `C:\Users\YourName\Documents\civicresolve`.
2. Open that extracted `civicresolve` folder in File Explorer.
3. Click the address bar, type `cmd`, and press Enter. A Command Prompt will open in the project folder.

You should see files such as `app.py`, `database.py`, and `requirements.txt` when you run:

```bat
dir
```

## Step 4 — Create a Python environment and install packages

In the Command Prompt opened inside the project folder, run these commands one at a time:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you use PowerShell and activation is blocked, open regular **Command Prompt** and use the commands above, or run the PowerShell activation script only after reviewing your system's execution-policy settings. You can also skip activation and use `.venv\Scripts\python -m pip install -r requirements.txt`.

The terminal should show `( .venv )` or `(.venv)` at the start of the line after activation. The package installation can take a little while because it downloads the libraries.

## Step 5 — Add your MongoDB connection string

1. In the project folder, make a copy of `.env.example`.
2. Rename the copy to exactly **`.env`** (not `.env.txt`). Windows File Explorer may hide file extensions; Notepad's **Save As** dialog can also be used by selecting **All files** and typing `.env` as the filename.
3. Open `.env` with Notepad.
4. Replace the example `MONGODB_URI` line with the connection URI from Atlas, or with `mongodb://localhost:27017` for local MongoDB.
5. Leave the second line as `MONGODB_DATABASE=civicresolve` unless you want a different database name.
6. Save and close the file.

Example format only — **do not copy these placeholders as real credentials**:

```text
MONGODB_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@YOUR_CLUSTER.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=civicresolve
```

Do not put spaces around the `=` sign. Do not wrap the value in quotation marks unless Atlas itself includes them (normally it does not).

## Step 6 — Set up the collections and validation

Run:

```bat
python setup_db.py
```

This creates two collections, `users` and `reports`, and indexes used by the app. It also tries to apply MongoDB JSON Schema validation to both collections. For an existing collection, updating a validator may require additional database permissions. If the script says it could not change a validator on an existing collection, check the database user's permissions; the project's Python input validation still remains active.

The database validates important rules too, such as allowed report statuses, priorities and categories; required fields; field types; and non-negative vote counts.

## Step 7 — Add demonstration records

Run:

```bat
python seed_data.py
```

This adds fictional users and sample reports in several statuses so you can immediately explore the charts and report list. It **does not overwrite an existing non-empty reports collection**.

If you want to use an empty database, make sure `MONGODB_DATABASE` points to the intended test database before running this command.

## Step 8 — Start CivicResolve

Run:

```bat
streamlit run app.py
```

A browser tab should open with the CivicResolve website. If it does not, copy the `Local URL` printed in the terminal (usually `http://localhost:8501`) into your browser.

To stop the app, go back to the terminal and press **Ctrl+C**.

Next time, open the project folder, activate the environment with `.venv\Scripts\activate`, and run `streamlit run app.py` again. The database setup and sample-data commands normally only need to be run once.

---

# How to demonstrate it for your assignment

1. Open **Community Dashboard** and describe the headline counts and charts.
2. Open **Report a Problem** and submit a new issue. Try an invalid email or too-short title to demonstrate Python validation.
3. Open **Browse & Support**, enter a name/email, find your report, support it, add a comment, and open the progress history.
4. Open **Admin Desk**, select the issue, change its status to `In Progress`, assign a department, add a note, and save. Then mark it `Resolved` to populate the resolution-time calculation.
5. Open **Analytics & Insights** and explain how the database groups records into useful summaries.
6. If asked to demonstrate delete, select a sample report in the Admin Desk, check the confirmation box, and delete it. Avoid deleting a report you want to keep for other demonstrations.

## CRUD mapping

| CRUD operation | Where it happens |
|---|---|
| Create | `create_report()` inserts a document into `reports`; `ensure_user()` creates/updates the citizen profile. |
| Read | `list_reports()` finds reports and uses `$lookup` to retrieve reporter information from `users`. |
| Update | `update_report()` edits status/priority/department and appends a progress update. Comments and support counts are also updated. |
| Delete | `delete_report()` removes a report after an explicit confirmation in the Admin Desk. |

## Aggregation pipelines in this project

- `reports_by_category()` groups reports by category and sorts the result.
- `reports_by_status()` counts records by current status.
- `unresolved_by_area()` matches open issues, groups them by location area, sorts the counts, and returns the top ten.
- `average_resolution_hours()` filters resolved reports, projects the elapsed hours, then groups by category to calculate an average.
- `list_reports()` uses `$lookup` and `$unwind` to add reporter profile fields to each report result.

## Validation rules

- Python checks required text, field lengths, email format, selected category, priority, and comment length before writing to MongoDB.
- MongoDB JSON Schema validators check required fields, data types, accepted status/category/priority values, and minimum vote count.
- A unique index prevents two user profiles from using the same email address.
- Indexes support sorting and common filters such as status, priority, category, area, and reporter.

## Suggested viva explanation

**Problem:** Residents often do not know where to report a local problem, whether others have reported it, or whether action has been taken. CivicResolve provides a shared place to report and track issues.

**Why MongoDB?** A report contains nested location information and changing arrays of comments and progress updates. MongoDB documents can store these related details naturally, while the separate `users` collection avoids duplicating the full reporter profile in every report.

**What is an aggregation?** An aggregation pipeline passes documents through stages. For example, the area report pipeline first filters out resolved/rejected reports (`$match`), counts remaining reports by area (`$group`), orders areas by count (`$sort`), and keeps the first ten (`$limit`).

**What is `$lookup`?** It combines report documents with a matching profile document from the `users` collection, similar to a join in a relational database.

## Important limitations

- The project is a **classroom prototype**, not a production civic service.
- The Admin Desk has no real authentication. Anyone who can open the app can access the admin controls. Do not deploy it publicly until proper login, role-based access control, rate limiting, and privacy controls are implemented.
- Email is used as a simple demo identifier for one-support-per-report; it does not verify that the person owns the email.
- The app stores plain-text demo comments. Do not enter sensitive personal information.
- It does not contact government departments or automatically submit complaints to an official service.

## Troubleshooting

**`MONGODB_URI is not set`**

- Confirm the file is named `.env` and sits next to `app.py`.
- Confirm the first line begins `MONGODB_URI=`.
- Stop the app with Ctrl+C and run it again after changing `.env`.

**Server selection timeout / DNS error**

- Recheck the URI and cluster host name.
- Make sure your internet connection works and your current IP is allowed in Atlas Network Access.
- Confirm the Atlas database user/password are correct.

**Authentication failed**

- Make sure you use the Atlas **database user**, not your Atlas website login.
- Check the password and URL-encode special characters in it.

**`streamlit` or `pymongo` is not recognized / module not found**

- Activate `.venv` and run `pip install -r requirements.txt` again.
- Make sure your terminal's current folder is the folder containing `requirements.txt`.

**A collection validator could not be updated**

- The Atlas database user may need permission to modify an existing collection. Review the `setup_db.py` output. If starting fresh for a class assignment, a new empty database is often the simplest way to avoid conflicts with unrelated old test data.
