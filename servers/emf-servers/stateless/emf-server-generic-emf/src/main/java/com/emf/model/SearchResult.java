package com.emf.model;

public class SearchResult {
    private String className;
    private String attributeName;
    private String value;

    public SearchResult(String className, String attributeName, String value) {
        this.className = className;
        this.attributeName = attributeName;
        this.value = value;
    }

    public String getClassName() {
        return className;
    }

    public String getAttributeName() {
        return attributeName;
    }

    public String getValue() {
        return value;
    }
} 