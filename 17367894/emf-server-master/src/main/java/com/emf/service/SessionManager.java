package com.emf.service;

import org.eclipse.emf.ecore.*;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.UUID;
import java.io.File;


public class SessionManager {
    private static final Map<String, Resource> sessions = new ConcurrentHashMap<>();
    private static final Map<String, EPackage> metamodels = new ConcurrentHashMap<>();
    private static final String UPLOADS_DIR = "uploads";

    static {
        // Register the XMI resource factory for both ecore and xmi extensions
        Resource.Factory.Registry.INSTANCE.getExtensionToFactoryMap()
            .put("ecore", new XMIResourceFactoryImpl());
        Resource.Factory.Registry.INSTANCE.getExtensionToFactoryMap()
            .put("xmi", new XMIResourceFactoryImpl());
    }

    public String createSession(Resource metamodelResource) {
        String sessionId = UUID.randomUUID().toString();
        // Prefer the first EPackage that defines at least one EClass (works for multi-root .ecore)
        EPackage ePackage = null;
        for (EObject root : metamodelResource.getContents()) {
            if (root instanceof EPackage) {
                EPackage candidate = (EPackage) root;
                boolean hasEClass = candidate.getEClassifiers().stream().anyMatch(c -> c instanceof EClass);
                if (hasEClass) {
                    ePackage = candidate;
                    break;
                }
                if (ePackage == null) {
                    // fallback to the first package if none has classes
                    ePackage = candidate;
                }
            }
        }
        if (ePackage == null) {
            throw new IllegalArgumentException("No EPackage found in metamodel resource");
        }
        metamodels.put(sessionId, ePackage);
        
        if (ePackage.getNsURI() == null || ePackage.getNsURI().isEmpty()) {
            ePackage.setNsURI(ePackage.getName());
        }
        EPackage.Registry.INSTANCE.put(ePackage.getNsURI(), ePackage);
        

        Resource modelResource = metamodelResource.getResourceSet().createResource(
            URI.createFileURI(UPLOADS_DIR + "/model_" + sessionId + ".xmi")
        );
        
  
        modelResource.getResourceSet().getPackageRegistry().put(ePackage.getNsURI(), ePackage);

        
        sessions.put(sessionId, modelResource);
        return sessionId;
    }

    public EPackage getMetamodel(String sessionId) {
        return metamodels.get(sessionId);
    }

    public Resource getSessionResource(String sessionId) {
        return sessions.get(sessionId);
    }

    public void setSessionResource(String sessionId, Resource resource) {
        // Save the resource to disk
        try {
            resource.setURI(URI.createFileURI(UPLOADS_DIR + "/model_" + sessionId + ".xmi"));
            resource.save(null);
        } catch (Exception e) {
            e.printStackTrace();
        }
        sessions.put(sessionId, resource);
    }

    public void removeSession(String sessionId) {
        Resource resource = sessions.get(sessionId);
        if (resource != null) {
            // Delete the model file
            File modelFile = new File(UPLOADS_DIR + "/model_" + sessionId + ".xmi");
            if (modelFile.exists()) {
                modelFile.delete();
            }
        }
        sessions.remove(sessionId);
        metamodels.remove(sessionId);
    }
} 