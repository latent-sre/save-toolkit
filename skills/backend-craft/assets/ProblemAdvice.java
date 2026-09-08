package com.example.web;

import java.net.URI;
import java.util.List;
import java.util.Map;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
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
 * shape.
 */
@RestControllerAdvice
public class ProblemAdvice extends ResponseEntityExceptionHandler {

    private static final String TYPE_BASE = "https://errors.example.internal/";

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers,
            HttpStatusCode status, WebRequest request) {
        // 422, not the framework's default 400: the body was well formed and its values failed
        // validation. valueOf works on Framework 6 and 7; UNPROCESSABLE_CONTENT starts in 7.
        ProblemDetail body = ProblemDetail.forStatusAndDetail(
                HttpStatusCode.valueOf(422), "The request failed validation.");
        body.setType(URI.create(TYPE_BASE + "validation-failed"));
        body.setTitle("Validation failed");
        body.setProperty("errors", ex.getBindingResult().getFieldErrors().stream()
                .map(error -> Map.of(
                        "loc", List.of("body", error.getField()),
                        "msg", String.valueOf(error.getDefaultMessage())))
                .toList());
        return ResponseEntity.status(422).headers(headers).body(body);
    }

    @ExceptionHandler(Exception.class)
    ProblemDetail handleUnexpected(Exception ex) {
        // Never ex.getMessage(): it leaks internals to the caller. Log it instead.
        ProblemDetail body = ProblemDetail.forStatusAndDetail(
                HttpStatus.INTERNAL_SERVER_ERROR, "The request could not be completed.");
        body.setType(URI.create(TYPE_BASE + "internal-server-error"));
        body.setTitle("Internal server error");
        return body;
    }
}
