"""Create CivicResolve collections, indexes, and MongoDB validators."""

from __future__ import annotations

from database import configure_database, get_connection_settings
from pymongo import MongoClient


def main() -> None:
    try:
        uri, database_name = get_connection_settings()
        client = MongoClient(uri, serverSelectionTimeoutMS=7000, connectTimeoutMS=7000)
        client.admin.command("ping")
        db = client[database_name]
        print(f"Connected to MongoDB database: {database_name}")
        notes = configure_database(db, apply_validation=True)
        for note in notes:
            print(f"- {note}")
        print("- Indexes are ready.")
        print("Database setup finished.")
        client.close()
    except Exception as exc:
        print("Database setup failed.")
        print(f"Reason: {exc}")
        print("Check the MONGODB_URI value in your .env file and the README troubleshooting section.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
