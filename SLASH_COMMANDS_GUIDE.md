# Discord Slash Commands User Guide

## 🚀 New Model Management Commands

The bot now supports modern Discord slash commands for model management! These commands replace the old `!model` text commands and provide a much better user experience.

### 📋 Available Commands

#### `/model` - Main model management command
Choose from these actions:
- **📋 List Models** - View all available models with status indicators
- **🎯 Show Current** - Display the currently active model
- **🔄 Switch Model** - Change to a different model (with autocomplete)
- **➕ Add Model** - Add a new model dynamically (with provider autocomplete)

#### `/model-info <model_name>` - Get detailed model information
- View configuration details for any model
- See API endpoints and status
- Get quick switch suggestions

#### `/providers` - List available providers
- View all configured providers
- Check API key status for each provider
- See endpoint configurations

### 🎯 Key Features

#### ✨ Autocomplete
- Model names autocomplete as you type
- Provider names filter based on your input
- No more guessing or typos!

#### 🎨 Rich Visual Feedback
- **🟢 Green** - Success/Active status
- **🔵 Blue** - Information/Available options  
- **❌ Red** - Errors with helpful solutions
- **⚪ Orange** - Warnings/Missing items

#### 💡 Smart Help
- Contextual tips in every response
- Troubleshooting suggestions for errors
- Next-step guidance for workflows

#### 🔒 Admin Protection
- Only bot administrators can use model commands
- Clear permission denied messages for non-admins
- Secure model management

### 📝 Usage Examples

```
/model action:📋 List Models
→ Shows all models with current model highlighted

/model action:🔄 Switch Model model_name:kimi-fast
→ Switches to kimi-fast model with confirmation

/model action:➕ Add Model model_name:my-gpt4 display_name:GPT-4 provider:openai
→ Adds a new GPT-4 model using OpenAI provider

/model-info model_name:kimi-fast
→ Shows detailed info about the kimi-fast model

/providers
→ Lists all configured providers with API key status
```

### 🔄 Migration from Text Commands

Old text commands still work but show deprecation warnings:
- `!model list` → Use `/model` with "📋 List Models" action
- `!model current` → Use `/model` with "🎯 Show Current" action  
- `!model <name>` → Use `/model` with "🔄 Switch Model" action
- `!model new ...` → Use `/model` with "➕ Add Model" action

### 🎉 Why Slash Commands Are Better

1. **Autocomplete** - No more remembering exact model names
2. **Rich UI** - Beautiful embeds with colors and emojis
3. **Better Error Handling** - Clear messages with solutions
4. **Type Safety** - Discord validates inputs automatically
5. **Modern UX** - Follows Discord's latest UI standards
6. **Discoverability** - Easy to find and explore commands

Start using `/model` today for a much better bot experience! 🚀