# VoiceRep — REST API Reference

Base URL: `/api/v1`

All authenticated requests require the header:
```http
Authorization: Bearer <jwt_token>
```

---

## 1. System & Health

### `GET /api/v1/health`
Returns system component health and connectivity.

**Response (200 OK):**
```json
{
  "status": "ok",
  "database": "healthy",
  "redis": "healthy",
  "environment": "development",
  "version": "1.0.0"
}
```

---

## 2. Voice Cloning & Voice Library

### `POST /api/v1/uploads/presign`
Generates a presigned upload URL for direct storage upload.

**Query Parameters:**
- `filename`: Original filename (e.g. `sample.wav`)
- `content_type`: MIME type (default `audio/mpeg`)

**Response (200 OK):**
```json
{
  "url": "https://... or /api/v1/storage/upload/...",
  "key": "uploads/user-id/uuid.wav",
  "method": "PUT"
}
```

### `POST /api/v1/voices`
Uploads an authorized voice sample, performs acoustic quality validation, records affirmative consent, and initiates cloning.

**Request (Multipart Form Data):**
- `file`: Audio binary (MP3, WAV, M4A, WebM, MP4; max 50MB)
- `name`: String (2-100 chars)
- `language`: String (default `"en"`)
- `speaker_relationship`: `"self"` or `"authorized_representative"`
- `consent_scope`: JSON string (e.g. `{"speech_generation": true, "ai_agent": true}`)
- `terms_accepted`: Boolean (`true`)

**Response (201 Created):**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "owner_id": "11111111-1111-1111-1111-111111111111",
  "name": "Sarah Persona",
  "provider": "elevenlabs",
  "provider_voice_id": "21m00Tcm4TlvDq8ikWAM",
  "status": "ready",
  "language": "en",
  "audio_duration": 65.4,
  "quality_report": {
    "duration_seconds": 65.4,
    "format": "wav",
    "sample_rate": 44100,
    "channels": 1,
    "quality": "good",
    "speech_ratio": 0.88,
    "has_clipping": false,
    "warnings": [],
    "recommendation": "Suitable for high-quality instant voice cloning",
    "is_clonable": true
  },
  "created_at": "2026-11-03T17:00:00Z",
  "updated_at": "2026-11-03T17:00:00Z"
}
```

### `GET /api/v1/voices`
Retrieves paginated voice profiles owned by the authenticated user.

**Query Parameters:**
- `page`: Integer (default 1)
- `limit`: Integer (default 20, max 100)

**Response (200 OK):**
```json
{
  "items": [ /* array of VoiceResponse */ ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

### `GET /api/v1/voices/{voice_id}`
Retrieves single voice profile. Returns `404 Not Found` if voice does not exist or belongs to another user.

### `PATCH /api/v1/voices/{voice_id}`
Updates voice name or language.

**Request (JSON):**
```json
{
  "name": "Updated Voice Name",
  "language": "es"
}
```

### `DELETE /api/v1/voices/{voice_id}`
Deletes voice clone from provider, removes stored sample, and marks profile deleted. Returns `204 No Content`.

---

## 3. Voice Studio (Speech Generation)

### `POST /api/v1/generations`
Synthesizes speech from text using an authorized cloned voice.

**Request (JSON):**
```json
{
  "voice_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "input_text": "Welcome to VoiceRep studio narration.",
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "speed": 1.0,
    "style": 0.0
  }
}
```

**Response (201 Created):**
```json
{
  "id": "4ba95f64-5717-4562-b3fc-2c963f66afb7",
  "owner_id": "11111111-1111-1111-1111-111111111111",
  "voice_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "input_text": "Welcome to VoiceRep studio narration.",
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "speed": 1.0,
    "style": 0.0
  },
  "status": "completed",
  "audio_storage_key": "generations/user-id/uuid.mp3",
  "audio_url": "https://... or /api/v1/storage/download/...",
  "character_count": 37,
  "duration_seconds": 2.8,
  "created_at": "2026-11-03T17:05:00Z",
  "completed_at": "2026-11-03T17:05:03Z"
}
```

### `GET /api/v1/generations`
Returns paginated list of previous speech generations for user.

### `GET /api/v1/generations/{generation_id}/audio`
Returns temporary expiring playback/download URL for generated audio.

**Response (200 OK):**
```json
{
  "audio_url": "https://signed-download-url-or-local-endpoint"
}
```

### `DELETE /api/v1/generations/{generation_id}`
Deletes generation record and associated audio file from storage. Returns `204 No Content`.

---

## 4. Voice Agents (Conversational AI)

### `POST /api/v1/agents`
Creates a conversational AI voice agent configured to speak with a verified cloned voice.

**Request (JSON):**
```json
{
  "name": "Research Buddy",
  "voice_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "description": "Technical research companion",
  "system_prompt": "You are a concise research specialist.",
  "first_message": "Hello! How can I assist with your research today?",
  "language": "en"
}
```

**Response (201 Created):**
```json
{
  "id": "5ca95f64-5717-4562-b3fc-2c963f66afc8",
  "owner_id": "11111111-1111-1111-1111-111111111111",
  "voice_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Research Buddy",
  "description": "Technical research companion",
  "system_prompt": "You are a concise research specialist.",
  "first_message": "Hello! How can I assist with your research today?",
  "language": "en",
  "status": "active",
  "created_at": "2026-11-03T17:10:00Z",
  "updated_at": "2026-11-03T17:10:00Z"
}
```

### `GET /api/v1/agents`
Returns list of user's voice agents.

### `GET /api/v1/agents/{agent_id}`
Returns details of single agent.

### `PATCH /api/v1/agents/{agent_id}`
Updates agent system instructions, voice assignment, greeting, or metadata.

### `DELETE /api/v1/agents/{agent_id}`
Deletes agent and cascades associated sessions. Returns `204 No Content`.

### `POST /api/v1/agents/{agent_id}/session`
Requests an authenticated live conversational session. Verifies user ownership, validates that the assigned voice is ready, requests a single-use signed WebSocket token from ElevenLabs Conversational AI, records the session in PostgreSQL, and returns the connection payload.

**Response (200 OK):**
```json
{
  "session_id": "6da95f64-5717-4562-b3fc-2c963f66afd9",
  "signed_url": "wss://api.elevenlabs.io/v1/convai/conversation?token=signed_token_here",
  "agent_id": "shared_provider_agent_id",
  "session_config": {
    "agent_id": "shared_provider_agent_id",
    "overrides": {
      "tts": {
        "voice_id": "cloned_provider_voice_id"
      },
      "agent": {
        "prompt": {
          "prompt": "You are a concise research specialist."
        },
        "first_message": "Hello! How can I assist with your research today?",
        "language": "en"
      }
    }
  }
}
```

---

## 5. Usage & Analytics

### `GET /api/v1/usage`
Returns summary metrics for user's dashboard.

**Response (200 OK):**
```json
{
  "total_voices": 2,
  "ready_voices": 2,
  "total_generations": 14,
  "completed_generations": 14,
  "total_characters_used": 4250,
  "total_agents": 2,
  "total_sessions": 5,
  "recent_activity": [
    {
      "type": "generation",
      "id": "...",
      "status": "completed",
      "characters": 120,
      "created_at": "2026-11-03T17:15:00Z"
    }
  ]
}
```
