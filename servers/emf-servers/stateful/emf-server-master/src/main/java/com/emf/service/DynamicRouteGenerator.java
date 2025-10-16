package com.emf.service;

import org.eclipse.emf.ecore.*;
import org.eclipse.emf.ecore.resource.Resource;
import io.vertx.ext.web.Router;
import io.vertx.ext.web.FileUpload;
import io.vertx.core.json.JsonObject;
import java.util.*;

public class DynamicRouteGenerator {
    private final EmfService emfService;
    private final SessionManager sessionManager;

    public DynamicRouteGenerator(EmfService emfService, SessionManager sessionManager) {
        this.emfService = emfService;
        this.sessionManager = sessionManager;
    }

    public void generateRoutes(Router router) {

        //Routes from the old service

        router.post("/metamodel/name").handler(ctx -> {
           
        });

        router.post("/model/conformant").handler(ctx -> {
           
        });

        // Add new dynamic routes
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
                response.put("routes", generateOpenAPISpec(metamodelResource));
                ctx.json(response);
            } catch (Exception e) {
                ctx.response().setStatusCode(400).end("Error: " + e.getMessage());
            }
        });

        
        // Dynamic CRUD routes for each EClass and EStructuralFeature
        router.post("/metamodel/:sessionId/:eClassName").handler(ctx -> {
            String sessionId = ctx.pathParam("sessionId");
            String eClassName = ctx.pathParam("eClassName");
            try {
                                EPackage ePackage = sessionManager.getMetamodel(sessionId);
                EClass eClass = (EClass) ePackage.getEClassifier(eClassName);
                if (eClass == null) {
                    ctx.response().setStatusCode(404).end("EClass not found: " + eClassName);
                    return;
                }
                
                // Create new instance
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
                // Check if the object is of the correct class type
                if (!target.eClass().getName().equals(eClassName)) {
                    ctx.response().setStatusCode(400).end("Eclass is not found: " + eClassName);
                    return;
                }
                EStructuralFeature feature = target.eClass().getEStructuralFeature(featureName);
                if (feature == null) {
                    ctx.response().setStatusCode(404).end("Feature not found: " + featureName);
                    return;
                }
                JsonObject body =  ctx.body().asJsonObject();
                Object value = body.getValue("value");

                //d'= feature types
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

                                //Inject instance class if missing
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
                                            // Fallback: treat it as String if nothing matches
                                            dataType.setInstanceClass(String.class);
                                            break;
                                    }
                                }

                                //call EMF's factory
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
                
                // Check if the object is of the correct class type
                if (!target.eClass().getName().equals(eClassName)) {
                    ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName);
                    return;
                }
                
                // Remove from resource
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
                
                // Check if the object is of the correct class type
                if (!target.eClass().getName().equals(eClassName)) {
                    ctx.response().setStatusCode(400).end("Object is not of type: " + eClassName);
                    return;
                }
                
                EStructuralFeature feature = target.eClass().getEStructuralFeature(featureName);
                if (feature == null) {
                    ctx.response().setStatusCode(404).end("Feature not found: " + featureName);
                    return;
                }
                
                // Clear the feature value (set to null or empty collection)
                if (feature.isMany()) {
                    ((List<?>)target.eGet(feature)).clear();
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

    

    private Map<String, Object> generateOpenAPISpec(Resource metamodelResource) {
    Map<String, Object> openAPI = new HashMap<>();
    openAPI.put("openapi", "3.0.0");
    openAPI.put("info", Map.of(
        "title", "EMF Dynamic API",
        "version", "1.0.0"
    ));

    Map<String, Object> paths = new HashMap<>();

    for (EObject root : metamodelResource.getContents()) {
        if (root instanceof EPackage) {
            EPackage ePackage = (EPackage) root;

            boolean hasClasses = ePackage.getEClassifiers().stream().anyMatch(c -> c instanceof EClass);
            if (!hasClasses) continue;

            for (EClassifier classifier : ePackage.getEClassifiers()) {
                if (classifier instanceof EClass eClass) {
                    String className = eClass.getName();
                    boolean isAbstract = eClass.isAbstract();

                    // Skip creating POST endpoints for abstract classes
                    if (!isAbstract) {
                        // POST path for creating instances
                        paths.put("/metamodel/{sessionId}/" + className, Map.of(
                            "post", Map.of(
                                "summary", "Create new " + className,
                                "parameters", List.of(
                                    Map.of(
                                        "name", "sessionId",
                                        "in", "path",
                                        "required", true,
                                        "schema", Map.of("type", "string")
                                    )
                                ),
                                "requestBody", Map.of(
                                    "description", "Data to create a new instance (optional for now)",
                                    "required", false,
                                    "content", Map.of(
                                        "application/json", Map.of(
                                            "schema", Map.of("type", "object")
                                        )
                                    )
                                ),
                                "responses", Map.of(
                                    "200", Map.of(
                                        "description", "Instance created",
                                        "content", Map.of(
                                            "application/json", Map.of(
                                                "schema", Map.of("type", "object")
                                            )
                                        )
                                    )
                                )
                            )
                        ));
                    }

                    // PUT paths for each structural feature, it should be double checked 
                    for (EStructuralFeature feature : eClass.getEAllStructuralFeatures()) {
                        String featureName = feature.getName();
                        String path = "/metamodel/{sessionId}/" + className + "/{id}/" + featureName;

                        // Add information about containment for references
                        boolean isContainment = false;
                        if (feature instanceof EReference) {
                            EReference reference = (EReference) feature;
                            isContainment = reference.isContainment();
                        }

                        Map<String, Object> schemaInfo = new HashMap<>();
                        schemaInfo.put("type", "object");
                        schemaInfo.put("properties", Map.of(
                            "value", Map.of("type", "string")
                        ));
                        
                        if (feature instanceof EReference) {
                            schemaInfo.put("x-containment", isContainment);
                        }

                        paths.put(path, Map.of(
                            "put", Map.of(
                                "summary", "Update " + featureName + " of " + className,
                                "parameters", List.of(
                                    Map.of(
                                        "name", "sessionId",
                                        "in", "path",
                                        "required", true,
                                        "schema", Map.of("type", "string")
                                    ),
                                    Map.of(
                                        "name", "id",
                                        "in", "path",
                                        "required", true,
                                        "schema", Map.of("type", "string")
                                    )
                                ),
                                "requestBody", Map.of(
                                    "description", "Value to update the feature",
                                    "required", true,
                                    "content", Map.of(
                                        "application/json", Map.of(
                                            "schema", schemaInfo,
                                            "required", List.of("value")
                                        )
                                    )
                                ),
                                "responses", Map.of(
                                    "200", Map.of(
                                        "description", "Feature updated",
                                        "content", Map.of(
                                            "application/json", Map.of(
                                                "schema", Map.of("type", "object")
                                            )
                                        )
                                    )
                                )
                            )
                        ));
                    }
                }
            }
        }
    }

    openAPI.put("paths", paths);
    return openAPI;
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