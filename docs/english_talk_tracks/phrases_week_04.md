# Week 04 — English Phrases — OIDC, PKCE & Auth Edge Cases

## Gathering evidence from a customer

1. **"Could you share the exact redirect URI registered in your OAuth app settings? Please copy-paste it rather than retyping — even a trailing slash will cause a mismatch."**
   → Pidiendo evidencia de redirect URI con precisión

2. **"Can you decode the JWT and share the `exp` and `iat` claims? I want to rule out clock skew between your server and the auth server."**
   → Pidiendo inspección de token para descartar clock skew

3. **"Are you generating a fresh `code_verifier` for each authorization flow, or reusing the same one across sessions?"**
   → Diagnosticando PKCE reuse bug

## Explaining technical concepts to non-technical stakeholders

4. **"PKCE is like a receipt the app generates at the start of login. When login completes, the app shows that receipt to prove it's the same one that started the process."**
   → Explicando PKCE a un PM o controller

5. **"The `id_token` tells you WHO the user is. The `access_token` tells you WHAT the user can do. They look similar but serve completely different purposes."**
   → Explicando OIDC tokens a un customer

6. **"Clock skew means your server's clock and our server's clock are out of sync. Even a few minutes of difference can make a perfectly valid token appear expired."**
   → Explicando clock skew a un VP

## Communicating during an incident

7. **"We've identified the root cause — there's a configuration mismatch in the redirect URI. Your team will need to update either the registered URI or the one in your code. I can walk you through it."**
   → Dando root cause + next steps claros

8. **"I'm still investigating but wanted to give you a quick update: we've ruled out token expiration and scope issues. I'm now looking at the certificate chain. I'll update you again in 15 minutes."**
   → Update intermedio durante investigación

## Pushing back professionally

9. **"I understand this is urgent, but before we make any changes I need to confirm the root cause with evidence. Can you share the full error response including headers? That will help me diagnose this much faster."**
   → Resistiendo presión para actuar sin evidencia

## Setting expectations

10. **"Based on what I'm seeing, this is a client-side configuration issue rather than a platform problem. Your engineering team will need to make the fix, and I'll stay on the call to verify it works once it's deployed."**
    → Clarificando ownership sin culpar al cliente