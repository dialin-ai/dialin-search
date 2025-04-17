import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";
import { FiDownload, FiExternalLink } from "react-icons/fi";

interface FilePreviewModalProps {
  fileName: string;
  filePath?: string;
  documentId?: string;
  isOpen: boolean;
  onClose: () => void;
  // For use with example data
  mockOriginalContent?: string;
  mockIndexedContent?: string;
}

interface IndexedContent {
  content: string;
  semantic_identifier: string;
  source_type: string;
  metadata: Record<string, any>;
  chunk_count: number;
}

export function FilePreviewModal({
  fileName,
  filePath,
  documentId,
  isOpen,
  onClose,
  mockOriginalContent,
  mockIndexedContent,
}: FilePreviewModalProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [originalContentLoading, setOriginalContentLoading] = useState(true);
  const [indexedContentLoading, setIndexedContentLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("original");
  const [originalContent, setOriginalContent] = useState<string>("");
  const [indexedContent, setIndexedContent] = useState<string>("");
  const [fileUrl, setFileUrl] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Get file extension
  const fileExt = fileName.split('.').pop()?.toLowerCase() || '';
  const isPdf = fileExt === 'pdf';
  const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(fileExt);
  const isTextFile = ['txt', 'md', 'markdown', 'json', 'csv', 'xml', 'html'].includes(fileExt);
  const isDocument = ['docx', 'doc', 'rtf'].includes(fileExt);
  const isSpreadsheet = ['xlsx', 'xls', 'csv'].includes(fileExt);
  const isCode = ['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'c', 'cpp', 'rb', 'php'].includes(fileExt);

  // Fetch original file content
  const fetchOriginalContent = async () => {
    if (mockOriginalContent) {
      setOriginalContent(mockOriginalContent);
      setOriginalContentLoading(false);
      return;
    }

    try {
      setOriginalContentLoading(true);
      
      // Determine file ID from either filePath or fileName
      const fileId = filePath || fileName;
      
      // Use existing file content API
      const response = await fetch(`/api/chat/file/${encodeURIComponent(fileId)}`, {
        method: "GET",
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load file: ${response.statusText}`);
      }
      
      // For binary files like PDFs, create a URL for the iframe
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setFileUrl(url);
      
      // For text files, also set the content
      if (isTextFile || isCode || isSpreadsheet) {
        const text = await blob.text();
        setOriginalContent(text);
      }
      
      setOriginalContentLoading(false);
    } catch (error) {
      console.error("Error fetching original file:", error);
      setError("Failed to load original file content.");
      setOriginalContentLoading(false);
    }
  };

  // Fetch indexed content
  const fetchIndexedContent = async () => {
    if (mockIndexedContent) {
      setIndexedContent(mockIndexedContent);
      setIndexedContentLoading(false);
      return;
    }

    try {
      setIndexedContentLoading(true);
      
      // Use either provided document ID or derive it from file path
      const docId = documentId || (filePath ? getDocumentIdFromPath(filePath) : "");
      
      if (!docId) {
        throw new Error("No document ID available for indexed content");
      }
      
      // Call our new API endpoint
      const response = await fetch(`/api/document/indexed-content?document_id=${encodeURIComponent(docId)}`, {
        method: "GET",
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load indexed content: ${response.statusText}`);
      }
      
      const data: IndexedContent = await response.json();
      setIndexedContent(data.content);
      setIndexedContentLoading(false);
    } catch (error) {
      console.error("Error fetching indexed content:", error);
      setIndexedContent("Indexed content is not available for this file.");
      setIndexedContentLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      setError(null);
      
      // Fetch both original and indexed content
      Promise.all([
        fetchOriginalContent(),
        fetchIndexedContent()
      ]).finally(() => {
        setIsLoading(false);
      });
    }
  }, [isOpen, fileName, filePath, documentId]);

  // Download handler
  const handleDownload = () => {
    if (fileUrl) {
      const link = document.createElement("a");
      link.href = fileUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  // Generate example content for use when real data isn't available
  const generateMockContent = (fileName: string, isOriginal: boolean): string => {
    const baseName = fileName.split('.')[0];
    
    if (isCode) {
      return isOriginal 
        ? `// ${baseName}.${fileExt}
import React from 'react';
import { Button } from './components/Button';

/**
 * Example component
 */
function ${baseName.charAt(0).toUpperCase() + baseName.slice(1)}() {
  const [count, setCount] = React.useState(0);
  
  return (
    <div className="container">
      <h1>Counter: {count}</h1>
      <Button onClick={() => setCount(count + 1)}>
        Increment
      </Button>
    </div>
  );
}

export default ${baseName.charAt(0).toUpperCase() + baseName.slice(1)};`
        : `This document contains:
- A React component named ${baseName.charAt(0).toUpperCase() + baseName.slice(1)}
- State management for a counter
- A Button component
- An increment function

This appears to be a simple counter application interface with increment functionality.`;
    }
    
    if (isTextFile) {
      return isOriginal
        ? `# ${baseName}

## Introduction
This is a sample document that demonstrates the capabilities of our system.

## Features
- Feature 1: Description of feature 1
- Feature 2: Description of feature 2
- Feature 3: Description of feature 3

## Conclusion
Thank you for using our product.`
        : `This document contains:
- A title: ${baseName}
- An introduction section
- A features section with 3 main features
- A conclusion

The document appears to be a product documentation explaining features of a system.`;
    }
    
    if (isSpreadsheet) {
      return isOriginal
        ? `ID,Name,Department,Salary
1,John Doe,Engineering,120000
2,Jane Smith,Marketing,95000
3,Robert Johnson,Sales,110000
4,Sarah Williams,HR,85000
5,Michael Brown,Engineering,125000`
        : `This spreadsheet contains employee data with the following columns:
- ID
- Name
- Department
- Salary

The data shows 5 employees across Engineering, Marketing, Sales, and HR departments with salaries ranging from $85,000 to $125,000.`;
    }
    
    // Default content for other file types
    return isOriginal
      ? `This is the original content for ${fileName}.\n\nExample data for demonstration purposes.`
      : `This is the indexed content extracted from ${fileName}.\n\nThe system has processed this document and extracted relevant information for search and retrieval.`;
  };

  // Render file content based on file type
  const renderFileContent = (isOriginal: boolean) => {
    // Show loading state
    if (isLoading || (isOriginal ? originalContentLoading : indexedContentLoading)) {
      return (
        <div className="flex justify-center items-center h-96">
          <Spinner />
        </div>
      );
    }

    // Show error if present
    if (error) {
      return (
        <div className="flex justify-center items-center h-96">
          <div className="text-center text-red-500">
            <p>{error}</p>
          </div>
        </div>
      );
    }

    if (isOriginal) {
      // Handle different original file types
      if (isPdf && fileUrl) {
        return (
          <div className="h-96 flex flex-col">
            <iframe 
              src={`${fileUrl}#toolbar=0`}
              className="w-full h-full border-none" 
              title="PDF Viewer"
            />
          </div>
        );
      } else if (isImage && fileUrl) {
        return (
          <div className="h-96 flex items-center justify-center">
            <div className="p-4 rounded border border-border">
              <img 
                src={fileUrl} 
                alt={fileName} 
                className="max-h-80 max-w-full object-contain"
              />
            </div>
          </div>
        );
      } else if (isDocument && !originalContent) {
        return (
          <div className="bg-background-800 dark:bg-background h-96 flex items-center justify-center">
            <div className="text-center">
              <div className="text-text-500 mb-4">Document Preview</div>
              <Button onClick={handleDownload}>
                <FiDownload className="mr-2" />
                Download Document
              </Button>
            </div>
          </div>
        );
      }
    }

    // Default display for text content (both original text files and indexed content)
    const displayContent = isOriginal ? originalContent : indexedContent;

    return (
      <pre className={`bg-background-800 dark:bg-background border border-border p-4 rounded h-96 overflow-auto ${isCode ? 'whitespace-pre' : 'whitespace-pre-wrap'}`}>
        {displayContent || (isOriginal ? "No original content available" : "No indexed content available")}
      </pre>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl w-full">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold flex items-center">
            <span className="truncate max-w-md">{fileName}</span>
          </DialogTitle>
        </DialogHeader>

        {renderFileContent(true)}

        <div className="flex justify-end mt-4">
          {fileUrl && (
            <Button variant="outline" onClick={handleDownload} className="mr-2">
              <FiDownload className="mr-2" />
              Download Original
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
} 