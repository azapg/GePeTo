# GePeTo
GePeTo (_Gepeto is also fine, I don't want to always write the casing_) is a Discord Bot Agent that can interact as any other Discord user. It can use many tools such as `send()`, `reply()`, `react()`, `send_private()`, `edit()`, `delete()`, `typing()`, `image_ctx()`, and more.

## Model Configuration

GePeTo uses a flexible JSON-based configuration system for managing AI models. This allows you to easily switch between different providers and models without modifying code.

### Configuration Files

#### `providers.json`
Defines provider presets with their API endpoints and environment variable references for API keys. This makes it easy to add multiple models from the same provider.

```json
{
  "groq": {
    "api_base": "https://api.groq.com/openai/v1",
    "api_key_env": "GROQ_API_KEY"
  },
  "cerebras": {
    "api_base": "https://api.cerebras.ai/v1",
    "api_key_env": "CEREBRAS_API_KEY"
  },
  "openai": {
    "api_base": "https://api.openai.com/v1",
    "api_key_env": "OPENAI_API_KEY"
  },
  "ollama": {
    "api_base": "http://localhost:11434",
    "api_key_env": ""
  }
}
```

#### `models.json`
Defines the available models and default model. There are two supported formats:

**Recommended format** (with default model):
```json
{
  "default": "kimi-fast",
  "models": [
    {
      "label": "kimi-fast",
      "name": "openai/moonshotai/kimi-k2-instruct",
      "provider": "groq"
    },
    {
      "label": "llama-fast",
      "name": "openai/llama3.3-70b",
      "provider": "cerebras"
    },
    {
      "label": "local-model",
      "name": "ollama_chat/llama3.1:8b",
      "provider": "ollama"
    }
  ]
}
```

**Alternative format** (array only):
```json
[
  {
    "label": "kimi-fast",
    "name": "openai/moonshotai/kimi-k2-instruct",
    "provider": "groq"
  },
  {
    "label": "llama-fast",
    "name": "openai/llama3.3-70b",
    "provider": "cerebras"
  }
]
```

When using the array format, the first model in the list will be used as the default. You can also specify model configurations directly without using providers:

```json
{
  "label": "custom-model",
  "name": "openai/gpt-4o",
  "api_base": "https://api.openai.com/v1",
  "api_key_env": "OPENAI_API_KEY"
}
```

### Model Switching Commands

Use Discord commands to manage models dynamically (add ADMIN_ID env variable with your ID to use this):

- `!model list` - Show all available models
- `!model current` - Show currently active model
- `!model <model_name>` - Switch to a specific model
- `!model new <label> <model_name> --provider <provider>` - Add a new model dynamically

### Recommended Models

For best performance with GePeTo, I recommend using **Groq** or **Cerebras** as providers since inference speed is crucial for responsive Discord interactions.

**Groq** offers excellent models like:
- `openai/moonshotai/kimi-k2-instruct` - Great for mimicking natural conversation, doesn't act like a formal assistant
- `openai/llama3.3-70b` - Good general-purpose model

**Cerebras** provides ultra-fast inference:
- `openai/llama3.3-70b` - Same model as Groq but potentially faster

**Local Ollama** for privacy/offline use:
- `ollama_chat/llama3.1:8b` - Good balance of performance and resource usage
- `ollama_chat/gemma2:9b` - Efficient smaller model

### Environment Variables

Make sure to set up the required API keys in your environment:
```bash
export GROQ_API_KEY="your_groq_key_here"
export CEREBRAS_API_KEY="your_cerebras_key_here"
export OPENAI_API_KEY="your_openai_key_here"
# Add other provider keys as needed
```

The system only stores references to environment variables, never actual API keys in the configuration files.

# To-do
Gepeto is pretty slow currently, even with +2000 T/s providers like [cerebras](https://www.cerebras.ai/), which introduces many bugs and boring behaviours. Because of this, the current work involves experimenting with the CoT, tool usage and inference. 

- [ ] **Heuristics**. When Gepeto receives a message like "Gepeto, React to this message with a heart emoji", it shouldn't do fancy CoT or do much tool calling, it could just react on the first inference run and stop it there. Maybe try to induce the get the main task done on your first response in the prompt, and maybe in the future in a finetune. So, for some messages, like "hi", it should go through a "short path".
- [ ] **Async tool calling**. Gepeto shouldn't have to wait for some tools so it can keep interacting. For example, if the bot has permission to send messages in a channel, there is no reason why the `typing()` tool would fail, so essentially you are just waiting for it to succeed to keep  doing inference. What if you just add what permissions the bot has in the context, and let it decide whether to wait for a tool to return its response, or just assume it would succeed.
- [ ] **Prompt simplification**. I think DSPy is just adding a lot of stuff into the prompt, and it can confuse the model. I don't like that it is following a System-User-Assistant response, because it sometimes makes the model think it is not Gepeto but an actual assistant, or treat the chat context not as it is, and get confused with users. Kimi-K2 gets really confused with the normal [[ # HEADING ]] format, so maybe using just my own prompt with simple json would be the way to go.

Cerebras currently doesn't have Kimi-K2, which is the most intelligent, interesting and cheapest model out there, so because of that and to not rely on only one provider, fixing those issues would probably improve the experience with slower (and cheaper) providers.

**Memory todos**

_i actually need to do more research on this, maybe some server rag database would do for now_
- [ ] implement somthing like [udara's memory for ai](https://udara.io/memory-for-ai)?
- [ ] or [MIRIX](http://arxiv.org/abs/2507.07957)

**Some nice to-dos:**

- [ ] Allow Gepeto to create its own embeds. It would be like a simple AI generated UI. It could create games, display better information, behave like a task specific bot (you could technically instruct it to listen to commands like !suggest with the memory system, and make it send a suggestion to some staff channel with a nice embed).
- [ ] Ensure ALL messages are readable to Gepeto. Currently, because of messaging parsing to keep the context as small as possible, there are only a selected amount of messages it can see (normal messages, messages with stickers, and that's it iirc). Last bug I found was it not recognizing when a message was pinned, but there could be more of those, like some bot responses or user executed commands.
- [ ] Use OpenAI voice models (maybe [sesame](https://github.com/SesameAILabs/csm) in the future) to support voice chat conversations.

---
