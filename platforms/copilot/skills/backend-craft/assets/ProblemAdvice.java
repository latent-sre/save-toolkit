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
 * <p>Set {@code spring.mvc.problemdetails.enabled=true} as well, or the framework's own exceptions
 * (unknown route, unsupported media type) still render as the default error-attributes body
 * instead of problem+json.
 */
@RestControllerAdvice
public class ProblemAdvice extends ResponseEntityExceptionHandler {

    private static final String TYPE_BASE = "https://errors.example.internal/";

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers,
            HttpStatusCode status, WebRequest request) {
        // 422, not the framework's default 400: the body was well formed and its values failed
        // validation. Spring Framework 6.2+ spells it UNPROCESSABLE_CONTENT (the RFC 9110 name);
        // older versions spell the same 422 UNPROCESSABLE_ENTITY.
        ProblemDetail body = ProblemDetail.forStatusAndDetail(
                HttpStatus.UNPROCESSABLE_CONTENT, "The request failed validation.");
        body.setType(URI.create(TYPE_BASE + "validation-failed"));
        body.setTitle("Validation failed");
        body.setProperty("errors", ex.getBindingResult().getFieldErrors().stream()
                .map(error -> Map.of(
                        "loc", List.of("body", error.getField()),
                        "msg", String.valueOf(error.getDefaultMessage())))
                .toList());
        return ResponseEntity.unprocessableEntity().body(body);
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
