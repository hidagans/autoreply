"""
Help Module untuk AutoReply Bot
"""

import logging

logger = logging.getLogger(__name__)


def get_help_text(prefix: str = "!" or "/"):
    """Return help text untuk AutoReply module"""

    return f"""
<b>『 Bantuan untuk AutoReply Discussion Group 』</b>

   <b>• Perintah:</b> <code>{prefix}add_autoreply group_id</code>
   <b>• Penjelasan:</b> Tambah discussion group ke daftar auto-reply.

   <b>• Perintah:</b> <code>{prefix}del_autoreply group_id</code>
   <b>• Penjelasan:</b> Hapus group dari daftar auto-reply.

   <b>• Perintah:</b> <code>{prefix}addwording</code>
   <b>• Penjelasan:</b> Tambah wording auto-reply. Bot akan menanyakan:
      - Jumlah pengiriman
      - Kata kunci
      - Pesan auto-reply
      Link pesan otomatis dikirim ke Saved Messages setelah reply.

   <b>• Perintah:</b> <code>{prefix}delwording nomor</code>
   <b>• Penjelasan:</b> Hapus wording berdasarkan nomor.

   <b>• Perintah:</b> <code>{prefix}list_wording</code>
   <b>• Penjelasan:</b> Lihat semua wording yang aktif.
"""