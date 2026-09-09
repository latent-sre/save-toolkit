package com.example.web;

import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.springframework.context.MessageSourceResolvable;
import org.springframework.core.MethodParameter;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * One RFC 9457 shape everywhere.
 *
 * <p>Because this advice extends {@link ResponseEntityExceptionHandler}, Boot's own problem-details
 * handler is not registered even with {@code spring.mvc.problemdetails.enabled=true}; the
 * framework's exceptions (unknown route, unsupported media type) are already mapped here.
 *
 * <p>What this advice cannot reach: Spring Security's filter-chain 401/403 and anything that falls
 * through to {@code /error} still render the error-attributes body — give the
 * {@code AuthenticationEntryPoint} and {@code AccessDeniedHandler} the same {@code ProblemDetail}
 * shape. Method-security exceptions raised inside MVC must propagate to those handlers too.
 * This starter requires spring-security-core and Spring Framework 6.2 or 7.
 */
@RestControllerAdvice
public class ProblemAdvice extends ResponseEntityExceptionHandler {

    private static final String TYPE_BASE = "https://errors.example.internal/";

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers,
            HttpStatusCode status, WebRequest request) {
        return validationProblem(ex.getBindingResult().getAllErrors().stream()
                .map(error -> validationError(List.of("body"), error)).toList(), headers);
    }

    @Override
    protected ResponseEntity<Object> handleHandlerMethodValidationException(
            HandlerMethodValidationException ex, HttpHeaders headers,
            HttpStatusCode status, WebRequest request) {
        // Invalid server output is a 500, not a client input failure.
        if (ex.isForReturnValue()) {
            return super.handleHandlerMethodValidationException(ex, headers, status, request);
        }
        List<Map<String, Object>> errors = new ArrayList<>();
        for (var result : ex.getParameterValidationResults()) {
            List<String> location = parameterLocation(result.getMethodParameter());
            result.getResolvableErrors().forEach(error -> errors.add(validationError(location, error)));
        }
        ex.getCrossParameterValidationResults().forEach(
                error -> errors.add(validationError(List.of("parameters"), error)));
        return validationProblem(errors, headers);
    }

    private static ResponseEntity<Object> validationProblem(
            List<Map<String, Object>> errors, HttpHeaders headers) {
        // valueOf works on Framework 6 and 7; UNPROCESSABLE_CONTENT starts in 7.
        ProblemDetail body = ProblemDetail.forStatusAndDetail(
                HttpStatusCode.valueOf(422), "The request failed validation.");
        body.setType(URI.create(TYPE_BASE + "validation-failed"));
        body.setTitle("Validation failed");
        body.setProperty("errors", errors);
        return ResponseEntity.status(422).headers(headers).body(body);
    }

    private static Map<String, Object> validationError(
            List<String> location, MessageSourceResolvable error) {
        List<String> path = new ArrayList<>(location);
        if (error instanceof FieldError field) {
            path.add(field.getField());
        }
        return Map.of("loc", path, "msg", String.valueOf(error.getDefaultMessage()));
    }

    private static List<String> parameterLocation(MethodParameter parameter) {
        if (parameter.hasParameterAnnotation(RequestBody.class)) {
            return List.of("body");
        }
        RequestParam query = parameter.getParameterAnnotation(RequestParam.class);
        if (query != null) {
            return List.of("query", parameterName(parameter, query.name(), query.value()));
        }
        PathVariable path = parameter.getParameterAnnotation(PathVariable.class);
        if (path != null) {
            return List.of("path", parameterName(parameter, path.name(), path.value()));
        }
        RequestHeader header = parameter.getParameterAnnotation(RequestHeader.class);
        if (header != null) {
            return List.of("header", parameterName(parameter, header.name(), header.value()));
        }
        return List.of("parameter", Integer.toString(parameter.getParameterIndex()));
    }

    private static String parameterName(MethodParameter parameter, String name, String value) {
        if (!name.isEmpty()) return name;
        if (!value.isEmpty()) return value;
        String discovered = parameter.getParameterName();
        return discovered != null ? discovered : Integer.toString(parameter.getParameterIndex());
    }

    @Override
    protected ResponseEntity<Object> createResponseEntity(
            Object body, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        // Spring 7 omits the default type; the house schema requires it explicitly.
        if (body instanceof ProblemDetail problem && problem.getType() == null) {
            problem.setType(URI.create("about:blank"));
        }
        return super.createResponseEntity(body, headers, status, request);
    }

    @ExceptionHandler(Exception.class)
    ProblemDetail handleUnexpected(Exception ex) throws Exception {
        if (ex instanceof AccessDeniedException || ex instanceof AuthenticationException) {
            // Leave 401/403 and their protocol headers to the configured security handlers.
            throw ex;
        }
        // Never ex.getMessage(): it leaks internals to the caller. Log it instead.
        ProblemDetail body = ProblemDetail.forStatusAndDetail(
                HttpStatus.INTERNAL_SERVER_ERROR, "The request could not be completed.");
        body.setType(URI.create(TYPE_BASE + "internal-server-error"));
        body.setTitle("Internal server error");
        return body;
    }
}
