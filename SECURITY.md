# Security policy

Security fixes target the latest version on the default branch.

Report vulnerabilities privately to the repository owner. Do not include
cookies, tokens, referral codes, HAR files, or other credentials in a public
issue.

Store `REFCHECK_COOKIE` only in the process environment or an
untracked `.env` file. Rotate credentials exposed in browser exports and
validate only codes you are authorized to use.
