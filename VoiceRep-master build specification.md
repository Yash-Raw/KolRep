# VoiceRep — AI Voice Replication Platform
## Master Product & Engineering Implementation Specification

You are Gemini 3.8 Flash acting as a senior full-stack software engineer, software architect, Python backend engineer, frontend developer, and integration engineer.

Your task is to build a complete, functional, production-minded MVP of **VoiceRep**, an AI voice replication platform.

Do not merely generate a project plan, mockup, boilerplate, or code snippets. Inspect the existing repository, make implementation decisions, write working code, run tests, fix errors, and deliver a functional application.

---

# 1. Product vision

VoiceRep allows users to upload an authorized voice recording, create a reusable AI voice clone, and use that voice for two purposes:

### Module A: Voice Studio

Users can:

- Upload a voice recording.
- Create a reusable voice profile.
- Preview the generated voice.
- Enter text and generate speech using that voice.
- Adjust supported speech settings.
- Listen to generated audio.
- Download generated audio.
- View previous generations.

### Module B: Voice Agents

Users can:

- Create an AI voice agent.
- Select one of their saved cloned voices.
- Give the agent a name and personality.
- Write its system instructions.
- Configure its greeting and language.
- Talk to it through a microphone.
- Receive spoken responses in their selected cloned voice.
- View conversation text.
- End conversations.

### Core product principle

A user should upload a voice recording only once.

The resulting voice profile should be reusable by both Voice Studio and Voice Agents.

Do not create separate cloning systems for these two modules.

---

# 2. Product boundaries

This is an MVP. Prioritize working functionality over unnecessary complexity.

### Build now

1. Authentication.
2. Audio upload.
3. Audio quality validation.
4. Voice cloning.
5. Reusable voice library.
6. Text-to-speech generation.
7. Audio preview and downloads.
8. AI voice agent creation.
9. Real-time voice conversations.
10. Basic usage tracking.
11. Voice deletion and data management.

### Do not build in the first version

- Train an independent voice cloning model.
- GPU infrastructure.
- Custom model fine-tuning.
- A public voice marketplace.
- Social-media scraping or automatic Instagram downloads.
- Mobile applications.
- Phone calling or Twilio integration.
- Complex subscription and payment systems.
- Multi-provider orchestration.
- Advanced team collaboration.

Keep the architecture extensible, but implement only what is required for this MVP.

---

# 3. Technology stack

Use the following stack unless an existing repository constraint makes a change necessary.

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript |
| Styling | Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic |
| Voice cloning | ElevenLabs Instant Voice Cloning API |
| Text-to-speech | ElevenLabs TTS API |
| Voice agents | ElevenLabs Conversational AI |
| Audio processing | FFmpeg, ffprobe |
| Storage | Cloudflare R2 |
| Background jobs | Redis + ARQ |
| Frontend validation | Zod |
| Backend validation | Pydantic |
| Testing | Pytest, Vitest, Playwright |
| Local environment | Docker Compose |

Use current stable compatible dependency versions. Verify the current official documentation before choosing package versions or API methods.

Do not blindly use outdated tutorials or deprecated SDK methods.

---

# 4. System architecture

Implement a modular monolithic architecture.

Do not create microservices.

The application should contain these logical components:

```text
                   VoiceRep
                        |
                 Next.js Frontend
                        |
                   FastAPI API
                        |
         +--------------+--------------+
         |              |              |
    Voice Service   Agent Service   User Service
         |              |              |
         +--------------+--------------+
                        |
                Provider Layer
                        |
                   ElevenLabs
              /          |          \
        Voice Clone     TTS       ConvAI
              \          |          /
               Shared Voice Library
                        |
         +--------------+--------------+
         |              |              |
     PostgreSQL       Redis          R2
```

### Architecture responsibilities

**Frontend**

Responsible for:

- User interactions.
- Audio uploads.
- Voice library.
- Text-to-speech generation forms.
- Agent configuration.
- Microphone recording.
- Real-time agent interface.

**FastAPI**

Responsible for:

- Authentication verification.
- Ownership validation.
- API endpoints.
- Audio validation.
- Provider communication.
- Background task management.
- Database operations.
- Signed URL generation.
- Usage tracking.

