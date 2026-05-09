"""
AutoReply Module - CHANNEL TARGET VERSION
Telethon + MongoDB

Concept:
- Target = CHANNEL ID
- Bot monitor discussion groups
- Hanya reply kalau forwarded post berasal dari channel target
- Forward random user tidak akan kena

Features:
- Target channel
- Multi keyword
- Multi reply
- Interactive add wording
- Auto delete after limit
- Report to Saved Messages
- Anti duplicate
- Full logging
"""

import asyncio
import logging
import time
from datetime import datetime

from telethon import events

logger = logging.getLogger(__name__)


class AutoReply:

    def __init__(self, client, db):

        self.client = client
        self.db = db

        self.userbot_id = None
        self.userbot_username = None

        # TARGET CHANNELS
        self.target_channels = []

        # WORDINGS
        self.wordings = {}

        # INTERACTIVE
        self.pending_inputs = {}

    # =====================================================
    # INIT
    # =====================================================

    async def init_userbot(self):

        me = await self.client.get_me()

        self.userbot_id = me.id
        self.userbot_username = me.username

        logger.info(
            f"[INIT] userbot={self.userbot_id}"
        )

    async def load_config(self):

        logger.info("[LOAD CONFIG]")

        channels = await self.db.autoreply_channels.find(
            {
                "userbot_id": self.userbot_id
            }
        ).to_list(None)

        self.target_channels = [
            str(c["channel_id"]).replace("-100", "")
            for c in channels
        ]

        wordings = await self.db.wordings.find(
            {
                "userbot_id": self.userbot_id
            }
        ).to_list(None)

        self.wordings[str(self.userbot_id)] = wordings

        logger.info(
            f"[CONFIG LOADED] "
            f"channels={len(channels)} "
            f"wordings={len(wordings)}"
        )

    # =====================================================
    # CHANNEL DATABASE
    # =====================================================

    async def save_channel(self, channel_input):

        try:

            # username
            if channel_input.startswith("@"):

                entity = await self.client.get_entity(
                    channel_input
                )

                channel_id = str(entity.id)

                channel_name = getattr(
                    entity,
                    "title",
                    channel_input
                )

            else:

                channel_id = (
                    str(channel_input)
                    .replace("-100", "")
                )

                entity = await self.client.get_entity(
                    int(channel_input)
                )

                channel_name = getattr(
                    entity,
                    "title",
                    channel_input
                )

            await self.db.autoreply_channels.update_one(
                {
                    "channel_id": channel_id,
                    "userbot_id": self.userbot_id
                },
                {
                    "$set": {
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                        "userbot_id": self.userbot_id,
                        "created_at": datetime.now()
                    }
                },
                upsert=True
            )

            if channel_id not in self.target_channels:
                self.target_channels.append(
                    channel_id
                )

            logger.info(
                f"[CHANNEL SAVED] {channel_id}"
            )

            return True, channel_name

        except Exception as e:

            logger.exception(e)

            return False, str(e)

    async def delete_channel(self, channel_id):

        channel_id = (
            str(channel_id)
            .replace("-100", "")
        )

        result = await self.db.autoreply_channels.delete_one(
            {
                "channel_id": channel_id,
                "userbot_id": self.userbot_id
            }
        )

        if channel_id in self.target_channels:

            self.target_channels.remove(
                channel_id
            )

        logger.info(
            f"[CHANNEL DELETED] {channel_id}"
        )

        return result.deleted_count > 0

    # =====================================================
    # WORDINGS
    # =====================================================

    async def save_wording(
        self,
        jumlah,
        keyword,
        pesan
    ):

        data = {
            "userbot_id": self.userbot_id,
            "jumlah": int(jumlah),
            "send_count": 0,
            "keyword": keyword.lower(),
            "message": pesan,
            "active": True,
            "created_at": datetime.now()
        }

        result = await self.db.wordings.insert_one(
            data
        )

        data["_id"] = result.inserted_id

        uid = str(self.userbot_id)

        if uid not in self.wordings:
            self.wordings[uid] = []

        self.wordings[uid].append(data)

        logger.info(
            f"[WORDING SAVED] "
            f"{keyword}"
        )

        return True, str(result.inserted_id)

    async def delete_wording(self, wording_id):

        result = await self.db.wordings.delete_one(
            {
                "_id": wording_id,
                "userbot_id": self.userbot_id
            }
        )

        uid = str(self.userbot_id)

        if uid in self.wordings:

            self.wordings[uid] = [
                w
                for w in self.wordings[uid]
                if str(w["_id"]) != str(wording_id)
            ]

        return result.deleted_count > 0

    # =====================================================
    # LISTS
    # =====================================================

    async def list_channels(self):

        channels = await self.db.autoreply_channels.find(
            {
                "userbot_id": self.userbot_id
            }
        ).to_list(None)

        if not channels:

            return (
                "❌ Belum ada target channel.\n\n"
                "Gunakan:\n"
                "<code>/add_channel @channel</code>"
            )

        text = "<b>📋 TARGET CHANNEL</b>\n\n"

        for i, ch in enumerate(channels, start=1):

            text += (
                f"<b>{i}.</b> "
                f"{ch.get('channel_name', 'Unknown')}\n"
                f"<code>{ch['channel_id']}</code>\n\n"
            )

        return text

    async def list_wordings(self):

        uid = str(self.userbot_id)

        wordings = self.wordings.get(uid, [])

        if not wordings:
            return "❌ Belum ada wording."

        text = "<b>📋 LIST WORDING</b>\n"

        for i, w in enumerate(wordings, start=1):

            text += (
                f"\n<b>{i}.</b>\n"
                f"🔑 Keyword: <code>{w['keyword']}</code>\n"
                f"💬 Pesan: <code>{w['message'][:50]}</code>\n"
                f"📦 Limit: {w['send_count']}/{w['jumlah']}\n"
            )

        return text

    # =====================================================
    # SETUP
    # =====================================================

    async def setup_handlers(self):

        # =================================================
        # COMMAND HANDLER
        # =================================================

        @self.client.on(events.NewMessage(outgoing=True))
        async def command_handler(event):

            text = event.raw_text.strip()

            if not text.startswith(("/", "!")):
                return

            args = text.split()

            command = args[0][1:].lower()

            # =============================================
            # ADD CHANNEL
            # =============================================

            if command == "add_channel":

                if len(args) < 2:

                    await event.reply(
                        "/add_channel @channel"
                    )

                    return

                success, result = await self.save_channel(
                    args[1]
                )

                if success:

                    await event.reply(
                        f"✅ Channel ditambahkan\n"
                        f"<code>{result}</code>"
                    )

                else:

                    await event.reply(
                        f"❌ Gagal\n{result}"
                    )

                return

            # =============================================
            # DELETE CHANNEL
            # =============================================

            if command == "del_channel":

                if len(args) < 2:

                    await event.reply(
                        "/del_channel channel_id"
                    )

                    return

                success = await self.delete_channel(
                    args[1]
                )

                if success:

                    await event.reply(
                        "✅ Channel dihapus"
                    )

                return

            # =============================================
            # LIST CHANNEL
            # =============================================

            if command == "list_channel":

                await self.load_config()

                result = await self.list_channels()

                await event.reply(result)

                return

            # =============================================
            # ADD WORDING
            # =============================================

            if command == "addwording":

                self.pending_inputs[event.sender_id] = {
                    "step": "jumlah"
                }

                await event.reply(
                    "📦 Berapa kali auto reply dikirim?"
                )

                return

            # =============================================
            # LIST WORDING
            # =============================================

            if command == "list_wording":

                await self.load_config()

                result = await self.list_wordings()

                await event.reply(result)

                return

            # =============================================
            # DELETE WORDING
            # =============================================

            if command == "delwording":

                if len(args) < 2:
                    return

                try:

                    nomor = int(args[1])

                except:

                    return

                uid = str(self.userbot_id)

                wordings = self.wordings.get(uid, [])

                if nomor < 1 or nomor > len(wordings):
                    return

                wording = wordings[nomor - 1]

                success = await self.delete_wording(
                    wording["_id"]
                )

                if success:

                    await event.reply(
                        "✅ Wording dihapus"
                    )

                return

            # =============================================
            # HELP
            # =============================================

            if command == "help":

                help_text = """
<b>📖 COMMAND LIST</b>

<b>CHANNEL TARGET</b>
<code>/add_channel @channel</code>
<code>/del_channel channel_id</code>
<code>/list_channel</code>

<b>WORDING</b>
<code>/addwording</code>
<code>/list_wording</code>
<code>/delwording nomor</code>

<b>INFO</b>
• Monitor linked discussion group
• Hanya post asli dari channel target
• Forward random user tidak kena
• Multi keyword
• Multi reply
• Auto delete setelah limit
                """

                await event.reply(
                    help_text,
                    parse_mode="html"
                )

                return

        # =================================================
        # INTERACTIVE
        # =================================================

        @self.client.on(events.NewMessage(outgoing=True))
        async def interactive_handler(event):

            sender_id = event.sender_id

            if sender_id not in self.pending_inputs:
                return

            text = event.raw_text.strip()

            if text.startswith(("/", "!")):
                return

            data = self.pending_inputs[sender_id]

            if data["step"] == "jumlah":

                if not text.isdigit():

                    await event.reply(
                        "❌ Harus angka"
                    )

                    return

                data["jumlah"] = int(text)

                data["step"] = "keyword"

                await event.reply(
                    "🔑 Masukkan keyword"
                )

                return

            if data["step"] == "keyword":

                data["keyword"] = text

                data["step"] = "message"

                await event.reply(
                    "💬 Masukkan pesan"
                )

                return

            if data["step"] == "message":

                success, result = await self.save_wording(
                    jumlah=data["jumlah"],
                    keyword=data["keyword"],
                    pesan=text
                )

                del self.pending_inputs[sender_id]

                if success:

                    await event.reply(
                        "✅ Wording berhasil ditambahkan"
                    )

                else:

                    await event.reply(
                        f"❌ {result}"
                    )

        # =================================================
        # AUTOREPLY
        # =================================================

        @self.client.on(events.NewMessage(incoming=True))
        async def autoreply_handler(event):

            start_time = time.time()

            try:

                if event.sender_id == self.userbot_id:
                    return

                if not event.is_group:
                    return

                # =========================================
                # HARUS FORWARDED POST
                # =========================================

                if not event.message.fwd_from:
                    return

                # =========================================
                # AMBIL SOURCE CHANNEL
                # =========================================

                try:

                    source_channel_id = str(
                        event.message
                        .fwd_from
                        .from_id
                        .channel_id
                    ).replace("-100", "")

                except:

                    return

                logger.info(
                    f"[SOURCE CHANNEL] "
                    f"{source_channel_id}"
                )

                # =========================================
                # CHECK TARGET CHANNEL
                # =========================================

                if (
                    source_channel_id
                    not in self.target_channels
                ):

                    logger.info(
                        "[SKIP] not target channel"
                    )

                    return

                # =========================================
                # MESSAGE
                # =========================================

                msg_text = (
                    event.raw_text or ""
                ).lower().strip()

                if not msg_text:
                    return

                logger.info(
                    f"[MESSAGE] {msg_text[:100]}"
                )

                uid = str(self.userbot_id)

                wordings = self.wordings.get(uid, [])

                matched_messages = []

                # =========================================
                # CHECK WORDINGS
                # =========================================

                for wording in wordings:

                    max_count = wording.get(
                        "jumlah",
                        0
                    )

                    sent_count = wording.get(
                        "send_count",
                        0
                    )

                    if (
                        max_count > 0
                        and
                        sent_count >= max_count
                    ):
                        continue

                    keywords = [
                        k.strip().lower()
                        for k in wording["keyword"].split(",")
                        if k.strip()
                    ]

                    matched_keyword = next(
                        (
                            kw for kw in keywords
                            if kw in msg_text
                        ),
                        None
                    )

                    if not matched_keyword:
                        continue

                    logger.info(
                        f"[MATCH] {matched_keyword}"
                    )

                    msg_key = (
                        f"{event.chat_id}:"
                        f"{event.id}:"
                        f"{wording['_id']}"
                    )

                    existing = await self.db.replied_messages.find_one(
                        {
                            "key": msg_key
                        }
                    )

                    if existing:
                        continue

                    matched_messages.append({
                        "wording": wording,
                        "msg_key": msg_key,
                        "sent_count": sent_count
                    })

                # =========================================
                # SEND REPLIES
                # =========================================

                for item in matched_messages:

                    wording = item["wording"]

                    reply = await event.reply(
                        wording["message"]
                    )

                    logger.info(
                        f"[REPLY SENT] "
                        f"{reply.id}"
                    )

                    await self.db.replied_messages.insert_one(
                        {
                            "key": item["msg_key"],
                            "created_at": datetime.now()
                        }
                    )

                    new_count = (
                        item["sent_count"] + 1
                    )

                    await self.db.wordings.update_one(
                        {
                            "_id": wording["_id"]
                        },
                        {
                            "$set": {
                                "send_count": new_count
                            }
                        }
                    )

                    wording["send_count"] = new_count

                    # =========================================
                    # SIMPAN BUKTI LINK
                    # =========================================

                    chat_id_str = str(
                        event.chat_id
                    ).replace("-100", "")

                    bukti_link = (
                        f"https://t.me/c/"
                        f"{chat_id_str}/"
                        f"{reply.id}"
                    )

                    await self.db.wording_bukti.insert_one(
                        {
                            "wording_id": str(
                                wording["_id"]
                            ),
                            "userbot_id": self.userbot_id,
                            "link": bukti_link,
                            "created_at": datetime.now()
                        }
                    )

                    # =========================================
                    # CEK APAKAH LIMIT TERCAPAI
                    # =========================================

                    max_count = wording.get("jumlah", 0)

                    if (
                        max_count > 0
                        and new_count >= max_count
                    ):

                        await self._send_completion_report(
                            wording
                        )

                    await asyncio.sleep(1)

                elapsed = round(
                    time.time() - start_time,
                    2
                )

                logger.info(
                    f"[DONE] "
                    f"replies={len(matched_messages)} "
                    f"time={elapsed}s"
                )

            except Exception as e:

                logger.exception(
                    f"[FATAL ERROR] {e}"
                )

    # =====================================================
    # COMPLETION REPORT
    # =====================================================

    async def _send_completion_report(self, wording):

        try:

            # Ambil semua bukti link dari DB
            bukti_list = await self.db.wording_bukti.find(
                {
                    "wording_id": str(wording["_id"]),
                    "userbot_id": self.userbot_id
                }
            ).sort("created_at", 1).to_list(None)

            keywords = wording.get("keyword", "")
            pesan = wording.get("message", "")
            total = wording.get("jumlah", 0)

            # Build bukti text
            bukti_text = ""
            for i, b in enumerate(bukti_list, start=1):
                bukti_text += f"{i}. {b['link']}\n"

            report = (
                f"✅ <b>WORDING SELESAI</b>\n\n"
                f"🔑 Keyword:\n"
                f"<code>{keywords}</code>\n\n"
                f"💬 Pesan:\n"
                f"<code>{pesan}</code>\n\n"
                f"📦 Total Send:\n"
                f"<code>{total}</code>\n\n"
                f"🔗 Bukti:\n"
                f"{bukti_text}\n"
                f"Thank you for use my services :D"
            )

            # Kirim ke Saved Messages (me)
            await self.client.send_message(
                "me",
                report,
                parse_mode="html"
            )

            logger.info(
                f"[REPORT SENT] wording={wording['_id']}"
            )

            # Delete wording + bukti dari DB
            await self.db.wordings.delete_one(
                {"_id": wording["_id"]}
            )

            await self.db.wording_bukti.delete_many(
                {
                    "wording_id": str(wording["_id"]),
                    "userbot_id": self.userbot_id
                }
            )

            # Hapus dari memory
            uid = str(self.userbot_id)
            if uid in self.wordings:
                self.wordings[uid] = [
                    w for w in self.wordings[uid]
                    if str(w["_id"]) != str(wording["_id"])
                ]

            logger.info(
                f"[WORDING DELETED] {wording['_id']}"
            )

        except Exception as e:

            logger.exception(
                f"[REPORT ERROR] {e}"
            )

    # =====================================================
    # START
    # =====================================================

    async def start(self):

        await self.init_userbot()

        await self.load_config()

        await self.setup_handlers()

        logger.info(
            "[STARTED] AutoReply running"
        )
