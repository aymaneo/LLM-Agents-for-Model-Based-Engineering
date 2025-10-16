package com.emf.service;

import org.eclipse.emf.ecore.*;
import org.eclipse.emf.ecore.resource.Resource;
import io.vertx.ext.web.Router;
import io.vertx.ext.web.FileUpload;
import io.vertx.core.json.JsonObject;
import java.util.*;

/**
 * StatelessRouteGenerator exposes a fixed set of routes that work for any EMF metamodel.
 * It does not generate per-class routes; instead, it uses generic path params
 * like {eClassName}, {id}, and {featureName} to operate on any model.
 */
public class StatelessRouteGenerator {
    private final EmfService emfService;
    private final SessionManager sessionManager;

    public StatelessRouteGenerator(EmfService emfService, SessionManager sessionManager) {
        this.emfService = emfService;
        this.sessionManager = sessionManager;
    }

    /**
     * Register all fixed routes up front (no dynamic route generation).
     */
    public void generateRoutes(Router router) {
        // Start a session by uploading a metamodel (.ecore)
        router.post("/metamodel/start").handler(ctx -> {
            List<FileUpload> files = ctx.fileUploads();
            if (files.isEmpty()) {
                ctx.response().setStatusCode(400).end("No metamodel file uploaded");
                return;
            }
            try {
                Resource metamodelResource = emfService.loadResource(files.get(0).uploadedFileName());
                String sessionId = sessionManager.createSession(metamodelResource);

                // Immediately create and save the empty resource (XMI)
                Resource resource = sessionManager.getSessionResource(sessionId);
                if (resource != null) {
                    resource.save(null);
                }

                Map<String, Object> response = new HashMap<>();
                response.put("sessionId", sessionId);
                response.put("routes", getFixedRoutesDescription());
                ctx.json(response);
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Introspection: list features of an EClass
        router.get("/metamodel/:sessionId/:eClassName/features").handler(ctx -> {
            String sessionId = ctx.pathParam("sessionId");
            String eClassName = ctx.pathParam("eClassName");
            try {
                EPackage ePackage = sessionManager.getMetamodel(sessionId);
                if (ePackage == null) {
                    ctx.response().setStatusCode(404).end("Session not found");
                    return;
                }
                EClass eClass = (EClass) ePackage.getEClassifier(eClassName);
                if (eClass == null) {
                    ctx.response().setStatusCode(404).end("EClass not found: " + eClassName);
                    return;
                }
                List<Map<String, Object>> features = new ArrayList<>();
                for (EStructuralFeature f : eClass.getEAllStructuralFeatures()) {
                    Map<String, Object> item = new HashMap<>();
                    item.put("name", f.getName());
                    item.put("many", f.isMany());
                    if (f instanceof EAttribute) {
                        item.put("kind", "attribute");
                        item.put("type", f.getEType() != null ? f.getEType().getName() : null);
                    } else if (f instanceof EReference) {
                        EReference r = (EReference) f;
                        item.put("kind", "reference");
                        item.put("type", r.getEReferenceType() != null ? r.getEReferenceType().getName() : null);
                        item.put("containment", r.isContainment());
                    } else {
                        item.put("kind", "structuralFeature");
                        item.put("type", f.getEType() != null ? f.getEType().getName() : null);
                    }
                    features.add(item);
                }
                ctx.json(Map.of("eClass", eClassName, "features", features));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Introspection: read all feature values of an instance
        router.get("/metamodel/:sessionId/:eClassName/:id").handler(ctx -> {
            String sessionId = ctx.pathParam("sessionId");
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            try {
                Resource resource = sessionManager.getSessionResource(sessionId);
                if (resource == null) {
                    ctx.response().setStatusCode(404).end("Session not found");
                    return;
                }
                EObject target = findObjectById(resource, Integer.parseInt(id));
                if (target == null) {
                    ctx.response().setStatusCode(404).end("Object not found");
                    return;
                }
                if (!target.eClass().getName().equals(eClassName)) {
                    ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName);
                    return;
                }
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("id", target.hashCode());
                payload.put("eClass", target.eClass().getName());
                Map<String, Object> values = new LinkedHashMap<>();
                for (EStructuralFeature f : target.eClass().getEAllStructuralFeatures()) {
                    Object v = target.eGet(f);
                    Object serial;
                    if (f instanceof EAttribute) {
                        if (f.isMany()) {
                            List<?> list = (List<?>) v;
                            serial = list == null ? List.of() : new ArrayList<>(list);
                        } else {
                            serial = v;
                        }
                    } else if (f instanceof EReference) {
                        if (f.isMany()) {
                            List<?> list = (List<?>) v;
                            List<Object> ids = new ArrayList<>();
                            if (list != null) {
                                for (Object o : list) {
                                    if (o instanceof EObject) ids.add(((EObject) o).hashCode());
                                }
                            }
                            serial = ids;
                        } else {
                            if (v instanceof EObject) serial = ((EObject) v).hashCode(); else serial = null;
                        }
                    } else {
                        serial = String.valueOf(v);
                    }
                    values.put(f.getName(), serial);
                }
                payload.put("values", values);
                ctx.json(payload);
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Create a new instance of an EClass within a session
        router.post("/metamodel/:sessionId/:eClassName").handler(ctx -> {
            String sessionId = ctx.pathParam("sessionId");
            String eClassName = ctx.pathParam("eClassName");
            try {
                EPackage ePackage = sessionManager.getMetamodel(sessionId);
                if (ePackage == null) {
                    ctx.response().setStatusCode(404).end("Session not found");
                    return;
                }
                EClass eClass = (EClass) ePackage.getEClassifier(eClassName);
                if (eClass == null) {
                    ctx.response().setStatusCode(404).end("EClass not found: " + eClassName);
                    return;
                }

                EObject newInstance = ePackage.getEFactoryInstance().create(eClass);
                Resource resource = sessionManager.getSessionResource(sessionId);
                if (resource == null) {
                    resource = emfService.createEmptyResource();
                    sessionManager.setSessionResource(sessionId, resource);
                }
                resource.getContents().add(newInstance);
                resource.save(null);
                ctx.json(Map.of("status", "created", "id", newInstance.hashCode()));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Update a structural feature (attribute/reference) on a target object
        router.put("/metamodel/:sessionId/:eClassName/:id/:featureName").handler(ctx -> {
            String sessionId = ctx.pathParam("sessionId");
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            String featureName = ctx.pathParam("featureName");
            try {
                Resource resource = sessionManager.getSessionResource(sessionId);
                if (resource == null) {
                    ctx.response().setStatusCode(404).end("Session not found");
                    return;
                }
                EObject target = findObjectById(resource, Integer.parseInt(id));
                if (target == null) {
                    ctx.response().setStatusCode(404).end("Object not found");
                    return;
                }
                if (!target.eClass().getName().equals(eClassName)) {
                    ctx.response().setStatusCode(400).end("Eclass is not found: " + eClassName);
                    return;
                }
                EStructuralFeature feature = target.eClass().getEStructuralFeature(featureName);
                if (feature == null) {
                    ctx.response().setStatusCode(404).end("Feature not found: " + featureName);
                    return;
                }
                JsonObject body = ctx.body().asJsonObject();
                Object value = body.getValue("value");

                if (feature instanceof EAttribute) {
                    EAttribute attribute = (EAttribute) feature;
                    EDataType dataType = attribute.getEAttributeType();
                    if (attribute.isMany()) {
                        List<Object> values = new ArrayList<>();
                        if (value instanceof List) {
                            for (Object item : (List<?>) value) {
                                values.add(dataType.getEPackage().getEFactoryInstance()
                                    .createFromString(dataType, item.toString()));
                            }
                        }
                        value = values;
                    } else {
                        try {
                            String stringValue = value.toString();
                            Object parsedValue;

                            // Ensure instance class is set for common Ecore types
                            if (dataType.getInstanceClass() == null) {
                                String typeName = dataType.getName();
                                switch (typeName) {
                                    case "String":
                                    case "EString":
                                        dataType.setInstanceClass(String.class);
                                        break;
                                    case "int":
                                    case "Integer":
                                    case "EInt":
                                        dataType.setInstanceClass(int.class);
                                        break;
                                    case "boolean":
                                    case "Boolean":
                                    case "EBoolean":
                                        dataType.setInstanceClass(boolean.class);
                                        break;
                                    case "float":
                                    case "Float":
                                    case "EFloat":
                                        dataType.setInstanceClass(float.class);
                                        break;
                                    case "double":
                                    case "Double":
                                    case "EDouble":
                                        dataType.setInstanceClass(double.class);
                                        break;
                                    case "long":
                                    case "Long":
                                    case "ELong":
                                        dataType.setInstanceClass(long.class);
                                        break;
                                    default:
                                        dataType.setInstanceClass(String.class);
                                        break;
                                }
                            }

                            parsedValue = dataType.getEPackage().getEFactoryInstance()
                                .createFromString(dataType, stringValue);

                            if (parsedValue == null && stringValue != null && !stringValue.isEmpty()) {
                                ctx.response().setStatusCode(400)
                                    .end("Invalid value for type " + dataType.getName() + ": " + stringValue);
                                return;
                            }

                            value = parsedValue;
                        } catch (Exception ex) {
                            ctx.response().setStatusCode(400)
                                .end("Failed to convert value to type " + dataType.getName() + ": " + ex.getMessage());
                            return;
                        }
                    }
                } else if (feature instanceof EReference) {
                    EReference reference = (EReference) feature;
                    if (reference.isMany()) {
                        List<EObject> refs = new ArrayList<>();
                        if (value instanceof List) {
                            for (Object item : (List<?>) value) {
                                EObject ref = findObjectById(resource, Integer.parseInt(item.toString()));
                                if (ref != null) {
                                    refs.add(ref);
                                }
                            }
                        }
                        value = refs;
                    } else {
                        EObject ref = findObjectById(resource, Integer.parseInt(value.toString()));
                        if (ref == null) {
                            ctx.response().setStatusCode(400).end("Referenced object not found");
                            return;
                        }
                        value = ref;
                    }
                }

                target.eSet(feature, value);
                resource.save(null);
                ctx.json(Map.of("status", "updated"));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Delete an object by ID
        router.delete("/metamodel/:sessionId/:eClassName/:id").handler(ctx -> {
            String sessionId = ctx.pathParam("sessionId");
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            try {
                Resource resource = sessionManager.getSessionResource(sessionId);
                if (resource == null) {
                    ctx.response().setStatusCode(404).end("Session not found");
                    return;
                }
                EObject target = findObjectById(resource, Integer.parseInt(id));
                if (target == null) {
                    ctx.response().setStatusCode(404).end("Object not found");
                    return;
                }
                if (!target.eClass().getName().equals(eClassName)) {
                    ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName);
                    return;
                }
                resource.getContents().remove(target);
                resource.save(null);
                ctx.json(Map.of("status", "deleted"));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Clear/delete a feature value
        router.delete("/metamodel/:sessionId/:eClassName/:id/:featureName").handler(ctx -> {
            String sessionId = ctx.pathParam("sessionId");
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            String featureName = ctx.pathParam("featureName");
            try {
                Resource resource = sessionManager.getSessionResource(sessionId);
                if (resource == null) {
                    ctx.response().setStatusCode(404).end("Session not found");
                    return;
                }
                EObject target = findObjectById(resource, Integer.parseInt(id));
                if (target == null) {
                    ctx.response().setStatusCode(404).end("Object not found");
                    return;
                }
                if (!target.eClass().getName().equals(eClassName)) {
                    ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName);
                    return;
                }
                EStructuralFeature feature = target.eClass().getEStructuralFeature(featureName);
                if (feature == null) {
                    ctx.response().setStatusCode(404).end("Feature not found: " + featureName);
                    return;
                }
                if (feature.isMany()) {
                    ((List<?>) target.eGet(feature)).clear();
                } else {
                    target.eUnset(feature);
                }
                resource.save(null);
                ctx.json(Map.of("status", "cleared"));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });
    }

    private Map<String, Object> getFixedRoutesDescription() {
        Map<String, Object> spec = new HashMap<>();
        spec.put("openapi", "3.0.0");
        spec.put("info", Map.of("title", "EMF Stateless API", "version", "1.0.0"));
        Map<String, Object> paths = new HashMap<>();
        paths.put("/metamodel/start", Map.of(
            "post", Map.of("summary", "Upload a metamodel and start a session")
        ));
        paths.put("/metamodel/{sessionId}/{eClassName}", Map.of(
            "post", Map.of("summary", "Create instance of EClass in session")
        ));
        paths.put("/metamodel/{sessionId}/{eClassName}/{id}/{featureName}", Map.of(
            "put", Map.of("summary", "Update feature value of instance"),
            "delete", Map.of("summary", "Clear feature value of instance")
        ));
        paths.put("/metamodel/{sessionId}/{eClassName}/{id}", Map.of(
            "delete", Map.of("summary", "Delete instance")
        ));
        spec.put("paths", paths);
        return spec;
    }

    private EObject findObjectById(Resource resource, int id) {
        for (EObject obj : resource.getContents()) {
            if (obj.hashCode() == id) {
                return obj;
            }
        }
        return null;
    }
}
