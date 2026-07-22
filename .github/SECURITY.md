# Security Policy

## Supported Versions

This project doesn't yet maintain release branches — security fixes are applied to
`master` only.

| Version | Supported |
| ------- | --------- |
| master  | ✅        |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, use GitHub's private vulnerability reporting for this repository:

1. Go to the **Security** tab of this repository.
2. Click **Report a vulnerability**.
3. Include a description of the issue, steps to reproduce, and potential impact.

This repository also runs [CodeQL](../.github/workflows/codeql.yml) and
[Dependency Review](../.github/workflows/dependency-review.yml) on every change,
and [Dependabot](../.github/dependabot.yml) for dependency updates — findings from
those show up in the Security tab automatically.

### What to expect

- Acknowledgement within a few days.
- A fix or mitigation plan communicated once the issue is confirmed.
- Credit in the fix's commit/PR description, if you'd like it.

## Scope

This is a project template. Security issues in the template's own code (auth,
middleware, dependency handling) are in scope. Issues in third-party dependencies
should be reported upstream, though flagging them here is also fine — Dependabot
and Dependency Review are already watching for known-vulnerable versions.
