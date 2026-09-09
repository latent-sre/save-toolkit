package com.example.web;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Constraint;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import jakarta.validation.Payload;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import java.io.IOException;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.test.context.junit.jupiter.web.SpringJUnitWebConfig;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.validation.Validator;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.WebApplicationContext;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@SpringJUnitWebConfig(ProblemAdviceTest.Config.class)
class ProblemAdviceTest {
    @Autowired WebApplicationContext context;
    private MockMvc mvc;
    private final ObjectMapper json = new ObjectMapper();

    @BeforeEach
    void setup() {
        mvc = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
    }

    @Test
    void methodDenialReachesAccessDeniedHandler() throws Exception {
        MvcResult result = mvc.perform(get("/secured").with(user("reader").roles("READER")))
                .andExpect(status().isForbidden())
                .andExpect(header().string("X-Error-Handler", "access-denied"))
                .andReturn();
        problem(result, 403);
    }

    @Test
    void anonymousMethodDenialReachesAuthenticationEntryPoint() throws Exception {
        MvcResult result = mvc.perform(get("/secured"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("X-Error-Handler", "entry-point"))
                .andExpect(header().string("WWW-Authenticate", "Bearer"))
                .andReturn();
        problem(result, 401);
    }

    @Test
    void authorizedMethodCallSucceeds() throws Exception {
        mvc.perform(get("/secured").with(user("admin").roles("ADMIN")))
                .andExpect(status().isOk());
    }

    @Test
    void authenticationExceptionReachesEntryPoint() throws Exception {
        MvcResult result = mvc.perform(get("/authentication-error"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("X-Error-Handler", "entry-point"))
                .andExpect(header().string("WWW-Authenticate", "Bearer"))
                .andReturn();
        problem(result, 401);
    }

    @Test
    void filterDenialKeepsAccessDeniedHandler() throws Exception {
        MvcResult result = mvc.perform(get("/filter-secured").with(user("reader").roles("READER")))
                .andExpect(status().isForbidden())
                .andExpect(header().string("X-Error-Handler", "access-denied"))
                .andReturn();
        problem(result, 403);
    }

    @Test
    void anonymousFilterDenialKeepsEntryPoint() throws Exception {
        MvcResult result = mvc.perform(get("/filter-secured"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("X-Error-Handler", "entry-point"))
                .andExpect(header().string("WWW-Authenticate", "Bearer"))
                .andReturn();
        problem(result, 401);
    }

    @Test
    void bodyFieldValidationHasLocation() throws Exception {
        JsonNode body = problem(mvc.perform(post("/body").contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"\"}")).andReturn(), 422);
        assertError(body, List.of("body", "name"), "must not be blank");
    }

    @ParameterizedTest
    @ValueSource(strings = {"/pair", "/combined?limit=1"})
    void objectValidationSurvivesBothValidationPaths(String path) throws Exception {
        JsonNode body = problem(mvc.perform(post(path).contentType(MediaType.APPLICATION_JSON)
                .content("{\"left\":\"a\",\"right\":\"b\"}")).andReturn(), 422);
        assertError(body, List.of("body"), "fields must match");
    }

    @ParameterizedTest
    @ValueSource(strings = {"/query?limit=0", "/path/0"})
    void methodInputValidationUses422(String path) throws Exception {
        JsonNode body = problem(mvc.perform(get(path)).andReturn(), 422);
        assertError(body, List.of(path.startsWith("/query") ? "query" : "path", "limit"),
                "must be greater than or equal to 1");
    }

    @Test
    void queryAliasUsesPublicParameterName() throws Exception {
        JsonNode body = problem(mvc.perform(get("/alias?count=0")).andReturn(), 422);
        assertError(body, List.of("query", "count"), "must be greater than or equal to 1");
    }

    @Test
    void headerValidationUsesPublicHeaderName() throws Exception {
        JsonNode body = problem(mvc.perform(get("/header").header("X-Cap", "0")).andReturn(), 422);
        assertError(body, List.of("header", "X-Cap"), "must be greater than or equal to 1");
    }

    @Test
    void combinedMethodValidationPreservesFieldErrors() throws Exception {
        JsonNode body = problem(mvc.perform(post("/combined?limit=1")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"left\":\"\",\"right\":\"\"}")).andReturn(), 422);
        assertError(body, List.of("body", "left"), "must not be blank");
        assertError(body, List.of("body", "right"), "must not be blank");
    }

    @Test
    void invalidReturnValueRemainsServerFailure() throws Exception {
        JsonNode body = problem(mvc.perform(get("/return")).andReturn(), 500);
        assertFalse(body.has("errors"), "server output constraints must not become client input errors");
    }

    @Test
    void malformedJsonRemains400() throws Exception {
        problem(mvc.perform(post("/body").contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":")).andReturn(), 400);
    }

    @Test
    void validInputSucceeds() throws Exception {
        mvc.perform(post("/combined?limit=1").contentType(MediaType.APPLICATION_JSON)
                .content("{\"left\":\"same\",\"right\":\"same\"}"))
                .andExpect(status().isOk());
        mvc.perform(get("/query?limit=1")).andExpect(status().isOk());
    }

