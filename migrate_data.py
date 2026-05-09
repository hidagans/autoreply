"""
Migration script for AutoReply database structure
Migrates from Pyrogram structure to Telethon userbot structure
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json
from datetime import datetime

# Use config from main.py
DB_HOST = 'localhost'
DB_PORT = 27017
DB_NAME = 'ahli_bot'

async def migrate():
    # Connect to MongoDB
    client = AsyncIOMotorClient(f"mongodb://{DB_HOST}:{DB_PORT}/")
    db = client[DB_NAME]

    print(f"Connected to MongoDB: {DB_NAME}")

    # 1. Export current Pyrogram data
    print("Exporting Pyrogram data...")

    try:
        wordings_old_cursor = db.wordings.find({}, {"jumlah": 1, "keyword": 1, "pesan": 1, "group_id": 1, "userbot_id": 1})
        groups_old_cursor = db.autoreply_groups.find({}, {"group_id": 1, "userbot_id": 1})

        wordings_old = await wordings_old_cursor.to_list(length=None)
        groups_old = await groups_old_cursor.to_list(length=None)
    except Exception as e:
        print(f"Error reading current data: {e}")
        print("\nTrying to export anyway...")
        # Try without filtering first
        wordings_old_cursor = db.wordings.find({})
        groups_old_cursor = db.autoreply_groups.find({})
        wordings_old = await wordings_old_cursor.to_list(length=None)
        groups_old = await groups_old_cursor.to_list(length=None)

    print(f"Found {len(wordings_old)} wordings")
    print(f"Found {len(groups_old)} groups")

    if len(wordings_old) == 0:
        print("No data to migrate!")
        return

    # Save to backup file
    with open('/home/ubuntu/ahli-bot/data_export.json', 'w') as f:
        json.dump({
            'wordings': wordings_old,
            'groups': groups_old
        }, f, indent=2)

    print(f"Export saved to: /home/ubuntu/ahli-bot/data_export.json")

    # 2. Create new structure
    print("\nCreating new database structure...")

    # Drop old collections
    await db.wordings.drop()
    await db.autoreply_groups.drop()

    print("Old collections dropped")

    # Migrate groups to new structure
    for group in groups_old:
        group_id = group.get('group_id')
        userbot_id = group.get('userbot_id')
        
        # Insert to new collection with userbot_id
        await db.autoreply_groups.insert_one({
            'group_id': group_id,
            'userbot_id': userbot_id,
            'created_at': datetime.now()
        })
        
        # Also add to wordings with userbot_id filter
        for wording in wordings_old:
            if str(wording.get('userbot_id')) == str(userbot_id):
                await db.wordings.insert_one({
                    '_id': str(wording.get('_id')),
                    'userbot_id': userbot_id,
                    'send_count': wording.get('jumlah', 0),
                    'keyword': wording.get('keyword', ''),
                    'message': wording.get('pesan', ''),
                    'group_id': wording.get('group_id', 'all'),
                    'active': True,
                    'created_at': datetime.now()
                })

    print("Migration complete!")
    print(f"Data structure updated to Telethon format")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())