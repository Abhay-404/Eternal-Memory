"""
Interactive Query Interface for MY_BRAIN
Uses proper multi-turn function calling with conversation context
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.main import MyBrain
from google import genai
from src.utils.config import Config


def answer_query(brain: MyBrain, user_query: str, conversation_history: list = None):
    """Answer user query using multi-turn function calling"""

    if conversation_history is None:
        conversation_history = []

    print("\n" + "="*80)
    print("CONTEXT & TOOLS")
    print("="*80)

    # Always get primary context
    primary_context = brain.context_manager.get_context()
    print(f"\n[Primary Context]")
    print(f"  Size: {len(primary_context.split())} words")
    print(f"  Content: {primary_context[:300]}...")

    if conversation_history:
        print(f"\n[Conversation History]")
        print(f"  Exchanges: {len(conversation_history)}")
        for i, (q, a) in enumerate(conversation_history[-3:], 1):
            print(f"  {i}. Q: {q[:60]}...")
            print(f"     A: {a[:60]}...")
    else:
        print(f"\n[Conversation History]")
        print(f"  No previous conversation")

    # Define tools for Gemini
    print(f"\n[Available Tools]")
    print(f"  1. get_short_term_memory()")
    print(f"     - Everything major about user + last 14 days events")
    print(f"  2. search_long_term_memory(query, limit=5)")
    print(f"     - Search all historical memories")

    tools = [
        genai.types.Tool(
            function_declarations=[
                genai.types.FunctionDeclaration(
                    name='get_short_term_memory',
                    description='Fetch short-term memory: everything major about user + last 14 days events (~6000-7000 words). Use for recent context and patterns.',
                    parameters=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={},
                        required=[]
                    )
                ),
                genai.types.FunctionDeclaration(
                    name='search_long_term_memory',
                    description='Search historical memories. Use for specific past events/details.',
                    parameters=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            'query': genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description='Search query'
                            ),
                            'limit': genai.types.Schema(
                                type=genai.types.Type.INTEGER,
                                description='Number of results (default 5)'
                            )
                        },
                        required=['query']
                    )
                )
            ]
        )
    ]

    # Build conversation context from history
    conv_context = ""
    if conversation_history:
        conv_context = "\n\nPREVIOUS CONVERSATION:\n"
        for q, a in conversation_history[-3:]:
            conv_context += f"User: {q}\nYou: {a}\n\n"

    # Build system instruction with primary context
    system_instruction = f"""
    You are a helpful, conversational assistant with access to the user's memory. You answer about users memory.

Guidelines:
- For greetings: Be warm and brief
- For questions: Use functions if needed, then answer naturally
- For follow-ups: Reference previous conversation
- Only answer based on information present in memory. If you search for specific information and cannot find it, clearly tell the user that the information is not available in their memory rather than guessing or making assumptions.

About user :
{primary_context}\n\n
{conv_context}
You have access to:
- get_short_term_memory(): Everything major about user + last 14 days events
- search_long_term_memory(query): Search all history


"""

    # Create client and chat session
    client = genai.Client(api_key=Config.GEMINI_API_KEY)

    # Start conversation with user query
    messages = [user_query]

    config = genai.types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=5000,
        tools=tools,
        system_instruction=system_instruction
    )

    print(f"\n[User Query] {user_query}")
    print("="*80 + "\n")

    # Initial call
    response = client.models.generate_content(
        model=Config.GEMINI_MODEL,
        contents=messages,
        config=config
    )

    # Track what memory was used
    fetched_memories = []
    print("[Processing...]")

    # Handle function calls in a loop
    while response.candidates[0].content.parts:
        parts = response.candidates[0].content.parts

        # Check if there are function calls
        has_function_calls = any(hasattr(part, 'function_call') and part.function_call for part in parts)

        if not has_function_calls:
            # No more function calls, we have the final answer
            break

        # Execute function calls
        function_responses = []

        for part in parts:
            if hasattr(part, 'function_call') and part.function_call:
                function_call = part.function_call
                function_name = function_call.name
                function_args = dict(function_call.args) if function_call.args else {}

                # Execute the function
                if function_name == 'get_short_term_memory':
                    print(f"  >> Calling: get_short_term_memory()")
                    result = brain.short_term_memory.get_memory()
                    fetched_memories.append("Short-term Memory")
                    print(f"     Retrieved: {len(result.split())} words")

                elif function_name == 'search_long_term_memory':
                    query = function_args.get('query', user_query)
                    limit = function_args.get('limit', 5)

                    print(f"  >> Calling: search_long_term_memory(query='{query}', limit={limit})")
                    results = brain.hybrid_search.search(
                        query=query,
                        limit=limit,
                        vector_weight=0.7,
                        bm25_weight=0.3
                    )

                    context_pieces = []
                    for i, res in enumerate(results, 1):
                        text = res['text']
                        metadata = res['metadata']
                        score = res['combined_score']
                        date = metadata.get('date', 'Unknown')[:10]
                        result_type = metadata.get('type', 'unknown')
                        context_pieces.append(f"[Memory {i} - {result_type} from {date}, relevance: {score:.2f}]\n{text}")

                    result = "\n\n".join(context_pieces)
                    fetched_memories.append("Long-term Search")
                    print(f"     Found: {len(results)} memories")

                # Create function response
                function_responses.append(
                    genai.types.Part(
                        function_response=genai.types.FunctionResponse(
                            name=function_name,
                            response={'result': result}
                        )
                    )
                )

        # Send function results back to model
        messages.append(response.candidates[0].content)
        messages.append(genai.types.Content(parts=function_responses))

        # Continue conversation
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=messages,
            config=config
        )

    # Extract final answer
    answer = response.text

    print(f"\n[Tools Used]")
    if fetched_memories:
        for mem in fetched_memories:
            print(f"  ✓ {mem}")
    else:
        print(f"  ✓ Primary Context only (no tools called)")
    print("="*80)

    return answer, fetched_memories


def main():
    print("=" * 80)
    print("MY_BRAIN - Conversational Memory Interface")
    print("=" * 80)
    print("\nInitializing...")

    brain = MyBrain()
    total_chunks = brain.vector_store.count()
    primary = brain.context_manager.get_context()

    print(f"\n[OK] Ready!")
    print(f"  Memory: {total_chunks} chunks | Primary: {len(primary.split())} words")

    print("\n" + "=" * 80)
    print("Chat naturally - I'll remember our conversation!")
    print("Type 'exit' or 'quit' to stop")
    print("=" * 80)

    # Maintain conversation history
    conversation_history = []

    while True:
        print("\n")
        user_query = input("You: ").strip()

        if not user_query:
            continue

        if user_query.lower() in ['exit', 'quit', 'q']:
            print("\nGoodbye!")
            break

        try:
            answer, fetched_memories = answer_query(brain, user_query, conversation_history)

            print("\n" + "-" * 80)
            print(f"Assistant: {answer}")
            print("-" * 80)

            # Show what memory was used (compact)
            if fetched_memories:
                print(f"\n[Used: Primary Context + {', '.join(fetched_memories)}]")
            else:
                print(f"\n[Used: Primary Context only]")

            # Add to conversation history
            conversation_history.append((user_query, answer))

            # Keep only last 5 exchanges
            if len(conversation_history) > 5:
                conversation_history = conversation_history[-5:]

        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
