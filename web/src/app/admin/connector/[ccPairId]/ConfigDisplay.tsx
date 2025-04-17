import { getNameFromPath } from "@/lib/fileUtils";
import { ValidSources } from "@/lib/types";
import { EditIcon } from "@/components/icons/icons";
import { FilePreviewModal } from "@/components/admin/connectors/FilePreviewModal";
import { useState } from "react";
import { ChevronUpIcon } from "lucide-react";
import { ChevronDownIcon, Eye, FileText, FileImage, FileCode } from "lucide-react";
import { FiFile } from "react-icons/fi";
import { Button } from "@/components/ui/button";

function convertObjectToString(obj: any): string | any {
  // Check if obj is an object and not an array or null
  if (typeof obj === "object" && obj !== null) {
    if (!Array.isArray(obj)) {
      return JSON.stringify(obj);
    } else {
      if (obj.length === 0) {
        return null;
      }
      return obj.map((item) => convertObjectToString(item)).join(", ");
    }
  }
  if (typeof obj === "boolean") {
    return obj.toString();
  }
  return obj;
}

function buildConfigEntries(
  obj: any,
  sourceType: ValidSources
): { [key: string]: string } {
  if (sourceType === ValidSources.File) {
    return obj.file_locations
      ? {
          file_names: obj.file_locations.map(getNameFromPath),
        }
      : {};
  } else if (sourceType === ValidSources.GoogleSites) {
    return {
      base_url: obj.base_url,
    };
  }
  return obj;
}

// Function to get file icon based on extension
function getFileIcon(fileName: string) {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  
  if (['pdf'].includes(ext)) {
    return <FiFile size={16} className="text-red-500" />;
  } else if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) {
    return <FileImage size={16} className="text-blue-500" />;
  } else if (['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'c', 'cpp', 'php', 'rb', 'go'].includes(ext)) {
    return <FileCode size={16} className="text-green-500" />;
  } else {
    return <FileText size={16} className="text-text-500" />;
  }
}

