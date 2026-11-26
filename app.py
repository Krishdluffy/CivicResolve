"""CivicResolve: Community Problem Reporting & Solution Tracker."""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

from database import (
    DEPARTMENTS,
    PRIORITIES,
    STATUSES,
    add_comment,
    add_support,
    average_resolution_hours,
    connect_to_database,
    create_report,
    dashboard_counts,
    delete_report,
    get_connection_settings,
    get_report,
    list_reports,
    reports_by_category,
    reports_by_status,
    unresolved_by_area,
)
from validation import CATEGORIES, choose_department, validate_email, validate_person, validate_report

load_dotenv()
st.set_page_config(
    page_title="CivicResolve | Community Issues",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.8rem; padding-bottom: 3rem;}
      div[data-testid="stMetric"] {background: rgba(120, 120, 120, 0.07); border: 1px solid rgba(120, 120, 120, 0.16); padding: 1rem; border-radius: 0.8rem;}
      .small-muted {color: #777; font-size: 0.88rem;}
      div.stButton > button {border-radius: 0.55rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def cached_database(uri: str, database_name: str):
    return connect_to_database(uri, database_name)


def display_time(value) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y, %I:%M %p")
    return str(value)


def short_id(report: dict) -> str:
    return str(report.get("_id", ""))[-6:].upper()


def show_status(status: str) -> str:
    symbols = {
        "Reported": "🆕",
        "Under Review": "🔎",
        "In Progress": "🛠️",
        "Resolved": "✅",
        "Rejected": "⛔",
    }
    return f"{symbols.get(status, '•')} {status}"


def report_summary_rows(reports: list[dict]) -> pd.DataFrame:
    rows = []
    for report in reports:
        location = report.get("location") or {}
        rows.append({
            "Issue": report.get("title", "Untitled"),
            "Category": report.get("category", "Other"),
            "Area": location.get("area", "Unknown"),
            "Status": report.get("status", "Reported"),
            "Priority": report.get("priority", "Medium"),
            "Support": int(report.get("votes", 0)),
            "Reported": display_time(report.get("created_at")),
        })
    return pd.DataFrame(rows)


def show_connection_help(message: str) -> None:
    st.error("CivicResolve could not connect to MongoDB.")
    st.write(message)
    st.markdown("**Check these three things:**")
    st.markdown(
        "1. The project has a `.env` file copied from `.env.example`.\n"
        "2. `MONGODB_URI` contains the correct MongoDB username, password, and cluster address.\n"
        "3. In MongoDB Atlas, your current IP address is allowed under **Network Access**, and your database user has read/write access."
    )
    st.info("Open `README.md` in the project folder for screenshots-free, step-by-step setup instructions.")
    with st.expander("Technical details"):
        st.code(message)


# A missing or invalid URI should result in a useful instruction screen, not a Python traceback.
try:
    uri, database_name = get_connection_settings()
except ValueError:
    st.title("🏙️ CivicResolve")
    st.subheader("Community Problem Reporting & Solution Tracker")
    st.write("This project is ready, but it needs your MongoDB connection string before it can store or retrieve data.")
    st.markdown("### First-time setup")
    st.markdown(
        "1. Open the downloaded project folder.\n"
        "2. Make a copy of `.env.example` and rename the copy to `.env`.\n"
        "3. Open `.env` in Notepad and replace the example `MONGODB_URI` with your real connection string.\n"
        "4. Save the file, then run `python setup_db.py`, `python seed_data.py`, and `streamlit run app.py` in the terminal."
    )
    st.warning("Do not share your `.env` file or publish your database password.")
    st.stop()

try:
    with st.spinner("Connecting to your MongoDB database…"):
        mongo_client, db = cached_database(uri, database_name)
except Exception as exc:  # show guidance instead of a traceback to a novice
    show_connection_help(str(exc))
    st.stop()

# Sidebar navigation
with st.sidebar:
    st.markdown("# 🏙️ CivicResolve")
    st.caption("Small issues. Shared action. Better communities.")
    page = st.radio(
        "Navigate",
        ["Community Dashboard", "Report a Problem", "Browse & Support", "Admin Desk", "Analytics & Insights"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Database status**")
    st.success("Connected to MongoDB")
    st.caption(f"Database: `{database_name}`")
    st.divider()
    st.caption("Classroom project prototype. The Admin Desk is not protected by real authentication.")


if page == "Community Dashboard":
    st.title("Community Dashboard")
    st.write("A snapshot of the problems residents have reported and the progress being made.")

    try:
        metrics = dashboard_counts(db)
        metric_cols = st.columns(4)
        metric_cols[0].metric("Total reports", metrics["total"])
        metric_cols[1].metric("Active issues", metrics["active"])
        metric_cols[2].metric("Resolved", metrics["resolved"])
        metric_cols[3].metric("High priority", metrics["high_priority"])

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Reports by category")
            category_data = reports_by_category(db)
            if category_data:
                chart_df = pd.DataFrame([{"Category": item["_id"], "Reports": item["count"]} for item in category_data])
                fig = px.bar(chart_df, x="Category", y="Reports", color="Category", title="Which issues are reported most?")
                fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Number of reports")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No reports yet. Add the first community report to populate this chart.")
        with col_b:
            st.subheader("Current report status")
            status_data = reports_by_status(db)
            if status_data:
                chart_df = pd.DataFrame([{"Status": item["_id"], "Reports": item["count"]} for item in status_data])
                fig = px.pie(chart_df, names="Status", values="Reports", hole=0.48, title="Progress at a glance")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Status breakdown will appear after reports are submitted.")

        st.subheader("Recently reported problems")
        latest = list_reports(db, limit=8)
        if latest:
            st.dataframe(report_summary_rows(latest), use_container_width=True, hide_index=True)
        else:
            st.info("No issues have been reported yet. Go to **Report a Problem** to create the first one.")
    except PyMongoError as exc:
        st.error(f"MongoDB could not load the dashboard: {exc}")


elif page == "Report a Problem":
    st.title("Report a Community Problem")
    st.write("Share enough detail so the right people can understand and act on the issue.")
    st.info("Please do not include private or sensitive information in a public report.")

    with st.form("create_report_form", clear_on_submit=False):
        st.subheader("Problem details")
        title = st.text_input("Short title *", placeholder="Example: Streetlight not working near the bus stop", max_chars=100)
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category *", CATEGORIES)
            priority = st.selectbox("Priority *", PRIORITIES, index=1, help="Choose High only when the issue needs urgent attention.")
        with col2:
            area = st.text_input("Area / neighbourhood *", placeholder="Example: Model Town")
            landmark = st.text_input("Nearby landmark", placeholder="Example: Near the main market", max_chars=150)
        description = st.text_area(
            "Describe the problem *",
            placeholder="What happened? Where exactly is it? How is it affecting people?",
            height=130,
            max_chars=2000,
        )
        st.subheader("Your contact details")
        col3, col4 = st.columns(2)
        with col3:
            person_name = st.text_input("Your name *", max_chars=80)
        with col4:
            email = st.text_input("Email address *", placeholder="name@example.com", max_chars=254)
        submitted = st.form_submit_button("Submit community report", type="primary", use_container_width=True)

    if submitted:
        try:
            clean_person, clean_email = validate_person(person_name, email)
            clean_data = validate_report({
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "area": area,
                "landmark": landmark,
            })
            clean_data["department"] = choose_department(clean_data["category"])
            new_id = create_report(db, clean_person, clean_email, clean_data)
            st.success(f"Your report was submitted successfully. Reference ID: {new_id}")
            st.write("You can use **Browse & Support** to check its status and follow updates.")
        except ValueError as exc:
            st.error(str(exc))
        except DuplicateKeyError:
            st.error("That email address already exists in an unexpected way. Please check the profile and try again.")
        except (PyMongoError, RuntimeError) as exc:
            st.error(f"The report could not be saved: {exc}")


elif page == "Browse & Support":
    st.title("Browse Community Reports")
    st.write("Find an issue, add your support, or leave a constructive suggestion.")
    f1, f2, f3 = st.columns([1, 1, 1])
    with f1:
        filter_status = st.selectbox("Filter by status", ["All"] + STATUSES)
    with f2:
        filter_category = st.selectbox("Filter by category", ["All"] + CATEGORIES)
    with f3:
        filter_area = st.text_input("Area contains", placeholder="e.g. Model Town")
    search_text = st.text_input("Search reports", placeholder="Search title, description, area, or landmark")

    with st.expander("Enter your details to support a report or comment"):
        profile_name = st.text_input("Your name", key="browse_profile_name", max_chars=80)
        profile_email = st.text_input("Your email", key="browse_profile_email", max_chars=254)
        st.caption("An email can support a given report only once. Use a consistent email for your own activity.")

    try:
        reports = list_reports(db, status=filter_status, category=filter_category, area=filter_area, search=search_text)
        st.caption(f"Showing {len(reports)} report(s), up to 200 per search.")
        if not reports:
            st.info("No reports match those filters. Try changing or clearing a filter.")
        for report in reports:
            rid = str(report["_id"])
            location = report.get("location") or {}
            label = f"{show_status(report.get('status', 'Reported'))}  ·  {report.get('title', 'Untitled')}  ·  {location.get('area', 'Unknown area')}"
            with st.expander(label):
                left, right = st.columns([2, 1])
                with left:
                    st.markdown(f"**Description**\n\n{report.get('description', '')}")
                    st.markdown(f"**Location:** {location.get('area', 'Unknown')} — {location.get('landmark', 'Not specified')}")
                    st.markdown(f"**Category:** {report.get('category', 'Other')}  ·  **Department:** {report.get('department', 'Other')}")
                    st.markdown(f"**Reported by:** {report.get('reporter_name', 'Community member')}  ·  **Date:** {display_time(report.get('created_at'))}")
                    st.caption(f"Reference: {report['_id']}")
                with right:
                    st.metric("Community support", int(report.get("votes", 0)))
                    st.write(f"**Priority:** {report.get('priority', 'Medium')}")
                    st.write(f"**Status:** {report.get('status', 'Reported')}")
                    if st.button("👍 Support this issue", key=f"support_{rid}", use_container_width=True):
                        try:
                            clean_person, clean_email = validate_person(profile_name, profile_email)
                            ok, message = add_support(db, rid, clean_person, clean_email, location.get("area", "Unknown area"))
                            st.session_state["_civicresolve_flash"] = ("success" if ok else "warning", message)
                            st.rerun()
                        except ValueError as exc:
                            st.error(f"Enter a valid name and email above first. {exc}")

                comments = report.get("comments") or []
                st.markdown(f"**Comments and suggestions ({len(comments)})**")
                if comments:
                    for comment in reversed(comments[-5:]):
                        st.markdown(f"**{comment.get('name', 'Community member')}** · {display_time(comment.get('created_at'))}")
                        st.write(comment.get("message", ""))
                else:
                    st.caption("No comments yet.")

                with st.form(f"comment_form_{rid}", clear_on_submit=True):
                    comment_text = st.text_area("Add a suggestion", max_chars=500, key=f"comment_text_{rid}", placeholder="Keep suggestions respectful and helpful.")
                    add_comment_submitted = st.form_submit_button("Post comment")
                if add_comment_submitted:
                    try:
                        clean_person, clean_email = validate_person(profile_name, profile_email)
                        add_comment(db, rid, clean_person, clean_email, location.get("area", "Unknown area"), comment_text)
                        st.session_state["_civicresolve_flash"] = ("success", "Your comment was posted.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                    except PyMongoError as exc:
                        st.error(f"Could not post comment: {exc}")

                updates = report.get("updates") or []
                st.markdown("**Recent progress history**")
                if updates:
                    for update in reversed(updates[-8:]):
                        st.markdown(f"**{show_status(update.get('status', 'Reported'))}** · {display_time(update.get('created_at'))}")
                        st.write(update.get("message", ""))
                        st.caption(f"Updated by {update.get('changed_by', 'Administrator')}")
                else:
                    st.caption("No progress updates have been recorded.")
    except PyMongoError as exc:
        st.error(f"Could not retrieve reports: {exc}")


elif page == "Admin Desk":
    st.title("Admin Desk")
    st.warning(
        "For this classroom prototype, the Admin Desk has no real sign-in protection. Do not expose this app publicly or store real personal data without adding authentication and authorization."
    )
    st.write("Update issue progress, assign departments, and keep a history of administrative actions.")

    try:
        reports = list_reports(db, limit=300)
        if not reports:
            st.info("There are no reports to manage yet. Submit a report or run `python seed_data.py` to add demonstration data.")
        else:
            label_to_report = {}
            for report in reports:
                location = report.get("location") or {}
                label = f"{report.get('title', 'Untitled')} — {location.get('area', 'Unknown')} — #{short_id(report)} ({report.get('status', 'Reported')})"
                label_to_report[label] = report
            selected_label = st.selectbox("Choose a report to manage", list(label_to_report.keys()))
            selected = label_to_report[selected_label]
            selected_id = str(selected["_id"])
            st.markdown(f"**Current status:** {show_status(selected.get('status', 'Reported'))}  ·  **Priority:** {selected.get('priority', 'Medium')}  ·  **Department:** {selected.get('department', 'Other')}")
            st.caption(f"Reference ID: {selected_id}")

            with st.form("admin_update_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    current_status = selected.get("status", "Reported")
                    new_status = st.selectbox("Status", STATUSES, index=STATUSES.index(current_status) if current_status in STATUSES else 0)
                with col2:
                    current_priority = selected.get("priority", "Medium")
                    new_priority = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(current_priority) if current_priority in PRIORITIES else 1)
                with col3:
                    current_department = selected.get("department", "Other")
                    new_department = st.selectbox("Responsible department", DEPARTMENTS, index=DEPARTMENTS.index(current_department) if current_department in DEPARTMENTS else DEPARTMENTS.index("Other"))
                changed_by = st.text_input("Administrator display name", value="CivicResolve Admin", max_chars=80)
                admin_note = st.text_area("Progress note", placeholder="Example: Inspection completed; repair work scheduled for Friday.", max_chars=500)
                update_submitted = st.form_submit_button("Save changes", type="primary", use_container_width=True)

            if update_submitted:
                try:
                    admin_name = " ".join(changed_by.split())
                    if len(admin_name) < 2:
                        raise ValueError("Administrator display name must contain at least 2 characters.")
                    update_report(db, selected_id, new_status, new_priority, new_department, admin_note, admin_name)
                    st.session_state["_civicresolve_flash"] = ("success", "Report updated and progress history saved.")
                    st.rerun()
                except (ValueError, PyMongoError) as exc:
                    st.error(f"Could not update this report: {exc}")

            st.divider()
            st.subheader("Delete a report")
            st.caption("Deleting is permanent in this prototype. Prefer changing the status to Rejected when a report should be retained for the audit trail.")
            confirm_delete = st.checkbox("I understand that deleting this report cannot be undone.", key=f"confirm_delete_{selected_id}")
            if st.button("Delete selected report", type="secondary", disabled=not confirm_delete, key=f"delete_{selected_id}"):
                try:
                    if delete_report(db, selected_id):
                        st.session_state["_civicresolve_flash"] = ("success", "Report deleted.")
                        st.rerun()
                    else:
                        st.error("The report was not found; it may already have been deleted.")
                except PyMongoError as exc:
                    st.error(f"Could not delete this report: {exc}")
    except PyMongoError as exc:
        st.error(f"Could not load the Admin Desk: {exc}")


elif page == "Analytics & Insights":
    st.title("Analytics & Insights")
    st.write("These results are calculated from MongoDB aggregation pipelines, not hard-coded summaries.")
    try:
        top_left, top_right = st.columns(2)
        category_data = reports_by_category(db)
        with top_left:
            st.subheader("1. Reports by category")
            if category_data:
                df = pd.DataFrame([{"Category": row["_id"], "Count": row["count"]} for row in category_data])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption("Pipeline: `$group` by category, then `$sort` by count.")
            else:
                st.info("No data yet.")
        with top_right:
            st.subheader("2. Open reports by area")
            area_data = unresolved_by_area(db)
            if area_data:
                df = pd.DataFrame([{"Area": row["_id"], "Open reports": row["open_reports"]} for row in area_data])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption("Pipeline: `$match` active statuses, `$group` by area, `$sort`, and `$limit`.")
            else:
                st.info("No unresolved reports yet.")

        st.divider()
        st.subheader("3. Report status breakdown")
        status_data = reports_by_status(db)
        if status_data:
            df = pd.DataFrame([{"Status": row["_id"], "Count": row["count"]} for row in status_data])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption("Pipeline: `$group` by status and sort by count.")
        else:
            st.info("No data yet.")

        st.divider()
        st.subheader("4. Average resolution time by category")
        resolution_data = average_resolution_hours(db)
        if resolution_data:
            df = pd.DataFrame([{
                "Category": row["_id"],
                "Resolved reports": row["resolved_count"],
                "Average hours to resolve": round(float(row["average_hours"]), 2),
            } for row in resolution_data])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption("Pipeline: `$match` resolved reports, `$project` time difference, then `$group` by category.")
        else:
            st.info("Resolution-time analytics will appear once at least one report has been marked Resolved.")

        with st.expander("What aggregation stages does this project demonstrate?"):
            st.markdown(
                "- **`$match`** — filter unresolved or resolved reports.\n"
                "- **`$group`** — count reports by category, status, or area.\n"
                "- **`$sort`** — place the largest groups first.\n"
                "- **`$limit`** — return only the top areas.\n"
                "- **`$project`** — calculate resolution duration.\n"
                "- **`$lookup`** — join each report with the reporter's profile in the `users` collection."
            )
    except PyMongoError as exc:
        st.error(f"Could not calculate analytics: {exc}")


st.sidebar.caption("CivicResolve · MongoDB + PyMongo + Streamlit")