**Provider layer**

Responsible for all ElevenLabs communication.

Do not call ElevenLabs directly from frontend code.

**Database**

Stores voice metadata, user information, agents, generations and consent records.

**Object storage**

Stores private source audio temporarily and generated audio permanently until the user deletes it.

---

# 5. Voice cloning implementation

This is the foundation of the entire application.

Implement this module before anything else.

## 5.1 Audio upload

Allow these formats:

- MP3
- WAV
- M4A
- WebM
- MP4

Use FFmpeg to extract audio from video files.

Create a drag-and-drop upload interface.

Display:

- Filename.
- File size.
- Audio duration.
- Upload progress.
- Processing status.
- Validation errors.

Set configurable application limits, initially:

- Maximum upload size: 50 MB.
- Maximum recording duration: 5 minutes.
- Prefer recordings between 60 and 120 seconds.
- Require sufficient actual speech before cloning.

These are application defaults, not claims about provider-enforced limits.

## 5.2 Audio validation service

Create:

`backend/app/services/audio_service.py`

Implement:

1. File signature and actual format validation.
2. Duration extraction using ffprobe.
3. Sample rate detection.
4. Channel detection.
5. Silence detection.
6. Clipping detection.
7. Basic speech-to-silence ratio estimation.
8. Audio conversion where necessary.
9. Upload rejection for unsupported or corrupted files.

Generate an audio quality report.

Example:

```json
{
  "duration_seconds": 87,
  "format": "mp3",
  "sample_rate": 44100,
  "channels": 1,
  "quality": "good",
  "warnings": [],
  "recommendation": "Suitable for instant voice cloning"
}
```

This is an illustrative response schema, not an API response from ElevenLabs.

Do not claim that simple audio checks can reliably identify multiple speakers or prove ownership.

Do not automatically apply aggressive noise reduction. It can reduce voice quality when the original sample is already clean.

## 5.3 Voice cloning provider

Create:

`backend/app/providers/elevenlabs.py`

Implement a provider adapter.

Use the official Instant Voice Cloning endpoint:

`POST https://api.elevenlabs.io/v1/voices/add`

It accepts multipart form data:

- `name`
- `files[]`
- Optional `description`
- Optional `labels`
- Optional `remove_background_noise`

Handle the provider response:

```json
{
  "voice_id": "provider_voice_id",
  "requires_verification": false
}
```

The returned voice ID must be saved in PostgreSQL.

Never expose the provider API key to the browser.

### Voice lifecycle

Implement these statuses:

```text
upload_pending
validating
awaiting_consent
cloning
verification_required
ready
failed
deleting
deleted
```

Only `ready` voices can be selected for speech generation or agents.

When `requires_verification` is true, move the voice into `verification_required`. Do not pretend that the voice is ready. Implement the applicable documented verification workflow or clearly report that provider verification is required.

## 5.4 Reusable voice library

Every user should have a private Voice Library.

Each voice record must contain:

- Internal UUID.
- Owner user ID.
- Voice name.
- Provider name.
- Provider voice ID.
- Status.
- Creation timestamp.
- Language, if known.
- Audio duration.
- Quality report.
- Consent status.

Do not expose another user's voice profile.

Allow users to:

- Rename their voices.
- Preview their voices.
- Delete voices.
- See their cloning status.
- See quality warnings.

When a user deletes a voice, call the provider's voice deletion endpoint and then clean up related database references and files.

Handle partial deletion failures and avoid leaving a misleading `deleted` status.

---

# 6. Voice Studio implementation

Create a dedicated Voice Studio.

## 6.1 User interface

The page should contain:

**Voice selector**

Display saved and ready voice profiles.

**Text editor**

A large text box for users to enter narration.

**Voice settings**

Expose supported controls:

- Stability.
- Similarity boost.
- Speaking speed.
- Style, where supported.

Keep reasonable defaults.

Do not expose settings that the selected model does not support.

**Generate button**

Starts speech generation and displays progress.

**Audio player**

Allows playback, pause, seek and download.

**Generation history**

