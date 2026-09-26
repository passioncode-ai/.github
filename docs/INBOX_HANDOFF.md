# Fabric Inbox profile update

Objective: add the requested product to the organization profile and link its public page.

Changes: `profile/README.md` adds Inbox development status, Cloudflare/Gmail preview scope, planned IMAP/Outlook, and public product link. The toolkit table also links the already published Observatory page. Source stays private; no release/download is advertised. Shared white/dark visual roles match website `design-system/tokens.css` source6085d1073b28dc3b97fb9b029350a038d20afd3c.

Evidence: Inbox sourcebaseline d577462572d332c1e7c157504b7dffd9cde00bea and unified API1612037002fe2a893f978bda95fdb44fcf844a0b; UI in codex/unified-workbench. Website product PR5 owns the target page. Checks: git diff --check; verify page HTTP after website deployment. Exact next task: merge this profile change once /inbox/ is live, verify anonymous raw profile and record remote SHA. No credential changes.
