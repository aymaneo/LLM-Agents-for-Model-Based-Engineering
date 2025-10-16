package com.emf.service;

import io.vertx.ext.web.Router;

public class DynamicRouteGenerator {
    private final EmfService emfService;

    public DynamicRouteGenerator(EmfService emfService) {
        this.emfService = emfService;
    }

    // Backward-compatible constructor (session manager unused in stateless mode)
    public DynamicRouteGenerator(EmfService emfService, SessionManager sessionManager) {
        this.emfService = emfService;
    }

    public void generateRoutes(Router router) {
        // Delegate to stateless, fixed (non-dynamic) routes
        new StatelessRouteGenerator(emfService).generateRoutes(router);
    }
}