Displays previous generations, associated voices, creation dates and statuses.

## 6.2 Provider integration

Use ElevenLabs text-to-speech streaming:

`POST /v1/text-to-speech/{voice_id}/stream`

Send:

- Text.
- Selected model ID.
- Voice settings.
- Supported output format.

Use the current official API documentation to select an appropriate model.

Prefer a quality-oriented model for long-form narration and a low-latency model for interactive use.

The provider endpoint returns an audio stream.

Store completed audio in Cloudflare R2.

Return a short-lived signed URL to the frontend for playback and download.

## 6.3 Generation lifecycle

Implement:

```text
queued
processing
completed
failed
```

Save:

- User ID.
- Voice ID.
- Text.
- Settings.
- Character count.
- Status.
- Audio storage key.
- Provider request ID, if available.
- Error information.
- Timestamp.

Prevent duplicate generation jobs caused by accidental double-clicks.

Enforce a configurable text-length limit.

Never silently return fake audio when the provider fails.

---

# 7. Voice Agents implementation

This is the second major product module.

The goal is to let users create conversational AI agents using their saved voices.

## 7.1 Architecture decision

For the MVP, use ElevenLabs Conversational AI instead of manually implementing an entire speech-to-text → LLM → TTS pipeline.

ElevenLabs already provides:

- Speech recognition.
- Language model orchestration.
- Text-to-speech.
- Turn detection.
- Audio input/output.
- WebSocket-based conversations.

This avoids unnecessary real-time audio infrastructure during the first release.

Use one shared, private ElevenLabs agent template for the platform.

Each application's agent record should store its own:

- Voice ID.
- Agent name.
- System prompt.
- Greeting.
- Language.
- Configuration.

Apply the relevant per-session overrides when opening a conversation.

Do not create a separate ElevenLabs agent for every application user unless a technical limitation makes the shared configuration approach impossible.

## 7.2 One-time provider setup

Create a shared ElevenLabs Conversational AI agent in the provider account.

Configure:

- Default LLM.
- Speech recognition.
- TTS model.
- Default system prompt.
- Default greeting.
- Audio format.

Enable the provider's supported conversation configuration overrides for:

- Voice ID.
- System prompt.
- First message.
- Language.

Store its ID in:

`ELEVENLABS_AGENT_ID`

Verify that custom voice IDs can actually be passed through the conversation initiation configuration before declaring the feature complete.

Do not assume that an override works simply because it appears in an example.

## 7.3 Creating agents in VoiceRep

Build a Create Agent form.

Fields:

- Agent name.
- Select voice.
- Agent description.
- System instructions.
- First greeting.
- Language.

Example:

```text
Name: Personal Research Assistant

Voice: My Cloned Voice

Instructions:
You are a knowledgeable research assistant.
Speak naturally and clearly.
Give direct explanations.
Ask follow-up questions only when necessary.

Greeting:
Hello! What would you like to explore today?

Language:
English
```

Save the configuration in PostgreSQL.

## 7.4 Starting an agent session

Implement:

`POST /api/v1/agents/{agent_id}/session`

Sequence:

1. Authenticate the user.
2. Validate ownership of the agent.
3. Validate that its selected voice is ready.
4. Request an authenticated signed URL from ElevenLabs.
5. Return the signed URL and required session configuration.
6. Establish the browser WebSocket connection.
7. Send the conversation initiation configuration with the selected voice ID and permitted prompt overrides.
8. Start the conversation.

Use the documented endpoint:

`GET /v1/convai/conversation/get-signed-url?agent_id={agent_id}`

Use a new signed URL for each session.

Never expose the ElevenLabs API key in frontend code.

The browser must not be permitted to use arbitrary voice IDs supplied by an unauthenticated request.

## 7.5 Agent playground

Create a polished live conversation interface.

Include:

- Microphone permission handling.
- Start conversation.
- End conversation.
- Connection indicator.
- Listening state.
- Thinking state.
- Speaking state.
- User transcript.
- Agent transcript.
- Audio playback.
- Error state.
- Conversation duration.

Use the official ElevenLabs client SDK or documented WebSocket protocol.

