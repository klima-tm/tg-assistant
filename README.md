# tg-assistant

A personal AI assistant running on Telegram, powered by Claude (Anthropic).

Handles incoming messages on Egor's behalf when he's unavailable. 
Maintains per-user system prompt, memory, logs all conversations, and responds 
intelligently based on context about Egor and the user.

## Features
- Claude-powered responses with persistent per-user memory
- Conversation compression to manage token costs
- Message logging with timestamps
- Persona loaded from external file for easy editing

## Planned development
- Owner-only assistant workflows for adding or updating facts about people and personal interaction
- Per-user system prompts with a default prompt for new users
- A global policy layer that applies to every user
- Readable per-user records with identity, prompt, facts, and full message history
- Telegram voice input and voice reply workflows
- Progressive response delivery for better long-response UX (Telegram streaming feature)
- Calendar-aware assistant behavior (Google Calendar API)

## Product direction

The target product is not just a Telegram chatbot. It is a personal AI assistant platform with controlled multi-user behavior, persistent user context, owner-side memory management, and deployable infrastructure.

## Stack
- Python
- Claude API (Anthropic)
- Telegram Bot API (pyTelegramBotAPI)
- Runs on VPS (coming soon)

## Status
Active development — Phase 1