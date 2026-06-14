#!/usr/bin/env python3
"""
paperclip_telegram_bot.py  (MVP, local-machine demo)

Text the bot a research question. It runs one headless Claude Code pass that
executes the Paperclip pipeline and sends the resulting digest .md back.

Setup (one time, from your shell):
    mkdir -p ~/paperclip-test/bot
    # put paperclip_telegram_bot.py, telegram_orchestration_prompt.md,
    # and a clean copy of the latest paperclip docs into ~/paperclip-test/bot/
    python3 -m venv ~/paperclip-test/bot/.venv
    ~/paperclip-test/bot/.venv/bin/python -m pip install "python-telegram-bot>=20"

Run:
    export TELEGRAM_BOT_TOKEN="<token from @BotFather>"
    export ALLOWED_CHAT_IDS="<your numeric chat id>"   # comma-separated if more than one
    ~/paperclip-test/bot/.venv/bin/python ~/paperclip-test/bot/paperclip_telegram_bot.py

To find your chat id: message the bot once, the console prints the chat id of
any sender (and unauthorized senders are refused), so you can read it off and
put it in ALLOWED_CHAT_IDS.

Assumptions (edit at the top if wrong):
  - Claude Code is installed, authed, and on PATH as `claude`.
  - paperclip is on PATH.
  - Bot files and a clean copy of the latest paperclip docs live in BOT_DIR.
  - One run at a time. Demo scope is capped at MAX_SQS sub-questions.
"""

import os
import re
import glob
import asyncio
import subprocess

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# ---------------- config ----------------
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_CHAT_IDS = {int(x) for x in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip()}
BOT_DIR = os.path.expanduser("~/paperclip-test/bot")               # bot files + a clean copy of the latest paperclip docs live here
ORCH_PROMPT = os.path.join(BOT_DIR, "telegram_orchestration_prompt.md")
RUNS_DIR = os.path.join(BOT_DIR, "runs")                            # per-question digest folders go here
CLAUDE = "claude"
MAX_SQS = 6
RUN_TIMEOUT_S = 90 * 60  # hard ceiling so a stalled run cannot hang forever

BUSY = False  # simple one-at-a-time guard; checked on the event loop, no threading needed
PENDING_QUESTION = {}  # chat_id -> question text awaiting a slug (two-step intake)


def normalize_slug(text: str) -> str:
    """Sanitize a user-provided slug for use as a directory/file name."""
    s = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return s[:40] if s else "run"


def run_claude_blocking(question: str, slug: str, workdir: str) -> str | None:
    """Runs the headless Claude Code pass. Returns the output file path or None.
    This blocks, so it is called via asyncio.to_thread to keep the bot responsive."""
    os.makedirs(workdir, exist_ok=True)
    with open(os.path.join(workdir, "question.txt"), "w", encoding="utf-8") as f:
        f.write(question)

    prompt = (
        f"Read {ORCH_PROMPT} and follow it exactly. "
        f"The research question is in the file {workdir}/question.txt. "
        f"A clean copy of the current Paperclip docs is in {BOT_DIR}; consult it for exact command syntax before using paperclip commands. "
        f'Use slug "{slug}", working directory {workdir}, and cap at {MAX_SQS} sub-questions. '
        f"Write the finished digest to {workdir}/{slug}_filled.md and then stop."
    )
    try:
        subprocess.run(
            [CLAUDE, "-p", prompt, "--dangerously-skip-permissions"],
            cwd=workdir,
            timeout=RUN_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT"

    out = os.path.join(workdir, f"{slug}_filled.md")
    if os.path.exists(out):
        return out
    mds = sorted(glob.glob(os.path.join(workdir, "*.md")), key=os.path.getmtime)
    return mds[-1] if mds else None


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global BUSY
    chat_id = update.effective_chat.id
    print(f"message from chat_id={chat_id}")  # so you can read off your id

    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        await update.message.reply_text("Not authorized for this bot.")
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    if BUSY:
        await update.message.reply_text("A run is already in progress. One at a time for now, try again when it finishes.")
        return

    # Two-step intake: first message is the question, second is the slug.
    if chat_id not in PENDING_QUESTION:
        PENDING_QUESTION[chat_id] = text
        await update.message.reply_text(
            "Got it. Now reply with a short slug for this run (lowercase, underscored), "
            "for example dry_eye_autoimmune. It names the run folder and the output files."
        )
        return

    # A question is already pending for this chat, so this message is the slug.
    question = PENDING_QUESTION.pop(chat_id)
    slug = normalize_slug(text)
    workdir = os.path.join(RUNS_DIR, slug)
    BUSY = True
    await update.message.reply_text(
        f"Slug: {slug}. Running the v1 pipeline now (Phase 0 scoping, per-sub-question work, "
        f"verification anchors). This takes a while; I'll send the digest when it's done."
    )
    try:
        result = await asyncio.to_thread(run_claude_blocking, question, slug, workdir)
        if result == "TIMEOUT":
            await update.message.reply_text("The run hit the 90-minute ceiling and was stopped. Check the working directory.")
        elif result and os.path.exists(result):
            with open(result, "rb") as fh:
                await context.bot.send_document(chat_id=chat_id, document=fh, filename=os.path.basename(result))
            await update.message.reply_text("Done. Digest attached above.")
        else:
            await update.message.reply_text("Run finished but I couldn't find an output file. Check the working directory.")
    except Exception as e:
        await update.message.reply_text(f"Run failed: {e}")
    finally:
        BUSY = False


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("Bot running. Send it a research question.")
    app.run_polling()


if __name__ == "__main__":
    main()