function ConfigItem({
  label,
  value,
  onEdit,
  sourceType,
  isFileItem = false,
  originalPaths = []
}: {
  label: string;
  value: any;
  onEdit?: () => void;
  sourceType?: ValidSources;
  isFileItem?: boolean;
  originalPaths?: string[];
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [previewFile, setPreviewFile] = useState<string | null>(null);
  const [previewFilePath, setPreviewFilePath] = useState<string | null>(null);
  const isExpandable = Array.isArray(value) && value.length > 5;

  // Find the original path for a given filename
  const findOriginalPath = (fileName: string): string | undefined => {
    if (!originalPaths || originalPaths.length === 0) return undefined;
    
    // Simple case: if the file name is the same as the path
    if (originalPaths.includes(fileName)) return fileName;
    
    // Otherwise try to find the path that ends with the filename
    return originalPaths.find(path => path.endsWith(`/${fileName}`) || path.endsWith(`\\${fileName}`));
  };

  const handlePreviewClick = (fileName: string) => {
    setPreviewFile(fileName);
    const originalPath = findOriginalPath(fileName);
    setPreviewFilePath(originalPath || null);
  };

  const renderValue = () => {
    if (Array.isArray(value)) {
      const displayedItems = isExpanded ? value : value.slice(0, 5);
      
      if (isFileItem) {
        return (
          <div className="overflow-x-auto">
            {displayedItems.map((item, index) => (
              <div
                key={index}
                className="mb-2 overflow-hidden flex items-center border border-border rounded p-1.5 pl-2 pr-1 hover:bg-background-800 dark:hover:bg-background-100 transition-colors"
              >
                <span className="mr-2 flex items-center">
                  {getFileIcon(item)}
                  <span className="ml-1.5 font-medium text-text-700">{item}</span>
                </span>
                <div className="ml-auto">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    className="p-1 h-7 hover:bg-background-800 dark:hover:bg-background-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePreviewClick(item);
                    }}
                  >
                    <Eye size={14} className="mr-1 text-text-600" />
                    <span className="text-xs text-text-600">Preview</span>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        );
      }
      
      return (
        <ul className="list-disc pl-4 overflow-x-auto">
          {displayedItems.map((item, index) => (
            <li
              key={index}
              className="mb-1 overflow-hidden text-ellipsis whitespace-nowrap flex items-center text-text-700"
            >
              <span className="mr-2">{convertObjectToString(item)}</span>
            </li>
          ))}
        </ul>
      );
    } else if (typeof value === "object" && value !== null) {
      return (
        <div className="overflow-x-auto">
          {Object.entries(value).map(([key, val]) => (
            <div key={key} className="mb-1 text-text-700">
              <span className="font-semibold">{key}:</span>{" "}
              {convertObjectToString(val)}
            </div>
          ))}
        </div>
      );
    }
    // TODO: figure out a nice way to display boolean values
    else if (typeof value === "boolean") {
      return value ? "True" : "False";
    }
    return convertObjectToString(value) || "-";
  };

  return (
    <li className="w-full py-4 px-1">
      <div className="flex flex-col w-full">
        <div className="flex items-center mb-2">
          <span className="text-sm font-medium text-text-700">{label}</span>
          {onEdit && (
            <button onClick={onEdit} className="ml-4">
              <EditIcon size={12} />
            </button>
          )}
        </div>
        
        <div className="w-full">
          {renderValue()}

          {isExpandable && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="mt-2 text-sm text-text-600 hover:text-text-800 flex items-center"
            >
              {isExpanded ? (
                <>
                  <ChevronUpIcon className="h-4 w-4 mr-1" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDownIcon className="h-4 w-4 mr-1" />
                  Show all ({value.length} items)
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* File Preview Modal */}
      {previewFile && (
        <FilePreviewModal
          fileName={previewFile}
          filePath={previewFilePath || undefined}
          isOpen={!!previewFile}
          onClose={() => {
            setPreviewFile(null);
            setPreviewFilePath(null);
          }}
        />
      )}
    </li>
  );
}

export function AdvancedConfigDisplay({
  pruneFreq,
  refreshFreq,
  indexingStart,
  onRefreshEdit,
  onPruningEdit,
}: {
  pruneFreq: number | null;
  refreshFreq: number | null;
  indexingStart: Date | null;
  onRefreshEdit: () => void;
  onPruningEdit: () => void;
}) {
  const formatRefreshFrequency = (seconds: number | null): string => {
    if (seconds === null) return "-";
    const minutes = Math.round(seconds / 60);
    return `${minutes} minute${minutes !== 1 ? "s" : ""}`;
  };
  const formatPruneFrequency = (seconds: number | null): string => {
    if (seconds === null) return "-";
    const days = Math.round(seconds / (60 * 60 * 24));
    return `${days} day${days !== 1 ? "s" : ""}`;
  };

  const formatDate = (date: Date | null): string => {
    if (date === null) return "-";
    return date.toLocaleString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  };

  return (
    <div>
      <ul className="w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        {pruneFreq !== null && (
          <ConfigItem
            label="Pruning Frequency"
            value={formatPruneFrequency(pruneFreq)}
            onEdit={onPruningEdit}
          />
        )}
        {refreshFreq && (
          <ConfigItem
            label="Refresh Frequency"
            value={formatRefreshFrequency(refreshFreq)}
            onEdit={onRefreshEdit}
          />
        )}
        {indexingStart && (
          <ConfigItem
            label="Indexing Start"
            value={formatDate(indexingStart)}
          />
        )}
      </ul>
    </div>
  );
}

export function ConfigDisplay({
  connectorSpecificConfig,
  sourceType,
  onEdit,
}: {
  connectorSpecificConfig: any;
  sourceType: ValidSources;
  onEdit?: (key: string) => void;
}) {
  const configEntries = Object.entries(
    buildConfigEntries(connectorSpecificConfig, sourceType)
  );
  if (!configEntries.length) {
    return null;
  }

  const originalPaths = sourceType === ValidSources.File 
    ? connectorSpecificConfig.file_locations || []
    : [];

  return (
    <ul className="w-full divide-y divide-background-200 dark:divide-background-700">
      {configEntries.map(([key, value]) => {
        console.log("key", key);
        console.log("value", value);
        return (
          <ConfigItem
            key={key}
            label={key}
            value={value}
            onEdit={onEdit ? () => onEdit(key) : undefined}
            sourceType={sourceType}
            isFileItem={key === "file_names"}
            originalPaths={originalPaths}
          />
        );
      })}
    </ul>
  );
}
