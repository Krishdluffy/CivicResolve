"""MongoDB access and query functions for CivicResolve."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import OperationFailure

from validation import DEPARTMENTS, PRIORITIES, STATUSES

load_dotenv()

USER_JSON_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["name", "email", "role", "area", "created_at"],
    "properties": {
        "name": {"bsonType": "string", "minLength": 2, "maxLength": 80},
        "email": {
            "bsonType": "string",
            "pattern": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
            "maxLength": 254,
        },
        "role": {"bsonType": "string", "enum": ["citizen", "admin"]},
        "area": {"bsonType": "string", "minLength": 2, "maxLength": 100},
        "created_at": {"bsonType": "date"},
    },
}

COMMENT_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["name", "email", "message", "created_at"],
    "properties": {
        "name": {"bsonType": "string", "minLength": 2, "maxLength": 80},
        "email": {"bsonType": "string", "maxLength": 254},
        "message": {"bsonType": "string", "minLength": 2, "maxLength": 500},
        "created_at": {"bsonType": "date"},
    },
}

UPDATE_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["status", "message", "changed_by", "created_at"],
    "properties": {
        "status": {"bsonType": "string", "enum": STATUSES},
        "message": {"bsonType": "string", "minLength": 2, "maxLength": 500},
        "changed_by": {"bsonType": "string", "minLength": 2, "maxLength": 80},
        "created_at": {"bsonType": "date"},
    },
}

REPORT_JSON_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": [
        "title", "description", "category", "location", "reported_by", "department",
        "status", "priority", "votes", "supporters", "comments", "updates",
        "created_at", "updated_at", "resolved_at",
    ],
    "properties": {
        "title": {"bsonType": "string", "minLength": 5, "maxLength": 100},
        "description": {"bsonType": "string", "minLength": 15, "maxLength": 2000},
        "category": {
            "bsonType": "string",
            "enum": [
                "Pothole / Road Damage", "Garbage / Waste", "Streetlight", "Water Leakage",
                "Drainage / Flooding", "Public Safety", "Other",
            ],
        },
        "location": {
            "bsonType": "object",
            "required": ["area", "landmark"],
            "properties": {
                "area": {"bsonType": "string", "minLength": 2, "maxLength": 100},
                "landmark": {"bsonType": "string", "maxLength": 150},
            },
        },
        "reported_by": {"bsonType": "objectId"},
        "department": {"bsonType": "string", "enum": DEPARTMENTS},
        "status": {"bsonType": "string", "enum": STATUSES},
        "priority": {"bsonType": "string", "enum": PRIORITIES},
        "votes": {"bsonType": ["int", "long"], "minimum": 0},
        "supporters": {"bsonType": "array", "items": {"bsonType": "string"}, "uniqueItems": True},
        "comments": {"bsonType": "array", "items": COMMENT_SCHEMA},
        "updates": {"bsonType": "array", "items": UPDATE_SCHEMA},
        "created_at": {"bsonType": "date"},
        "updated_at": {"bsonType": "date"},
        "resolved_at": {"bsonType": ["date", "null"]},
    },
}

VALIDATORS = {
    "users": {"$jsonSchema": USER_JSON_SCHEMA},
    "reports": {"$jsonSchema": REPORT_JSON_SCHEMA},
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_connection_settings() -> tuple[str, str]:
    uri = os.getenv("MONGODB_URI", "").strip()
    database_name = os.getenv("MONGODB_DATABASE", "civicresolve").strip() or "civicresolve"
    if not uri:
        raise ValueError(
            "MONGODB_URI is not set. Copy .env.example to .env and add your MongoDB connection string."
        )
    return uri, database_name


def connect_to_database(uri: str, database_name: str) -> tuple[MongoClient, Database]:
    client = MongoClient(uri, serverSelectionTimeoutMS=7000, connectTimeoutMS=7000)
    client.admin.command("ping")
    db = client[database_name]
    configure_database(db, apply_validation=False)
    return client, db


def configure_database(db: Database, apply_validation: bool = False) -> list[str]:
    """Create collections and indexes. Optionally try to add validators to existing collections."""
    notes: list[str] = []
    existing = set(db.list_collection_names())
    for name, validator in VALIDATORS.items():
        if name not in existing:
            db.create_collection(name, validator=validator, validationLevel="strict", validationAction="error")
            notes.append(f"Created {name} with MongoDB schema validation.")
        elif apply_validation:
            try:
                db.command({
                    "collMod": name,
                    "validator": validator,
                    "validationLevel": "strict",
                    "validationAction": "error",
                })
                notes.append(f"Applied MongoDB schema validation to {name}.")
            except OperationFailure as exc:
                notes.append(
                    f"Could not update validation on existing collection '{name}' ({exc.codeName or 'permission/error'}). "
                    "Python-side validation still works; check the setup guide if you need database-level validation."
                )

    users: Collection = db["users"]
    users.create_index([("email", ASCENDING)], unique=True, name="unique_user_email")
    reports: Collection = db["reports"]
    reports.create_index([("created_at", DESCENDING)], name="reports_newest_first")
    reports.create_index([("status", ASCENDING), ("priority", ASCENDING)], name="reports_status_priority")
    reports.create_index([("category", ASCENDING)], name="reports_category")
    reports.create_index([("location.area", ASCENDING)], name="reports_area")
    reports.create_index([("reported_by", ASCENDING)], name="reports_reporter")
    return notes


def ensure_user(db: Database, name: str, email: str, area: str) -> ObjectId:
    now = utc_now()
    normalized_email = email.strip().lower()
    user_area = (area.strip() or "Unknown area")[:100]
    result = db["users"].update_one(
        {"email": normalized_email},
        {
            "$set": {"name": name.strip(), "area": user_area},
            "$setOnInsert": {"role": "citizen", "created_at": now},
        },
        upsert=True,
    )
    if result.upserted_id:
        return result.upserted_id
    existing = db["users"].find_one({"email": normalized_email}, {"_id": 1})
    if not existing:
        raise RuntimeError("Could not create or find the user profile.")
    return existing["_id"]


def create_report(db: Database, person_name: str, email: str, data: dict[str, Any]) -> ObjectId:
    now = utc_now()
    user_id = ensure_user(db, person_name, email, data["area"])
    document = {
        "title": data["title"],
        "description": data["description"],
        "category": data["category"],
        "location": {"area": data["area"], "landmark": data["landmark"]},
        "reported_by": user_id,
        "department": data["department"],
        "status": "Reported",
        "priority": data["priority"],
        "votes": 0,
        "supporters": [],
        "comments": [],
        "updates": [{
            "status": "Reported",
            "message": "Report submitted.",
            "changed_by": person_name.strip(),
            "created_at": now,
        }],
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
    }
    result = db["reports"].insert_one(document)
    return result.inserted_id


def build_report_query(
    status: str = "All",
    category: str = "All",
    area: str = "",
    search: str = "",
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if status != "All":
        query["status"] = status
    if category != "All":
        query["category"] = category
    if area.strip():
        query["location.area"] = {"$regex": area.strip(), "$options": "i"}
    if search.strip():
        import re
        escaped = re.escape(search.strip())
        query["$or"] = [
            {"title": {"$regex": escaped, "$options": "i"}},
            {"description": {"$regex": escaped, "$options": "i"}},
            {"location.area": {"$regex": escaped, "$options": "i"}},
            {"location.landmark": {"$regex": escaped, "$options": "i"}},
        ]
    return query


def list_reports(
    db: Database,
    status: str = "All",
    category: str = "All",
    area: str = "",
    search: str = "",
    limit: int = 200,
) -> list[dict[str, Any]]:
    query = build_report_query(status, category, area, search)
    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {"$limit": max(1, min(limit, 1000))},
        {"$lookup": {
            "from": "users",
            "localField": "reported_by",
            "foreignField": "_id",
            "as": "reporter",
        }},
        {"$unwind": {"path": "$reporter", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "title": 1, "description": 1, "category": 1, "location": 1,
            "department": 1, "status": 1, "priority": 1, "votes": 1,
            "supporters": 1, "comments": 1, "updates": 1, "created_at": 1,
            "updated_at": 1, "resolved_at": 1, "reported_by": 1,
            "reporter_name": "$reporter.name", "reporter_email": "$reporter.email",
        }},
    ]
    return list(db["reports"].aggregate(pipeline))


def get_report(db: Database, report_id: str) -> dict[str, Any] | None:
    if not ObjectId.is_valid(report_id):
        return None
    return db["reports"].find_one({"_id": ObjectId(report_id)})


def add_support(db: Database, report_id: str, name: str, email: str, area: str) -> tuple[bool, str]:
    if not ObjectId.is_valid(report_id):
        return False, "This report ID is invalid."
    normalized_email = email.strip().lower()
    ensure_user(db, name, normalized_email, area or "Unknown area")
    result = db["reports"].update_one(
        {"_id": ObjectId(report_id), "supporters": {"$ne": normalized_email}},
        {
            "$addToSet": {"supporters": normalized_email},
            "$inc": {"votes": 1},
            "$set": {"updated_at": utc_now()},
        },
    )
    if result.modified_count:
        return True, "Your support has been recorded."
    if db["reports"].find_one({"_id": ObjectId(report_id)}, {"_id": 1}):
        return False, "This email has already supported this report."
    return False, "This report no longer exists."


def add_comment(db: Database, report_id: str, name: str, email: str, area: str, message: str) -> None:
    if not ObjectId.is_valid(report_id):
        raise ValueError("Invalid report ID.")
    clean_message = message.strip()
    if not 2 <= len(clean_message) <= 500:
        raise ValueError("Comment must contain between 2 and 500 characters.")
    ensure_user(db, name, email, area or "Unknown area")
    result = db["reports"].update_one(
        {"_id": ObjectId(report_id)},
        {
            "$push": {"comments": {
                "name": name.strip(),
                "email": email.strip().lower(),
                "message": clean_message,
                "created_at": utc_now(),
            }},
            "$set": {"updated_at": utc_now()},
        },
    )
    if result.matched_count == 0:
        raise ValueError("This report no longer exists.")


def update_report(
    db: Database,
    report_id: str,
    status: str,
    priority: str,
    department: str,
    note: str,
    changed_by: str = "Administrator",
) -> None:
    if not ObjectId.is_valid(report_id):
        raise ValueError("Invalid report ID.")
    if status not in STATUSES or priority not in PRIORITIES or department not in DEPARTMENTS:
        raise ValueError("Choose a valid status, priority, and department.")
    existing = db["reports"].find_one({"_id": ObjectId(report_id)})
    if not existing:
        raise ValueError("This report no longer exists.")

    now = utc_now()
    if status == "Resolved":
        resolved_at = existing.get("resolved_at") if existing.get("status") == "Resolved" else now
    else:
        resolved_at = None

    clean_note = note.strip()
    if clean_note:
        history_message = clean_note[:500]
    else:
        history_message = f"Administrative update: status set to {status}, priority set to {priority}, department set to {department}."

    result = db["reports"].update_one(
        {"_id": ObjectId(report_id)},
        {
            "$set": {
                "status": status,
                "priority": priority,
                "department": department,
                "updated_at": now,
                "resolved_at": resolved_at,
            },
            "$push": {"updates": {
                "status": status,
                "message": history_message,
                "changed_by": changed_by[:80],
                "created_at": now,
            }},
        },
    )
    if result.matched_count == 0:
        raise ValueError("This report no longer exists.")


def delete_report(db: Database, report_id: str) -> bool:
    if not ObjectId.is_valid(report_id):
        return False
    return db["reports"].delete_one({"_id": ObjectId(report_id)}).deleted_count == 1


def dashboard_counts(db: Database) -> dict[str, int]:
    reports: Collection = db["reports"]
    return {
        "total": reports.count_documents({}),
        "active": reports.count_documents({"status": {"$nin": ["Resolved", "Rejected"]}}),
        "resolved": reports.count_documents({"status": "Resolved"}),
        "high_priority": reports.count_documents({"priority": "High", "status": {"$ne": "Resolved"}}),
    }


def reports_by_category(db: Database) -> list[dict[str, Any]]:
    return list(db["reports"].aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]))


def reports_by_status(db: Database) -> list[dict[str, Any]]:
    return list(db["reports"].aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))


def unresolved_by_area(db: Database) -> list[dict[str, Any]]:
    return list(db["reports"].aggregate([
        {"$match": {"status": {"$nin": ["Resolved", "Rejected"]}}},
        {"$group": {"_id": "$location.area", "open_reports": {"$sum": 1}}},
        {"$sort": {"open_reports": -1, "_id": 1}},
        {"$limit": 10},
    ]))


def average_resolution_hours(db: Database) -> list[dict[str, Any]]:
    return list(db["reports"].aggregate([
        {"$match": {"status": "Resolved", "resolved_at": {"$type": "date"}}},
        {"$project": {
            "category": 1,
            "resolution_hours": {
                "$divide": [{"$subtract": ["$resolved_at", "$created_at"]}, 3_600_000]
            },
        }},
        {"$group": {
            "_id": "$category",
            "average_hours": {"$avg": "$resolution_hours"},
            "resolved_count": {"$sum": 1},
        }},
        {"$sort": {"average_hours": 1}},
    ]))


def validate_database_connection() -> tuple[MongoClient, Database]:
    uri, name = get_connection_settings()
    return connect_to_database(uri, name)
