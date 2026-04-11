Hi [Name],

Thank you for reaching out today regarding the unauthorized errors
affecting your payments integration.

The issue started yesterday and has been impacting all POST requests
to the payments endpoint. After investigating, we identified the root
cause: the token being used was missing the required `write:payments`
scope.

**Action required:** Please have your engineering team regenerate the
token including the `write:payments` scope. Once the new token is in
place, please confirm and we will run a reconciliation to ensure no
events were missed during the outage window.

I will monitor the integration closely after the fix is applied and
will follow up with a confirmation once everything is processing
correctly.

Please don't hesitate to reach out if you need anything in the meantime.

Best regards,
[Your name]


# Week 03 — English Phrases: Auth Troubleshooting

1. "Let's get this resolved as quickly as possible."
2. "Can you share the exact error message and status code?"
3. "Could you paste the token at jwt.io and share the `exp` field?"
4. "The root cause appears to be a missing scope in the token."
5. "Please have your engineering team regenerate the token with the correct scope."
6. "Once resolved, we'll run a reconciliation to ensure no events were missed."
7. "I'll monitor the integration closely after the fix is applied."
8. "This looks like an authorization issue rather than an authentication issue."
9. "The token is valid, but it doesn't have permission for this endpoint."
10. "Please confirm once the new token is in place and I'll verify from our side."