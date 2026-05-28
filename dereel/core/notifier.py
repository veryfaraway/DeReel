from loguru import logger
from telegram import Bot
from telegram.request import HTTPXRequest

from dereel.core.settings import settings

MAX_LENGTH = 4096


class Notifier:

    def __init__(self) -> None:
        request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
        self._bot = Bot(token=settings.telegram_bot_token, request=request)
        self._chat_id = settings.telegram_chat_id

    async def send(self, message: str, dry_run: bool = False) -> None:
        """Telegram 메시지를 발송한다."""
        if dry_run:
            logger.info(f"[DRY-RUN] 알림 발송 스킵\n{message}")
            return

        text = message if len(message) <= MAX_LENGTH else message[:MAX_LENGTH - 3] + "..."

        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
            )
            logger.info("Telegram 알림 발송 완료")
        except Exception as e:
            logger.error(f"Telegram 알림 발송 실패 — {e}")
