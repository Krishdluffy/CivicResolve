"""Insert sample reports for a classroom demonstration. Does not overwrite existing reports."""

from __future__ import annotations

from datetime import timedelta

from database import get_connection_settings, utc_now, configure_database
from pymongo import MongoClient
from validation import choose_department


def main() -> None:
    try:
        uri, database_name = get_connection_settings()
        client = MongoClient(uri, serverSelectionTimeoutMS=7000, connectTimeoutMS=7000)
        client.admin.command("ping")
        db = client[database_name]
        configure_database(db, apply_validation=False)

        if db["reports"].count_documents({}) > 0:
            print("Sample data was not added because the reports collection is not empty.")
            print("This protects any reports you have already created.")
            client.close()
            return

        now = utc_now()
        people = [
            {"name": "Aarav Sharma", "email": "aarav.demo@example.com", "area": "Model Town"},
            {"name": "Simran Kaur", "email": "simran.demo@example.com", "area": "Urban Estate"},
            {"name": "Rohan Verma", "email": "rohan.demo@example.com", "area": "Green Park"},
            {"name": "Meera Singh", "email": "meera.demo@example.com", "area": "Bus Stand Road"},
            {"name": "Kabir Das", "email": "kabir.demo@example.com", "area": "Model Town"},
        ]
        person_ids = {}
        for person in people:
            normalized_email = person["email"].lower()
            db["users"].update_one(
                {"email": normalized_email},
                {
                    "$set": {"name": person["name"], "area": person["area"]},
                    "$setOnInsert": {"role": "citizen", "created_at": now},
                },
                upsert=True,
            )
            person_doc = db["users"].find_one({"email": normalized_email}, {"_id": 1})
            person_ids[normalized_email] = person_doc["_id"]

        specifications = [
            {
                "title": "Streetlight not working near the bus stop",
                "description": "The streetlight has been off for several nights, making the bus stop and nearby footpath very dark after sunset.",
                "category": "Streetlight", "area": "Model Town", "landmark": "Near the main bus stop",
                "person": "aarav.demo@example.com", "priority": "High", "status": "In Progress", "days": 5,
                "note": "The electrical team has been informed and repair work is being scheduled.", "votes": ["simran.demo@example.com", "rohan.demo@example.com", "kabir.demo@example.com"],
            },
            {
                "title": "Garbage accumulating beside the market",
                "description": "Waste bags are being left beside the market entrance. The smell is getting worse and the area attracts stray animals.",
                "category": "Garbage / Waste", "area": "Model Town", "landmark": "Market entrance",
                "person": "simran.demo@example.com", "priority": "Medium", "status": "Under Review", "days": 4,
                "note": "The sanitation department has been asked to inspect the location.", "votes": ["aarav.demo@example.com", "meera.demo@example.com"],
            },
            {
                "title": "Large pothole on the main road",
                "description": "A deep pothole has developed on the road and vehicles are swerving to avoid it, creating a possible safety risk.",
                "category": "Pothole / Road Damage", "area": "Bus Stand Road", "landmark": "Opposite the pharmacy",
                "person": "rohan.demo@example.com", "priority": "High", "status": "Reported", "days": 2,
                "note": "Report submitted.", "votes": ["aarav.demo@example.com", "simran.demo@example.com", "kabir.demo@example.com", "meera.demo@example.com"],
            },
            {
                "title": "Water leakage near residential homes",
                "description": "Clean water has been leaking from a roadside pipe and forming a puddle outside nearby homes for multiple days.",
                "category": "Water Leakage", "area": "Green Park", "landmark": "Lane beside the community park",
                "person": "meera.demo@example.com", "priority": "Medium", "status": "Resolved", "days": 8,
                "note": "The pipe joint was repaired and the site was checked.", "votes": ["simran.demo@example.com"],
            },
            {
                "title": "Drain blocks after heavy rain",
                "description": "The roadside drain is blocked and rainwater stays on the pavement, making it difficult for pedestrians to pass.",
                "category": "Drainage / Flooding", "area": "Urban Estate", "landmark": "Outside the public park gate",
                "person": "kabir.demo@example.com", "priority": "High", "status": "In Progress", "days": 6,
                "note": "A cleaning visit is planned; team will check the drain outlet as well.", "votes": ["aarav.demo@example.com", "meera.demo@example.com"],
            },
            {
                "title": "Broken pavement tiles create a trip hazard",
                "description": "Several pavement tiles are loose and uneven. Pedestrians have to walk close to moving traffic to get around them.",
                "category": "Pothole / Road Damage", "area": "Urban Estate", "landmark": "Near the community hall",
                "person": "aarav.demo@example.com", "priority": "Low", "status": "Reported", "days": 1,
                "note": "Report submitted.", "votes": [],
            },
            {
                "title": "Unsafe exposed electrical wire",
                "description": "A wire appears to be hanging low close to the walking path. Please inspect it and make the area safe as soon as possible.",
                "category": "Public Safety", "area": "Bus Stand Road", "landmark": "Near the crossing",
                "person": "simran.demo@example.com", "priority": "High", "status": "Under Review", "days": 3,
                "note": "The report has been sent for an initial safety assessment.", "votes": ["rohan.demo@example.com", "meera.demo@example.com"],
            },
            {
                "title": "Overflowing public waste bin",
                "description": "The public bin is full and rubbish is spilling onto the footpath. A collection visit is needed.",
                "category": "Garbage / Waste", "area": "Green Park", "landmark": "Outside the community centre",
                "person": "rohan.demo@example.com", "priority": "Medium", "status": "Rejected", "days": 7,
                "note": "A duplicate report for the same bin was already being handled.", "votes": ["kabir.demo@example.com"],
            },
            {
                "title": "Street drain cover is missing",
                "description": "A drain cover is missing from the roadside opening. It should be secured to prevent a person or vehicle from falling in.",
                "category": "Public Safety", "area": "Model Town", "landmark": "Close to the corner tea shop",
                "person": "meera.demo@example.com", "priority": "High", "status": "Reported", "days": 0,
                "note": "Report submitted.", "votes": ["aarav.demo@example.com", "simran.demo@example.com"],
            },
        ]

        documents = []
        for spec in specifications:
            created_at = now - timedelta(days=spec["days"])
            status = spec["status"]
            resolved_at = None
            updates = [{
                "status": "Reported",
                "message": "Report submitted.",
                "changed_by": people[[p["email"] for p in people].index(spec["person"])]["name"],
                "created_at": created_at,
            }]
            if status != "Reported":
                update_time = created_at + timedelta(hours=5)
                updates.append({
                    "status": status,
                    "message": spec["note"],
                    "changed_by": "CivicResolve Admin",
                    "created_at": update_time,
                })
            if status == "Resolved":
                resolved_at = created_at + timedelta(hours=18)
            supporters = sorted(set(spec["votes"]))
            comments = []
            if spec["votes"]:
                comments.append({
                    "name": "Community member",
                    "email": "community.demo@example.com",
                    "message": "Thank you for raising this issue. I hope it can be checked soon.",
                    "created_at": created_at + timedelta(hours=2),
                })
                # Also ensure the sample comment author exists for lookup consistency.
                db["users"].update_one(
                    {"email": "community.demo@example.com"},
                    {"$set": {"name": "Community member", "area": spec["area"]}, "$setOnInsert": {"role": "citizen", "created_at": now}},
                    upsert=True,
                )
            documents.append({
                "title": spec["title"],
                "description": spec["description"],
                "category": spec["category"],
                "location": {"area": spec["area"], "landmark": spec["landmark"]},
                "reported_by": person_ids[spec["person"]],
                "department": choose_department(spec["category"]),
                "status": status,
                "priority": spec["priority"],
                "votes": len(supporters),
                "supporters": supporters,
                "comments": comments,
                "updates": updates,
                "created_at": created_at,
                "updated_at": now if status in ("Reported", "Resolved") else created_at + timedelta(hours=5),
                "resolved_at": resolved_at,
            })

        result = db["reports"].insert_many(documents)
        print(f"Inserted {len(result.inserted_ids)} sample reports into '{database_name}.reports'.")
        print("Open the app and explore the dashboard, community report feed, Admin Desk, and analytics.")
        print("The sample names/emails are fictional demonstration data.")
        client.close()
    except Exception as exc:
        print("Could not insert sample data.")
        print(f"Reason: {exc}")
        print("Run `python setup_db.py` first and check the README troubleshooting section.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
