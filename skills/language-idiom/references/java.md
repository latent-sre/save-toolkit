# Java idiom

Match the repo's existing tooling first; defaults below apply when none is set.

## Establish the version contract first
- **Read the build file before reasoning about language behavior** — `maven.compiler.release` in
  `pom.xml` or `java.toolchain.languageVersion` in Gradle. It gates version-dependent features:
  records (16), sealed types (17), pattern matching for `switch` and virtual threads (21), unnamed
  variables (22), flexible constructor bodies and module imports (25). Don't infer from whichever
  `java` is on `PATH`.
- **The PCF Java buildpack picks the JRE from its own config** (`JBP_CONFIG_OPEN_JDK_JRE`), not from
  the build file — check the two agree before blaming the code for a `ClassFormatError`.
- Current LTS line: 17, 21, 25 (25 GA 2025-09-16). Spring Boot 3 and 4 both need 17+; virtual
  threads need 21+. *[sourced: openjdk.org/projects/jdk/25; reviewed 2026-08-21]* The team's
  deployed version is `[unverified]` — read it from the repo.

## Style & tooling
- **Format with a checked-in formatter** (Spotless driving google-java-format or palantir-java-format)
  enforced in CI; don't hand-format.
- **Static analysis in the build**: Error Prone + NullAway, and `-Xlint:all` treated as errors.
- **Records for data carriers**, with a compact constructor for invariants. **Sealed interfaces +
  exhaustive `switch`** for closed hierarchies — the compiler then refuses a missing case, which is
  the whole point; a `default` branch throws that away.
- **Package by feature, not by layer** (`orders/`, not `controllers/`). A package called `util` or
  `common` hides unrelated responsibilities.

## Nullability
- **Annotate packages `@NullMarked`** (JSpecify) and mark the exceptions `@Nullable`; run NullAway so a
  violation fails the build instead of throwing in prod. Spring Framework 7 / Boot 4 APIs are
  JSpecify-annotated, so the checker understands framework return types. JSpecify annotations are
  `TYPE_USE`: `List<@Nullable String>` and `@Nullable List<String>` mean different things.
  *[sourced: spring-framework `core/null-safety.adoc`; reviewed 2026-08-21]*
- **`Optional` is a return type** — never a field, parameter, or collection element. `.get()` without
  a presence check is a null check with extra steps; use `orElseThrow`, `map`, `orElse`.

## Errors
- **Unchecked for programming errors and unrecoverable failures**; checked only when every caller can
  genuinely recover — rare. Don't catch `Exception` to log-and-continue.
- **Never swallow `InterruptedException`** — restore the flag (`Thread.currentThread().interrupt()`)
  or rethrow, or the thread can't be stopped.
- **`try-with-resources` for every `AutoCloseable`.** Wrap with the cause
  (`new DomainException("…", e)`); never `e.printStackTrace()`.

## Concurrency
- **Virtual threads for blocking I/O** (21+): one task per thread, no pool to size. Don't pool them;
  bound concurrency with a `Semaphore` instead. Before Java 24, `synchronized` around I/O pins the
  carrier thread — use `ReentrantLock`; Spring recommends 24+ for this reason. *[sourced: Spring Boot
  `spring-application.adoc`; reviewed 2026-08-21]*
- Prefer immutable values; `ConcurrentHashMap` over synchronized wrappers; `AtomicX` for counters.
  **`ThreadLocal` leaks on pooled threads** and is expensive per virtual thread — pass context
  explicitly.
- **Structured concurrency is still preview in 25** — don't ship it behind `--enable-preview`.
  *[sourced: openjdk.org JDK 25 JEPs-since-21; reviewed 2026-08-21]*

## Correctness traps
- **`==` on boxed types compares references.** `Integer` caches −128..127, so the test passes and
  prod fails at 128. Use `.equals()` or unbox.
- **`List.of` / `Map.of` are immutable and reject `null`** — the `UnsupportedOperationException` or
  NPE fires at the call site, far from where the collection was built.
- **`java.time` only**: `Instant` for storage (UTC), `ZonedDateTime` for display; never `Date` or
  `Calendar`. `LocalDateTime` has no zone — it is a wall-clock reading, not a point in time.
- **Record `equals`/`hashCode` are component-wise, except arrays** (compared by reference). Use a
  `List` component.
- **`Collectors.toMap` throws on duplicate keys** — pass a merge function. A stream is single-use;
  don't mutate shared state inside `map`/`forEach`.
- String concatenation in a loop → `StringBuilder`; `"…".formatted(…)` and text blocks for templates.

## Logging
- **SLF4J, parameterized**: `log.info("order={} status={}", id, status)` — never concatenate; the
  string is built even when the level is off. MDC carries the correlation id. Never log secrets or
  full request bodies; the `obs-logs` skill owns redaction.

## Tests
- **JUnit Jupiter — currently 6.x** *[sourced: Maven Central `org.junit.jupiter:junit-jupiter`
  6.1.3, checked 2026-08-21]*; AssertJ for assertions; Mockito only for collaborators you don't own.
  `@ParameterizedTest` for tables, `@Nested` to group. See the [tests-first process](./tdd.md).
  Slice and integration tests against Spring are in the `backend-craft` Spring Boot reference.

## Build & PCF runtime
- **Wrapper checked in** (`./mvnw` / `./gradlew`); versions come from the Spring Boot BOM, not
  hand-pinned; plugin versions pinned for reproducibility.
- **The Java buildpack's memory calculator sizes the JVM from the container's `$MEMORY_LIMIT` before
  every start**: heap (`-Xmx`/`-Xms`), metaspace, thread stacks (`-Xss` × `stack_threads`, default
  250), code cache, direct memory. Three consequences:
  1. `cf scale -m` needs a **restart, not a restage** — the numbers are recomputed at start.
  2. Pinning `-Xmx` yourself does not opt out: since calculator v4 the container must still fit
     heap **plus** non-heap, or the app fails at start with `required memory … is greater than …
     available for allocation`. Fix the thread count or the container size, not the heap flag.
  3. The staging log line `Loaded Classes: N, Threads: 300` is the calculator's input; tune
     `stack_threads` via `JBP_CONFIG_OPEN_JDK_JRE` rather than hand-setting `-Xss`.

  A container memory kill (the platform's out-of-memory exit, no JVM stack trace) is total RSS over
  the limit; a JVM `OutOfMemoryError` is heap exhaustion. They are diagnosed differently — the first
  is usually native memory (threads, direct buffers, metaspace), not heap. *[sourced:
  cloudfoundry/java-buildpack `docs/IMPLEMENTING_JRES.md`, `docs/jre-open_jdk_jre.md`,
  `RUBY_VS_GO_BUILDPACK_COMPARISON.md`; reviewed 2026-08-21]*

## Definition of done
Formatter clean · Error Prone/NullAway clean · `-Xlint` resolved · `./mvnw verify` or
`./gradlew check` green.