Do not reinvent audio transport unless necessary.

Ensure that users can interrupt an agent when the provider's conversation protocol supports interruption.

For the MVP, transcripts may be displayed during the session without permanently saving them.

Make transcript persistence an explicit opt-in feature.

---

# 8. Database schema

Use PostgreSQL with SQLAlchemy and Alembic.

Create these tables:

## users

```text
id
email
created_at
updated_at
```

Authentication should be managed by Supabase Auth. Do not duplicate password storage.

## voices

```text
id UUID PRIMARY KEY
owner_id UUID
name VARCHAR
provider VARCHAR
provider_voice_id VARCHAR
status VARCHAR
language VARCHAR NULL
audio_duration FLOAT NULL
quality_report JSONB
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP NULL
```

Add a unique constraint for provider and provider voice ID where appropriate.

## voice_consents

```text
id UUID PRIMARY KEY
voice_id UUID
owner_id UUID
speaker_relationship VARCHAR
consent_scope JSONB
terms_version VARCHAR
consent_status VARCHAR
evidence_storage_key VARCHAR NULL
consented_at TIMESTAMP
reviewed_at TIMESTAMP NULL
```

## generations

```text
id UUID PRIMARY KEY
owner_id UUID
voice_id UUID
input_text TEXT
model_id VARCHAR
voice_settings JSONB
status VARCHAR
audio_storage_key VARCHAR NULL
provider_request_id VARCHAR NULL
character_count INTEGER
duration_seconds FLOAT NULL
error_code VARCHAR NULL
created_at TIMESTAMP
completed_at TIMESTAMP NULL
```

## agents

```text
id UUID PRIMARY KEY
owner_id UUID
voice_id UUID
name VARCHAR
description TEXT
system_prompt TEXT
first_message TEXT
language VARCHAR
status VARCHAR
created_at TIMESTAMP
updated_at TIMESTAMP
```

## agent_sessions

```text
id UUID PRIMARY KEY
owner_id UUID
agent_id UUID
provider_conversation_id VARCHAR NULL
status VARCHAR
started_at TIMESTAMP
ended_at TIMESTAMP NULL
duration_seconds INTEGER NULL
```

Use proper foreign keys, indexes and cascading deletion where appropriate.

Do not rely only on frontend ownership checks.

Every backend query must enforce the authenticated user's ownership.

---

# 9. Backend API design

Use versioned REST endpoints.

Base URL:

`/api/v1`

## Authentication

Use Supabase Auth on the frontend.

Validate Supabase JWTs in FastAPI.

Protect private endpoints with authentication dependencies.

## Voice endpoints

```http
POST   /uploads/presign
POST   /voices
GET    /voices
GET    /voices/{voice_id}
PATCH  /voices/{voice_id}
DELETE /voices/{voice_id}
```

## Studio endpoints

```http
POST   /generations
GET    /generations
GET    /generations/{generation_id}
GET    /generations/{generation_id}/audio
DELETE /generations/{generation_id}
```

## Agent endpoints

```http
POST   /agents
GET    /agents
GET    /agents/{agent_id}
PATCH  /agents/{agent_id}
DELETE /agents/{agent_id}

POST   /agents/{agent_id}/session
```

## Usage endpoints

```http
GET /usage
```

Implement pagination for collections.

Use consistent JSON response schemas.

Use appropriate HTTP status codes.

Return clear and actionable error messages without exposing provider secrets or internal stack traces.

---

# 10. Frontend product design

The product should feel like a modern, premium AI SaaS application.

Avoid generic AI dashboard templates.

### Design direction

- Minimal interface.
- Strong typography.
- Generous spacing.
- Neutral background.
- Subtle borders.
- Carefully designed dark and light modes.
- Restrained accent color.
- Refined audio-player components.
- Smooth but restrained transitions.

Use shadcn/ui where it helps.

Avoid overusing gradients, glowing effects and excessive glassmorphism.

### Main navigation

```text
Dashboard
Voice Library
Voice Studio
Voice Agents
Generation History
Settings
```

### Required screens

**1. Landing page**

Explain what the application does.

Primary actions:

