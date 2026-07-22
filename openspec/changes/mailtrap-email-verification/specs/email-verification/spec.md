## ADDED Requirements

### Requirement: Verification email on registration
The system SHALL generate a single-use, expiring email verification token when a new user registers, and SHALL enqueue delivery of a confirmation email containing a verification link to the registrant's email address via Mailtrap, without blocking the registration response on delivery.

#### Scenario: Successful registration enqueues a verification email
- **WHEN** a new user completes `POST /register` with a valid, unique email
- **THEN** the account is created with `email_verified = false`, a hashed verification token and expiry are stored, and a task to send the confirmation email is enqueued on the users worker queue

#### Scenario: Registration response does not wait on email delivery
- **WHEN** the Mailtrap send takes longer than the request lifecycle, or temporarily fails
- **THEN** `POST /register` still returns success to the client based on account creation alone, not on email delivery completing

### Requirement: Email verification endpoint
The system SHALL provide an endpoint that accepts a verification token, marks the corresponding account as verified when the token is valid and unexpired, and rejects invalid, expired, or already-used tokens.

#### Scenario: Valid token verifies the account
- **WHEN** a user submits a verification token that matches a stored, unexpired token for their account
- **THEN** the account's `email_verified` flag is set to true and the stored token is cleared so it cannot be reused

#### Scenario: Expired token is rejected
- **WHEN** a user submits a verification token whose expiry timestamp has passed
- **THEN** the request is rejected and the account remains unverified

#### Scenario: Already-used token is rejected
- **WHEN** a user submits a verification token that was already consumed by a prior successful verification
- **THEN** the request is rejected because no matching pending token exists

### Requirement: Resend verification email
The system SHALL provide an endpoint that issues a new verification token and enqueues a new confirmation email for an account that is not yet verified, invalidating any previously issued token for that account.

#### Scenario: Resend for an unverified account
- **WHEN** an unverified user requests a resend of the verification email
- **THEN** a new token and expiry are generated, any prior token is invalidated, and a new confirmation email is enqueued

#### Scenario: Resend for an already-verified account
- **WHEN** an already-verified user requests a resend of the verification email
- **THEN** the system SHALL NOT generate a new token or enqueue an email

### Requirement: Onboarding gated on email verification
The system SHALL prevent an authenticated user whose account is not email-verified from completing onboarding, and SHALL present a confirmation-pending state instead until verification succeeds.

#### Scenario: Unverified user is redirected away from onboarding
- **WHEN** an authenticated user whose `email_verified` claim is false attempts to access the onboarding flow
- **THEN** the system redirects them to a "confirm your email" screen instead of the onboarding form

#### Scenario: Verified user proceeds to onboarding as before
- **WHEN** an authenticated user whose `email_verified` claim is true accesses the onboarding flow
- **THEN** the system behaves exactly as it did before this change, with no additional gate

### Requirement: Login remains available to unverified users
The system SHALL allow a user with an unverified email to authenticate successfully; the verification gate SHALL apply only to onboarding and any capability that depends on it, not to login itself.

#### Scenario: Unverified user logs in successfully
- **WHEN** a registered but unverified user submits correct credentials to `POST /login`
- **THEN** authentication succeeds and a JWT is issued with `email_verified: false`, without blocking the login request itself

### Requirement: Verification state reflected in JWT claims
The system SHALL include an `email_verified` boolean claim in issued JWTs, kept consistent with the account's current verification state at the time of issuance.

#### Scenario: Claim reflects current state at token issuance
- **WHEN** a JWT is issued at register, login, or refresh
- **THEN** the token's `email_verified` claim matches the account's `email_verified` value in the database at that moment

### Requirement: Pre-existing accounts are treated as verified
The system SHALL treat all user accounts that existed before this capability was deployed as already email-verified, so they are not newly gated out of onboarding.

#### Scenario: Migration backfills existing accounts
- **WHEN** the email-verification migration runs against the existing users table
- **THEN** every pre-existing account is set to `email_verified = true`
