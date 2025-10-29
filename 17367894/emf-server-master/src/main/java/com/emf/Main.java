package com.emf;

import io.vertx.core.AbstractVerticle;
import io.vertx.core.Vertx;
import io.vertx.core.http.HttpServer;
import io.vertx.ext.web.Router;
import io.vertx.ext.web.handler.BodyHandler;
import com.emf.service.EmfService;
import com.emf.service.SessionManager;
import com.emf.service.StatelessRouteGenerator;

public class Main extends AbstractVerticle {
    private final EmfService emfService;
    private final SessionManager sessionManager;
    private final StatelessRouteGenerator routeGenerator;

    public Main() {
        this.emfService = new EmfService();
        this.sessionManager = new SessionManager();
    this.routeGenerator = new StatelessRouteGenerator(emfService, sessionManager);
    }

    @Override
    public void start() {
        HttpServer server = vertx.createHttpServer();
        Router router = Router.router(vertx);
        router.route().handler(BodyHandler.create().setUploadsDirectory("uploads"));

    // Register fixed, stateless routes (no per-metamodel dynamic generation)
        routeGenerator.generateRoutes(router);

    server.requestHandler(router).listen(8095, http -> {
            if (http.succeeded()) {
        System.out.println("Server started on port 8095");
            } else {
                System.out.println("Failed to start server: " + http.cause());
            }
        });
    }

    public static void main(String[] args) {
        Vertx vertx = Vertx.vertx();
        vertx.deployVerticle(new Main());
    }
} 