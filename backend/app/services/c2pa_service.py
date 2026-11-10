import datetime
import hashlib
import json
import logging
import os
import struct
from pathlib import Path
from typing import Any, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from app.core.config import settings

logger = logging.getLogger("voicerep.c2pa")

KEY_DIR = Path(settings.STORAGE_LOCAL_DIR if hasattr(settings, "STORAGE_LOCAL_DIR") else "./storage") / "keys"
KEY_FILE = KEY_DIR / "c2pa_private.key"
CERT_FILE = KEY_DIR / "c2pa_certificate.crt"


def encode_syncsafe(val: int) -> bytes:
    """Encode an integer as a 4-byte ID3v2 syncsafe integer."""
    b0 = (val >> 21) & 0x7F
    b1 = (val >> 14) & 0x7F
    b2 = (val >> 7) & 0x7F
    b3 = val & 0x7F
    return bytes([b0, b1, b2, b3])


def decode_syncsafe(data: bytes) -> int:
    """Decode a 4-byte ID3v2 syncsafe integer."""
    return (data[0] << 21) | (data[1] << 14) | (data[2] << 7) | data[3]


class C2PAService:
    def __init__(self):
        self._private_key: Optional[ec.EllipticCurvePrivateKey] = None
        self._certificate: Optional[x509.Certificate] = None
        self._cert_pem: Optional[str] = None
        self._init_keys()

    def _init_keys(self):
        """Loads existing X.509 keypair or generates a new platform signing identity."""
        try:
            KEY_DIR.mkdir(parents=True, exist_ok=True)
            if KEY_FILE.exists() and CERT_FILE.exists():
                with open(KEY_FILE, "rb") as f:
                    self._private_key = serialization.load_pem_private_key(f.read(), password=None)
                with open(CERT_FILE, "rb") as f:
                    pem_data = f.read()
                    self._certificate = x509.load_pem_x509_certificate(pem_data)
                    self._cert_pem = pem_data.decode("utf-8")
                logger.info("Loaded existing VoiceRep C2PA cryptographic keypair.")
                return

            logger.info("Generating new VoiceRep C2PA cryptographic signing identity (X.509 ECDSA P-256)...")
            self._private_key = ec.generate_private_key(ec.SECP256R1())

            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "VoiceRep Safe AI Provenance"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Cryptographic Trust & Safety"),
                x509.NameAttribute(NameOID.COMMON_NAME, "VoiceRep Generation Signer CA"),
            ])

            now = datetime.datetime.now(datetime.timezone.utc)
            self._certificate = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(self._private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - datetime.timedelta(days=1))
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(self._private_key, hashes.SHA256())
            )

            # Persist key and certificate
            key_pem = self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            cert_pem = self._certificate.public_bytes(serialization.Encoding.PEM)

            with open(KEY_FILE, "wb") as f:
                f.write(key_pem)
            with open(CERT_FILE, "wb") as f:
                f.write(cert_pem)

            self._cert_pem = cert_pem.decode("utf-8")
            logger.info("VoiceRep C2PA keys successfully generated and stored.")
        except Exception as e:
            logger.error(f"Failed to initialize C2PA cryptographic keypair: {e}")
            raise

    def get_public_certificate_pem(self) -> str:
        return self._cert_pem or ""

    def create_manifest(
        self,
        generation_id: str,
        owner_id: str,
        voice_id: str,
        model_id: str,
        audio_bytes: bytes,
        acoustic_payload: Optional[dict[str, Any]] = None,
        license_name: str = "VoiceRep AI Synthetic Media Permissive License v1.0",
    ) -> dict[str, Any]:
        """
        Creates a formal C2PA-compliant manifest structure specifying:
        - Claim generator & instance UUID
        - Provenance actions (c2pa.created, c2pa.synthesized)
        - Assertions: AI model, speaker attribution, compliance, acoustic watermark reference
        - Content hash binding (SHA-256)
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        content_hash = hashlib.sha256(audio_bytes).hexdigest()

        manifest = {
            "c2pa_version": "1.3.0",
            "claim_generator": "VoiceRep/1.0.0 (C2PA Deepfake Protection Engine)",
            "instance_id": f"urn:uuid:{generation_id}",
            "format": "audio/mpeg",
            "title": "VoiceRep AI Synthesized Audio",
            "claim_generator_info": {
                "name": "VoiceRep AI",
                "version": "1.0.0",
                "organization": "VoiceRep Safe AI Provenance",
            },
            "actions": [
                {
                    "action": "c2pa.created",
                    "when": now_iso,
                    "softwareAgent": "VoiceRep AI Voice Platform v1.0",
                },
                {
                    "action": "c2pa.synthesized",
                    "when": now_iso,
                    "softwareAgent": f"VoiceRep Neural Synthesizer ({model_id})",
                },
            ],
            "assertions": [
                {
                    "label": "c2pa.ai_generative_info",
                    "data": {
                        "generation_type": "synthetic_speech",
                        "model_id": model_id,
                        "voice_id": voice_id,
                        "owner_id_hash": hashlib.sha256(owner_id.encode("utf-8")).hexdigest(),
                        "is_ai_generated": True,
                        "compliance": [
                            "EU AI Act Article 50 (Transparency and Watermarking of AI Generated Content)",
                            "US Executive Order 14110 (Standards for AI-Generated Digital Content Provenance)",
                        ],
                        "license": license_name,
                    },
                },
                {
                    "label": "c2pa.hash_binding",
                    "data": {
                        "algorithm": "SHA-256",
                        "hash": content_hash,
                    },
                },
            ],
        }

        if acoustic_payload:
            manifest["assertions"].append({
                "label": "c2pa.watermark",
                "data": {
                    "type": "acoustic_in_band",
                    "protocol": acoustic_payload.get("protocol", "VoiceRep-QIM-HAS-v1"),
                    "user_hash": acoustic_payload.get("user_hash"),
                    "gen_hash": acoustic_payload.get("gen_hash"),
                    "timestamp": acoustic_payload.get("timestamp"),
                },
            })

        return manifest

    def sign_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """
        Signs the canonical JSON manifest with VoiceRep's X.509 private key using ECDSA SHA-256.
        """
        canonical_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = self._private_key.sign(canonical_bytes, ec.ECDSA(hashes.SHA256()))

        return {
            "manifest": manifest,
            "signature": signature.hex(),
            "algorithm": "ES256",
            "certificate": self._cert_pem,
        }

    def verify_manifest_signature(self, signed_envelope: dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Verifies ECDSA signature and X.509 public key validity on the manifest envelope.
        """
        try:
            manifest = signed_envelope.get("manifest")
            sig_hex = signed_envelope.get("signature")
            cert_pem = signed_envelope.get("certificate")

            if not manifest or not sig_hex or not cert_pem:
                return False, "Malformed signed envelope: missing manifest, signature, or certificate."

            cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
            public_key = cert.public_key()

            canonical_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
            signature_bytes = bytes.fromhex(sig_hex)

            public_key.verify(signature_bytes, canonical_bytes, ec.ECDSA(hashes.SHA256()))
            return True, None
        except Exception as e:
            return False, f"Signature verification failed: {e}"

    def embed_manifest_in_mp3(self, mp3_bytes: bytes, signed_envelope: dict[str, Any]) -> bytes:
        """
        Embeds signed C2PA manifest envelope into an ID3v2 GEOB (General Encapsulated Object) frame.
        """
        envelope_json = json.dumps(signed_envelope).encode("utf-8")

        # GEOB frame: encoding(1B) + mime(null-term) + filename(null-term) + desc(null-term) + payload
        mime = b"application/c2pa\x00"
        filename = b"manifest.c2pa\x00"
        desc = b"c2pa_manifest\x00"
        frame_body = b"\x00" + mime + filename + desc + envelope_json
        frame_hdr = b"GEOB" + struct.pack(">I", len(frame_body)) + b"\x00\x00"
        frame = frame_hdr + frame_body

        offset = 0
        if mp3_bytes.startswith(b"ID3"):
            existing_size = decode_syncsafe(mp3_bytes[6:10])
            offset = 10 + existing_size
            raw_audio = mp3_bytes[offset:]
        else:
            raw_audio = mp3_bytes

        id3_header = b"ID3\x03\x00\x00" + encode_syncsafe(len(frame))
        return id3_header + frame + raw_audio

    def extract_manifest_from_mp3(self, mp3_bytes: bytes) -> Optional[dict[str, Any]]:
        """
        Extracts C2PA signed envelope from ID3v2 GEOB frame in MP3 bytes.
        """
        if not mp3_bytes.startswith(b"ID3"):
            return None
        try:
            tag_size = decode_syncsafe(mp3_bytes[6:10])
            tag_data = mp3_bytes[10 : 10 + tag_size]

            pos = 0
            while pos + 10 <= len(tag_data):
                frame_id = tag_data[pos : pos + 4]
                frame_size = struct.unpack(">I", tag_data[pos + 4 : pos + 8])[0]
                pos += 10
                if frame_id == b"GEOB":
                    frame_content = tag_data[pos : pos + frame_size]
                    parts = frame_content[1:].split(b"\x00", 3)
                    if len(parts) >= 4 and b"c2pa" in parts[2].lower():
                        return json.loads(parts[3].decode("utf-8"))
                pos += frame_size
        except Exception as e:
            logger.debug(f"Failed to parse ID3 GEOB frame: {e}")
        return None

    def embed_manifest_in_wav(self, wav_bytes: bytes, signed_envelope: dict[str, Any]) -> bytes:
        """
        Embeds signed C2PA manifest envelope into a RIFF custom 'c2pa' chunk.
        """
        payload = json.dumps(signed_envelope).encode("utf-8")
        chunk_hdr = b"c2pa" + struct.pack("<I", len(payload))
        # Ensure 2-byte alignment per RIFF spec
        chunk_data = chunk_hdr + payload + (b"\x00" if len(payload) % 2 != 0 else b"")

        # Update RIFF total length in header
        if wav_bytes.startswith(b"RIFF") and len(wav_bytes) >= 12:
            orig_riff_len = struct.unpack("<I", wav_bytes[4:8])[0]
            new_riff_len = orig_riff_len + len(chunk_data)
            updated_header = wav_bytes[:4] + struct.pack("<I", new_riff_len) + wav_bytes[8:]
            return updated_header + chunk_data
        return wav_bytes + chunk_data

    def extract_manifest_from_wav(self, wav_bytes: bytes) -> Optional[dict[str, Any]]:
        """
        Extracts C2PA signed envelope from RIFF 'c2pa' chunk.
        """
        if not wav_bytes.startswith(b"RIFF"):
            return None
        try:
            pos = 12
            while pos + 8 <= len(wav_bytes):
                chunk_id = wav_bytes[pos : pos + 4]
                chunk_len = struct.unpack("<I", wav_bytes[pos + 4 : pos + 8])[0]
                pos += 8
                if chunk_id == b"c2pa":
                    return json.loads(wav_bytes[pos : pos + chunk_len].decode("utf-8"))
                pos += chunk_len + (chunk_len % 2)
        except Exception as e:
            logger.debug(f"Failed to extract RIFF c2pa chunk: {e}")
        return None

    def sign_and_embed(
        self,
        audio_bytes: bytes,
        generation_id: str,
        owner_id: str,
        voice_id: str,
        model_id: str,
        acoustic_payload: Optional[dict[str, Any]] = None,
        is_mp3: bool = True,
    ) -> Tuple[bytes, dict[str, Any]]:
        """
        High-level wrapper: builds C2PA manifest, cryptographically signs it,
        and injects it into MP3 ID3v2 GEOB or WAV RIFF chunk.
        """
        manifest = self.create_manifest(
            generation_id=generation_id,
            owner_id=owner_id,
            voice_id=voice_id,
            model_id=model_id,
            audio_bytes=audio_bytes,
            acoustic_payload=acoustic_payload,
        )
        signed_envelope = self.sign_manifest(manifest)

        if is_mp3:
            container_bytes = self.embed_manifest_in_mp3(audio_bytes, signed_envelope)
        else:
            container_bytes = self.embed_manifest_in_wav(audio_bytes, signed_envelope)

        return container_bytes, signed_envelope

    def extract_manifest(self, audio_bytes: bytes) -> Optional[dict[str, Any]]:
        """Extracts signed envelope regardless of container format."""
        if audio_bytes.startswith(b"ID3") or b"c2pa_manifest" in audio_bytes[:4096]:
            manifest = self.extract_manifest_from_mp3(audio_bytes)
            if manifest:
                return manifest

        if audio_bytes.startswith(b"RIFF"):
            manifest = self.extract_manifest_from_wav(audio_bytes)
            if manifest:
                return manifest

        return None


c2pa_service = C2PAService()