- Get started.
- Explore features.

**2. Authentication**

Signup, login and logout.

**3. Dashboard**

Show:

- Total saved voices.
- Generated audio count.
- Active agents.
- Recent activity.

Use real database information.

**4. Voice Library**

Display all saved voice profiles.

Provide:

- Upload new voice.
- Preview.
- Rename.
- Delete.
- Status badges.

**5. Voice Creation**

Create a multi-step workflow:

- Upload.
- Audio validation.
- Consent.
- Cloning.
- Preview.
- Save.

**6. Voice Studio**

Text editor, voice selection, settings and audio player.

**7. Agent Dashboard**

List agents and allow creation, editing and deletion.

**8. Agent Playground**

Real-time conversational interface.

**9. Settings**

Account information, data deletion and application preferences.

Every button must perform its advertised action.

Do not leave decorative controls pretending to be functional.

---

# 11. Security, consent and privacy

Voice cloning can be misused for impersonation and fraud. Treat authorization as a core product requirement.

### Voice authorization

Do not allow users to clone arbitrary voices simply because they possess an audio file.

Require users to confirm that:

- They are the speaker, or
- They have explicit authorization from the speaker for synthetic voice creation and use.

For the initial MVP:

- Support self-owned voices.
- Require documentation and manual approval for third-party voices.
- Capture explicit consent separately for content generation and AI-agent use.
- Maintain consent records and a clear revocation path.
- Do not support impersonation, scams, identity fraud or attempts to bypass voice authentication.
- Do not support non-consensual cloning or children's voices.

Do not treat an automated voice similarity check as legal proof of consent.

If consent is revoked, disable all related generation and agent sessions and remove the provider clone.

### Storage and security

- Keep all source audio in private object storage.
- Use expiring signed URLs.
- Validate MIME type and actual file content.
- Enforce upload limits.
- Prevent path traversal and unsafe FFmpeg arguments.
- Never expose API keys.
- Add backend rate limiting.
- Add per-user usage limits.
- Protect against IDOR vulnerabilities.
- Restrict CORS.
- Log security-relevant events.
- Delete temporary sample audio after successful cloning unless the user explicitly opts into retention.
- Support deletion of voices and generated files.

Clearly disclose that audio is AI-generated in the application and agent experience.

Do not claim that third-party storage providers delete all backups immediately; describe actual retention accurately.

---

# 12. Provider abstraction

Although ElevenLabs is the only provider implemented initially, avoid tightly coupling every service to its SDK.

Create an interface similar to:

```python
class VoiceProvider:
    async def create_voice(self, audio_file, name):
        pass

    async def get_voice(self, provider_voice_id):
        pass

    async def delete_voice(self, provider_voice_id):
        pass

    async def synthesize(self, voice_id, text, settings):
        pass

    async def create_agent_session(self, agent_config):
        pass
```

Implement:

```text
providers/
    base.py
    elevenlabs.py
```

Future integrations may include:

- Cartesia.
- Fish Audio.
- OpenAI Custom Voices.

Do not implement additional providers in the initial release.

Make provider credentials environment-based.

Allow the provider to be changed later without modifying the frontend or database schema.

---

# 13. Suggested repository structure

```text
vox-foundry/
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   ├── dashboard/
│   │   ├── voices/
│   │   ├── studio/
│   │   ├── agents/
│   │   ├── history/
│   │   └── settings/
│   │
│   ├── components/
│   │   ├── audio/
│   │   ├── voices/
│   │   ├── agents/
│   │   ├── dashboard/
│   │   └── ui/
│   │
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   └── types/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── providers/
│   │   ├── workers/
│   │   └── utils/
│   │
│   ├── migrations/
│   ├── tests/
│   └── main.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATABASE.md
│   ├── IMPLEMENTATION_LOG.md
│   └── DEPLOYMENT.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Modify this structure if the existing repository has sensible conventions. Do not create unnecessary abstractions or empty files.

---

# 14. Environment variables

Create a complete `.env.example`.

Include:

```dotenv
# Application
APP_ENV=development
APP_SECRET_KEY=
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

# Database
DATABASE_URL=

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_JWKS_URL=

# ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_AGENT_ID=

# Gemini - optional voice/sample analysis
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash

# Storage
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_ENDPOINT_URL=

# Redis
REDIS_URL=

# Upload configuration
MAX_UPLOAD_SIZE_MB=50
MAX_AUDIO_DURATION_SECONDS=300
```

Validate required variables at application startup.

Do not put actual secrets in the repository.

The Gemini integration is optional. Use it only for additional text-based analysis or descriptions if useful. It must not replace ElevenLabs TTS or voice cloning.

---

# 15. Implementation roadmap

Build the application in the following order.

## Phase 0 — Repository inspection and setup

Tasks:

1. Inspect the complete repository.
2. Identify existing code, dependencies and conventions.
3. Create an implementation plan.
4. Establish frontend and backend structure.
5. Configure environment loading.
6. Configure Docker Compose.
7. Connect PostgreSQL.
8. Configure Supabase authentication.
9. Create initial migrations.
10. Add health-check endpoints.

Acceptance criteria:

- Frontend starts successfully.
- Backend starts successfully.
- Database connection works.
- Health endpoint works.
- Authentication can be tested.

## Phase 1 — Voice cloning

Tasks:

1. Build audio upload.
2. Add private R2 uploads.
3. Implement audio validation.
4. Build quality report.
5. Implement voice consent.
6. Integrate ElevenLabs IVC API.
7. Persist provider voice ID.
8. Implement status lifecycle.
9. Build Voice Library.
10. Implement provider voice deletion.

Acceptance criteria:

- User uploads authorized audio.
- File validation works.
- A real provider clone is created.
- Provider voice ID is saved.
- Voice status is accurate.
- User can preview their voice.
- User can delete their voice.
- Another user cannot access it.

This is the first major milestone.

Do not move to Phase 2 until this workflow is tested.

## Phase 2 — Voice Studio

Tasks:

1. Build text editor.
2. Add voice selector.
3. Add supported voice settings.
4. Integrate TTS streaming.
5. Build background generation job.
6. Store audio in R2.
7. Build audio player.
8. Add download functionality.
9. Build generation history.
10. Track character usage.

Acceptance criteria:

- User selects a saved voice.
- User enters text.
- Provider generates real speech.
- Audio can be played.
- Audio can be downloaded.
- Generation is saved in history.
- Failed generations are handled correctly.

## Phase 3 — Voice Agents

Tasks:

1. Configure the shared provider agent.
2. Configure allowed conversation overrides.
3. Build agent CRUD operations.
4. Connect agents to saved voices.
5. Implement signed URL generation.
6. Connect the browser to the provider WebSocket.
7. Add live conversation UI.
8. Display transcripts.
9. Implement conversation termination.
10. Add session tracking.

Acceptance criteria:

- User creates an agent.
- Agent references a ready voice.
- User starts a real conversation.
- Agent answers in the selected cloned voice.
- User can interrupt or stop the conversation where supported.
- Invalid sessions are rejected.
- Another user cannot start a session using someone else's voice.

## Phase 4 — Product hardening

Tasks:

1. Add rate limiting.
2. Add usage tracking.
3. Add better error reporting.
4. Add API validation.
5. Add pagination.
6. Improve loading states.
7. Test data ownership.
8. Test deletion and revocation.
9. Add privacy and terms pages.
10. Improve application responsiveness.
11. Add logging and monitoring.
12. Write deployment documentation.

Acceptance criteria:

- No secrets are exposed.
- No unauthorized voice access is possible.
- API failures are handled.
- Database migrations work from a fresh installation.
- Frontend and backend tests pass.
- The application can be deployed using documented instructions.

---

# 16. Testing strategy

Do not consider the project complete merely because it builds.

### Backend tests

Test:

- Audio validation.
- Supported and unsupported formats.
- Invalid upload rejection.
- Voice creation with mocked provider.
- Provider timeout handling.
- Provider rate-limit handling.
- Database lifecycle transitions.
- Voice ownership.
- Voice deletion.
- Generation creation.
- Agent configuration.
- Signed URL authorization.

### Frontend tests

Test:

- Authentication.
- Audio upload interaction.
- Upload errors.
- Voice selector.
- Generation form.
- Audio player.
- Agent creation.
- Agent session lifecycle.
- Responsive layouts.

### Integration tests

Use real provider credentials only when configured.

Test:

1. Create an actual voice clone.
2. Generate actual speech.
3. Start an actual agent conversation.
4. Verify the selected cloned voice is used.
5. Delete a test voice.

Never substitute mock provider responses for real integrations during production use.

Mocks are permitted in automated tests.

### End-to-end acceptance scenario

A fresh user should be able to:

1. Register.
2. Upload an authorized voice sample.
3. Create a clone.
4. See it inside Voice Library.
5. Enter a paragraph in Voice Studio.
6. Generate speech.
7. Play and download the result.
8. Create an AI agent.
9. Select the same cloned voice.
10. Start a microphone conversation.
11. Hear the agent respond using the selected voice.
12. Delete the voice and have dependent features disabled.

This complete scenario is the definition of a successful MVP.

---

# 17. Engineering rules for execution

Follow these instructions throughout implementation.

1. Inspect before modifying.
2. Do not rewrite the whole repository without a reason.
3. Do not generate the entire project in one enormous operation.
4. Work in logical, independently testable phases.
5. Finish the current milestone before starting the next.
6. Run the relevant tests after every major feature.
7. Fix errors instead of hiding them.
8. Do not silently remove existing functionality.
9. Do not hardcode API keys.
10. Do not invent provider API endpoints or request schemas.
11. Read the current official API documentation before integrating a provider feature.
12. Use typed request and response schemas.
13. Handle loading, empty, success and error states.
14. Avoid unnecessary dependencies.
15. Avoid unnecessary abstractions.
16. Keep reusable frontend components separate.
17. Keep all provider integration inside the provider layer.
18. Use database transactions where needed.
19. Add migrations for schema changes.
20. Make all destructive operations explicit.

If provider credentials are missing, implement the integration correctly, create a clear setup guide and report that real-provider verification remains blocked. Never fabricate a successful clone or generated audio.

Do not stop after generating `README.md` and a frontend skeleton.

Implement the actual backend and provider workflows.

---

# 18. Documentation deliverables

Maintain these files while developing:

### README.md

Include:

- Product overview.
- Technology stack.
- Prerequisites.
- Installation.
- Environment configuration.
- Running locally.
- Testing.
- Provider setup.
- Deployment instructions.

### docs/ARCHITECTURE.md

Explain:

- System components.
- Service responsibilities.
- Provider integration.
- Data flow.
- Audio processing.
- Agent session lifecycle.

### docs/API.md

Document each endpoint and its request/response format.

### docs/IMPLEMENTATION_LOG.md

After each phase, record:

- Completed functionality.
- Files created or modified.
- Tests executed.
- Results.
- Known problems.
- Remaining work.

### docs/DEPLOYMENT.md

Include deployment and production configuration.

---

# 19. Final delivery requirements

At completion, provide:

1. What was implemented.
2. Architecture overview.
3. Repository structure.
4. Required environment variables.
5. Exact local startup commands.
6. Database setup and migration commands.
7. Provider configuration instructions.
8. Test results.
9. Screenshots of the implemented interface, where supported.
10. Known limitations.
11. Remaining external configuration requirements.

Distinguish clearly between:

- Implemented and tested.
- Implemented but awaiting external credentials.
- Not implemented.

Do not claim production readiness without appropriate testing.

---

# 20. Start execution

Begin by inspecting the existing project directory.

Your first response should contain:

1. A brief repository assessment.
2. Any significant architectural constraints discovered.
3. A concrete execution checklist.

Then immediately start Phase 0.

Do not ask me to select a technology stack: the stack has already been specified.

Do not ask for approval between ordinary implementation phases. Make sensible engineering decisions and proceed.

When a genuine external dependency blocks implementation, continue with all independent work and clearly document the blocker.

Your ultimate goal is a working VoiceRep application in which the same uploaded and authorized voice can power both long-form speech generation and conversational AI agents.

**Build the product, not just the demonstration.**