import ipywidgets as widgets
from IPython.display import display, HTML
import asyncio
from datetime import datetime
from typing import Callable, Awaitable

# ── Shared CSS injected once per session ──────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

.rag-chat-wrap * { box-sizing: border-box; font-family: 'Inter', sans-serif; }

/* Outer shell */
.rag-chat-wrap {
    width: 95%;
    max-width: 860px;
    margin: 16px auto;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    background: #ffffff;
    border: 1px solid #e5e7eb;
}

/* Header bar */
.rag-chat-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.rag-chat-header .hdr-avatar {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #e94560, #f5a623);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; line-height: 1;
}
.rag-chat-header .hdr-title   { color: #fff; font-weight: 600; font-size: 15px; }
.rag-chat-header .hdr-sub     { color: #9ca3af; font-size: 12px; margin-top: 1px; }

/* Scrollable message area */
.rag-chat-messages {
    height: 340px;
    overflow-y: auto;
    padding: 20px 16px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    gap: 14px;
}
.rag-chat-messages::-webkit-scrollbar { width: 6px; }
.rag-chat-messages::-webkit-scrollbar-track { background: transparent; }
.rag-chat-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }

/* Message rows */
.rag-msg-row {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    animation: fadeUp 0.25s ease;
}
.rag-msg-row.user { flex-direction: row-reverse; }

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Bubble avatars */
.rag-msg-icon {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; flex-shrink: 0;
}
.rag-msg-row.user .rag-msg-icon { background: #dbeafe; }
.rag-msg-row.bot  .rag-msg-icon {
    background: linear-gradient(135deg, #e94560, #f5a623);
}

/* Bubbles */
.rag-bubble {
    max-width: 75%;
    padding: 10px 14px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.55;
    word-wrap: break-word;
}
.rag-msg-row.user .rag-bubble {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: #fff;
    border-bottom-right-radius: 4px;
}
.rag-msg-row.bot .rag-bubble {
    background: #ffffff;
    color: #1f2937;
    border: 1px solid #e5e7eb;
    border-bottom-left-radius: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* Timestamp */
.rag-ts {
    font-size: 10px;
    color: #9ca3af;
    margin-top: 4px;
    text-align: right;
}
.rag-msg-row.bot .rag-ts { text-align: left; }

/* Status badge row */
.rag-status-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    padding-left: 38px;
    animation: fadeUp 0.25s ease;
}
.rag-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 500;
}
.rag-badge.cache  { background: #fef3c7; color: #92400e; }
.rag-badge.fresh  { background: #dbeafe; color: #1e40af; }
.rag-badge.memory { background: #ede9fe; color: #5b21b6; }
.rag-badge.time   { background: #f0fdf4; color: #166534; }

/* Thinking animation */
.rag-thinking span {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #9ca3af;
    margin: 0 2px;
    animation: bounce 1.2s infinite ease-in-out;
}
.rag-thinking span:nth-child(2) { animation-delay: 0.2s; }
.rag-thinking span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
    0%,80%,100% { transform: translateY(0); opacity:.5; }
    40%         { transform: translateY(-6px); opacity:1; }
}
</style>
"""

_CSS_INJECTED = False


def _inject_css():
    global _CSS_INJECTED
    if not _CSS_INJECTED:
        display(HTML(_CSS))
        _CSS_INJECTED = True


def _user_bubble(text: str, ts: str) -> str:
    return (
        '<div class="rag-msg-row user">'
        '<div class="rag-msg-icon">🧑</div>'
        '<div>'
        f'<div class="rag-bubble">{text}</div>'
        f'<div class="rag-ts">{ts}</div>'
        '</div>'
        '</div>'
    )


def _thinking_bubble() -> str:
    return (
        '<div class="rag-msg-row bot">'
        '<div class="rag-msg-icon">🤖</div>'
        '<div class="rag-bubble">'
        '<div class="rag-thinking"><span></span><span></span><span></span></div>'
        '</div>'
        '</div>'
    )


def _bot_bubble(text: str, ts: str) -> str:
    safe = str(text).replace("\n", "<br>")
    return (
        '<div class="rag-msg-row bot">'
        '<div class="rag-msg-icon">🤖</div>'
        '<div>'
        f'<div class="rag-bubble">{safe}</div>'
        f'<div class="rag-ts">{ts}</div>'
        '</div>'
        '</div>'
    )


def _status_badges(response: dict) -> str:
    badges = []
    if response.get("cached"):
        badges.append('<span class="rag-badge cache">⚡ Cache hit</span>')
    else:
        badges.append('<span class="rag-badge fresh">🧠 Fresh LLM</span>')
    if response.get("used_memory"):
        badges.append('<span class="rag-badge memory">💾 Session memory</span>')
    elapsed = response.get("elapsed", 0)
    badges.append(f'<span class="rag-badge time">⏱ {elapsed:.2f}s</span>')
    return f'<div class="rag-status-row">{"".join(badges)}</div>'


def build_chat_ui(send_callback: Callable[[str], Awaitable[str | dict]]):
    """Render a styled chat widget inside a Jupyter notebook cell."""

    _inject_css()

    # ── Header ────────────────────────────────────────────────────────────────
    header = widgets.HTML(
        '<div class="rag-chat-header">'
        '<div class="hdr-avatar">📊</div>'
        '<div>'
        '<div class="hdr-title">Chat Bot</div>'
        '<div class="hdr-sub">Ask me anything</div>'
        '</div>'
        '</div>'
    )

    # ── Message area ──────────────────────────────────────────────────────────
    messages_box = widgets.VBox(
        [],
        layout=widgets.Layout(
            height="340px",
            overflow_y="auto",
            padding="20px 16px",
            background="#f8fafc",
            display="flex",
            flex_flow="column",
            gap="14px",
        ),
    )
    messages_box.add_class("rag-chat-messages")

    def _append(html_str: str):
        messages_box.children = (*messages_box.children, widgets.HTML(html_str))

    # Welcome message
    _append(_bot_bubble("👋 Welcome! Ask me anything.", ""))

    # ── Input bar ─────────────────────────────────────────────────────────────
    question_input = widgets.Text(
        value="",
        placeholder="Ask a question about ",
        layout=widgets.Layout(flex="1", margin="0"),
    )
    submit_button = widgets.Button(
        description="Send ↵",
        layout=widgets.Layout(width="90px", height="36px"),
        style={"button_color": "#667eea", "font_weight": "600"},
    )

    input_bar = widgets.HBox(
        [question_input, submit_button],
        layout=widgets.Layout(
            width="100%",
            padding="12px 16px",
            background="#fff",
            border_top="1px solid #e5e7eb",
            flex="0 0 auto",
            align_items="center",
            gap="8px",
        ),
    )

    # ── Outer container ───────────────────────────────────────────────────────
    main_container = widgets.VBox(
        [header, messages_box, input_bar],
        layout=widgets.Layout(
            width="95%",
            max_width="860px",
            margin="16px auto",
            border="1px solid #e5e7eb",
            border_radius="16px",
            overflow="hidden",
            display="flex",
            flex_flow="column",
            box_shadow="0 8px 32px rgba(0,0,0,0.12)",
        ),
    )
    main_container.add_class("rag-chat-wrap")

    # ── Event handlers ────────────────────────────────────────────────────────
    async def handle_question(query: str):
        submit_button.disabled = True
        question_input.disabled = True

        ts = datetime.now().strftime("%H:%M")
        _append(_user_bubble(query, ts))

        # Animated thinking indicator
        thinking_widget = widgets.HTML(_thinking_bubble())
        messages_box.children = (*messages_box.children, thinking_widget)

        try:
            response = await send_callback(query)

            # Remove thinking indicator
            messages_box.children = tuple(
                c for c in messages_box.children if c is not thinking_widget
            )

            ts_reply = datetime.now().strftime("%H:%M")
            if isinstance(response, dict):
                _append(_bot_bubble(response["text"], ts_reply))
                _append(_status_badges(response))
            else:
                _append(_bot_bubble(str(response), ts_reply))

        except Exception as e:
            messages_box.children = tuple(
                c for c in messages_box.children if c is not thinking_widget
            )
            _append(_bot_bubble(f"❌ <strong>{type(e).__name__}</strong>: {e}", ts))

        finally:
            submit_button.disabled = False
            question_input.disabled = False

    def on_submit(_):
        query = question_input.value.strip()
        if query:
            question_input.value = ""
            asyncio.get_event_loop().create_task(handle_question(query))

    submit_button.on_click(on_submit)
    question_input.on_submit(lambda _: on_submit(None))

    display(main_container)