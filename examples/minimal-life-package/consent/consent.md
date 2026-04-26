# Consent statement (example)

Subject: `dlrs_EXAMPLE_minimal_life`
Captured: 2026-04-25T10:30:00+00:00
Withdrawal endpoint: `https://example.org/dlrs/withdraw/EXAMPLE_minimal_life`

The subject ("the subject") consents to the following uses of the data
referenced by the source DLRS record:

- Storage and structured processing of text and metadata.
- Generation of an `.life` package (this archive) for distribution
  to a compatible runtime, scoped to producing an *AI digital life
  instance* — never claimed to be equivalent to the human.
- Mounting in compatible runtimes that honour `forbidden_uses[]`,
  `withdrawal_endpoint`, and `expires_at` per
  `docs/LIFE_RUNTIME_STANDARD.md`.

The subject does NOT consent to:

- Voice cloning (despite `allow_voice_clone: true` in the source
  manifest, `forbidden_uses[]` in this `.life` MUST list
  `voice_clone_for_fraud`).
- Avatar cloning.
- Use in political endorsement, fraud, or explicit content.
- Mounting after `expires_at` in any runtime.

Withdrawal procedure: send any HTTP request (GET, HEAD, or POST) to the
`withdrawal_endpoint`. A response status `410 Gone` indicates the
package has been withdrawn; the runtime MUST then complete the current
turn and terminate the session.

This statement is illustrative. Real-world consent statements MUST be
captured per the legal regime applicable to the subject (PIPL / GDPR /
EU AI Act / etc.), with stronger evidence than markdown text.
