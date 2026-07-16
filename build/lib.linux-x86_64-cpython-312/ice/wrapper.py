from .proxy.policy import MemoryPolicy
from .store.base import MemoryStore
from .parser import IceStreamParser
import asyncio

class ChatProxy:
    def __init__(self, wrapper_instance):
        self._wrapper = wrapper_instance
        self._original_completions = wrapper_instance.client.chat.completions

    def __getattr__(self, name):
        # Pass through any other calls to the original completions object
        return getattr(self._original_completions, name)

    async def create(self, *args, **kwargs):
        # 1. Retrieve relevant memories
        messages = kwargs.get("messages", [])
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), "")
        retrieved_memories = await self._wrapper.memory.retrieve(last_user_message)

        # 2. Inject memories into the prompt (simplified for now)
        if retrieved_memories:
            memory_prompt = "[Recalled Memory]: " + " ".join(str(mem) for mem in retrieved_memories)
            # Find the last user message and prepend memory
            for msg in reversed(messages):
                if msg['role'] == 'user':
                    msg['content'] = memory_prompt + "\n\n" + msg['content']
                    break
        
        # 3. Forward the call to the original client
        response = await self._original_completions.create(*args, **kwargs)

        # 4. Handle streaming and non-streaming responses
        if kwargs.get("stream"):
            async def stream_generator():
                full_response = ""
                async for chunk in response:
                    # Here we would use the IceStreamParser
                    # For now, just yield the content
                    if chunk.choices:
                        content = chunk.choices[0].delta.content or ""
                        full_response += content
                        # This is where we'd parse for <reasoning> tags
                        yield chunk
                # 5. Save the full response after the stream ends
                await self._wrapper.memory.save("assistant", full_response)
            return stream_generator()
        else:
            # 5. Save the full response
            if response.choices:
                full_response = response.choices[0].message.content
                await self._wrapper.memory.save("assistant", full_response)
            return response

class ICEWrapper:
    def __init__(self, client, policy=None, connection_string=None):
        self.client = client
        self.policy = policy or MemoryPolicy.default()
        self.memory = MemoryStore(connection_string)
        self.parser = IceStreamParser()
        # Dynamically create a proxy for the 'chat' attribute
        self._chat_proxy = self._create_chat_proxy()

    def __getattr__(self, name):
        # If somebody asks for 'chat', give them our proxy
        if name == 'chat':
            return self._chat_proxy
        # Otherwise, pass through to the original client
        return getattr(self.client, name)

    def _create_chat_proxy(self):
        # This object will hold our custom 'completions' proxy
        chat_container = type('ChatContainer', (), {})()
        
        # The 'completions' attribute is now our ChatProxy instance
        chat_container.completions = ChatProxy(self)
        
        # Copy other attributes from the original client.chat over
        for attr_name in dir(self.client.chat):
            if not hasattr(chat_container, attr_name):
                setattr(chat_container, attr_name, getattr(self.client.chat, attr_name))
                
        return chat_container
