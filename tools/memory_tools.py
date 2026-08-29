from core.storage import storage

def remember_user_fact(topic: str, fact: str) -> str:
    """
    Saves a persistent memory or user fact into long-term storage so Wednesday never forgets it.
    
    Args:
        topic: Category or subject of the memory (e.g. 'user_name', 'favorite_music', 'birthday', 'project_goal')
        fact: The information to remember (e.g. 'User prefers dark mode and Python', 'User name is Tanush')
    """
    if not fact or not fact.strip():
        return "No fact specified to remember."
    
    success = storage.remember_fact(topic, fact)
    if success:
        return f"I have saved that to my memory under [{topic}]."
    return "Failed to save memory."

def recall_memories() -> str:
    """
    Retrieves all persistent memories and known facts stored about the user.
    """
    memories = storage.get_all_memories()
    if not memories:
        return "My memory is currently empty. Tell me something to remember."
    
    lines = [f"- {m['topic'].capitalize()}: {m['fact']}" for m in memories]
    return "Here is what I remember:\n" + "\n".join(lines)

def forget_memory_topic(topic: str) -> str:
    """
    Deletes memories related to a given topic.
    
    Args:
        topic: The topic or keyword of memories to delete (e.g. 'favorite_music')
    """
    count = storage.forget_fact(topic)
    if count > 0:
        return f"I have purged {count} memory entry related to '{topic}'."
    return f"I could not find any memories under '{topic}'."
