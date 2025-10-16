package com.emf;

import io.vertx.core.AbstractVerticle;
import io.vertx.core.Vertx;
import io.vertx.core.http.HttpServer;
import io.vertx.ext.web.Router;
import io.vertx.ext.web.handler.BodyHandler;
import com.emf.service.EmfService;
import com.emf.service.DynamicRouteGenerator;

public class Main extends AbstractVerticle {
    private final EmfService emfService;
    private final DynamicRouteGenerator routeGenerator;

    public Main() {
        this.emfService = new EmfService();
        this.routeGenerator = new DynamicRouteGenerator(emfService);
    }

    @Override
    public void start() {
        HttpServer server = vertx.createHttpServer();
        Router router = Router.router(vertx);
        router.route().handler(BodyHandler.create().setUploadsDirectory("uploads"));

        // Register stateless, fixed routes
        routeGenerator.generateRoutes(router);

        server.requestHandler(router).listen(8080, http -> {
            if (http.succeeded()) {
                System.out.println("Server started on port 8080");
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