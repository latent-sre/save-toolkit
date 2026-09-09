# Spring problem-response contract fixture

This fixture compiles `skills/backend-craft/assets/ProblemAdvice.java` directly. A real Spring MVC
application context, Bean Validation provider, method-security proxy and security filter chain
exercise the HTTP contract through MockMvc. The test authentication principal is injected locally;
no external identity provider or network service is involved.

Requires Java 17+ and Maven. The POM pins the test dependencies and defaults to Framework 6.2.10
with Security 6.5.3. Run from the repository root:

```text
mvn -B -ntp -f scripts/fixtures/spring-problem/pom.xml test
mvn -B -ntp -f scripts/fixtures/spring-problem/pom.xml '-Dspring.version=7.0.9' '-Dspring-security.version=7.0.0' clean test
```

Both runs use JUnit 6.0.3 and Servlet API 6.1.0, matching
[Framework 7.0.9's dependency baseline](https://github.com/spring-projects/spring-framework/blob/v7.0.9/framework-platform/framework-platform.gradle).
JUnit 6 retains the older store methods called by Framework 6.2; it requires Java 17 and Maven
Surefire 3.0.0 or later. The POM pins Surefire 3.5.3 and explicitly aligns the JUnit launcher.

The 18 cases cover method- and filter-level 401/403 through the configured security handlers,
authentication exceptions and challenge headers, successful authorization, field/object errors
through both validation paths, constrained query/path/header parameters and public aliases, valid
input, malformed JSON, invalid server return values and redacted unexpected failures. They establish the shipped advice's
behavior; they do not validate an application's own identity provider, authorization policy,
logging, `/error` mapping or deployment.

The asset requires `spring-security-core`. Its validation locations use `body`, `query`, `path`
and `header` plus field/parameter names. Other parameter kinds use their zero-based method parameter
index; cross-parameter constraints use `parameters`. Adapt these locations to an existing client
contract when integrating the starter.

For [Docker-backed verification](../../../docs/docker-verification.md), mount the repository
read-only and use `-Dfixture.build=/build` with a writable container-local build directory. A
task-specific Maven cache can be warmed with the pinned dependencies, then reused with network
disabled and `mvn -o`. Pass property options as quoted arguments in PowerShell. For example, using
an already cached official image and Maven cache:

```powershell
docker run --rm --network none --mount "type=bind,source=$PWD,target=/workspace,readonly" --mount type=volume,source=spring-problem-task-cache,target=/maven-cache --tmpfs /build maven:3.9.9-eclipse-temurin-17@sha256:f58d59b6273e785ac0a4477f6e9b5ba1d7731c75b906c0f7b34076f1851318cc mvn -o -B -ntp -f /workspace/scripts/fixtures/spring-problem/pom.xml '-Dmaven.repo.local=/maven-cache' '-Dfixture.build=/build' test
```

To exercise a historical asset against these same tests, provide an isolated directory containing
only that revision's `ProblemAdvice.java` through `-Dproblem.source=/path/to/asset`. Production
source remains untouched; use a fresh build directory for each candidate.
