package com.emf.service;

import io.vertx.core.json.JsonArray;
import io.vertx.core.json.JsonObject;
import io.vertx.ext.web.Router;
import org.eclipse.emf.common.util.EList;
import org.eclipse.emf.ecore.*;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.util.EcoreUtil;

// import org.eclipse.emf.ecore.xmi.XMLResource;
import java.util.*;

public class StatelessRouteGenerator {
    private final EmfService emfService;

    public StatelessRouteGenerator(EmfService emfService) {
        this.emfService = emfService;
    }

    public void generateRoutes(Router router) {
        // Create an instance with optional nested content
        router.post("/model/:eClassName").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) {
                    ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required");
                    return;
                }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) {
                    ctx.response().setStatusCode(404).end("Metamodel not found or invalid");
                    return;
                }
                // Ensure the package is registered in both global and local registries
                if (ePackage.getNsURI() != null && !ePackage.getNsURI().isEmpty()) {
                    EPackage.Registry.INSTANCE.put(ePackage.getNsURI(), ePackage);
                }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) {
                    ctx.response().setStatusCode(404).end("EClass not found: " + eClassName);
                    return;
                }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                EObject instance = ePackage.getEFactoryInstance().create(eClass);
                JsonObject body = safeBody(ctx.body().asJsonObject());
                if (!body.isEmpty()) {
                    body.remove("metamodelPath");
                    body.remove("modelPath");
                    applyJsonToEObject(instance, body, resource);
                }
                resource.getContents().add(instance);
                resource.save(null);
                EStructuralFeature nameFeature = instance.eClass().getEStructuralFeature("name");
                String name = nameFeature != null ? (String)instance.eGet(nameFeature) : null;
                ctx.json(Map.of("name", name));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Update multiple features at once
        router.put("/model/:eClassName/:id").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) {
                    ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required");
                    return;
                }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) {
                    ctx.response().setStatusCode(404).end("Metamodel not found or invalid");
                    return;
                }
                if (ePackage.getNsURI() != null && !ePackage.getNsURI().isEmpty()) {
                    EPackage.Registry.INSTANCE.put(ePackage.getNsURI(), ePackage);
                }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) {
                    ctx.response().setStatusCode(404).end("EClass not found: " + eClassName);
                    return;
                }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                EObject target = findObjectByIdDeep(resource, id);
                if (target == null) { ctx.response().setStatusCode(404).end("Object not found"); return; }
                if (!target.eClass().getName().equals(eClassName)) { ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName); return; }

                JsonObject body = safeBody(ctx.body().asJsonObject());
                body.remove("metamodelPath"); body.remove("modelPath");
                if (!body.isEmpty()) applyJsonToEObject(target, body, resource);
                resource.save(null);
                ctx.json(Map.of("status", "updated"));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Per-feature update
        router.put("/model/:eClassName/:id/:featureName").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            String featureName = ctx.pathParam("featureName");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) {
                    ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required");
                    return;
                }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) { ctx.response().setStatusCode(404).end("Metamodel not found or invalid"); return; }
                if (ePackage.getNsURI() != null && !ePackage.getNsURI().isEmpty()) {
                    EPackage.Registry.INSTANCE.put(ePackage.getNsURI(), ePackage);
                }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) { ctx.response().setStatusCode(404).end("EClass not found: " + eClassName); return; }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                EObject target = findObjectByIdDeep(resource, id);
                if (target == null) { ctx.response().setStatusCode(404).end("Object not found"); return; }
                if (!target.eClass().getName().equals(eClassName)) { ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName); return; }
                EStructuralFeature feature = target.eClass().getEStructuralFeature(featureName);
                if (feature == null) { ctx.response().setStatusCode(404).end("Feature not found: " + featureName); return; }
                JsonObject body = safeBody(ctx.body().asJsonObject());
                if (!body.containsKey("value")) { ctx.response().setStatusCode(400).end("Body must contain 'value'"); return; }
                Object valueNode = body.getValue("value");
                Object value = parseFeatureValue(feature, valueNode, resource);
                setFeature(target, feature, value);
                resource.save(null);
                ctx.json(Map.of("status", "updated"));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Append to a feature (adds instead of replacing for multi-valued features)
        router.post("/model/:eClassName/:id/:featureName").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            String featureName = ctx.pathParam("featureName");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) {
                    ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required");
                    return;
                }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) { ctx.response().setStatusCode(404).end("Metamodel not found or invalid"); return; }
                if (ePackage.getNsURI() != null && !ePackage.getNsURI().isEmpty()) {
                    EPackage.Registry.INSTANCE.put(ePackage.getNsURI(), ePackage);
                }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) { ctx.response().setStatusCode(404).end("EClass not found: " + eClassName); return; }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                EObject target = findObjectByIdDeep(resource, id);
                if (target == null) { ctx.response().setStatusCode(404).end("Object not found"); return; }
                if (!target.eClass().getName().equals(eClassName)) { ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName); return; }
                EStructuralFeature feature = target.eClass().getEStructuralFeature(featureName);
                if (feature == null) { ctx.response().setStatusCode(404).end("Feature not found: " + featureName); return; }

                JsonObject body = safeBody(ctx.body().asJsonObject());
                if (!body.containsKey("value")) { ctx.response().setStatusCode(400).end("Body must contain 'value'"); return; }
                Object valueNode = body.getValue("value");
                Object value = parseFeatureValue(feature, valueNode, resource);

                if (feature.isMany()) {
                    @SuppressWarnings("unchecked")
                    EList<Object> list = (EList<Object>) target.eGet(feature);
                    if (value instanceof Collection<?>) list.addAll((Collection<?>) value);
                    else list.add(value);
                } else {
                    target.eSet(feature, value);
                }
                resource.save(null);
                ctx.json(Map.of("status", "added"));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Remove a specific element from a feature (by value for attributes, by id for references, or by index with ?index=)
        router.delete("/model/:eClassName/:id/:featureName/:itemKey").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            String featureName = ctx.pathParam("featureName");
            String itemKey = ctx.pathParam("itemKey");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) { ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required"); return; }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) { ctx.response().setStatusCode(404).end("Metamodel not found or invalid"); return; }
                if (ePackage.getNsURI() != null && !ePackage.getNsURI().isEmpty()) {
                    EPackage.Registry.INSTANCE.put(ePackage.getNsURI(), ePackage);
                }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) { ctx.response().setStatusCode(404).end("EClass not found: " + eClassName); return; }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                EObject target = findObjectByIdDeep(resource, id);
                if (target == null) { ctx.response().setStatusCode(404).end("Object not found"); return; }
                if (!target.eClass().getName().equals(eClassName)) { ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName); return; }
                EStructuralFeature feature = target.eClass().getEStructuralFeature(featureName);
                if (feature == null) { ctx.response().setStatusCode(404).end("Feature not found: " + featureName); return; }

                // Single-valued feature: clear if matches (or just clear)
                if (!feature.isMany()) {
                    target.eUnset(feature);
                    resource.save(null);
                    ctx.json(Map.of("status", "removed"));
                    return;
                }

                // Multi-valued feature: remove by index, value, or id
                String indexStr = getParam(ctx, "index");
                if (indexStr != null) {
                    try {
                        int idx = Integer.parseInt(indexStr);
                        @SuppressWarnings("unchecked")
                        EList<Object> list = (EList<Object>) target.eGet(feature);
                        if (idx < 0 || idx >= list.size()) { ctx.response().setStatusCode(404).end("Index out of bounds"); return; }
                        list.remove(idx);
                        resource.save(null);
                        ctx.json(Map.of("status", "removed"));
                        return;
                    } catch (NumberFormatException nfe) {
                        ctx.response().setStatusCode(400).end("Invalid index");
                        return;
                    }
                }

                if (feature instanceof EAttribute attr) {
                    // Remove by scalar value using EMF conversion
                    EDataType dt = attr.getEAttributeType();
                    Object toRemove = dt.getEPackage().getEFactoryInstance().createFromString(dt, itemKey);
                    @SuppressWarnings("unchecked")
                    EList<Object> list = (EList<Object>) target.eGet(feature);
                    boolean removed = list.remove(toRemove);
                    if (!removed) { ctx.response().setStatusCode(404).end("Value not found"); return; }
                } else if (feature instanceof EReference) {
                    EObject refObj = findObjectByIdDeep(resource, itemKey);
                    if (refObj == null) { ctx.response().setStatusCode(404).end("Referenced object not found"); return; }
                    @SuppressWarnings("unchecked")
                    EList<Object> list = (EList<Object>) target.eGet(feature);
                    boolean removed = list.remove(refObj);
                    if (!removed) { ctx.response().setStatusCode(404).end("Reference not in list"); return; }
                } else {
                    ctx.response().setStatusCode(400).end("Unsupported feature type");
                    return;
                }

                resource.save(null);
                ctx.json(Map.of("status", "removed"));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // List objects by class
        router.get("/model/:eClassName").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) {
                    ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required");
                    return;
                }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) { ctx.response().setStatusCode(404).end("Metamodel not found or invalid"); return; }
                if (ePackage.getNsURI() != null && !ePackage.getNsURI().isEmpty()) {
                    EPackage.Registry.INSTANCE.put(ePackage.getNsURI(), ePackage);
                }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) { ctx.response().setStatusCode(404).end("EClass not found: " + eClassName); return; }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                List<Map<String, Object>> items = allObjects(resource).stream()
                    .filter(o -> o.eClass().getName().equals(eClassName))
                    .map(o -> { 
                        EStructuralFeature nameFeature = o.eClass().getEStructuralFeature("name");
                        String name = nameFeature != null ? (String)o.eGet(nameFeature) : null;
                        Map<String, Object> result = new HashMap<>();
                        result.put("name", name);
                        return result;
                    })
                    .toList();
                ctx.json(items);
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Get object by id (shallow)
        router.get("/model/:eClassName/:id").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) {
                    ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required");
                    return;
                }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) { ctx.response().setStatusCode(404).end("Metamodel not found or invalid"); return; }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) { ctx.response().setStatusCode(404).end("EClass not found: " + eClassName); return; }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                EObject obj = findObjectByIdDeep(resource, id);
                if (obj == null || !obj.eClass().getName().equals(eClassName)) { ctx.response().setStatusCode(404).end("Object not found"); return; }
                EStructuralFeature nameFeature = obj.eClass().getEStructuralFeature("name");
                String name = nameFeature != null ? (String)obj.eGet(nameFeature) : null;
                ctx.json(Map.of("name", name, "eClass", obj.eClass().getName()));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Delete an object
        router.delete("/model/:eClassName/:id").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) { ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required"); return; }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) { ctx.response().setStatusCode(404).end("Metamodel not found or invalid"); return; }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) { ctx.response().setStatusCode(404).end("EClass not found: " + eClassName); return; }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                EObject target = findObjectByIdDeep(resource, id);
                if (target == null) { ctx.response().setStatusCode(404).end("Object not found"); return; }
                if (!target.eClass().getName().equals(eClassName)) { ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName); return; }
                EcoreUtil.delete(target, true);
                resource.save(null);
                ctx.json(Map.of("status", "deleted"));
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        // Clear feature value
        router.delete("/model/:eClassName/:id/:featureName").handler(ctx -> {
            String eClassName = ctx.pathParam("eClassName");
            String id = ctx.pathParam("id");
            String featureName = ctx.pathParam("featureName");
            try {
                String metamodelPath = getParam(ctx, "metamodelPath");
                String modelPath = getParam(ctx, "modelPath");
                if (metamodelPath == null || modelPath == null) { ctx.response().setStatusCode(400).end("metamodelPath and modelPath are required"); return; }
                EPackage ePackage = loadMetamodelPackage(metamodelPath);
                if (ePackage == null) { ctx.response().setStatusCode(404).end("Metamodel not found or invalid"); return; }
                EClass eClass = findEClassDeep(ePackage, eClassName);
                if (eClass == null) { ctx.response().setStatusCode(404).end("EClass not found: " + eClassName); return; }
                Resource resource = emfService.loadOrCreateModelResource(modelPath);
                EObject target = findObjectByIdDeep(resource, id);
                if (target == null) { ctx.response().setStatusCode(404).end("Object not found"); return; }
                if (!target.eClass().getName().equals(eClassName)) { ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName); return; }
                EStructuralFeature feature = target.eClass().getEStructuralFeature(featureName);
                if (feature == null) { ctx.response().setStatusCode(404).end("Feature not found: " + featureName); return; }
                if (feature.isMany()) {
                    @SuppressWarnings("unchecked")
                    EList<Object> list = (EList<Object>) target.eGet(feature);
                    list.clear();
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

    // ===== Helpers =====
    private JsonObject safeBody(JsonObject body) {
        return body == null ? new JsonObject() : body;
    }

    private void applyJsonToEObject(EObject target, JsonObject body, Resource resource) {
        // Apply features without setting ID
        for (EStructuralFeature f : target.eClass().getEAllStructuralFeatures()) {
            if (!body.containsKey(f.getName())) continue;
            Object node = body.getValue(f.getName());
            Object value = parseFeatureValue(f, node, resource);
            setFeature(target, f, value);
        }
    // Do not save here; caller will handle save
    }

    private void setFeature(EObject target, EStructuralFeature feature, Object value) {
        if (feature.isMany()) {
            @SuppressWarnings("unchecked")
            EList<Object> list = (EList<Object>) target.eGet(feature);
            list.clear();
            if (value instanceof Collection<?>) {
                list.addAll((Collection<?>) value);
            }
        } else {
            target.eSet(feature, value);
        }
        // Ensure any new objects get IDs
        if (value instanceof EObject) {
            if (EcoreUtil.getID((EObject)value) == null) {
                EcoreUtil.setID((EObject)value, "_" + UUID.randomUUID().toString());
            }
        } else if (value instanceof Collection<?>) {
            for (Object o : (Collection<?>)value) {
                if (o instanceof EObject && EcoreUtil.getID((EObject)o) == null) {
                    EcoreUtil.setID((EObject)o, "_" + UUID.randomUUID().toString());
                }
            }
        }
    }

    private Object parseFeatureValue(EStructuralFeature feature, Object node, Resource resource) {
        if (feature instanceof EAttribute attr) {
            return parseAttributeValue(attr, node);
        } else if (feature instanceof EReference ref) {
            return parseReferenceValue(ref, node, resource);
        }
        return null;
    }

    private Object parseAttributeValue(EAttribute attr, Object node) {
        EDataType dt = attr.getEAttributeType();
        EFactory factory = dt.getEPackage().getEFactoryInstance();
        if (attr.isMany()) {
            List<Object> out = new ArrayList<>();
            if (node instanceof JsonArray arr) {
                for (int i = 0; i < arr.size(); i++) {
                    Object v = arr.getValue(i);
                    if (v != null) out.add(factory.createFromString(dt, String.valueOf(v)));
                }
            } else if (node instanceof Collection<?> coll) {
                for (Object v : coll) {
                    if (v != null) out.add(factory.createFromString(dt, String.valueOf(v)));
                }
            } else if (node != null) {
                out.add(factory.createFromString(dt, String.valueOf(node)));
            }
            return out;
        } else {
            if (node == null) return null;
            return factory.createFromString(dt, String.valueOf(node));
        }
    }

    private Object parseReferenceValue(EReference ref, Object node, Resource resource) {
        if (ref.isMany()) {
            List<EObject> out = new ArrayList<>();
            if (node instanceof JsonArray arr) {
                for (int i = 0; i < arr.size(); i++) {
                    Object el = arr.getValue(i);
                    EObject eo = resolveRefElementIdOnly(el, resource);
                    if (eo != null) out.add(eo);
                }
            } else if (node instanceof Collection<?> coll) {
                for (Object el : coll) {
                    EObject eo = resolveRefElementIdOnly(el, resource);
                    if (eo != null) out.add(eo);
                }
            } else {
                EObject eo = resolveRefElementIdOnly(node, resource);
                if (eo != null) out.add(eo);
            }
            return out;
        } else {
            return resolveRefElementIdOnly(node, resource);
        }
    }

    private EObject resolveRefElementIdOnly(Object node, Resource resource) {
        if (node == null) return null;
        if (node instanceof String || node instanceof Number) {
            return findObjectByIdDeep(resource, String.valueOf(node));
        }
        if (node instanceof JsonObject jo && jo.containsKey("id")) {
            return findObjectByIdDeep(resource, String.valueOf(jo.getValue("id")));
        }
        return null;
    }
    
    // Removed advanced subtype resolution to keep API simple and generic

    /**
     * Finds an EObject by ID or hash in a resource.
     * Searches through all contents recursively.
     * 
     * @param resource The resource to search in
     * @param idOrHash The ID or hash to find
     * @return The found EObject or null if not found
     */
    private EObject findObjectByIdDeep(Resource resource, String nameOrId) {
        if (nameOrId == null || nameOrId.isEmpty()) {
            return null;
        }
        
        // Use name-based lookup instead of ID
        for (EObject root : resource.getContents()) {
            EObject found = findInTree(root, nameOrId);
            if (found != null) return found;
        }
        
        return null;
    }

    private EObject findInTree(EObject start, String name) {
        // Check if this object has a name feature and if it matches
        EStructuralFeature nameFeature = start.eClass().getEStructuralFeature("name");
        if (nameFeature != null && name.equals(start.eGet(nameFeature))) {
            return start;
        }
        
        // Recursively check children
        for (EObject child : start.eContents()) {
            EObject f = findInTree(child, name);
            if (f != null) return f;
        }
        return null;
    }

    // No hash-based search for simplicity

    private List<EObject> allObjects(Resource resource) {
        List<EObject> out = new ArrayList<>();
        for (EObject root : resource.getContents()) {
            collect(root, out);
        }
        return out;
    }

    private void collect(EObject o, List<EObject> out) {
        out.add(o);
        for (EObject c : o.eContents()) collect(c, out);
    }

    // ID-based methods removed as we now use name-based lookups

    private String getParam(io.vertx.ext.web.RoutingContext ctx, String key) {
        try {
            java.util.List<String> q = ctx.queryParam(key);
            if (q != null && !q.isEmpty()) return q.get(0);
        } catch (Exception ignored) {}
        try {
            JsonObject body = ctx.body().asJsonObject();
            if (body != null && body.containsKey(key)) return body.getString(key);
        } catch (Exception ignored) {}
        return null;
    }

    private EPackage loadMetamodelPackage(String metamodelPath) throws Exception {
        Resource metaRes = emfService.loadResource(metamodelPath);
        for (EObject root : metaRes.getContents()) {
            if (root instanceof EPackage pkg) {
                if ("Class".equals(pkg.getName())) {
                    return pkg;
                }
            }
        }
        for (EObject root : metaRes.getContents()) {
            if (root instanceof EPackage) return (EPackage) root;
        }
        return null;
    }

    /**
     * Finds an EClass by name in a package hierarchy.
     * Performs a deep search through all packages and subpackages.
     * 
     * @param pkg The root package to search in
     * @param name The name of the class to find
     * @return The found EClass or null if not found
     */
    private EClass findEClassDeep(EPackage pkg, String name) {
        // Direct lookup first (most efficient)
        EClassifier c = pkg.getEClassifier(name);
        if (c instanceof EClass) return (EClass) c;
        
        // Then try case-insensitive match
        for (EClassifier classifier : pkg.getEClassifiers()) {
            if (classifier instanceof EClass && classifier.getName().equalsIgnoreCase(name)) {
                return (EClass) classifier;
            }
        }
        
        // Recursively check subpackages
        for (EPackage sub : pkg.getESubpackages()) {
            EClass found = findEClassDeep(sub, name);
            if (found != null) return found;
        }
        
        return null;
    }
}
