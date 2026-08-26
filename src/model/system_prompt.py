def create_system_prompt(context, question):
    """Creates a concise system prompt for OpenAI based on retrieved context and user question."""
    return f"""
    You are a helpful assistant. Answer the question based on the given context.
    Respond accurately and avoid guessing if the context doesn't provide the information.

    <context>
    {context}
    </context>

    Question: {question}

    Answer:
    """
