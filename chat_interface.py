from chat_ui import build_chat_ui  # where the common widget UI lives

def start_chat(answer_function, index):
    """
    Basic chat interface: accepts a function + index
    For use in lab 2 (basic RAG) and the first half of lab 3 (caching only)
    """
    async def send(query):
        return await answer_function(index, query)

    build_chat_ui(send)


def start_chat_advanced(chatbot):
    """
    Advanced chat interface: accepts a ChatBot instance
    For use in the second half of lab 3 (session memory + caching)
    """
    async def send(query):
        return await chatbot.answer_question_with_cache_and_history(query)

    build_chat_ui(send)