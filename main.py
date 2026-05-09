"""
Main Userbot dengan AutoReply Module
"""

import os
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv('API_ID', 20304260))
API_HASH = os.getenv('API_HASH', '763e943987ee09ec449ad1611b7f5fc1')
SESSION_DIR = os.getenv('SESSION_DIR', 'sessions')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 27017))
DB_NAME = os.getenv('DB_NAME', 'ahli_bot')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class AhliBot:
    """Main Userbot Class"""

    def __init__(self, session_name: str = 'userbot.session'):
        self.session_name = session_name
        self.client = TelegramClient(
            session_name,
            API_ID,
            API_HASH,
            base_logger=logging.getLogger('telethon'),
            # ── Speed optimizations ──
            connection_retries=-1,        # retry selamanya kalau disconnect
            auto_reconnect=True,
            flood_sleep_threshold=0,      # jangan sleep saat flood, handle manual
            receive_updates=True,
            sequential_updates=False,     # proses update secara paralel
            timeout=10,                   # timeout lebih ketat biar cepet reconnect
        )
        self.db = None
        self.autoreply = None
        self.modules = {}

    async def connect(self):
        """Connect to Telegram and MongoDB"""
        try:
            logger.info(f"Connecting to Telegram with session: {self.session_name}")
            await self.client.start()

            # Check if we're authorized
            if not await self.client.is_user_authorized():
                logger.error("Not authorized. Generate session file first.")
                return False

            # Log DC info
            me = await self.client.get_me()
            logger.info(f"✅ Connected as {me.first_name} (id={me.id})")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False

    async def connect_db(self):
        """Connect to MongoDB"""
        try:
            logger.info(f"Connecting to MongoDB at {DB_HOST}:{DB_PORT}")
            self.db = AsyncIOMotorClient(
                f"mongodb://{DB_HOST}:{DB_PORT}",
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=3000,
                socketTimeoutMS=3000,
            )[DB_NAME]

            # Create indexes for faster queries
            await self.db.replied_messages.create_index("key", unique=True)
            await self.db.wordings.create_index("userbot_id")
            await self.db.wording_bukti.create_index("wording_id")

            await self.db.command('ping')
            logger.info("✅ Connected to MongoDB")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False

    async def setup_modules(self):
        """Load and setup modules"""
        try:
            logger.info("Loading modules...")
            from plugins.modules.autoreply import AutoReply

            # Initialize AutoReply module
            self.autoreply = AutoReply(self.client, self.db)

            # Load config
            await self.autoreply.load_config()

            # Setup handlers
            await self.autoreply.setup_handlers()

            # Store module
            self.modules = {
                'autoreply': self.autoreply
            }

            logger.info("✅ AutoReply module loaded successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup modules: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def start(self):
        """Start the bot"""
        logger.info("=" * 50)
        logger.info("Starting Ahli Bot...")
        logger.info("=" * 50)

        # Connect to services
        telegram_connected = await self.connect()
        if telegram_connected:
            logger.info("✅ Connected to Telegram")
        else:
            logger.error("❌ Failed to connect to Telegram")
            return False

        mongodb_connected = await self.connect_db()
        if mongodb_connected:
            logger.info("✅ Connected to MongoDB")
        else:
            logger.error("❌ Failed to connect to MongoDB")
            return False

        # Setup modules
        modules_ready = await self.setup_modules()
        if not modules_ready:
            logger.warning("Modules failed to load. Bot will not start handlers.")
        else:
            logger.info("✅ All modules loaded successfully")

        # Start bot
        if modules_ready:
            logger.info("Starting bot handlers...")
            await self.client.run_until_disconnected()
        else:
            logger.info("Modules disabled, bot will not run handlers")

        return True

    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        await self.client.disconnect()
        logger.info("✅ Bot stopped")


async def main():
    """Main entry point"""
    bot = AhliBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        await bot.stop()


if __name__ == '__main__':
    asyncio.run(main())


    async def connect(self):
        """Connect to Telegram and MongoDB"""
        try:
            logger.info(f"Connecting to Telegram with session: {self.session_name}")
            await self.client.start()

            # Check if we're authorized
            if not await self.client.is_user_authorized():
                logger.error("Not authorized. Generate session file first.")
                return False

            logger.info("✅ Connected to Telegram")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False

    async def connect_db(self):
        """Connect to MongoDB"""
        try:
            logger.info(f"Connecting to MongoDB at {DB_HOST}:{DB_PORT}")
            self.db = AsyncIOMotorClient(f"mongodb://{DB_HOST}:{DB_PORT}")[DB_NAME]

            # Test connection
            await self.db.command('ping')
            logger.info("✅ Connected to MongoDB")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False

    async def setup_modules(self):
        """Load and setup modules"""
        try:
            logger.info("Loading modules...")
            from plugins.modules.autoreply import AutoReply

            # Initialize AutoReply module
            self.autoreply = AutoReply(self.client, self.db)

            # Load config
            await self.autoreply.load_config()

            # Setup handlers
            await self.autoreply.setup_handlers()

            # Store module
            self.modules = {
                'autoreply': self.autoreply
            }

            logger.info("✅ AutoReply module loaded successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup modules: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def start(self):
        """Start the bot"""
        logger.info("=" * 50)
        logger.info("Starting Ahli Bot...")
        logger.info("=" * 50)

        # Connect to services
        telegram_connected = await self.connect()
        if telegram_connected:
            logger.info("✅ Connected to Telegram")
        else:
            logger.error("❌ Failed to connect to Telegram")
            return False

        mongodb_connected = await self.connect_db()
        if mongodb_connected:
            logger.info("✅ Connected to MongoDB")
        else:
            logger.error("❌ Failed to connect to MongoDB")
            return False

        # Setup modules
        modules_ready = await self.setup_modules()
        if not modules_ready:
            logger.warning("Modules failed to load. Bot will not start handlers.")
        else:
            logger.info("✅ All modules loaded successfully")

        # Start bot
        if modules_ready:
            logger.info("Starting bot handlers...")
            await self.client.run_until_disconnected()
        else:
            logger.info("Modules disabled, bot will not run handlers")

        return True

    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        await self.client.disconnect()
        logger.info("✅ Bot stopped")


async def main():
    """Main entry point"""
    bot = AhliBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        await bot.stop()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())