    @Test
    void unexpectedFailureRemainsRedacted500() throws Exception {
        JsonNode body = problem(mvc.perform(get("/unexpected")).andReturn(), 500);
        assertFalse(body.toString().contains("private diagnostic"));
    }

    private JsonNode problem(MvcResult result, int status) throws Exception {
        assertEquals(status, result.getResponse().getStatus());
        assertTrue(MediaType.APPLICATION_PROBLEM_JSON.isCompatibleWith(
                MediaType.parseMediaType(result.getResponse().getContentType())));
        JsonNode body = json.readTree(result.getResponse().getContentAsString());
        assertEquals(status, body.path("status").asInt());
        assertTrue(body.path("type").isTextual(), () -> "Problem type missing from: " + body);
        assertTrue(body.path("title").isTextual(), () -> "Problem title missing from: " + body);
        return body;
    }

    private void assertError(JsonNode body, List<String> location, String message) {
        for (JsonNode error : body.path("errors")) {
            if (json.valueToTree(location).equals(error.path("loc"))
                    && message.equals(error.path("msg").asText())) {
                return;
            }
        }
        throw new AssertionError("Missing validation error " + location + ": " + message + " in " + body);
    }

    @Configuration
    @EnableWebMvc
    @EnableWebSecurity
    @EnableMethodSecurity
    @Import(ProblemAdvice.class)
    static class Config implements WebMvcConfigurer {
        @Bean Api api(SecuredService service) { return new Api(service); }
        @Bean SecuredService securedService() { return new SecuredService(); }
        @Bean LocalValidatorFactoryBean validator() { return new LocalValidatorFactoryBean(); }
        @Override public Validator getValidator() { return validator(); }

        @Bean
        SecurityFilterChain security(HttpSecurity http) throws Exception {
            return http.csrf(csrf -> csrf.disable())
                    .authorizeHttpRequests(auth -> auth.requestMatchers("/filter-secured").hasRole("ADMIN")
                            .anyRequest().permitAll())
                    .exceptionHandling(errors -> errors
                            .authenticationEntryPoint((request, response, exception) -> {
                                response.setHeader("WWW-Authenticate", "Bearer");
                                securityProblem(response, 401, "entry-point");
                            })
                            .accessDeniedHandler((request, response, exception) ->
                                    securityProblem(response, 403, "access-denied")))
                    .build();
        }

        private static void securityProblem(HttpServletResponse response, int status, String handler)
                throws IOException {
            response.setStatus(status);
            response.setContentType("application/problem+json");
            response.setHeader("X-Error-Handler", handler);
            response.getWriter().write("{\"type\":\"about:blank\",\"title\":\"Denied\",\"status\":" + status + "}");
        }
    }

    static class SecuredService {
        @PreAuthorize("hasRole('ADMIN')")
        public String read() { return "allowed"; }
    }

    @RestController
    static class Api {
        private final SecuredService service;
        Api(SecuredService service) { this.service = service; }
        @GetMapping("/secured") String secured() { return service.read(); }
        @GetMapping("/filter-secured") String filterSecured() { return "allowed"; }
        @GetMapping("/authentication-error")
        String authenticationError() { throw new BadCredentialsException("private diagnostic"); }
        @PostMapping("/body") Body body(@Valid @RequestBody Body body) { return body; }
        @PostMapping("/pair") Pair pair(@Valid @RequestBody Pair pair) { return pair; }
        @PostMapping("/combined")
        Pair combined(@Valid @RequestBody Pair pair, @RequestParam @Min(1) int limit) { return pair; }
        @GetMapping("/query") int query(@RequestParam @Min(1) int limit) { return limit; }
        @GetMapping("/alias") int alias(@RequestParam("count") @Min(1) int limit) { return limit; }
        @GetMapping("/header") int header(@RequestHeader(name = "X-Cap") @Min(1) int limit) { return limit; }
        @GetMapping("/path/{limit}") int path(@PathVariable @Min(1) int limit) { return limit; }
        @GetMapping("/return") @Min(1) int invalidReturn() { return 0; }
        @GetMapping("/unexpected") String unexpected() { throw new IllegalStateException("private diagnostic"); }
    }

    record Body(@NotBlank String name) {}
    @MatchingFields record Pair(@NotBlank String left, @NotBlank String right) {}

    @Target(ElementType.TYPE)
    @Retention(RetentionPolicy.RUNTIME)
    @Constraint(validatedBy = MatchingFieldsValidator.class)
    @interface MatchingFields {
        String message() default "fields must match";
        Class<?>[] groups() default {};
        Class<? extends Payload>[] payload() default {};
    }

    public static class MatchingFieldsValidator implements ConstraintValidator<MatchingFields, Pair> {
        @Override
        public boolean isValid(Pair value, ConstraintValidatorContext context) {
            return value == null || java.util.Objects.equals(value.left(), value.right());
        }
    }
}
