package com.emf.service;

import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.*;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;
import com.emf.model.SearchResult;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class EmfService {
    private final ResourceSet resourceSet;

    public EmfService() {
        this.resourceSet = new ResourceSetImpl();
        Resource.Factory.Registry.INSTANCE.getExtensionToFactoryMap()
            .put("ecore", new XMIResourceFactoryImpl());
        Resource.Factory.Registry.INSTANCE.getExtensionToFactoryMap()
            .put("xmi", new XMIResourceFactoryImpl());
    }

    public String getMetamodelName(String filePath) throws Exception {
        Resource resource = loadResource(filePath);
        if (resource.getContents().isEmpty()) {
            throw new Exception("Empty metamodel file");
        }
        EObject root = resource.getContents().get(0);
        if (root instanceof EPackage) {
            return ((EPackage) root).getName();
        }
        throw new Exception("Invalid metamodel file");
    }

    public boolean checkModelConformance(String modelPath, String metamodelPath) throws Exception {
        Resource metamodelResource = loadResource(metamodelPath);
        Resource modelResource = loadResource(modelPath);
        
        if (metamodelResource.getContents().isEmpty() || modelResource.getContents().isEmpty()) {
            System.out.println("Empty resource found");
            return false;
        }

        // Collect all EPackages from the metamodel resource
        List<EPackage> allPackages = new ArrayList<>();
        for (EObject obj : metamodelResource.getContents()) {
            if (obj instanceof EPackage) {
                allPackages.add((EPackage) obj);
                System.out.println("Found package: " + ((EPackage) obj).getName());
            }
        }
        // Also collect nested packages
        List<EPackage> nestedPackages = new ArrayList<>();
        for (EPackage pkg : allPackages) {
            collectNestedPackages(pkg, nestedPackages);
        }
        allPackages.addAll(nestedPackages);

        // Create a map of all EClasses in the metamodel for quick lookup
        Map<String, EClass> metamodelClasses = new HashMap<>();
        for (EPackage pkg : allPackages) {
            for (EClassifier classifier : pkg.getEClassifiers()) {
                if (classifier instanceof EClass) {
                    metamodelClasses.put(classifier.getName(), (EClass) classifier);
                    System.out.println("Found class: " + classifier.getName());
                }
            }
        }

        // Check conformance of all elements in the model
        for (EObject root : modelResource.getContents()) {
            System.out.println("Checking root element: " + root.eClass().getName());
            if (!checkElementConformance(root, metamodelClasses)) {
                return false;
            }
        }

        return true;
    }

    private boolean checkElementConformance(EObject element, Map<String, EClass> metamodelClasses) {
        // Check if element's class is defined in metamodel
        EClass elementClass = element.eClass();
        EClass metamodelClass = metamodelClasses.get(elementClass.getName());
        
        if (metamodelClass == null) {
            System.out.println("Element class not found in metamodel: " + elementClass.getName());
            return false;
        }

        System.out.println("Checking element of class: " + elementClass.getName());

        // Check attributes - only verify they exist, not their types
        for (EAttribute attribute : elementClass.getEAllAttributes()) {
            Object value = element.eGet(attribute);
            if (value != null) {
                System.out.println("Found attribute: " + attribute.getName() + " in " + elementClass.getName());
            }
        }

        // Check references - only verify they exist, not their types or multiplicities
        for (EReference reference : elementClass.getEAllReferences()) {
            Object value = element.eGet(reference);
            if (value != null) {
                System.out.println("Found reference: " + reference.getName() + " in " + elementClass.getName());
            }
        }

        // Recursively check all contained elements
        for (EObject child : element.eContents()) {
            if (!checkElementConformance(child, metamodelClasses)) {
                return false;
            }
        }

        return true;
    }

    // Helper method to collect nested packages recursively
    private void collectNestedPackages(EPackage pkg, List<EPackage> result) {
        for (EPackage nested : pkg.getESubpackages()) {
            result.add(nested);
            collectNestedPackages(nested, result);
        }
    }

    public void addAttribute(String filePath, String className, String attributeName, String attributeType) throws Exception {
        Resource resource = loadResource(filePath);
        if (resource.getContents().isEmpty()) {
            throw new Exception("Empty model file");
        }

        EObject root = resource.getContents().get(0);
        if (root instanceof EPackage) {
            EPackage ePackage = (EPackage) root;
            EClassifier eClassifier = ePackage.getEClassifier(className);
            
            if (eClassifier instanceof EClass) {
                EClass eClass = (EClass) eClassifier;
                EAttribute attribute = EcoreFactory.eINSTANCE.createEAttribute();
                attribute.setName(attributeName);
                attribute.setEType(getEDataType(attributeType));
                eClass.getEStructuralFeatures().add(attribute);
                resource.save(null);
            } else {
                throw new Exception("Class not found: " + className);
            }
        } else {
            throw new Exception("Invalid model file");
        }
    }

    public void deleteAttribute(String filePath, String className, String attributeName) throws Exception {
        Resource resource = loadResource(filePath);
        if (resource.getContents().isEmpty()) {
            throw new Exception("Empty model file");
        }

        EObject root = resource.getContents().get(0);
        if (root instanceof EPackage) {
            EPackage ePackage = (EPackage) root;
            EClassifier eClassifier = ePackage.getEClassifier(className);
            
            if (eClassifier instanceof EClass) {
                EClass eClass = (EClass) eClassifier;
                EStructuralFeature feature = eClass.getEStructuralFeature(attributeName);
                if (feature != null) {
                    eClass.getEStructuralFeatures().remove(feature);
                    resource.save(null);
                } else {
                    throw new Exception("Attribute not found: " + attributeName);
                }
            } else {
                throw new Exception("Class not found: " + className);
            }
        } else {
            throw new Exception("Invalid model file");
        }
    }

    public List<SearchResult> searchInModel(String filePath, String searchTerm) throws Exception {
        Resource resource = loadResource(filePath);
        List<SearchResult> results = new ArrayList<>();
        
        if (!resource.getContents().isEmpty()) {
            EObject root = resource.getContents().get(0);
            searchInEObject(root, searchTerm, results);
        }
        
        return results;
    }

    private void searchInEObject(EObject object, String searchTerm, List<SearchResult> results) {
        EStructuralFeature nameFeature = object.eClass().getEStructuralFeature("name");
        if (nameFeature != null) {
            Object nameValue = object.eGet(nameFeature);
            if (nameValue instanceof String && ((String) nameValue).contains(searchTerm)) {
                results.add(new SearchResult(
                    object.eClass().getName(),
                    "name",
                    (String) nameValue
                ));
            }
        }

        for (EAttribute attribute : object.eClass().getEAllAttributes()) {
            Object value = object.eGet(attribute);
            if (value instanceof String && ((String) value).contains(searchTerm)) {
                results.add(new SearchResult(
                    object.eClass().getName(),
                    attribute.getName(),
                    (String) value
                ));
            }
        }

        for (EObject child : object.eContents()) {
            searchInEObject(child, searchTerm, results);
        }
    }

    public Resource loadResource(String filePath) throws Exception {
        File file = new File(filePath);
        if (!file.exists()) {
            throw new Exception("File not found: " + filePath);
        }

        // Create a temporary file with .ecore extension
        File tempFile = File.createTempFile("temp", ".ecore");
        tempFile.deleteOnExit();
        
        // Copy the content of the uploaded file to the temporary file
        java.nio.file.Files.copy(file.toPath(), tempFile.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);

        URI uri = URI.createFileURI(tempFile.getAbsolutePath());
        Resource resource = resourceSet.getResource(uri, true);
        if (resource == null) {
            resource = resourceSet.createResource(uri);
            if (resource == null) {
                throw new Exception("Failed to create resource for: " + filePath);
            }
        }
        try {
            resource.load(null);
            // Register all packages found in the resource
            for (EObject root : resource.getContents()) {
                if (root instanceof EPackage) {
                    EPackage ePackage = (EPackage) root;
                    // If the package has no URI, set it to the package name
                    if (ePackage.getNsURI() == null || ePackage.getNsURI().isEmpty()) {
                        ePackage.setNsURI(ePackage.getName());
                    }
                    // Register the package
                    EPackage.Registry.INSTANCE.put(ePackage.getNsURI(), ePackage);
                }
            }
        } catch (Exception e) {
            throw new Exception("Failed to load resource: " + e.getMessage());
        }
        return resource;
    }

    private EDataType getEDataType(String type) {
        switch (type.toLowerCase()) {
            case "string":
                return EcorePackage.eINSTANCE.getEString();
            case "int":
            case "integer":
                return EcorePackage.eINSTANCE.getEInt();
            case "boolean":
                return EcorePackage.eINSTANCE.getEBoolean();
            case "float":
                return EcorePackage.eINSTANCE.getEFloat();
            case "double":
                return EcorePackage.eINSTANCE.getEDouble();
            default:
                return EcorePackage.eINSTANCE.getEString();
        }
    }

    public Resource createEmptyResource() {
        Resource resource = resourceSet.createResource(URI.createURI("temp.xmi"));
        return resource;
    }
} 