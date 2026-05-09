"""
AutoReply Module - Clean Version
Telethon + MongoDB
"""

import asyncio
import logging
import re
from datetime import datetime
import time

from telethon import events

logger = logging.getLogger(__name__)


class AutoReply:

    def __init__(self, client, db):
        self.client = client
        self.db = db

        self.userbot_id = None
        self.userbot_username = None

        # cache
        self.autoreply_groups = []
        self.wordings = {}

        # interactive session
        self.pending_inputs = {}

    # =========================================================
    # INIT
    # =========================================================

    async def init_userbot(self):
        me = await self.client.get_me()

        self.userbot_id = me.id
        self.userbot_username = me.username

        logger.info(
            f"Userbot initialized: {self.userbot_id}"
        )

    async def load_config(self):

        groups = await self.db.autoreply_groups.find(
            {
                "userbot_id": self.userbot_id
            }
        ).to_list(None)

        self.autoreply_groups = [
            str(g["group_id"])
            for g in groups
        ]

        wordings = await self.db.wordings.find(
            {
                "userbot_id": self.userbot_id
            }
        ).to_list(None)

        self.wordings[str(self.userbot_id)] = wordings

        logger.info(
            f"Loaded {len(wordings)} wordings"
        )

    async def list_autoreply_groups(self):

        if not self.autoreply_groups:

            return (
                "❌ Belum ada target autoreply.\n\n"
                "Gunakan:\n"
                "<code>/add_autoreply -100xxxxxxxx</code>"
            )

        text = "<b>📋 TARGET AUTOREPLY</b>\n\n"

        for i, group_id in enumerate(
            self.autoreply_groups,
            start=1
        ):

            group_name = "Unknown"

            try:

                entity = await self.client.get_entity(
                    int(group_id)
                )

                group_name = getattr(
                    entity,
                    "title",
                    "Unknown"
                )

            except:
                pass

            text += (
                f"<b>{i}.</b> "
                f"{group_name}\n"
                f"<code>{group_id}</code>\n\n"
            )

        text += (
            f"📦 Total Target: "
            f"<b>{len(self.autoreply_groups)}</b>"
        )

        return text

    # =========================================================
    # DATABASE
    # =========================================================

    async def save_group(self, group_id):

        await self.db.autoreply_groups.update_one(
            {
                "group_id": str(group_id),
                "userbot_id": self.userbot_id
            },
            {
                "$set": {
                    "group_id": str(group_id),
                    "userbot_id": self.userbot_id,
                    "created_at": datetime.now()
                }
            },
            upsert=True
        )

        if str(group_id) not in self.autoreply_groups:
            self.autoreply_groups.append(str(group_id))

        return True

    async def delete_group(self, group_id):

        result = await self.db.autoreply_groups.delete_one(
            {
                "group_id": str(group_id),
                "userbot_id": self.userbot_id
            }
        )

        if str(group_id) in self.autoreply_groups:
            self.autoreply_groups.remove(str(group_id))

        return result.deleted_count > 0

    async def save_wording(
        self,
        jumlah,
        keyword,
        pesan,
        group_id="all"
    ):

        data = {
            "userbot_id": self.userbot_id,
            "jumlah": jumlah,
            "send_count": 0,
            "keyword": keyword,
            "message": pesan,
            "group_id": str(group_id),
            "active": True,
            "created_at": datetime.now()
        }

        result = await self.db.wordings.insert_one(data)

        data["_id"] = result.inserted_id

        uid = str(self.userbot_id)

        if uid not in self.wordings:
            self.wordings[uid] = []

        self.wordings[uid].append(data)

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

    async def list_wordings(self):

        uid = str(self.userbot_id)

        if uid not in self.wordings:
            return "Belum ada wording."

        wordings = self.wordings[uid]

        if not wordings:
            return "Belum ada wording."

        text = "<b>📋 LIST WORDING</b>\n"

        for i, w in enumerate(wordings, start=1):

            text += (
                f"\n<b>{i}.</b>\n"
                f"🔑 Keyword: <code>{w['keyword']}</code>\n"
                f"💬 Pesan: <code>{w['message'][:50]}</code>\n"
                f"📦 Limit: {w['send_count']}/{w['jumlah']}\n"
            )

        return text

    # =========================================================
    # HANDLERS
    # =========================================================

    async def setup_handlers(self):

        # =====================================================
        # COMMAND HANDLER
        # =====================================================

        @self.client.on(events.NewMessage(outgoing=True))
        async def command_handler(event):

            text = event.raw_text

            if not text.startswith(("/", "!")):
                return

            args = text.split()

            command = args[0][1:].lower()

            # =========================================
            # ADD GROUP
            # =========================================

            if command == "add_autoreply":

                if len(args) < 2:
                    await event.reply(
                        "Gunakan:\n"
                        "/add_autoreply -100xxxxxxxx"
                    )
                    return

                group_id = args[1]

                success = await self.save_group(group_id)

                if success:
                    await event.reply(
                        f"✅ Group ditambahkan\n"
                        f"<code>{group_id}</code>"
                    )

                return

            # =========================================
            # DELETE GROUP
            # =========================================

            if command == "del_autoreply":

                if len(args) < 2:
                    await event.reply(
                        "Gunakan:\n"
                        "/del_autoreply -100xxxxxxxx"
                    )
                    return

                group_id = args[1]

                success = await self.delete_group(group_id)

                if success:
                    await event.reply(
                        f"✅ Group dihapus\n"
                        f"<code>{group_id}</code>"
                    )

                return

            # =========================================
            # LIST WORDING
            # =========================================

            if command == "list_wording":

                result = await self.list_wordings()

                await event.reply(result)

                return

            # =========================================
            # DELETE WORDING
            # =========================================

            if command == "delwording":

                if len(args) < 2:
                    await event.reply(
                        "/delwording nomor"
                    )
                    return

                try:
                    nomor = int(args[1])

                except:
                    await event.reply(
                        "Nomor harus angka"
                    )
                    return

                uid = str(self.userbot_id)

                if uid not in self.wordings:
                    await event.reply(
                        "Belum ada wording"
                    )
                    return

                wordings = self.wordings[uid]

                if nomor < 1 or nomor > len(wordings):
                    await event.reply(
                        "Nomor tidak valid"
                    )
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

            # =========================================
            # ADD WORDING INTERACTIVE
            # =========================================

            if command == "addwording":

                self.pending_inputs[event.sender_id] = {
                    "step": "jumlah"
                }

                await event.reply(
                    "📦 Berapa kali auto reply dikirim?\n\n"
                    "Ketik angka."
                )

                return

            # =========================================
            # LIST AUTOREPLY GROUPS
            # =========================================

            if command == "list_autoreply":

                result = await self.list_autoreply_groups()

                await event.reply(result)

                return

            # =========================================
            # HELP
            # =========================================

            if command == "help":

                help_text = """
<b>📖 COMMAND LIST</b>

<code>/add_autoreply group_id</code>
<code>/del_autoreply group_id</code>
<code>/list_autoreply</code>

<code>/addwording</code>
<code>/delwording nomor</code>

<code>/list_wording</code>
                """

                await event.reply(help_text)

                return

        # =====================================================
        # INTERACTIVE HANDLER
        # =====================================================

        @self.client.on(events.NewMessage(outgoing=True))
        async def interactive_handler(event):

            sender_id = event.sender_id

            # gak ada session interactive
            if sender_id not in self.pending_inputs:
                return

            text = event.raw_text.strip()

            # =========================================
            # FIX BUG:
            # jangan proses command
            # =========================================

            if text.startswith("/") or text.startswith("!"):
                return

            data = self.pending_inputs[sender_id]

            # cancel
            if text.lower() == "cancel":

                del self.pending_inputs[sender_id]

                await event.reply(
                    "❌ Dibatalkan"
                )

                return

            # =========================================
            # STEP 1
            # =========================================

            if data["step"] == "jumlah":

                if not text.isdigit():

                    await event.reply(
                        "❌ Harus angka"
                    )

                    return

                data["jumlah"] = int(text)

                data["step"] = "keyword"

                await event.reply(
                    "🔑 Masukkan keyword\n\n"
                    "Contoh:\n"
                    "<code>jual,beli,promo</code>"
                )

                return

            # =========================================
            # STEP 2
            # =========================================

            if data["step"] == "keyword":

                data["keyword"] = text

                data["step"] = "message"

                await event.reply(
                    "💬 Masukkan pesan auto reply"
                )

                return

            # =========================================
            # STEP 3
            # =========================================

            if data["step"] == "message":

                data["message"] = text

                success, result = await self.save_wording(
                    jumlah=data["jumlah"],
                    keyword=data["keyword"],
                    pesan=data["message"],
                    group_id="all"
                )

                del self.pending_inputs[sender_id]

                if success:

                    await event.reply(
                        "✅ Wording berhasil ditambahkan\n\n"
                        f"📦 Jumlah: {data['jumlah']}\n"
                        f"🔑 Keyword: {data['keyword']}\n"
                        f"💬 Pesan: {data['message']}"
                    )

                else:

                    await event.reply(
                        f"❌ Gagal\n{result}"
                    )

                return

        # =====================================================
        # AUTOREPLY HANDLER
        # =====================================================
        # =====================================================
        # AUTOREPLY HANDLER
        # =====================================================

        @self.client.on(events.NewMessage(incoming=True))
        async def autoreply_handler(event):

            start_time = time.time()

            try:

                logger.info(
                    f"[NEW EVENT] "
                    f"chat={event.chat_id} "
                    f"msg_id={event.id}"
                )

                # =====================================
                # SKIP SELF
                # =====================================

                if event.sender_id == self.userbot_id:

                    logger.info(
                        "[SKIP] self message"
                    )

                    return

                # =====================================
                # ONLY GROUP
                # =====================================

                if not event.is_group:

                    logger.info(
                        "[SKIP] not group"
                    )

                    return

                chat_id = str(event.chat_id)

                # =====================================
                # CHECK MONITORED GROUP
                # =====================================

                if chat_id not in self.autoreply_groups:

                    logger.info(
                        f"[SKIP] group not monitored: {chat_id}"
                    )

                    return

                logger.info(
                    f"[GROUP MATCH] {chat_id}"
                )

                # =====================================
                # MUST FORWARDED POST
                # =====================================

                if not event.message.fwd_from:

                    logger.info(
                        "[SKIP] not forwarded channel post"
                    )

                    return

                logger.info(
                    "[FORWARDED POST DETECTED]"
                )

                # =====================================
                # MESSAGE TEXT
                # =====================================

                msg_text = (
                    event.raw_text or ""
                ).lower().strip()

                if not msg_text:

                    logger.info(
                        "[SKIP] empty text"
                    )

                    return

                logger.info(
                    f"[MESSAGE] {msg_text[:200]}"
                )

                uid = str(self.userbot_id)

                wordings = self.wordings.get(uid, [])

                logger.info(
                    f"[WORDINGS] loaded={len(wordings)}"
                )

                matched_messages = []

                # =====================================
                # LOOP WORDINGS
                # =====================================

                for wording in wordings:

                    keyword_raw = wording.get(
                        "keyword",
                        ""
                    )

                    logger.info(
                        f"[CHECK] keyword={keyword_raw}"
                    )

                    if not wording.get("active", True):

                        logger.info(
                            "[SKIP] inactive wording"
                        )

                        continue

                    max_count = wording.get(
                        "jumlah",
                        0
                    )

                    sent_count = wording.get(
                        "send_count",
                        0
                    )

                    if (
                        max_count > 0 and
                        sent_count >= max_count
                    ):

                        logger.info(
                            f"[SKIP] limit reached "
                            f"{sent_count}/{max_count}"
                        )

                        continue

                    # =====================================
                    # GROUP FILTER
                    # =====================================

                    if (
                        wording["group_id"] != "all"
                        and
                        str(wording["group_id"]) != chat_id
                    ):

                        logger.info(
                            "[SKIP] group filter mismatch"
                        )

                        continue

                    # =====================================
                    # KEYWORDS
                    # =====================================

                    keywords = [
                        k.strip().lower()
                        for k in keyword_raw.split(",")
                        if k.strip()
                    ]

                    logger.info(
                        f"[KEYWORDS] {keywords}"
                    )

                    # =====================================
                    # SIMPLE MATCH
                    # =====================================

                    matched_keyword = next(
                        (
                            kw for kw in keywords
                            if kw in msg_text
                        ),
                        None
                    )

                    if not matched_keyword:

                        logger.info(
                            f"[NO MATCH] {keywords}"
                        )

                        continue

                    logger.info(
                        f"[MATCH FOUND] {matched_keyword}"
                    )

                    # =====================================
                    # DUPLICATE CHECK
                    # =====================================

                    msg_key = (
                        f"{chat_id}:"
                        f"{event.id}:"
                        f"{wording['_id']}"
                    )

                    existing = await self.db.replied_messages.find_one(
                        {
                            "key": msg_key
                        }
                    )

                    if existing:

                        logger.info(
                            "[SKIP] duplicate reply"
                        )

                        continue

                    matched_messages.append({
                        "wording": wording,
                        "message": wording["message"],
                        "msg_key": msg_key,
                        "sent_count": sent_count,
                        "chat_id": chat_id
                    })

                # =====================================
                # NO MATCH
                # =====================================

                if not matched_messages:

                    logger.info(
                        "[RESULT] no matched messages"
                    )

                    return

                logger.info(
                    f"[RESULT] matched={len(matched_messages)}"
                )

                # =====================================
                # SEND REPLIES
                # =====================================

                for item in matched_messages:

                    wording = item["wording"]

                    logger.info(
                        f"[SENDING] "
                        f"{wording['message'][:100]}"
                    )

                    reply = await event.reply(
                        item["message"]
                    )

                    # =====================================
                    # GENERATE LINK
                    # =====================================

                    reply_chat_id = str(event.chat_id).replace("-100", "")

                    reply_link = (
                        f"https://t.me/c/"
                        f"{reply_chat_id}/"
                        f"{reply.id}"
                    )

                    await self.db.reply_logs.insert_one(
                        {
                            "wording_id": str(wording["_id"]),
                            "keyword": wording["keyword"],
                            "message": wording["message"],
                            "link": reply_link,
                            "created_at": datetime.now()
                        }
                    )

                    logger.info(
                        f"[LINK] {reply_link}"
                    )

                    logger.info(
                        f"[SENT] reply_id={reply.id}"
                    )

                    # duplicate tracker
                    await self.db.replied_messages.insert_one(
                        {
                            "key": item["msg_key"],
                            "created_at": datetime.now()
                        }
                    )

                    # increment counter
                    new_count = item["sent_count"] + 1

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
                    # =====================================
                    # LIMIT REACHED
                    # =====================================

                    if (
                        wording["jumlah"] > 0
                        and
                        new_count >= wording["jumlah"]
                    ):

                        logger.info(
                            f"[LIMIT REACHED] "
                            f"{wording['keyword']}"
                        )

                        # =====================================
                        # AMBIL SEMUA BUKTI
                        # =====================================

                        logs = await self.db.reply_logs.find(
                            {
                                "wording_id": str(wording["_id"])
                            }
                        ).to_list(None)

                        bukti_links = []

                        for i, log in enumerate(logs, start=1):

                            bukti_links.append(
                                f"{i}. {log['link']}"
                            )

                        bukti_text = "\n".join(
                            bukti_links
                        )

                        # =====================================
                        # KIRIM KE SAVED MESSAGES
                        # =====================================

                        report_text = (
                            f"✅ <b>WORDING SELESAI</b>\n\n"

                            f"🔑 Keyword:\n"
                            f"<code>{wording['keyword']}</code>\n\n"

                            f"💬 Pesan:\n"
                            f"<code>{wording['message']}</code>\n\n"

                            f"📦 Total Send:\n"
                            f"<code>{new_count}</code>\n\n"

                            f"🔗 Bukti:\n"
                            f"{bukti_text}\n\n"

                            f"Thank you for use my services :D"
                        )

                        await self.client.send_message(
                            "me",
                            report_text,
                            link_preview=False
                        )

                        # =====================================
                        # DELETE WORDING
                        # =====================================

                        await self.db.wordings.delete_one(
                            {
                                "_id": wording["_id"]
                            }
                        )

                        uid = str(self.userbot_id)

                        if uid in self.wordings:

                            self.wordings[uid] = [
                                w
                                for w in self.wordings[uid]
                                if str(w["_id"])
                                != str(wording["_id"])
                            ]

                        logger.info(
                            f"[WORDING DELETED] "
                            f"{wording['keyword']}"
                        )

                    await asyncio.sleep(1)

                elapsed = round(
                    time.time() - start_time,
                    2
                )

                logger.info(
                    f"[DONE] "
                    f"sent={len(matched_messages)} "
                    f"time={elapsed}s"
                )

            except Exception as e:

                logger.exception(
                    f"[FATAL ERROR] {e}"
                )

                # =====================================
                # UPDATE DATABASE
                # =====================================

                for item in matched_messages:

                    wording = item["wording"]

                    # save anti duplicate
                    await self.db.replied_messages.insert_one(
                        {
                            "key": item["msg_key"],
                            "created_at": datetime.now()
                        }
                    )

                    # increment send count
                    new_count = item["sent_count"] + 1

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

                logger.info(
                    f"Sent {len(matched_messages)} replies "
                    f"to discussion thread"
                )

            except Exception as e:

                logger.error(
                    f"AutoReply Error: {e}"
                )

    # =========================================================
    # START
    # =========================================================

    async def start(self):

        await self.init_userbot()

        await self.load_config()

        await self.setup_handlers()

        logger.info(
            "AutoReply started successfully"
        )
